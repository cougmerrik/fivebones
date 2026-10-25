import json
import secrets
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from app import main as m
from test_api import connect,cmd

BASE='/api/v1/campaigns/belwether'
KEY='test-only-campaign-host-key-32-characters'


def access(client,monkeypatch):
    monkeypatch.setenv('HOST_INVITE_SECRET',KEY)
    response=client.post(BASE+'/dm-access',json={'hostSecret':KEY})
    assert response.status_code==200,response.text
    return response.json()['dmToken']


def headers(token):return {'Authorization':'Bearer '+token}


def start(client,token,previous=None,identifier=None):
    response=client.post(BASE+'/sessions',headers=headers(token),json={'id':identifier or str(uuid.uuid4()),'expectedRoomId':previous,'smallBetCp':100})
    assert response.status_code==200,response.text
    return response.json()


def join_body(rid,name='Merrik'):
    return dict(expectedRoomId=rid,joinKey=secrets.token_hex(32),name=name,startingCp=12500,dexterity=16)


def test_campaign_requires_real_dm_auth_and_preserves_existing_game(client,monkeypatch):
    monkeypatch.setenv('HOST_INVITE_SECRET',KEY)
    assert client.get(BASE).json()['roomId'] is None
    assert client.post(BASE+'/dm-access',json={'hostSecret':'wrong'}).status_code==403
    assert client.post(BASE+'/dm-access',json={'hostSecret':'🔑'}).status_code==403
    assert client.get(BASE+'/dm-session?isdm=1').status_code==401
    assert client.post(BASE+'/sessions?isdm=1',json={'id':str(uuid.uuid4())}).status_code==401
    token=access(client,monkeypatch);assert client.get(BASE+'/dm-session',headers=headers(token)).json()=={'session':None}
    host=start(client,token)
    status=client.get(BASE).json();assert status['roomId']==host['roomId'] and status['canJoin']
    assert status['playerUrl'].endswith('/?room=belwether')
    assert not any(k in status for k in ('credentials','seatToken','dmToken','inviteCode','dice'))
    assert client.get(BASE+'/dm-session',headers=headers(token)).json()['session']==host
    response=client.post(BASE+'/sessions',headers=headers(token),json={'id':str(uuid.uuid4()),'expectedRoomId':host['roomId']})
    assert response.status_code==409 and response.json()['detail']=='END_CURRENT_SESSION_FIRST'
    assert client.get('/api/v1/campaigns/another-room').status_code==404
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]==1
        credentials=c.execute('SELECT credentials FROM campaigns').fetchone()[0]
        assert token not in credentials and KEY not in credentials


def test_player_form_no_invite_with_idempotent_join_and_locked_stats(client,monkeypatch):
    token=access(client,monkeypatch);host=start(client,token);body=join_body(host['roomId'])
    first=client.post(BASE+'/join',json=body);assert first.status_code==200,first.text
    assert client.post(BASE+'/join',json=body).json()==first.json()
    assert client.post(BASE+'/join?isdm=1',json={**body,'gm':True}).status_code==422
    assert client.post(BASE+'/join',json={**body,'dexterity':17}).json()['detail']=='JOIN_DETAILS_CHANGED'
    assert client.get(BASE+'/dm-session',headers=headers(first.json()['seatToken'])).status_code==401
    with connect(client,host['roomId'],first.json()['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':first.json()['seatToken']});state=ws.receive_json()['state']
        assert state['role']=='player' and state['seats'][0]['abilities']=={'dexterity':16}
        ack,state=cmd(ws,state,'startHand');assert not ack['accepted']
    with m.db() as c:
        r,creds,_=m.get(c,host['roomId']);assert len(r['seats'])==1
        assert first.json()['seatToken'] not in json.dumps(creds) and body['joinKey'] not in json.dumps(r)
        assert len(r['campaignJoinSalt'])==64 and 'campaignJoinSalt' not in m.e.view(r,sid='1')


