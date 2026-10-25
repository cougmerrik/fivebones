import json
import pytest
from app import engine as e
from app import main as m
from test_api import setup, connect, cmd


def plan(initial=None,indexes=None,replacements=None):
    return {'initial':initial or [1,2,3,4,5],'rerollIndexes':[] if indexes is None else indexes,'replacements':[] if replacements is None else replacements}


def room(scripts=None):
    r=e.room('Automated NPCs')
    e.add_seat(r,'Human',10000)
    for i,script in enumerate(scripts or [plan(indexes=[4,1],replacements=[6,6]),plan()]):
        npc=e.add_seat(r,f'NPC {i+1}',10000,True)
        r=e.apply(r,'scriptNPC',{'seatId':npc,'queue':[script]},gm=True)
    return r


def act(r,action='check',data=None):
    if e.seat(r,r['actor'])['npc']:
        return e.apply(r,'takeNPCAction',{'action':action,'data':data or {}},gm=True,die=lambda:3,randbelow=lambda _:0)
    return e.apply(r,action,data or {},sid=r['actor'],die=lambda:3,randbelow=lambda _:0)


def first_round(r):
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    while r['phase']=='BETTING_1':r=act(r)
    return r


def test_consecutive_npcs_automatically_reroll_then_stop_at_human():
    r=first_round(room())
    assert r['phase']=='REROLL' and r['actor']=='1'
    a,b=r['seats'][1:]
    assert a['dice']==[1,6,3,4,6] and a['rerollCount']==2
    assert b['dice']==[1,2,3,4,5] and b['rerollCount']==0
    assert a['autoRerollIndexes'] is None and b['autoRerollIndexes'] is None
    assert len([x for x in r['audit'] if x['kind']=='npcAutoReroll'])==2
    assert 'NPC 1 rerolled 2 dice.' in r['lastTurn'] and 'NPC 2 stood pat.' in r['lastTurn']
    # Only counts and public action metadata appear outside GM projections.
    public=e.view(r,sid='1');gm=e.view(r,gm=True)
    assert 'audit' not in public and all('autoReroll' not in s and 'queue' not in s and 'dice' not in s for s in public['seats'][1:])
    assert gm['seats'][1]['dice']==a['dice']
    for event in public['events']:
        assert not any(key in event for key in ('indexes','rerollIndexes','replacements','before','after','dice'))
    r=act(r,'setReroll',{'indexes':[]})
    assert r['phase']=='BETTING_2' and r['actor']=='2'
    assert sum(s['balance'] for s in r['seats'])+r['pot']==30000


def test_human_turn_waits_then_automatic_chain_finishes_rerolls():
    r=room();r['dealer']=1
    r=first_round(r)
    assert r['actor']=='1' and all(s['rerollCount'] is None for s in r['seats'])
    assert e.view(r,gm=True)['seats'][1]['autoReroll']=={'indexes':[4,1],'replacements':[6,6]}
    with pytest.raises(e.RuleError,match='NOT_YOUR_TURN'):e.apply(r,'setReroll',{'indexes':[]},sid='2',die=lambda:2)
    r=act(r,'setReroll',{'indexes':[]})
    assert r['phase']=='BETTING_2' and r['actor']=='1'
    assert [s['rerollCount'] for s in r['seats']]==[0,2,0]
    assert r['lastTurn'].endswith('Betting 2 begins.')
    assert all(s['commitment']==0 for s in r['seats'])  # Betting stays manual.


def test_legacy_queue_waits_for_gm_before_next_automatic_npc():
    r=first_round(room([{'initial':[2]*5,'replacements':[6]},plan(indexes=[0],replacements=[4])]))
    assert r['actor']=='2' and r['seats'][1]['rerollCount'] is None
    r=act(r,'setReroll',{'indexes':[3]})
    assert r['actor']=='1' and r['seats'][1]['dice']==[2,2,2,6,2]
    assert r['seats'][2]['dice']==[4,2,3,4,5] and r['seats'][2]['rerollCount']==1


