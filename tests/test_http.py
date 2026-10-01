import json
import sys
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import app
import store
from notifications import FirebaseSender

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db';store.initialize(self.path)
        self.db=store.connect(self.path)
        handler=app.make_handler(self.path,FirebaseSender(Path(self.tmp.name)/'missing1',Path(self.tmp.name)/'missing2'),Path(self.tmp.name)/'missing2')
        handler.log_message=lambda *args:None
        self.server=ThreadingHTTPServer(('127.0.0.1',0),handler);self.port=self.server.server_port
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.db.close();self.tmp.cleanup()
    def request(self,path,body=None,headers=None):
        h=dict(headers or {})
        if body is not None:h['Content-Type']='application/json'
        c=HTTPConnection('127.0.0.1',self.port,timeout=3);c.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,h)
        r=c.getresponse();status,data=r.status,r.read();c.close();return status,json.loads(data)
    def local_headers(self):return {'X-Ogun-Lab':'1','Origin':f'http://127.0.0.1:{self.port}'}
    def test_catalogue_requires_pairing_or_local_browser(self):
        self.assertEqual(self.request('/api/catalogue')[0],401)
        status,data=self.request('/api/catalogue',headers=self.local_headers());self.assertEqual(status,200);self.assertEqual(len(data['items']),100)
    def test_pair_authenticate_and_watch(self):
        _,result=self.request('/api/admin/pair-code',{},self.local_headers())
        status,pair=self.request('/api/pair',{'code':result['code'],'name':'Test phone'})
        self.assertEqual(status,200);self.assertIsNone(pair['firebase'])
        h={'Authorization':'Bearer '+pair['access_token']}
        self.assertEqual(self.request('/api/watch',{'meal_id':'m0201','mode':'target','target_minor':14000},h)[0],200)
        _,data=self.request('/api/catalogue',headers=h)
        self.assertEqual(next(x for x in data['items'] if x['id']=='m0201')['watch']['target_minor'],14000)
        self.assertEqual(self.request('/api/admin/status',headers=h)[0],403)
    def test_admin_cross_origin_rejected(self):
        headers=self.local_headers();headers['Origin']='https://unrelated.example'
        self.assertEqual(self.request('/api/admin/pair-code',{},headers)[0],403)
        self.assertEqual(self.request('/api/admin/pair-code',{}, {})[0],403)
        self.assertEqual(self.request('/api/health',headers={'Host':'unrelated.example'})[0],403)
    def test_admin_update_and_conflict(self):
        _,data=self.request('/api/catalogue',headers=self.local_headers());meal=next(x for x in data['items'] if x['id']=='m0201')
        body={'meal_id':meal['id'],'version':meal['version'],'price_minor':14000,'request_id':'http-test-change'}
        self.assertEqual(self.request('/api/admin/price',body,self.local_headers())[0],200)
        body['request_id']='http-test-change2'
        self.assertEqual(self.request('/api/admin/price',body,self.local_headers())[0],409)
    def test_pair_rate_limit(self):
        for _ in range(8):self.assertEqual(self.request('/api/pair',{'code':'wrong','name':'Phone'})[0],400)
        self.assertEqual(self.request('/api/pair',{'code':'wrong','name':'Phone'})[0],429)

if __name__=='__main__':unittest.main()
