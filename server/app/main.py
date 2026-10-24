import asyncio
import csv
import hashlib
import io
import json
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from . import engine as e
from . import storage
from .settings import origins, validate_production
from sqlalchemy.exc import SQLAlchemyError

DB=os.getenv('DATABASE_PATH','fivebones.sqlite3')
DATABASE_URL=os.getenv('DATABASE_URL','')
ORIGINS=origins(os.getenv('ALLOWED_ORIGINS','http://localhost:5173'))
WS_ORIGINS=origins(os.getenv('WS_ALLOWED_ORIGINS',','.join(ORIGINS)))

@asynccontextmanager
async def lifespan(app):
    validate_production(os.environ)
    with db() as c: c.execute('SELECT 1')
    yield
    sockets=[ws for room_clients in list(clients.values()) for ws in list(room_clients)]
    await asyncio.gather(*(ws.close(code=1012) for ws in sockets), return_exceptions=True)
    storage.dispose(DATABASE_URL,DB)

app=FastAPI(title='Five Bones',docs_url=None,redoc_url=None,lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=ORIGINS,allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type'])

def digest(token): return hashlib.sha256(token.encode()).hexdigest()

def db():
    return storage.transaction(DATABASE_URL,DB)

def get(conn,rid):
    query='SELECT state,credentials,invite FROM rooms WHERE id=?'
    if conn.postgres: query+=' FOR UPDATE'
    row=conn.execute(query,(rid,)).fetchone()
    if not row: raise HTTPException(404,'ROOM_NOT_FOUND')
    return json.loads(row[0]),json.loads(row[1]),row[2]

def save(conn,rid,r,creds):
    conn.execute('UPDATE rooms SET state=?,credentials=? WHERE id=?',(json.dumps(r),json.dumps(creds),rid))

def auth(creds,token):
    identity=creds.get(digest(token))
    if not identity: raise HTTPException(401,'UNAUTHORIZED')
    return identity

rates=defaultdict(deque)
def limit(key, maximum=120):
    now=time.monotonic(); q=rates[key]
    while q and q[0]<now-60: q.popleft()
    if len(q)>=maximum: raise HTTPException(429,'RATE_LIMIT')
    q.append(now)
    if len(rates)>10000:
        for k in list(rates):
            if not rates[k] or rates[k][-1]<now-60: del rates[k]

class Strict(BaseModel): model_config=ConfigDict(extra='forbid',strict=True)
class Create(Strict):
    name: str=Field(min_length=1,max_length=60)
    smallBetCp: int=100
    anteCp: int | None=None
    ties: str='kickers'
    remainder: str='clockwise'
    hostSecret: str=''
class Join(Strict):
    inviteCode: str
    name: str=Field(min_length=1,max_length=40)
    startingCp: int=Field(ge=0,le=1000000000)
    spectator: bool=False
    dexterity: int | None=Field(default=None,ge=1,le=30)
class Command(Strict):
    type: str='command'
    id: str=Field(min_length=8,max_length=100)
    expectedVersion: int
    action: str
    data: dict=Field(default_factory=dict)

# Exact input shapes prevent silently accepting client-supplied dice or money.
SHAPES={'setParticipation':{'seatId','participating'},'removeSeat':{'seatId','confirmed'},'restoreSeat':{'seatId'},'startHand':set(),'endSession':set(),'fold':set(),'check':set(),'call':set(),'bet':set(),'raise':set(),
        'setReroll':{'indexes'},'addNPC':{'name','startingCp','dexterity'},'scriptNPC':{'seatId','queue'},
        'setAbilities':{'dexterity'},'setNPCDexterity':{'seatId','dexterity'},'requestNPCCheat':{'kind','dieIndex','face','description'},'requestCheat':{'kind','dieIndex','face','description'},
        'gmChangeDie':{'seatId','dieIndex','face','reason'},'rollCheatCheck':{'requestId','ability'},
        'resolveCheat':{'requestId','decision','reason'},'takeNPCAction':{'action','data'},'forceFold':{'confirmed'},'adjudicate':{'reason'}}
def validate_data(action,data):
    e.require(action in SHAPES and set(data)<=SHAPES[action],'INVALID_DATA')
    if action=='takeNPCAction':
        e.require(data.get('action') in ('fold','check','call','bet','raise','setReroll'),'INVALID_ACTION')
        validate_data(data['action'],data.get('data',{}))
    if action=='addNPC':
        e.require(isinstance(data.get('name'),str) and 1<=len(data['name'])<=40,'INVALID_NAME')

clients=defaultdict(dict)
def projection(r,rid,identity):
    v=e.view(r,identity.get('sid'),identity['gm'])
    online={i.get('sid') for i in clients[rid].values()}
    for s in v['seats']: s['connected']=s['npc'] or s['id'] in online
    return v

async def broadcast(rid,exclude=None):
    with db() as c: r,_,_=get(c,rid)
    for ws,identity in list(clients[rid].items()):
        if ws is exclude: continue
        try: await ws.send_json({'type':'snapshot','state':projection(r,rid,identity)})
        except Exception: clients[rid].pop(ws,None)

def execute(rid,identity,raw):
    cmd=Command.model_validate(raw)
    with db() as c:
        r,creds,_=get(c,rid)
        if not any(value==identity for value in creds.values()): raise HTTPException(401,'UNAUTHORIZED')
        key=identity['key']+':'+cmd.id
        if key in r['receipts']: return r['receipts'][key]
        try:
            e.require(cmd.type=='command','INVALID_COMMAND')
            e.require(cmd.expectedVersion==r['version'],'CONFLICT')
            validate_data(cmd.action,cmd.data)
            updated=e.apply(r,cmd.action,cmd.data,gm=identity['gm'],sid=identity.get('sid'),die=lambda:secrets.randbelow(6)+1,randbelow=secrets.randbelow)
            updated['version']+=1
            r=updated
            ack=dict(type='ack',id=cmd.id,accepted=True,roomVersion=r['version'])
        except (e.RuleError,KeyError,TypeError,StopIteration) as exc:
            ack=dict(type='ack',id=cmd.id,accepted=False,roomVersion=r['version'],errorCode=str(exc) if isinstance(exc,e.RuleError) else 'INVALID_DATA')
        r['receipts'][key]=ack; save(c,rid,r,creds)
        return ack

@app.get('/live')
def live():
    return {'status':'ok'}

@app.get('/health')
@app.get('/api/v1/health')
def health():
    try:
        with db() as c: c.execute('SELECT 1')
    except SQLAlchemyError:
        raise HTTPException(503,'DATABASE_UNAVAILABLE')
    return {'status':'ok'}

@app.post('/api/v1/rooms')
def create(body:Create,request:Request):
    limit(('create',request.client.host),20)
    secret=os.getenv('HOST_INVITE_SECRET','')
    if secret and not secrets.compare_digest(secret,body.hostSecret): raise HTTPException(403,'HOST_SECRET_REQUIRED')
    try: r=e.room(body.name,body.smallBetCp,body.anteCp,body.ties,body.remainder)
    except e.RuleError as exc: raise HTTPException(422,str(exc))
    rid=secrets.token_urlsafe(9); token=secrets.token_urlsafe(32); invite=secrets.token_urlsafe(9)
    creds={digest(token):dict(gm=True,sid=None,key=secrets.token_hex(8))}
    with db() as c: c.execute('INSERT INTO rooms VALUES (?,?,?,?,?)',(rid,json.dumps(r),json.dumps(creds),digest(invite),time.time()))
    return dict(roomId=rid,inviteCode=invite,seatToken=token,joiningUrl=os.getenv('APP_BASE_URL','http://localhost:5173').rstrip('/')+'/?room='+rid+'&invite='+invite)

@app.post('/api/v1/rooms/{rid}/join')
async def join(rid:str,body:Join,request:Request):
    limit(('join',request.client.host),40)
    with db() as c:
        r,creds,invite=get(c,rid)
        if not secrets.compare_digest(digest(body.inviteCode),invite): raise HTTPException(403,'INVALID_INVITE')
        if r['ended']: raise HTTPException(409,'SESSION_ENDED')
        try: sid=None if body.spectator else e.add_seat(r,body.name,body.startingCp)
        except e.RuleError as exc: raise HTTPException(409,str(exc))
        if sid is not None and body.dexterity is not None:
            try: e.seat(r,sid)['abilities']=e.ability_scores(body.dexterity)
            except e.RuleError as exc: raise HTTPException(422,str(exc))
        if len(creds)>=40: raise HTTPException(409,'ROOM_FULL')
        token=secrets.token_urlsafe(32); creds[digest(token)]=dict(gm=False,sid=sid,key=secrets.token_hex(8))
        r['version']+=1; save(c,rid,r,creds)
    await broadcast(rid)
    return dict(roomId=rid,seatToken=token,seatId=sid)

@app.get('/api/v1/rooms/{rid}/ledger.csv')
def ledger(rid:str,authorization:str=Header(default='')):
    with db() as c:
        r,creds,_=get(c,rid); identity=auth(creds,authorization.removeprefix('Bearer '))
    if not identity['gm']: raise HTTPException(403,'UNAUTHORIZED')
    out=io.StringIO(); w=csv.writer(out); w.writerow(['hand','seatId','name','kind','amountCp','openingCp','endingCp','netCp'])
    for entry in r['ledger']:
        s=e.seat(r,entry['seatId']); name=s['name']
        if name.startswith(('=','+','-','@','\t','\r')): name="'"+name
        w.writerow([entry['hand'],s['id'],name,entry['kind'],entry['amountCp'],'','',''])
    for hand in sorted({x['hand'] for x in r['ledger']}):
        for s in r['seats']:
            entries=[x for x in r['ledger'] if x['hand']==hand and x['seatId']==s['id']]
            if entries:
                name=s['name']; name="'"+name if name.startswith(('=','+','-','@','\t','\r')) else name
                w.writerow([hand,s['id'],name,'HAND_NET',sum(x['amountCp'] for x in entries),'','',''])
    for s in r['seats']:
        name=s['name']; name="'"+name if name.startswith(('=','+','-','@','\t','\r')) else name
        w.writerow(['TOTAL',s['id'],name,'', '',s['opening'],s['balance'],s['balance']-s['opening']])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="five-bones-ledger.csv"'})

@app.post('/api/v1/rooms/{rid}/delete')
async def delete(rid:str,body:dict,authorization:str=Header(default='')):
    with db() as c:
        _,creds,_=get(c,rid); identity=auth(creds,authorization.removeprefix('Bearer '))
        if not identity['gm'] or body!={'confirmed':True}: raise HTTPException(403,'CONFIRMATION_REQUIRED')
        c.execute('DELETE FROM rooms WHERE id=?',(rid,))
    for ws in list(clients.pop(rid,{})): await ws.close(code=1000)
    return {'deleted':True}

@app.websocket('/api/v1/rooms/{rid}/ws')
async def socket(ws:WebSocket,rid:str):
    try: limit(('socket',ws.client.host),120)
    except HTTPException:
        await ws.close(code=1008); return
    origin=ws.headers.get('origin','')
    if origin not in WS_ORIGINS:
        await ws.close(code=1008); return
    await ws.accept()
    try:
        raw=await asyncio.wait_for(ws.receive_json(),10)
        if not isinstance(raw,dict) or not isinstance(raw.get('seatToken'),str) or len(raw['seatToken'])>100 or raw.get('type')!='authenticate': raise HTTPException(401,'UNAUTHORIZED')
        with db() as c:
            r,creds,_=get(c,rid); identity=auth(creds,raw.get('seatToken',''))
        clients[rid][ws]=identity
        await ws.send_json({'type':'snapshot','state':projection(r,rid,identity)})
        await broadcast(rid,exclude=ws)
        while True:
            raw=await ws.receive_json(); limit(('command',identity['key']))
            if not isinstance(raw,dict): raise HTTPException(400,'INVALID_REQUEST')
            if raw.get('type')=='ping': await ws.send_json({'type':'pong'}); continue
            try: ack=execute(rid,identity,raw)
            except (ValueError,HTTPException):
                await ws.send_json({'type':'error','errorCode':'INVALID_REQUEST'}); continue
            await ws.send_json(ack); await broadcast(rid)
    except SQLAlchemyError:
        try: await ws.close(code=1013)
        except RuntimeError: pass
    except (WebSocketDisconnect,asyncio.TimeoutError,HTTPException,ValueError,TypeError):
        pass
    finally:
        clients[rid].pop(ws,None)
        try: await broadcast(rid)
        except (HTTPException,SQLAlchemyError): pass
        try: await ws.close()
        except RuntimeError: pass