def test_skipped_folded_and_removed_npcs_do_not_auto_reroll():
    r=room();r=e.apply(r,'setParticipation',{'seatId':'3','participating':False},gm=True)
    r=first_round(r)
    assert r['actor']=='1' and len(r['seats'][2]['queue'])==1 and r['seats'][2]['rerollCount'] is None
    r=room();r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    r=act(r,'fold')
    while r['phase']=='BETTING_1':r=act(r)
    assert r['seats'][1]['rerollCount'] is None and not any(x['kind']=='npcAutoReroll' and x['seatId']=='2' for x in r['audit'])
    r=room();r['dealer']=1;r=first_round(r)
    r=e.apply(r,'removeSeat',{'seatId':'1','confirmed':True},gm=True,die=lambda:2,randbelow=lambda _:0)
    assert r['phase']=='BETTING_2' and [s['rerollCount'] for s in r['seats']]==[None,2,0]
    assert sum(s['balance'] for s in r['seats'])+r['pot']==30000


def test_loaded_slot_keeps_odds_without_shifting_other_scripted_faces():
    r=room([plan(indexes=[0,4],replacements=[1,6]),plan()])
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    r['seats'][1]['loadedIndexes']=[0]
    while r['phase']=='BETTING_1':r=act(r)
    assert r['seats'][1]['dice']==[5,2,3,4,6]
    execution=next(x for x in r['audit'] if x['kind']=='npcAutoReroll')
    assert execution['replacements']==[1,6] and execution['after']==[5,2,3,4,6]


@pytest.mark.parametrize('entry',[
    None, {}, {'initial':None}, plan(indexes=[0,0],replacements=[1,2]),
    plan(indexes=[-1],replacements=[1]),plan(indexes=[5],replacements=[1]),
    plan(indexes=[True],replacements=[1]),plan(indexes='0',replacements=[1]),
    plan(indexes=[0],replacements=[]),plan(indexes=[],replacements=[1]),
    plan(indexes=[0],replacements=[True]),plan(indexes=[0],replacements=[7]),
    {**plan(),'futureWinner':'1'},
])
def test_invalid_plans_reject_atomically(entry):
    r=room();before=json.dumps(r)
    with pytest.raises(e.RuleError):e.apply(r,'scriptNPC',{'seatId':'2','queue':[entry]},gm=True)
    assert json.dumps(r)==before


def test_plan_is_only_for_npc_and_current_plan_survives_future_queue_edit():
    r=room()
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):e.apply(r,'scriptNPC',{'seatId':'1','queue':[plan()]},gm=True)
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):e.apply(r,'scriptNPC',{'seatId':'2','queue':[plan()]},sid='1')
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    r=e.apply(r,'scriptNPC',{'seatId':'2','queue':[]},gm=True)
    while r['phase']=='BETTING_1':r=act(r)
    assert r['seats'][1]['dice']==[1,6,3,4,6] and r['seats'][1]['queue']==[]


def test_automatic_reroll_is_durable_idempotent_and_private(client):
    rid,host,players=setup(client)
    def execute(token,action,data=None,cid=None,expected=None):
        with m.db() as c:
            r,creds,_=m.get(c,rid);identity=m.auth(creds,token)
        command={'id':cid or 'auto-test-'+str(r['version']),'expectedVersion':r['version'] if expected is None else expected,'action':action,'data':data or {}}
        ack=m.execute(rid,identity,command)
        with m.db() as c:r,_,_=m.get(c,rid)
        assert ack['accepted'],ack
        return ack,r,command
    execute(host['seatToken'],'addNPC',{'name':'Scripted','startingCp':10000})
    execute(host['seatToken'],'scriptNPC',{'seatId':'3','queue':[plan(indexes=[3],replacements=[6])]})
    execute(host['seatToken'],'startHand')
    execute(players[1]['seatToken'],'check');execute(host['seatToken'],'takeNPCAction',{'action':'check'});execute(players[0]['seatToken'],'check')
    ack,r,command=execute(players[1]['seatToken'],'setReroll',{'indexes':[]},cid='automatic-reroll-durable-command')
    assert r['phase']=='REROLL' and r['actor']=='1' and r['seats'][2]['dice']==[1,2,3,6,5]
    assert len([x for x in r['audit'] if x['kind']=='npcAutoReroll'])==1
    with connect(client,rid,players[1]['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':players[1]['seatToken']});state=ws.receive_json()['state']
        assert 'dice' not in state['seats'][2] and 'autoReroll' not in state['seats'][2] and 'audit' not in state
        repeated,current=cmd(ws,{'version':command['expectedVersion']},'setReroll',{'indexes':[]},id=command['id'])
        assert repeated==ack and current['version']==r['version'] and current['seats'][2]['rerollCount']==1
    with m.db() as c:persisted,_,_=m.get(c,rid)
    assert persisted['seats'][2]['dice']==[1,2,3,6,5] and len([x for x in persisted['audit'] if x['kind']=='npcAutoReroll'])==1
