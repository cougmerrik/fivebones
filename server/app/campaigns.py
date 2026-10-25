"""Stable campaign entrypoint. URL flags never authorize GM access."""
import hashlib
import hmac
import json
import os
import secrets
import time
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router=APIRouter(prefix='/api/v1/campaigns')
ALIAS='belwether'
_DEV_KEY=secrets.token_bytes(32)  # Blank local-development secrets never yield a predictable token.

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Access(Strict):hostSecret:str=Field(max_length=500)
class Start(Strict):
    id:str=Field(min_length=8,max_length=100)
    expectedRoomId:str|None=None
    smallBetCp:int=100
class Join(Strict):
    expectedRoomId:str=Field(min_length=1,max_length=100)
    joinKey:str=Field(pattern='^[0-9a-f]{64}$')
    name:str=Field(min_length=1,max_length=40)
    startingCp:int=Field(ge=0,le=1000000000)
    dexterity:int=Field(ge=1,le=30)


def check_alias(alias):
    if alias!=ALIAS:raise HTTPException(404,'CAMPAIGN_NOT_FOUND')


def campaign(c,alias):
    query='SELECT room_id,credentials,receipts FROM campaigns WHERE alias=?'
    if c.postgres:query+=' FOR UPDATE'
    row=c.execute(query,(alias,)).fetchone()
    return None if row is None else (row[0],json.loads(row[1]),json.loads(row[2]))


def current(c,rid):
    from . import main as m
    if rid is None:return None
    try:return m.get(c,rid)
    except HTTPException as exc:
        if exc.status_code!=404:raise
        return None


def owner(row,authorization):
    from . import main as m
    if row is None:raise HTTPException(401,'DM_ACCESS_REQUIRED')
    token=authorization.removeprefix('Bearer ')
    if not token or len(token)>100:raise HTTPException(401,'DM_ACCESS_REQUIRED')
    identity=m.auth(row[1],token)
    if not identity['gm']:raise HTTPException(403,'UNAUTHORIZED')
    return token,identity


def session(c,rid,token):
    from . import main as m
    data=current(c,rid)
    if data is None:return None
    identity=m.auth(data[1],token)
    if not identity['gm']:raise HTTPException(403,'UNAUTHORIZED')
    return dict(roomId=rid,seatToken=token,campaignAlias=ALIAS)


@router.get('/{alias}')
def status(alias:str):
    check_alias(alias)
    from . import main as m
    with m.db() as c:
        row=campaign(c,alias);rid=row[0] if row else None;data=current(c,rid)
        r=data[0] if data else None
    return dict(alias=alias,roomId=rid,available=r is not None,ended=r['ended'] if r else True,
                canJoin=bool(r and not r['ended'] and r['phase'] in ('LOBBY','READY_NEXT_HAND')),
                playerUrl=os.getenv('APP_BASE_URL','http://localhost:5173').rstrip('/')+'/?room='+alias)


@router.post('/{alias}/dm-access')
def access(alias:str,body:Access,request:Request):
    check_alias(alias)
    from . import main as m
    m.limit(('campaign-access',request.client.host),10)
    secret=os.getenv('HOST_INVITE_SECRET','')
    if not secrets.compare_digest(secret.encode(),body.hostSecret.encode()):raise HTTPException(403,'HOST_SECRET_REQUIRED')
    token=hmac.new(secret.encode() if secret else _DEV_KEY,('fivebones:campaign:'+alias).encode(),hashlib.sha256).hexdigest()
    with m.db() as c:
        c.execute('INSERT INTO campaigns (alias,room_id,credentials,receipts) VALUES (?,?,?,?) ON CONFLICT(alias) DO NOTHING',(alias,None,'{}','{}'))
        rid,creds,receipts=campaign(c,alias)
        if m.digest(token) not in creds and len(creds)>=40:raise HTTPException(409,'DM_DEVICE_LIMIT')
        identity=creds.get(m.digest(token)) or dict(gm=True,sid=None,key=secrets.token_hex(8))
        creds[m.digest(token)]=identity
        data=current(c,rid)
        if data is not None:
            r,room_creds,_=data;room_creds[m.digest(token)]=identity;m.save(c,rid,r,room_creds)
        c.execute('UPDATE campaigns SET credentials=? WHERE alias=?',(json.dumps(creds),alias))
    # Never retain the host creation secret or return another device's token.
    return dict(dmToken=token)


