import json
import uuid
import pytest
from fastapi.testclient import TestClient
from app import main as m


def setup(c):
    host=c.post('/api/v1/rooms',json={'name':'Test'}).json();rid=host['roomId']
    players=[c.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':host['inviteCode'],'name':str(i),'startingCp':10000}).json() for i in range(2)]
    return rid,host,players

def cmd(ws,state,action,data=None,id=None):
    ws.send_json({'type':'command','id':id or str(uuid.uuid4()),'expectedVersion':state['version'],'action':action,'data':data or {}})
    ack=ws.receive_json();snap=ws.receive_json()['state'];return ack,snap

def connect(c,rid,token):
    return c.websocket_connect(f'/api/v1/rooms/{rid}/ws',headers={'origin':'http://localhost:5173'})

def test_protocol_persistence_and_security(client):
    rid,host,players=setup(client)
    with connect(client,rid,host['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':host['seatToken']});s=ws.receive_json()['state']
        a,s=cmd(ws,s,'startHand');assert a['accepted']
        assert all('dice' not in p for p in s['seats'])
    p=next(p for p in players if p['seatId']==s['actor'])
    with connect(client,rid,p['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':p['seatToken']});s=ws.receive_json()['state']
        assert len(next(x for x in s['seats'] if x['id']==p['seatId'])['dice'])==5
        a,s=cmd(ws,s,'addNPC',{'name':'x','startingCp':10});assert not a['accepted']
        a,s=cmd(ws,s,'bet',{'dice':[6]*5});assert a['errorCode']=='INVALID_DATA'
        cid=str(uuid.uuid4());old=s.copy();a,s=cmd(ws,s,'bet',id=cid);assert a['accepted'];version=s['version'];pot=s['pot']
        a,s=cmd(ws,old,'bet',id=cid);assert a['accepted'] and s['pot']==pot and s['version']==version
        a,s=cmd(ws,old,'fold');assert a['errorCode']=='CONFLICT'
    # New application instance recovers aggregate and hashed credentials from SQLite.
    with TestClient(m.app) as recovered:
        with connect(recovered,rid,p['seatToken']) as ws:
            ws.send_json({'type':'authenticate','seatToken':p['seatToken']});new=ws.receive_json()['state'];assert new['pot']==pot
    with m.db() as c:
        row=c.execute('SELECT credentials FROM rooms').fetchone()[0];assert p['seatToken'] not in row and host['seatToken'] not in row
    assert client.get(f'/api/v1/rooms/{rid}/ledger.csv').status_code==401
    assert client.get(f'/api/v1/rooms/{rid}/ledger.csv',headers={'Authorization':'Bearer '+p['seatToken']}).status_code==403
    result=client.get(f'/api/v1/rooms/{rid}/ledger.csv',headers={'Authorization':'Bearer '+host['seatToken']});assert result.status_code==200 and 'TOTAL' in result.text

def test_invites_inputs_and_deletion(client):
    rid,h,p=setup(client)
    assert client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':'bad','name':'x','startingCp':100}).status_code==403
    assert client.post('/api/v1/rooms',json={'name':'x','smallBetCp':2}).status_code==422
    assert client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':h['inviteCode'],'name':'x','startingCp':True}).status_code==422
    headers={'Authorization':'Bearer '+h['seatToken']}
    assert client.post(f'/api/v1/rooms/{rid}/delete',json={},headers=headers).status_code==403
    assert client.post(f'/api/v1/rooms/{rid}/delete',json={'confirmed':True},headers=headers).status_code==200
    assert client.get(f'/api/v1/rooms/{rid}/ledger.csv',headers=headers).status_code==404

def test_spectator_and_seat_limit(client):
    rid,h,p=setup(client)
    for i in range(3): assert client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':h['inviteCode'],'name':'x','startingCp':10000}).status_code==200
    assert client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':h['inviteCode'],'name':'x','startingCp':10000}).status_code==409
    watcher=client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':h['inviteCode'],'name':'watch','startingCp':0,'spectator':True}).json()
    with connect(client,rid,watcher['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':watcher['seatToken']});s=ws.receive_json()['state'];assert s['role']=='spectator'
        a,s=cmd(ws,s,'startHand');assert a['errorCode']=='UNAUTHORIZED'

def test_serialized_transactions_under_concurrent_retry(client):
    from concurrent.futures import ThreadPoolExecutor
    rid,host,players=setup(client)
    with m.db() as c:
        r,creds,_=m.get(c,rid);identity=m.auth(creds,host['seatToken'])
    first={'id':str(uuid.uuid4()),'expectedVersion':r['version'],'action':'startHand'}
    assert m.execute(rid,identity,first)['accepted']
    with m.db() as c:
        r,creds,_=m.get(c,rid)
        player=next(p for p in players if p['seatId']==r['actor']);identity=m.auth(creds,player['seatToken'])
    command={'id':str(uuid.uuid4()),'expectedVersion':r['version'],'action':'bet'}
    with ThreadPoolExecutor(max_workers=2) as pool: responses=list(pool.map(lambda _:m.execute(rid,identity,command),range(2)))
    assert responses[0]==responses[1] and responses[0]['accepted']
    with m.db() as c:
        final,_,_=m.get(c,rid)
        assert final['pot']==300 and final['version']==r['version']+1

def test_socket_auth_and_origin_rejection(client):
    from starlette.websockets import WebSocketDisconnect
    rid,host,players=setup(client)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/api/v1/rooms/{rid}/ws',headers={'origin':'https://evil.example'}) as ws:ws.receive_json()
    for payload in ({'type':'authenticate','seatToken':'wrong'},{'type':'authenticate','seatToken':4},[]):
        with pytest.raises(WebSocketDisconnect):
            with connect(client,rid,'unused') as ws:ws.send_json(payload);ws.receive_json()
