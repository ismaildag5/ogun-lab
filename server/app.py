import argparse
import ipaddress
import json
import os
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import store
from notifications import FirebaseSender,Worker,acknowledge

ROOT=Path(__file__).resolve().parents[1]
DEFAULT_DB=ROOT/'data/lab.sqlite3'

def client_config(path):
    if not path.is_file(): return None
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    fields=('application_id','api_key','sender_id','project_id')
    if not all(isinstance(data.get(k),str) and data[k].strip() for k in fields):
        raise ValueError('Firebase istemci ayarları eksik.')
    return {k:data[k] for k in fields}

def make_handler(dbpath,sender,client_path):
    attempts={};attempt_lock=threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):
            # Never log bodies, credentials, or pairing codes.
            if args and isinstance(args[0],str): print(self.command,urlparse(self.path).path,flush=True)
        def respond(self,status,data,kind='application/json; charset=utf-8'):
            raw=data if isinstance(data,bytes) else json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status)
            for key,value in {'Content-Type':kind,'Content-Length':str(len(raw)),
                'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer',
                'Content-Security-Policy':"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'"}.items():
                self.send_header(key,value)
            self.end_headers();self.wfile.write(raw)
        def local(self): return ipaddress.ip_address(self.client_address[0]).is_loopback
        def host_ok(self):
            host=urlparse('http://'+self.headers.get('Host','')).hostname
            if host=='localhost': return True
            try:
                address=ipaddress.ip_address(host)
                return address.is_loopback or address.is_private
            except ValueError: return False
        def browser_request(self,mutation=False):
            if not self.local() or self.headers.get('X-Ogun-Lab')!='1': return False
            origin=self.headers.get('Origin')
            if mutation or origin: return origin=='http://'+self.headers.get('Host','')
            return self.headers.get('Sec-Fetch-Site')=='same-origin'
        def device(self,db):
            if self.browser_request(self.command=='POST'): return 'preview'
            value=self.headers.get('Authorization','')
            return store.authenticate(db,value[7:]) if value.startswith('Bearer ') else None
        def do_GET(self): self.handle_request(False)
        def do_POST(self): self.handle_request(True)
        def handle_request(self,mutation):
            if not self.host_ok(): return self.respond(403,{'error':'Geçersiz sunucu adresi.'})
            path=urlparse(self.path).path;db=None
            try:
                body={}
                if mutation:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=16384 or self.headers.get_content_type()!='application/json':
                        return self.respond(400,{'error':'JSON isteği gerekli.'})
                    body=json.loads(self.rfile.read(size))
                    if not isinstance(body,dict): raise ValueError('İstek nesne olmalı.')
                assets={'/':'index.html','/admin':'admin.html','/app.js':'app.js','/admin.js':'admin.js','/style.css':'style.css'}
                if not mutation and path in assets:
                    if not self.local(): return self.respond(403,{'error':'Yönetim ve tarayıcı denemesi yalnızca bilgisayarda açılır.'})
                    suffix=Path(assets[path]).suffix
                    mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8'}[suffix]
                    return self.respond(200,(ROOT/'web'/assets[path]).read_bytes(),mime)
                if not mutation and path=='/api/health':
                    return self.respond(200,{'name':'Öğün Deneme','fictional':True,'version':3})
                db=store.connect(dbpath)
                if mutation and path=='/api/pair':
                    peer=self.client_address[0]
                    with attempt_lock:
                        recent=[t for t in attempts.get(peer,[]) if time.time()-t<60]
                        if len(recent)>=8: return self.respond(429,{'error':'Bir dakika bekleyip tekrar dene.'})
                        attempts[peer]=recent+[time.time()]
                    paired=store.pair(db,body.get('code'),body.get('name','Android telefon'))
                    paired['firebase']=client_config(client_path)
                    return self.respond(200,paired)
                if path.startswith('/api/admin/'):
                    if not self.browser_request(mutation): return self.respond(403,{'error':'Yönetim yalnızca yerel yönetim ekranından kullanılabilir.'})
                    if path=='/api/admin/price' and mutation: return self.respond(200,store.change_price(db,body))
                    if path=='/api/admin/pair-code' and mutation: return self.respond(200,store.create_pair_code(db))
                    if path=='/api/admin/status' and not mutation:
                        data=store.delivery_status(db); data['firebase_configured']=sender.configured()
                        data['lan_addresses']=sorted(set(socket.gethostbyname_ex(socket.gethostname())[2]))
                        data['port']=self.server.server_port; data['lan_enabled']=self.server.server_address[0]!='127.0.0.1'
                        return self.respond(200,data)
                    return self.respond(404,{'error':'Yol bulunamadı.'})
                device=self.device(db)
                if not device: return self.respond(401,{'error':'Telefonu yeniden eşleştir.'})
                if not mutation and path=='/api/catalogue': return self.respond(200,store.catalogue(db,device))
                if not mutation and path=='/api/firebase': return self.respond(200,{'firebase':client_config(client_path)})
                if not mutation and path=='/api/inbox': return self.respond(200,{'items':store.inbox(db,device)})
                if not mutation and path.startswith('/api/history/'):
                    mid=path.rsplit('/',1)[-1]
                    return self.respond(200,{'items':[dict(r) for r in db.execute('SELECT price_minor,changed_at,id FROM prices WHERE meal_id=? ORDER BY id DESC LIMIT 100',(mid,))]})
                if mutation and path=='/api/watch': store.save_watch(db,device,body)
                elif mutation and path=='/api/token': store.register_token(db,device,body.get('token'))
                elif mutation and path=='/api/received':
                    if not isinstance(body.get('notification_id'),str): raise ValueError('Bildirim kimliği gerekli.')
                    return self.respond(200,{'ok':acknowledge(db,device,body['notification_id'])})
                else: return self.respond(404,{'error':'Yol bulunamadı.'})
                return self.respond(200,{'ok':True})
            except store.Conflict as exc: self.respond(409,{'error':str(exc)})
            except (ValueError,TypeError,KeyError) as exc: self.respond(400,{'error':str(exc)})
            except Exception as exc:
                print('Request error:',type(exc).__name__,flush=True)
                self.respond(500,{'error':'İşlem tamamlanamadı. Sunucu kaydını kontrol et.'})
            finally:
                if db is not None: db.close()
    return Handler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',type=Path,default=DEFAULT_DB)
    parser.add_argument('--port',type=int,default=8767)
    parser.add_argument('--lan',action='store_true',help='Enable phone API on the local network; admin remains loopback-only.')
    parser.add_argument('--init-only',action='store_true')
    args=parser.parse_args();store.initialize(args.db)
    if args.init_only: print('100 deneme yemeği hazır.');return
    private=ROOT/'private'
    sender=FirebaseSender(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS',str(private/'firebase-service-account.json')),private/'firebase-client.json')
    worker=Worker(args.db,sender);worker.thread.start()
    server=ThreadingHTTPServer(('0.0.0.0' if args.lan else '127.0.0.1',args.port),make_handler(args.db,sender,private/'firebase-client.json'))
    print(f'Öğün: http://127.0.0.1:{args.port} | Yönetim: /admin',flush=True)
    print('Firebase: '+('yapılandırıldı' if sender.configured() else 'kurulum bekleniyor'),flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close();worker.stop.set();worker.thread.join(timeout=5)

if __name__=='__main__': main()