@router.get('/{alias}/dm-session')
def dm_session(alias:str,authorization:str=Header(default='')):
    check_alias(alias)
    from . import main as m
    with m.db() as c:
        row=campaign(c,alias);token,_=owner(row,authorization)
        return dict(session=session(c,row[0],token))


@router.post('/{alias}/sessions')
def start(alias:str,body:Start,authorization:str=Header(default='')):
    check_alias(alias)
    from . import main as m
    with m.db() as c:
        row=campaign(c,alias);token,_=owner(row,authorization);rid,creds,receipts=row
        if body.id in receipts:return session(c,receipts[body.id],token)
        if body.expectedRoomId!=rid:raise HTTPException(409,'CAMPAIGN_CHANGED')
        previous=current(c,rid)
        if previous is not None and not previous[0]['ended']:raise HTTPException(409,'END_CURRENT_SESSION_FIRST')
        try:r=m.e.room('Belwether',body.smallBetCp)
        except m.e.RuleError as exc:raise HTTPException(422,str(exc))
        r['campaignJoinSalt']=secrets.token_hex(32)
        new_id=secrets.token_urlsafe(9)
        c.execute('INSERT INTO rooms (id,state,credentials,invite,created) VALUES (?,?,?,?,?)',
                  (new_id,json.dumps(r),json.dumps(creds),m.digest(secrets.token_urlsafe(16)),time.time()))
        receipts[body.id]=new_id
        c.execute('UPDATE campaigns SET room_id=?,receipts=? WHERE alias=?',(new_id,json.dumps(receipts),alias))
        return session(c,new_id,token)


@router.post('/{alias}/join')
async def join(alias:str,body:Join,request:Request):
    check_alias(alias)
    from . import main as m
    m.limit(('campaign-join',request.client.host),40)
    # The client's private random retry key lets the server reproduce its issued
    # player token without storing plaintext tokens or duplicating seats on retry.
    with m.db() as c:
        row=campaign(c,alias)
        if row is None or row[0]!=body.expectedRoomId:raise HTTPException(409,'CAMPAIGN_CHANGED')
        rid=row[0];r,creds,_=m.get(c,rid)
        salt=r.get('campaignJoinSalt')
        if not salt:raise HTTPException(409,'CAMPAIGN_UPGRADE_REQUIRED')
        token=hmac.new(bytes.fromhex(salt),('campaign-seat:'+rid+':'+body.joinKey).encode(),hashlib.sha256).hexdigest()
        hashed=m.digest(token)
        if hashed in creds:
            identity=m.auth(creds,token)
            if identity['gm'] or identity['sid'] is None:raise HTTPException(409,'INVALID_JOIN_KEY')
            s=m.e.seat(r,identity['sid'])
            if s['name']!=body.name or s['opening']!=body.startingCp or s.get('abilities')!={'dexterity':body.dexterity}:
                raise HTTPException(409,'JOIN_DETAILS_CHANGED')
            return dict(roomId=rid,seatId=s['id'],seatToken=token,campaignAlias=alias)
        if r['ended']:raise HTTPException(409,'SESSION_ENDED')
        if len(creds)>=40:raise HTTPException(409,'ROOM_FULL')
        try:
            sid=m.e.add_seat(r,body.name,body.startingCp)
            m.e.seat(r,sid)['abilities']=m.e.ability_scores(body.dexterity)
        except m.e.RuleError as exc:raise HTTPException(409,str(exc))
        creds[hashed]=dict(gm=False,sid=sid,key=secrets.token_hex(8))
        r['version']+=1;m.save(c,rid,r,creds)
    await m.broadcast(rid)
    return dict(roomId=rid,seatId=sid,seatToken=token,campaignAlias=alias)

@router.get('/{alias}/history')
def history(alias:str,authorization:str=Header(default='')):
    check_alias(alias)
    from . import main as m
    sessions=[]
    with m.db() as c:
        row=campaign(c,alias);owner(row,authorization)
        for rid in reversed(list(dict.fromkeys(row[2].values()))):
            data=current(c,rid)
            if data is None or not data[0]['ended']:continue
            r=data[0]
            sessions.append(dict(roomId=rid,hand=r['hand'],seats=[{k:s[k] for k in ('id','name','npc','opening','balance')} for s in r['seats']]))
    return dict(sessions=sessions)
