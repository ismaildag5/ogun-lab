"""SQLite domain model. Price event and notification intent commit atomically."""
import hashlib
import json
import secrets
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from catalog_seed import rows

def connect(path):
    db=sqlite3.connect(path,timeout=15,isolation_level=None)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    return db

@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise

def initialize(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    db=connect(path)
    db.execute('PRAGMA journal_mode=WAL')
    db.executescript('''
      CREATE TABLE IF NOT EXISTS meals(id TEXT PRIMARY KEY,name TEXT NOT NULL,branch TEXT NOT NULL,
        category TEXT NOT NULL,portion TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS prices(id INTEGER PRIMARY KEY AUTOINCREMENT,
        meal_id TEXT NOT NULL REFERENCES meals(id), price_minor INTEGER NOT NULL CHECK(price_minor>0),
        changed_at REAL NOT NULL, request_id TEXT UNIQUE NOT NULL, old_minor INTEGER);
      CREATE INDEX IF NOT EXISTS prices_meal ON prices(meal_id,id DESC);
      CREATE TRIGGER IF NOT EXISTS prices_immutable_update BEFORE UPDATE ON prices
        BEGIN SELECT RAISE(ABORT,'Price history is append-only'); END;
      CREATE TRIGGER IF NOT EXISTS prices_immutable_delete BEFORE DELETE ON prices
        BEGIN SELECT RAISE(ABORT,'Price history is append-only'); END;
      CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY, secret_hash TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL, fcm_token TEXT, created_at REAL NOT NULL);
      CREATE UNIQUE INDEX IF NOT EXISTS device_token ON devices(fcm_token) WHERE fcm_token IS NOT NULL;
      CREATE TABLE IF NOT EXISTS watches(device_id TEXT REFERENCES devices(id),meal_id TEXT REFERENCES meals(id),
        mode TEXT NOT NULL CHECK(mode IN ('any','target','big')),target_minor INTEGER,
        PRIMARY KEY(device_id,meal_id));
      CREATE TABLE IF NOT EXISTS notifications(id TEXT PRIMARY KEY, device_id TEXT REFERENCES devices(id),
        event_id INTEGER REFERENCES prices(id), meal_id TEXT REFERENCES meals(id),payload TEXT NOT NULL,
        created_at REAL NOT NULL, expires_at REAL NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
        attempts INTEGER NOT NULL DEFAULT 0,next_attempt REAL NOT NULL DEFAULT 0,
        lease_until REAL NOT NULL DEFAULT 0,last_error TEXT,provider_id TEXT,received_at REAL,
        UNIQUE(device_id,event_id));
      CREATE TABLE IF NOT EXISTS pair_codes(digest TEXT PRIMARY KEY,expires_at REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    ''')
    with transaction(db):
        for meal in rows():
            inserted=db.execute('INSERT OR IGNORE INTO meals VALUES(?,?,?,?,?)',
               (meal['id'],meal['name'],meal['branch'],meal['category'],meal['portion'])).rowcount
            if inserted:
                db.execute('INSERT INTO prices(meal_id,price_minor,changed_at,request_id) VALUES(?,?,?,?)',
                   (meal['id'],meal['price_minor'],time.time(),'seed-'+meal['id']))
        db.execute("INSERT OR IGNORE INTO devices VALUES('preview','preview-no-login','Tarayıcı denemesi',NULL,?)",(time.time(),))
    db.close()

def digest(value): return hashlib.sha256(value.encode()).hexdigest()

def create_pair_code(db):
    code=secrets.token_hex(4).upper()
    with transaction(db):
        db.execute('DELETE FROM pair_codes')
        db.execute('INSERT INTO pair_codes VALUES(?,?)',(digest(code),time.time()+600))
    return {'code':code,'expires_in':600}

def pair(db,code,name):
    if not isinstance(code,str) or not isinstance(name,str) or not 1<=len(name.strip())<=60:
        raise ValueError('Eşleştirme bilgisi geçersiz.')
    with transaction(db):
        row=db.execute('SELECT * FROM pair_codes WHERE digest=?',(digest(code.strip().upper()),)).fetchone()
        if not row or row['expires_at']<time.time(): raise ValueError('Kod yanlış veya süresi dolmuş.')
        db.execute('DELETE FROM pair_codes WHERE digest=?',(row['digest'],))
        secret=secrets.token_urlsafe(32); device_id=str(uuid.uuid4())
        db.execute('INSERT INTO devices VALUES(?,?,?,?,?)',(device_id,digest(secret),name.strip(),None,time.time()))
    return {'device_id':device_id,'access_token':secret}

def authenticate(db,token):
    if not token: return None
    row=db.execute('SELECT id FROM devices WHERE secret_hash=?',(digest(token),)).fetchone()
    return row['id'] if row else None

def register_token(db,device_id,token):
    if not isinstance(token,str) or not 20<=len(token)<=4096: raise ValueError('Bildirim cihaz kimliği geçersiz.')
    with transaction(db):
        db.execute('UPDATE devices SET fcm_token=NULL WHERE fcm_token=? AND id<>?',(token,device_id))
        db.execute('UPDATE devices SET fcm_token=? WHERE id=?',(token,device_id))
        db.execute("UPDATE notifications SET next_attempt=0 WHERE device_id=? AND status='pending'",(device_id,))

def validate_money(value):
    if type(value) is not int or not 0<value<=10000000:
        raise ValueError('Fiyat 0 TL’den büyük, en fazla 100.000 TL olmalı; kuruş olarak tam sayı gönderilmeli.')

def save_watch(db,device_id,body):
    mid=body.get('meal_id')
    if not isinstance(mid,str) or not db.execute('SELECT 1 FROM meals WHERE id=?',(mid,)).fetchone():
        raise ValueError('Yemek bulunamadı.')
    with transaction(db):
        if body.get('remove') is True:
            db.execute('DELETE FROM watches WHERE device_id=? AND meal_id=?',(device_id,mid))
            db.execute("UPDATE notifications SET status='cancelled' WHERE device_id=? AND meal_id=? AND status='pending'",(device_id,mid))
            return
        mode=body.get('mode'); target=body.get('target_minor')
        if mode not in ('any','target','big'): raise ValueError('Takip türü geçersiz.')
        if mode=='target': validate_money(target)
        else: target=None
        db.execute('INSERT INTO watches VALUES(?,?,?,?) ON CONFLICT(device_id,meal_id) DO UPDATE SET mode=excluded.mode,target_minor=excluded.target_minor',
                   (device_id,mid,mode,target))
        # Existing queued alerts use the old preference; changing a watch cancels them.
        db.execute("UPDATE notifications SET status='cancelled' WHERE device_id=? AND meal_id=? AND status='pending'",(device_id,mid))

def drop_for(history,now):
    latest=history[0]; start=latest['changed_at']; candidates=[]; prior=False
    for row in history[1:]:
        if not prior and row['price_minor']==latest['price_minor']:
            start=row['changed_at']; continue
        prior=True
        if row['changed_at']<start-7*86400: break
        candidates.append(row['price_minor'])
    if not candidates: return None
    reference=min(candidates); saved=reference-latest['price_minor']
    if saved<=0: return None
    return {'reference_minor':reference,'saved_minor':saved,'percent':round(saved*100/reference,1),
            'big':saved>=4000 and saved*100>=reference*25,
            'active':0<=now-start<=72*3600,'started_at':start}

def catalogue(db,device_id='preview'):
    groups={}
    for row in db.execute('SELECT * FROM prices ORDER BY id DESC'):
        groups.setdefault(row['meal_id'],[]).append(dict(row))
    watches={r['meal_id']:dict(r) for r in db.execute('SELECT * FROM watches WHERE device_id=?',(device_id,))}
    result=[]
    for row in db.execute('SELECT * FROM meals ORDER BY name'):
        item=dict(row); history=groups[item['id']]; latest=history[0]
        item.update(price_minor=latest['price_minor'],version=latest['id'],changed_at=latest['changed_at'],
                    drop=drop_for(history,time.time()),watch=watches.get(item['id']))
        result.append(item)
    return {'items':result,'fictional':True,'generated_at':time.time()}

class Conflict(ValueError): pass

def change_price(db,body,now=None):
    now=time.time() if now is None else now
    mid=body.get('meal_id'); price=body.get('price_minor'); version=body.get('version'); req=body.get('request_id')
    validate_money(price)
    if not isinstance(mid,str) or type(version) is not int or not isinstance(req,str) or not 8<=len(req)<=100:
        raise ValueError('Yemek, sürüm ve işlem kimliği gerekli.')
    with transaction(db):
        repeated=db.execute('SELECT * FROM prices WHERE request_id=?',(req,)).fetchone()
        if repeated:
            if repeated['meal_id']!=mid or repeated['price_minor']!=price: raise Conflict('İşlem kimliği başka değişiklikte kullanılmış.')
            return {'changed':False,'repeated':True,'event_id':repeated['id']}
        meal=db.execute('SELECT * FROM meals WHERE id=?',(mid,)).fetchone()
        old=db.execute('SELECT * FROM prices WHERE meal_id=? ORDER BY id DESC LIMIT 1',(mid,)).fetchone()
        if not meal or not old: raise ValueError('Yemek bulunamadı.')
        if old['id']!=version: raise Conflict('Fiyat başka bir işlemde değişti. Listeyi yenileyip tekrar dene.')
        if old['price_minor']==price: return {'changed':False,'event_id':old['id'],'queued':0}
        event=db.execute('INSERT INTO prices(meal_id,price_minor,changed_at,request_id,old_minor) VALUES(?,?,?,?,?)',
            (mid,price,now,req,old['price_minor'])).lastrowid
        # A rebound invalidates queued discounts. A further reduction keeps an
        # earlier target crossing valid unless we replace it with a newer alert.
        if price>old['price_minor']:
            db.execute("UPDATE notifications SET status='superseded' WHERE meal_id=? AND status='pending'",(mid,))
        history=[dict(r) for r in db.execute('SELECT * FROM prices WHERE meal_id=? ORDER BY id DESC',(mid,))]
        drop=drop_for(history,now); queued=0
        if price<old['price_minor']:
            for watch in db.execute('SELECT * FROM watches WHERE meal_id=?',(mid,)):
                hit=(watch['mode']=='any' or
                     watch['mode']=='target' and old['price_minor']>watch['target_minor']>=price or
                     watch['mode']=='big' and drop and drop['big'] and drop['active'])
                if not hit: continue
                db.execute("UPDATE notifications SET status='superseded' WHERE meal_id=? AND device_id=? AND status='pending'",(mid,watch['device_id']))
                nid=str(uuid.uuid4())
                payload={'notification_id':nid,'meal_id':mid,'device_id':watch['device_id'],
                    'title':f"{meal['name']} fiyatı düştü",
                    'body':f"{meal['branch']}: {old['price_minor']/100:.2f} TL → {price/100:.2f} TL. Deneme verisidir.",
                    'price_minor':str(price),'event_id':str(event),'expires_at':str(int(now+900))}
                db.execute('INSERT INTO notifications(id,device_id,event_id,meal_id,payload,created_at,expires_at,status) VALUES(?,?,?,?,?,?,?,?)',
                    (nid,watch['device_id'],event,mid,json.dumps(payload,ensure_ascii=False),now,now+900,
                     'preview' if watch['device_id']=='preview' else 'pending'))
                queued+=1
    return {'changed':True,'event_id':event,'queued':queued}

def inbox(db,device_id):
    return [dict(r) for r in db.execute('SELECT id,meal_id,payload,created_at,status,received_at FROM notifications WHERE device_id=? ORDER BY created_at DESC LIMIT 50',(device_id,))]

def delivery_status(db):
    return {'devices':[dict(r) for r in db.execute("SELECT id,name,(fcm_token IS NOT NULL) AS push_ready,created_at FROM devices WHERE id<>'preview'")],
            'counts':{r['status']:r['n'] for r in db.execute('SELECT status,count(*) n FROM notifications GROUP BY status')},
            'recent':[dict(r) for r in db.execute('SELECT id,meal_id,device_id,status,attempts,last_error,created_at,received_at FROM notifications ORDER BY created_at DESC LIMIT 20')]}
