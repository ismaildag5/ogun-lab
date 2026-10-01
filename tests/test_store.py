import json
import sqlite3
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import store
from notifications import dispatch_once,acknowledge

class Sender:
    def __init__(self,configured=True,error=None):self.ready=configured;self.error=error;self.calls=[]
    def configured(self):return self.ready
    def send(self,token,payload):
        self.calls.append((token,payload))
        if self.error:raise self.error
        return 'test-provider-message-id'

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3'
        store.initialize(self.path);self.db=store.connect(self.path)
        pair=store.pair(self.db,store.create_pair_code(self.db)['code'],'Test phone')
        self.device=pair['device_id'];self.secret=pair['access_token'];self.mid='m0201'
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def latest(self):return self.db.execute('SELECT * FROM prices WHERE meal_id=? ORDER BY id DESC LIMIT 1',(self.mid,)).fetchone()
    def change(self,price,**extra):
        body={'meal_id':self.mid,'price_minor':price,'version':self.latest()['id'],'request_id':str(uuid.uuid4())};body.update(extra)
        return store.change_price(self.db,body)
    def watch(self,mode='any',target=None,device=None):store.save_watch(self.db,device or self.device,{'meal_id':self.mid,'mode':mode,'target_minor':target})
    def notifications(self):return list(self.db.execute('SELECT * FROM notifications ORDER BY created_at'))
    def token(self):store.register_token(self.db,self.device,'test-token-not-a-real-device-token')
    def test_seed_exact_count_and_idempotent(self):
        store.initialize(self.path)
        self.assertEqual(self.db.execute('SELECT count(*) FROM meals').fetchone()[0],100)
        self.assertEqual(self.db.execute('SELECT count(DISTINCT branch) FROM meals').fetchone()[0],10)
        self.assertEqual(self.db.execute('SELECT count(*) FROM prices').fetchone()[0],100)
    def test_price_history_is_append_only(self):
        self.change(14000)
        values=[r[0] for r in self.db.execute('SELECT price_minor FROM prices WHERE meal_id=? ORDER BY id',(self.mid,))]
        self.assertEqual(values,[18000,14000])
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('UPDATE prices SET price_minor=1')
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute('DELETE FROM prices')
    def test_any_drop_queues_but_same_and_increase_do_not(self):
        self.watch();self.change(18000);self.change(20000);self.assertFalse(self.notifications())
        result=self.change(14000);self.assertEqual(result['queued'],1);self.assertEqual(len(self.notifications()),1)
    def test_target_only_on_crossing(self):
        self.watch('target',14000);self.change(15000);self.assertFalse(self.notifications())
        self.change(14000);self.assertEqual(len(self.notifications()),1)
        self.change(13000);self.assertEqual(len(self.notifications()),1)
        self.assertEqual(self.notifications()[0]['status'],'pending')
    def test_new_watch_below_target_does_not_fake_a_drop(self):
        self.watch('target',20000);self.change(17000);self.assertFalse(self.notifications())
    def test_big_threshold_and_price_spike(self):
        self.watch('big');self.change(30000);self.change(18000);self.assertFalse(self.notifications())
        self.change(14000);self.assertFalse(self.notifications()) # 22.2% vs original 180
        self.change(10000);self.assertEqual(len(self.notifications()),1) # 140 -> 100 is 28.6%, 40 TL
    def test_repeat_request_does_not_duplicate_event_or_alert(self):
        self.watch();req=str(uuid.uuid4());self.change(14000,request_id=req)
        result=self.change(14000,request_id=req);self.assertTrue(result['repeated']);self.assertEqual(len(self.notifications()),1)
        with self.assertRaises(store.Conflict):self.change(13000,request_id=req)
    def test_stale_version_conflict_does_not_write(self):
        version=self.latest()['id'];self.change(17000)
        with self.assertRaises(store.Conflict):self.change(14000,version=version)
        self.assertEqual(self.latest()['price_minor'],17000)
    def test_invalid_money_never_writes(self):
        before=self.latest()['id']
        for value in (0,-1,True,1.5,'120',10000001,None):
            with self.assertRaises(ValueError):self.change(value)
        self.assertEqual(before,self.latest()['id'])
    def test_pair_one_time_and_secret_is_hashed(self):
        code=store.create_pair_code(self.db)['code'];store.pair(self.db,code,'Other phone')
        with self.assertRaises(ValueError):store.pair(self.db,code,'Third phone')
        self.assertEqual(store.authenticate(self.db,self.secret),self.device)
        self.assertNotEqual(self.db.execute('SELECT secret_hash FROM devices WHERE id=?',(self.device,)).fetchone()[0],self.secret)
        self.assertIsNone(store.authenticate(self.db,'wrong'))
    def test_expired_pair_code_rejected(self):
        code=store.create_pair_code(self.db)['code'];self.db.execute('UPDATE pair_codes SET expires_at=0')
        with self.assertRaises(ValueError):store.pair(self.db,code,'Phone')
    def test_watch_is_per_device_and_branch(self):
        self.watch();self.assertIsNone(next(x for x in store.catalogue(self.db)['items'] if x['id']==self.mid)['watch'])
        self.assertEqual(next(x for x in store.catalogue(self.db,self.device)['items'] if x['id']==self.mid)['watch']['mode'],'any')
    def test_remove_watch_cancels_unsent_alert(self):
        self.watch();self.change(14000);store.save_watch(self.db,self.device,{'meal_id':self.mid,'remove':True})
        self.assertEqual(self.notifications()[0]['status'],'cancelled')
        self.change(12000);self.assertEqual(len(self.notifications()),1)
    def test_new_price_supersedes_pending_alert(self):
        self.watch();self.change(14000);self.change(20000)
        self.assertEqual(self.notifications()[0]['status'],'superseded')
    def test_queue_survives_restart_and_fcm_missing_is_not_success(self):
        self.watch();self.change(14000);self.token();self.db.close();self.db=store.connect(self.path)
        sender=Sender(False);self.assertFalse(dispatch_once(self.db,sender));self.assertFalse(sender.calls)
        self.assertEqual(self.notifications()[0]['status'],'pending')
    def test_provider_acceptance_and_device_receipt_are_different(self):
        self.watch();self.change(14000);self.token();sender=Sender()
        self.assertTrue(dispatch_once(self.db,sender));self.assertFalse(dispatch_once(self.db,sender))
        row=self.notifications()[0];self.assertEqual(row['status'],'sent');self.assertIsNone(row['received_at'])
        self.assertFalse(acknowledge(self.db,'preview',row['id']))
        self.assertTrue(acknowledge(self.db,self.device,row['id']))
        self.assertEqual(self.notifications()[0]['status'],'received')
    def test_transient_failure_retries_same_notification(self):
        self.watch();self.change(14000);self.token();now=time.time();sender=Sender(error=TimeoutError())
        dispatch_once(self.db,sender,now);row=self.notifications()[0];self.assertEqual(row['status'],'pending')
        self.assertFalse(dispatch_once(self.db,sender,now+1));sender.error=None;dispatch_once(self.db,sender,now+5)
        self.assertEqual(sender.calls[0][1]['notification_id'],sender.calls[1][1]['notification_id'])
        self.assertEqual(self.notifications()[0]['attempts'],2)
    def test_expiry_does_not_send_late_discount(self):
        self.watch();self.change(14000);self.token();sender=Sender()
        dispatch_once(self.db,sender,time.time()+901);self.assertFalse(sender.calls)
        self.assertEqual(self.notifications()[0]['status'],'expired')
    def test_missing_device_token_waits(self):
        self.watch();self.change(14000);sender=Sender();self.assertFalse(dispatch_once(self.db,sender))
        self.token();self.assertTrue(dispatch_once(self.db,sender))
    def test_inflight_lease_recovered_after_restart(self):
        self.watch();self.change(14000);self.token()
        self.db.execute("UPDATE notifications SET status='sending',lease_until=?",(time.time()-1,))
        sender=Sender();self.assertTrue(dispatch_once(self.db,sender));self.assertEqual(len(sender.calls),1)
    def test_preview_does_not_send_to_a_phone(self):
        self.watch(device='preview');self.change(14000);sender=Sender();self.assertFalse(dispatch_once(self.db,sender))
        self.assertEqual(self.notifications()[0]['status'],'preview')
    def test_foreign_keys_and_integrity(self):
        self.watch();self.change(14000)
        self.assertFalse(list(self.db.execute('PRAGMA foreign_key_check')))
        self.assertEqual(self.db.execute('PRAGMA integrity_check').fetchone()[0],'ok')

if __name__=='__main__':unittest.main()
