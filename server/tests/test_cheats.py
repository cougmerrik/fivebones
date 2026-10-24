"""Private cheat actions, exact loaded-die odds, and GM-only adjudication."""
from collections import Counter
from copy import deepcopy
import pytest
from app import engine as e
from app import main as m
from test_api import setup


def table():
    r=e.room('Cheats')
    for name in ('Alice','Bob','Cara'):
        sid=e.add_seat(r,name,10000)
        e.seat(r,sid)['abilities']=e.ability_scores(16)
    return e.apply(r,'startHand',{},gm=True,die=lambda:2)


def act(r,action,data=None,**kw):
    return e.apply(r,action,data or {},sid=r['actor'],die=lambda:3,randbelow=lambda n:0,**kw)


def test_exact_loaded_distribution():
    counts=Counter(e.loaded_face(lambda n,i=i:i) for i in range(500))
    assert counts=={5:165,1:67,2:67,3:67,4:67,6:67}


def test_loaded_applies_immediately_check_private_and_no_extra_turn():
    r=table();sid=r['actor'];before=deepcopy(r)
    r=act(r,'requestCheat',{'kind':'loadedDie','dieIndex':2})
    q=r['cheatRequests'][0]
    assert q['status']=='applied' and q['check']==dict(ability='dexterity',score=16,roll=1,modifier=3,total=4)
    assert e.seat(r,sid)['dice'][2]==5 and e.seat(r,sid)['loadedIndexes']==[2]
    assert (r['actor'],r['phase'],r['pot'],r['events'],r['ledger'])==(before['actor'],before['phase'],before['pot'],before['events'],before['ledger'])
    for identity in ('1','3',None):
        v=e.view(r,identity)
        assert v['cheatRequests']==[] and v['diceChanges']==[]
        target=next(s for s in v['seats'] if s['id']==sid)
        assert 'dice' not in target and 'abilities' not in target and 'loadedIndexes' not in target
    assert e.view(r,sid)['cheatRequests']==[q]
    gm=e.view(r,gm=True)
    assert gm['cheatRequests']==[q] and 'dice' not in next(s for s in gm['seats'] if s['id']==sid)
    with pytest.raises(e.RuleError,match='CHEAT_ALREADY_USED'):act(r,'requestCheat',{'kind':'other','description':'again'})
    while r['phase']=='BETTING_1':r=act(r,'check')
    r=act(r,'setReroll',{'indexes':[0,2]})
    assert e.seat(r,sid)['dice'][0]==3 and e.seat(r,sid)['dice'][2]==5
    assert e.seat(r,sid)['rerollCount']==2
    while r['phase'] in e.CHEAT_PHASES:
        r=act(r,'setReroll',{'indexes':[]}) if r['phase']=='REROLL' else act(r,'check')
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    assert all(s['loadedIndexes']==[] for s in r['seats'])
    assert all(q['status']=='expired' for q in r['cheatRequests'])


def test_change_die_and_authorized_gm_edit():
    r=table();sid=r['actor']
    r=act(r,'requestCheat',{'kind':'changeDie','dieIndex':0,'face':6})
    assert e.seat(r,sid)['dice'][0]==6 and r['cheatRequests'][0]['status']=='applied'
    original=deepcopy(r)
    payload={'seatId':sid,'dieIndex':0,'face':1,'reason':'Caught swapping the die'}
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):act(r,'gmChangeDie',payload)
    assert r==original
    r=e.apply(r,'gmChangeDie',payload,gm=True)
    assert e.seat(r,sid)['dice'][0]==1 and r['diceChanges'][-1]['before']==6
    assert r['audit'][-1]['kind']=='gmDiceChanged'
    assert e.view(r,sid)['diceChanges'][-1]['reason']=='Caught swapping the die'
    r=e.apply(r,'resolveCheat',{'requestId':'1','decision':'noted','reason':'Resolved at table'},gm=True)
    assert r['cheatRequests'][0]['status']=='acknowledged'
    with pytest.raises(e.RuleError,match='REQUEST_CLOSED'):e.apply(r,'resolveCheat',{'requestId':'1','decision':'noted','reason':'Again'},gm=True)
    r=act(r,'fold')
    with pytest.raises(e.RuleError,match='FOLDED'):e.apply(r,'gmChangeDie',payload,gm=True)


def test_other_waits_for_dm_and_has_optional_one_time_dex_check():
    r=table();original=deepcopy(r)
    r=act(r,'requestCheat',{'kind':'other','description':'Distract the dealer with a story'})
    assert r['cheatRequests'][0]['check'] is None
    assert r['seats']==original['seats']
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):act(r,'rollCheatCheck',{'requestId':'1','ability':'dexterity'})
    r=e.apply(r,'rollCheatCheck',{'requestId':'1','ability':'dexterity'},gm=True,randbelow=lambda n:19)
    assert r['cheatRequests'][0]['check']['total']==23
    with pytest.raises(e.RuleError,match='CHECK_ALREADY_ROLLED'):e.apply(r,'rollCheatCheck',{'requestId':'1','ability':'dexterity'},gm=True,randbelow=lambda n:19)
    r=e.apply(r,'resolveCheat',{'requestId':'1','decision':'noted','reason':'No extra effect'},gm=True)
    assert r['cheatRequests'][0]['status']=='adjudicated'


