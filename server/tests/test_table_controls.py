import json
import pytest
from app import engine as e
from app import main as m
from test_api import setup, connect, cmd


def table(n=3):
    r=e.room('Table controls')
    for i in range(n):e.add_seat(r,f'Player {i+1}',10000)
    return r


def start(r):return e.apply(r,'startHand',{},gm=True,die=lambda:2)


def finish(r):
    while r['phase'] in e.CHEAT_PHASES:
        action='setReroll' if r['phase']=='REROLL' else 'call' if e.seat(r,r['actor'])['commitment']<r['target'] else 'check'
        r=e.apply(r,action,{'indexes':[]} if action=='setReroll' else {},sid=r['actor'],die=lambda:3)
    return r


def test_opt_out_is_next_hand_only_and_persistent():
    r=start(table());before=repr(r)
    updated=e.apply(r,'setParticipation',{'participating':False},sid=r['actor'])
    assert repr(r)==before and not e.seat(updated,r['actor'])['folded']
    assert updated['actor']==r['actor'] and updated['pot']==r['pot']
    done=finish(updated);next_hand=start(done)
    out=e.seat(next_hand,r['actor'])
    assert out['folded'] and out['dice']==[] and out['contribution']==0 and out['balance']==e.seat(done,r['actor'])['balance']
    assert sum(s['balance'] for s in next_hand['seats'])+next_hand['pot']==30000
    again=e.apply(next_hand,'setParticipation',{'participating':True},sid=out['id'])
    assert e.seat(again,out['id'])['folded']  # Never join an already started hand.
    assert not e.seat(start(finish(again)),out['id'])['folded']


@pytest.mark.parametrize('sid,gm,data,error',[(None,False,{'participating':False},'UNAUTHORIZED'),('1',False,{'seatId':'2','participating':False},'UNAUTHORIZED'),('1',False,{'participating':1},'INVALID_PARTICIPATION')])
def test_participation_permissions(sid,gm,data,error):
    r=table()
    with pytest.raises(e.RuleError,match=error):e.apply(r,'setParticipation',data,gm=gm,sid=sid)


@pytest.mark.parametrize('phase',['BETTING_1','REROLL','BETTING_2'])
@pytest.mark.parametrize('current',[True,False])
def test_remove_any_active_seat_preserves_money_and_turns(phase,current):
    r=start(table())
    while r['phase']!=phase:
        r=e.apply(r,'setReroll' if r['phase']=='REROLL' else 'check',{'indexes':[]} if r['phase']=='REROLL' else {},sid=r['actor'],die=lambda:3)
    target=r['actor'] if current else next(s['id'] for s in e.active(r) if s['id']!=r['actor'])
    old_actor=r['actor'];opening=e.seat(r,target)['balance'];dice=e.seat(r,target)['dice'][:]
    removed=e.apply(r,'removeSeat',{'seatId':target,'confirmed':True},gm=True)
    s=e.seat(removed,target)
    assert s['removed'] and not s['nextHand'] and s['folded'] and s['balance']==opening
    assert removed['actor']!=target and (current or removed['actor']==old_actor)
    assert sum(s['balance'] for s in removed['seats'])+removed['pot']==30000
    assert target not in removed['pending'] and 'dice' not in next(x for x in e.view(removed)['seats'] if x['id']==target)
    assert 'dice' not in removed['lastTurn'] and str(dice) not in json.dumps(removed['events'])
    with pytest.raises(e.RuleError,match='SEAT_REMOVED'):e.apply(removed,'setParticipation',{'participating':True},sid=target)
    restored=e.apply(removed,'restoreSeat',{'seatId':target},gm=True)
    assert e.seat(restored,target)['folded'] and e.seat(restored,target)['nextHand']
    assert sum(s['balance'] for s in finish(restored)['seats'])==30000


def test_remove_settles_uncontested_and_history_survives():
    r=start(table(2));target=r['actor']
    r=e.apply(r,'removeSeat',{'seatId':target,'confirmed':True},gm=True)
    assert r['phase']=='READY_NEXT_HAND' and r['pot']==0 and r['revealed']==[]
    assert len(r['seats'])==2 and sum(s['balance'] for s in r['seats'])==20000
    assert 'winner:' in r['lastTurn']
    with pytest.raises(e.RuleError,match='INSUFFICIENT_SEATS'):start(r)
    r=e.apply(r,'restoreSeat',{'seatId':target},gm=True)
    assert len(e.active(start(r)))==2