def test_fresh_session_switch_retains_history_and_other_dm_devices(client,monkeypatch):
    one=access(client,monkeypatch);first=start(client,one)
    player=client.post(BASE+'/join',json=join_body(first['roomId'])).json()
    two=access(client,monkeypatch)
    assert two==one  # Reauthorizing a device doesn't accumulate GM seats/credentials.
    assert client.get(BASE+'/dm-session',headers=headers(two)).json()['session']['roomId']==first['roomId']
    with connect(client,first['roomId'],one) as ws:
        ws.send_json({'type':'authenticate','seatToken':one});s=ws.receive_json()['state'];ack,s=cmd(ws,s,'endSession');assert ack['accepted']
    identifier=str(uuid.uuid4());second=start(client,one,first['roomId'],identifier)
    assert second['roomId']!=first['roomId']
    assert start(client,one,first['roomId'],identifier)==second
    assert client.get(BASE+'/dm-session',headers=headers(two)).json()['session']['roomId']==second['roomId']
    old=client.get('/api/v1/rooms/'+first['roomId']+'/ledger.csv',headers=headers(one))
    assert old.status_code==200 and 'Merrik' in old.text
    assert client.get(BASE+'/history').status_code==401
    archive=client.get(BASE+'/history',headers=headers(two)).json()['sessions']
    assert archive[0]['roomId']==first['roomId'] and archive[0]['seats'][0]['balance']==12500
    assert set(archive[0]['seats'][0])=={'id','name','npc','opening','balance'}
    stale=client.post(BASE+'/join',json=join_body(first['roomId']))
    assert stale.status_code==409 and stale.json()['detail']=='CAMPAIGN_CHANGED'
    with connect(client,first['roomId'],player['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':player['seatToken']});assert ws.receive_json()['state']['ended']
    with m.db() as c:
        new,creds,_=m.get(c,second['roomId']);assert not new['seats'] and not new['ledger']
        assert m.digest(player['seatToken']) not in creds


def test_campaign_start_and_join_concurrent_retries(client,monkeypatch):
    token=access(client,monkeypatch)
    def request_start(_):return client.post(BASE+'/sessions',headers=headers(token),json={'id':'same-session-command','expectedRoomId':None})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(request_start,range(2)))
    assert all(r.status_code==200 for r in responses) and responses[0].json()==responses[1].json()
    rid=responses[0].json()['roomId'];body=join_body(rid)
    with ThreadPoolExecutor(max_workers=2) as pool:joined=list(pool.map(lambda _:client.post(BASE+'/join',json=body),range(2)))
    assert all(r.status_code==200 for r in joined) and joined[0].json()==joined[1].json()
    with m.db() as c:
        assert c.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]==1
        assert len(m.get(c,rid)[0]['seats'])==1


def test_campaign_join_limits_and_live_recovery(client,monkeypatch):
    token=access(client,monkeypatch);host=start(client,token);bodies=[join_body(host['roomId'],str(i)) for i in range(5)]
    players=[client.post(BASE+'/join',json=b).json() for b in bodies]
    assert client.post(BASE+'/join',json=join_body(host['roomId'],'overflow')).json()['detail']=='ROOM_FULL'
    with connect(client,host['roomId'],token) as ws:
        ws.send_json({'type':'authenticate','seatToken':token});s=ws.receive_json()['state'];ack,s=cmd(ws,s,'startHand');assert ack['accepted']
    assert not client.get(BASE).json()['canJoin']
    assert client.post(BASE+'/join',json=bodies[0]).json()==players[0]  # Lost first response can recover mid-hand.
    assert client.post(BASE+'/join',json=join_body(host['roomId'],'late')).json()['detail']=='WRONG_PHASE'
    for changes in ({'dexterity':True},{'dexterity':31},{'joinKey':'guessable'},{'startingCp':-1}):
        assert client.post(BASE+'/join',json={**bodies[0],**changes}).status_code==422


def test_two_dms_cannot_create_competing_sessions(client,monkeypatch):
    a=access(client,monkeypatch);b=access(client,monkeypatch)
    def create(token):return client.post(BASE+'/sessions',headers=headers(token),json={'id':str(uuid.uuid4()),'expectedRoomId':None})
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(create,[a,b]))
    assert sorted(r.status_code for r in responses)==[200,409]
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]==1