@pytest.mark.parametrize('score',[True,0,31,12.5,'16',None])
def test_bad_ability(score):
    with pytest.raises(e.RuleError):e.ability_scores(score)


def test_negative_dex_modifier_and_limits():
    r=table();sid=r['actor'];e.seat(r,sid)['abilities']=e.ability_scores(7)
    assert e.cheat_check(e.seat(r,sid),'dexterity',lambda n:0)['total']==-1
    other=next(s['id'] for s in r['seats'] if s['id']!=sid)
    with pytest.raises(e.RuleError,match='NOT_YOUR_TURN'):e.apply(r,'requestCheat',{'kind':'loadedDie','dieIndex':0},sid=other,randbelow=lambda n:0)
    with pytest.raises(e.RuleError,match='DEXTERITY_LOCKED'):act(r,'setAbilities',{'dexterity':20})
    for data in ({'kind':'loadedDie','dieIndex':True},{'kind':'loadedDie','dieIndex':5},{'kind':'changeDie','dieIndex':0,'face':7},{'kind':'other','description':' '},{'kind':'other','description':'x'*501}):
        with pytest.raises(e.RuleError):act(r,'requestCheat',data)
    r['phase']='READY_NEXT_HAND'
    with pytest.raises(e.RuleError,match='WRONG_PHASE'):e.apply(r,'gmChangeDie',{'seatId':sid,'dieIndex':0,'face':6,'reason':'late'},gm=True)


def test_legacy_seat_can_add_score_once_on_turn():
    r=table();s=e.seat(r,r['actor']);s.pop('abilities')
    with pytest.raises(e.RuleError,match='ABILITY_SCORES_REQUIRED'):act(r,'requestCheat',{'kind':'loadedDie','dieIndex':0})
    r=act(r,'setAbilities',{'dexterity':14})
    assert e.seat(r,r['actor'])['abilities']=={'dexterity':14}
    with pytest.raises(e.RuleError,match='DEXTERITY_LOCKED'):act(r,'setAbilities',{'dexterity':20})


def test_api_cheat_receipt_redaction_and_persistence(client,monkeypatch):
    rid,host,players=setup(client)
    with m.db() as c:
        r,creds,_=m.get(c,rid);gm=m.auth(creds,host['seatToken'])
    import uuid
    def send(who,action,data=None,cid=None):
        with m.db() as c:r,_,_=m.get(c,rid)
        cmd={'id':cid or str(uuid.uuid4()),'expectedVersion':r['version'],'action':action,'data':data or {}}
        return m.execute(rid,who,cmd),cmd
    assert send(gm,'startHand')[0]['accepted']
    with m.db() as c:
        r,creds,_=m.get(c,rid);p=next(p for p in players if p['seatId']==r['actor']);player=m.auth(creds,p['seatToken'])
    assert send(player,'setAbilities',{'dexterity':18})[0]['accepted']
    assert not send(player,'requestCheat',{'kind':'loadedDie','dieIndex':0,'roll':20})[0]['accepted']
    calls=[]
    monkeypatch.setattr(m.secrets,'randbelow',lambda n:calls.append(n) or 0)
    ack,command=send(player,'requestCheat',{'kind':'loadedDie','dieIndex':0})
    assert ack['accepted'] and calls==[20,500]
    assert m.execute(rid,player,command)==ack and calls==[20,500]
    with m.db() as c:
        r,_,_=m.get(c,rid)
        assert len(r['cheatRequests'])==1 and r['cheatRequests'][0]['check']['modifier']==4
        assert e.view(r)['cheatRequests']==[] and e.view(r)['diceChanges']==[]
        assert len(e.view(r,gm=True)['cheatRequests'])==1
    assert not send(player,'gmChangeDie',{'seatId':p['seatId'],'dieIndex':1,'face':6,'reason':'forged GM'})[0]['accepted']
    assert send(gm,'gmChangeDie',{'seatId':p['seatId'],'dieIndex':1,'face':6,'reason':'out-of-game adjudication'})[0]['accepted']
    public_csv=client.get(f'/api/v1/rooms/{rid}/ledger.csv',headers={'Authorization':'Bearer '+host['seatToken']}).text
    assert 'out-of-game adjudication' not in public_csv
    assert client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':host['inviteCode'],'name':'Bad','startingCp':100,'charisma':18}).status_code==422


def test_dexterity_is_locked_for_entire_session():
    r=e.room('locked');sid=e.add_seat(r,'Player',10000)
    r=e.apply(r,'setAbilities',{'dexterity':14},sid=sid)
    for phase in ('LOBBY','BETTING_1','REROLL','BETTING_2','READY_NEXT_HAND'):
        original=deepcopy(r);original['phase']=phase
        with pytest.raises(e.RuleError,match='DEXTERITY_LOCKED'):
            e.apply(original,'setAbilities',{'dexterity':20},sid=sid)
        assert e.seat(original,sid)['abilities']=={'dexterity':14}