def test_remove_requires_gm_confirmation_and_widowmaker_adjudication():
    r=start(table(2))
    for gm,data,error in [(False,{'seatId':'1','confirmed':True},'UNAUTHORIZED'),(True,{'seatId':'1'},'CONFIRMATION_REQUIRED')]:
        with pytest.raises(e.RuleError,match=error):e.apply(r,'removeSeat',data,gm=gm,sid='1')
    with pytest.raises(e.RuleError,match='UNAUTHORIZED'):e.apply(r,'restoreSeat',{'seatId':'1'},sid='1')
    for s in r['seats']:s['dice']=[6,6,6,1,1]
    r=finish(r)
    with pytest.raises(e.RuleError,match='ADJUDICATION_REQUIRED'):e.apply(r,'removeSeat',{'seatId':'1','confirmed':True},gm=True)


def test_public_turn_recap_excludes_private_cheats_and_handles_npc():
    r=table();npc=e.add_seat(r,'NPC',10000,True);e.seat(r,'2')['abilities']=e.ability_scores(16)
    r=start(r);r=e.apply(r,'bet',{},sid=r['actor'])
    assert r['lastTurn']=='Player 2 bet 1.00 gp.'
    r=e.apply(r,'call',{},sid=r['actor']);assert r['lastTurn']=='Player 3 called 1.00 gp.'
    r=e.apply(r,'takeNPCAction',{'action':'call'},gm=True);assert r['lastTurn']=='NPC called 1.00 gp.'
    r=e.apply(r,'call',{},sid=r['actor']);assert 'Rerolls begin.' in r['lastTurn']
    r=e.apply(r,'requestCheat',{'kind':'other','description':'secret distraction'},sid=r['actor']);old=r['lastTurn']
    assert 'secret distraction' not in json.dumps(e.view(r)['events']) and e.view(r)['lastTurn']==old
    r=e.apply(r,'setReroll',{'indexes':[]},sid=r['actor'],die=lambda:3)
    assert r['lastTurn']=='Player 2 stood pat.'


def test_old_room_defaults_and_queue_skips_opted_out_npc():
    r=table();npc=e.add_seat(r,'NPC',10000,True)
    for s in r['seats']:s.pop('nextHand');s.pop('removed')
    assert all(s['nextHand'] and not s['removed'] for s in e.view(r)['seats'])
    r=e.apply(r,'scriptNPC',{'seatId':npc,'queue':[{'initial':[6]*5,'replacements':[1,2]}]},gm=True)
    r=e.apply(r,'setParticipation',{'seatId':npc,'participating':False},gm=True)
    r=start(r);assert len(e.seat(r,npc)['queue'])==1
    assert 'queue' not in e.view(r)['seats'][-1]
    r=finish(r);r=e.apply(r,'setParticipation',{'seatId':npc,'participating':True},gm=True);r=start(r)
    assert e.seat(r,npc)['dice']==[6]*5 and e.seat(r,npc)['queue']==[]
    r=finish(r);r=e.apply(r,'endSession',{},gm=True)
    assert 'finished the session' in e.view(r)['lastTurn']
    with pytest.raises(e.RuleError,match='SESSION_ENDED'):e.apply(r,'setParticipation',{'participating':False},sid='1')


def test_controls_persist_retry_and_reconnect(client):
    rid,host,players=setup(client)
    with connect(client,rid,players[0]['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':players[0]['seatToken']});state=ws.receive_json()['state']
        ack,state=cmd(ws,state,'setParticipation',{'seatId':players[1]['seatId'],'participating':False});assert ack['errorCode']=='UNAUTHORIZED'
        ack,state=cmd(ws,state,'removeSeat',{'seatId':players[1]['seatId'],'confirmed':True});assert ack['errorCode']=='UNAUTHORIZED'
        ack,state=cmd(ws,state,'setParticipation',{'participating':False});assert ack['accepted']
    with connect(client,rid,host['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':host['seatToken']});state=ws.receive_json()['state']
        assert state['seats'][0]['nextHand'] is False
        ack,state=cmd(ws,state,'setParticipation',{'seatId':players[0]['seatId'],'participating':True});assert ack['accepted']
        ack,state=cmd(ws,state,'startHand');assert ack['accepted']
        original=state;command_id='remove-seat-durable-retry'
        ack,state=cmd(ws,state,'removeSeat',{'seatId':players[1]['seatId'],'confirmed':True},id=command_id);assert ack['accepted']
        repeated,current=cmd(ws,original,'removeSeat',{'seatId':players[1]['seatId'],'confirmed':True},id=command_id)
        assert repeated==ack and state==current
    with connect(client,rid,players[1]['seatToken']) as ws:
        ws.send_json({'type':'authenticate','seatToken':players[1]['seatToken']});state=ws.receive_json()['state']
        assert state['seats'][1]['removed'] and 'removed' in state['lastTurn']
        ack,state=cmd(ws,state,'setParticipation',{'participating':True});assert ack['errorCode']=='SEAT_REMOVED'
    with m.db() as c:
        persisted,_,_=m.get(c,rid)
        assert persisted['seats'][1]['removed'] and len(persisted['ledger'])==len(state['ledger'])
