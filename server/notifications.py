"""Durable FCM outbox. Provider acceptance and device receipt are distinct."""
import json
import threading
import time
from pathlib import Path
from store import connect,transaction

class FirebaseSender:
    def __init__(self,credential_file,client_file):
        self.credential_file=Path(credential_file); self.client_file=Path(client_file); self.app=None
    def configured(self): return self.credential_file.is_file() and self.client_file.is_file()
    def send(self,token,payload):
        import firebase_admin
        from firebase_admin import credentials,messaging
        if self.app is None:
            credential=json.loads(self.credential_file.read_text(encoding='utf-8-sig'))
            client=json.loads(self.client_file.read_text(encoding='utf-8-sig'))
            if credential.get('project_id')!=client.get('project_id'):
                raise ValueError('Firebase project IDs differ')
            self.app=firebase_admin.initialize_app(credentials.Certificate(credential),name='ogun-lab')
        remaining=max(1,int(payload['expires_at'])-int(time.time()))
        from datetime import timedelta
        return messaging.send(messaging.Message(token=token,data=payload,
            android=messaging.AndroidConfig(priority='high',ttl=timedelta(seconds=remaining))),app=self.app)

def dispatch_once(db,sender,now=None):
    now=time.time() if now is None else now
    with transaction(db):
        db.execute("UPDATE notifications SET status='expired',lease_until=0 WHERE status IN ('pending','sending') AND expires_at<=?",(now,))
        db.execute("UPDATE notifications SET status='pending' WHERE status='sending' AND lease_until<?",(now,))
        if not sender.configured(): return False
        row=db.execute('''SELECT n.*,d.fcm_token FROM notifications n JOIN devices d ON d.id=n.device_id
            WHERE n.status='pending' AND n.next_attempt<=? AND d.fcm_token IS NOT NULL
            ORDER BY n.created_at LIMIT 1''',(now,)).fetchone()
        if not row: return False
        db.execute("UPDATE notifications SET status='sending',lease_until=?,attempts=attempts+1 WHERE id=?",(now+90,row['id']))
    try:
        provider_id=sender.send(row['fcm_token'],json.loads(row['payload']))
        with transaction(db):
            db.execute("UPDATE notifications SET status=CASE WHEN received_at IS NULL THEN 'sent' ELSE 'received' END,provider_id=?,lease_until=0,last_error=NULL WHERE id=?",(provider_id,row['id']))
    except Exception as exc:
        name=type(exc).__name__
        permanent=name in ('UnregisteredError','SenderIdMismatchError','InvalidArgumentError')
        # Error class only: provider text can contain credentials or device tokens.
        with transaction(db):
            if name=='UnregisteredError':
                db.execute('UPDATE devices SET fcm_token=NULL WHERE id=? AND fcm_token=?',(row['device_id'],row['fcm_token']))
            db.execute('UPDATE notifications SET status=?,last_error=?,next_attempt=?,lease_until=0 WHERE id=?',
                ('failed' if permanent else 'pending',name,now+min(300,2**min(row['attempts']+1,8)),row['id']))
    return True

def acknowledge(db,device_id,notification_id):
    with transaction(db):
        changed=db.execute("UPDATE notifications SET received_at=COALESCE(received_at,?),status='received' WHERE id=? AND device_id=? AND status IN ('pending','sending','sent','received')",
                           (time.time(),notification_id,device_id)).rowcount
    return bool(changed)

class Worker:
    def __init__(self,path,sender):
        self.path=path;self.sender=sender;self.stop=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True,name='notification-outbox')
    def run(self):
        db=connect(self.path)
        try:
            while not self.stop.is_set():
                try: busy=dispatch_once(db,self.sender)
                except Exception as exc:
                    print('Outbox:',type(exc).__name__,flush=True);busy=False
                self.stop.wait(.1 if busy else 2)
        finally: db.close()