def test_npc_creation_and_dm_only_cheat_check():
    r=e.room('NPC');e.add_seat(r,'Human',12500)
    r=e.apply(r,'addNPC',{'name':'Loaded Jack','startingCp':24050,'dexterity':18},gm=True)
    npc=r['seats'][1];assert npc['opening']==npc['balance']==24050
    assert npc['abilities']=={'dexterity':18}
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    assert r['actor']=='2'
    original=deepcopy(r)
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):
        e.apply(r,'requestNPCCheat',{'kind':'loadedDie','dieIndex':0},sid='1',randbelow=lambda n:19)
    assert r==original
    r=e.apply(r,'requestNPCCheat',{'kind':'loadedDie','dieIndex':0},gm=True,randbelow=lambda n:19)
    q=r['cheatRequests'][0]
    assert q['seatId']=='2' and q['check']['roll']==20 and q['check']['modifier']==4 and q['check']['total']==24
    assert q['status']=='applied' and e.seat(r,'2')['dice'][0]==5
    assert r['actor']=='2' and r['pot']==200
    assert any(x['kind']=='gmNPCCheatRequested' for x in r['audit'])
    assert any(x['kind']=='gmNPCCheatApplied' for x in r['audit'])
    for viewer in (e.view(r,'1'),e.view(r)):
        assert viewer['cheatRequests']==[] and viewer['diceChanges']==[]
        assert 'dice' not in viewer['seats'][1] and 'abilities' not in viewer['seats'][1]
    assert len(e.view(r,gm=True)['cheatRequests'])==1
    with pytest.raises(e.RuleError,match='CHEAT_ALREADY_USED'):
        e.apply(r,'requestNPCCheat',{'kind':'loadedDie','dieIndex':0},gm=True,randbelow=lambda n:0)
    r=e.apply(r,'takeNPCAction',{'action':'check'},gm=True)
    with pytest.raises(e.RuleError,match='NOT_NPC_TURN'):
        e.apply(r,'requestNPCCheat',{'kind':'changeDie','dieIndex':0,'face':6},gm=True,randbelow=lambda n:0)


def test_npc_legacy_score_is_one_time_gm_only():
    r=e.room('legacy');e.add_seat(r,'Human',1000);sid=e.add_seat(r,'NPC',1000,True)
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):
        e.apply(r,'setNPCDexterity',{'seatId':sid,'dexterity':18},sid='1')
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):
        e.apply(r,'setNPCDexterity',{'seatId':'1','dexterity':18},gm=True)
    r=e.apply(r,'setNPCDexterity',{'seatId':sid,'dexterity':18},gm=True)
    with pytest.raises(e.RuleError,match='DEXTERITY_LOCKED'):
        e.apply(r,'setNPCDexterity',{'seatId':sid,'dexterity':20},gm=True)


@pytest.mark.parametrize('data',[
 {'name':'Bad','startingCp':-1,'dexterity':10},
 {'name':'Bad','startingCp':100,'dexterity':True},
 {'name':'Bad','startingCp':100,'dexterity':31},
])
def test_invalid_npc_creation_is_atomic(data):
    r=e.room('Test');before=deepcopy(r)
    with pytest.raises(e.RuleError):e.apply(r,'addNPC',data,gm=True)
    assert r==before


def test_npc_check_api_retries_and_dex_lock(client,monkeypatch):
    import uuid
    host=client.post('/api/v1/rooms',json={'name':'NPC checks'}).json();rid=host['roomId']
    player=client.post(f'/api/v1/rooms/{rid}/join',json={'inviteCode':host['inviteCode'],'name':'Human','startingCp':10000,'dexterity':16}).json()
    with m.db() as c:
        r,creds,_=m.get(c,rid);gm=m.auth(creds,host['seatToken']);human=m.auth(creds,player['seatToken'])
    def send(identity,action,data):
        with m.db() as c:r,_,_=m.get(c,rid)
        cmd={'id':str(uuid.uuid4()),'expectedVersion':r['version'],'action':action,'data':data}
        return m.execute(rid,identity,cmd),cmd
    ack,_=send(human,'setAbilities',{'dexterity':20});assert ack['errorCode']=='DEXTERITY_LOCKED'
    assert send(gm,'addNPC',{'name':'Jack','startingCp':40000,'dexterity':18})[0]['accepted']
    assert send(gm,'startHand',{})[0]['accepted']
    assert not send(human,'requestNPCCheat',{'kind':'loadedDie','dieIndex':0})[0]['accepted']
    calls=[];monkeypatch.setattr(m.secrets,'randbelow',lambda n:calls.append(n) or 0)
    ack,cmd=send(gm,'requestNPCCheat',{'kind':'loadedDie','dieIndex':0})
    assert ack['accepted'] and calls==[20,500]
    assert m.execute(rid,gm,cmd)==ack and calls==[20,500]
    with m.db() as c:
        r,_,_=m.get(c,rid)
        assert e.seat(r,'2')['opening']==40000
        assert len(e.view(r,gm=True)['cheatRequests'])==1 and e.view(r,'1')['cheatRequests']==[]
