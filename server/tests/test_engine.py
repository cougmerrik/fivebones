import itertools
import pytest
from app import engine as e

def make(n=3,balance=10000):
    r=e.room('Test')
    for i in range(n): e.add_seat(r,str(i),balance)
    return e.apply(r,'startHand',{},gm=True,die=lambda:2)

def action(r,a,data=None,**kw): return e.apply(r,a,data or {},sid=r['actor'],die=lambda:3,**kw)
def through(r):
    while r['phase'] not in ('READY_NEXT_HAND','ADJUDICATION'):
        r=action(r,'setReroll',{'indexes':[]} ) if r['phase']=='REROLL' else action(r,'call' if e.seat(r,r['actor'])['commitment']<r['target'] else 'check')
    return r

@pytest.mark.parametrize('dice,category',[([2]*5,7),([2,2,2,2,1],6),([2,2,2,3,3],5),([1,2,3,4,5],4),([2,3,4,5,6],4),([2,2,2,1,3],3),([2,2,3,3,1],2),([2,2,1,3,4],1),([1,2,3,4,6],0)])
def test_ranks(dice,category): assert e.rank(dice)[0]==category

def test_rank_kickers_and_widowmaker():
    assert e.rank([3,3,3,3,1])>e.rank([2,2,2,2,6])
    assert e.rank([2,3,4,5,6])>e.rank([1,2,3,4,5])
    assert e.rank([1,1,6,6,6])<e.rank([1,1,2,3,4])
    for d in set(itertools.permutations([6,6,6,1,1])): assert e.rank(d)==(-1,)
    assert e.rank([1,2,3,4,6]) == (0,6,4,3,2,1)

@pytest.mark.parametrize('dice',[[0]*5,[7]*5,[True]*5,[1,2],[1.0]*5])
def test_bad_dice(dice):
    with pytest.raises(e.RuleError): e.rank(dice)

def test_bets_and_cap():
    r=make();r=action(r,'bet');r=action(r,'raise');r=action(r,'raise')
    old=repr(r)
    with pytest.raises(e.RuleError): action(r,'raise')
    assert repr(r)==old
    r=action(r,'call');r=action(r,'call'); assert r['phase']=='REROLL'
    while r['phase']=='REROLL': r=action(r,'setReroll',{'indexes':[0,1,2,3,4]})
    assert all(s['rerollCount']==5 for s in r['seats'])
    assert r['phase']=='BETTING_2' and r['raises']==0
    before=e.seat(r,r['actor'])['balance'];r=action(r,'bet')
    assert before-e.seat(r,r['seats'][1]['id'])['balance']==200
    assert sum(s['balance'] for s in r['seats'])+r['pot']==30000
    r=through(r);assert sum(s['balance'] for s in r['seats'])==30000 and r['pot']==0

@pytest.mark.parametrize('indices',[[0,0],[-1],[5],[True],list(range(6)),None])
def test_bad_rerolls(indices):
    r=make(2)
    while r['phase']=='BETTING_1':r=action(r,'check')
    with pytest.raises(e.RuleError): action(r,'setReroll',{'indexes':indices})

def test_one_reroll_and_turn():
    r=make(2)
    while r['phase']=='BETTING_1': r=action(r,'check')
    old=r['actor'];r=action(r,'setReroll',{'indexes':[]})
    with pytest.raises(e.RuleError):e.apply(r,'setReroll',{'indexes':[]},sid=old,die=lambda:1)
    assert e.seat(r,old)['rerollCount']==0

def test_widowmaker_uncontested_and_adjudication():
    r=make(2)
    for s in r['seats']:s['dice']=[6,6,6,1,1]
    final=action(r,'fold');assert final['phase']=='READY_NEXT_HAND' and final['revealed']==[]
    assert sum(s['balance'] for s in final['seats'])==20000
    r=through(r);assert r['phase']=='ADJUDICATION'
    r=e.apply(r,'adjudicate',{'reason':'refund'},gm=True);assert all(s['balance']==10000 for s in r['seats'])

def test_widowmaker_loses_and_folded_stays_hidden():
    r=make();r['seats'][0]['dice']=[1,1,6,6,6];r['seats'][2]['dice']=[1,1,2,3,4]
    r=action(r,'fold');r=through(r)
    assert r['seats'][2]['balance']>10000
    assert 'dice' not in e.view(r)['seats'][1]

def test_underfunded_and_turns():
    r=e.room('test');e.add_seat(r,'poor',99);e.add_seat(r,'rich',1000)
    with pytest.raises(e.RuleError):e.apply(r,'startHand',{},gm=True,die=lambda:1)
    e.add_seat(r,'third',100);r=e.apply(r,'startHand',{},gm=True,die=lambda:1)
    assert r['seats'][0]['folded'];assert r['actor']=='2'
    r=action(r,'bet')
    with pytest.raises(e.RuleError): action(r,'call')
    r=action(r,'fold')
    with pytest.raises(e.RuleError):e.apply(r,'startHand',{},gm=True,die=lambda:1)
    r=through(make());r=e.apply(r,'startHand',{},gm=True,die=lambda:1)
    assert r['dealer']==1

def test_tie_remainder():
    r=make();r['pot']+=1;r['seats'][0]['balance']-=1
    r['seats'][0]['dice']=[1]*5
    r=through(r)
    assert r['seats'][1]['balance']==10051 and r['seats'][2]['balance']==10050

def test_privacy_and_scripts():
    r=make();e.add_seat if False else None
    assert 'dice' not in e.view(r,gm=True)['seats'][0]
    assert 'dice' in e.view(r,sid='1')['seats'][0]
    assert 'dice' not in e.view(r,sid='1')['seats'][1]
    with pytest.raises(e.RuleError):e.apply(r,'startHand',{})
    r=e.room('npc');e.add_seat(r,'human',1000);e.add_seat(r,'npc',1000,True)
    r=e.apply(r,'scriptNPC',{'seatId':'2','queue':[{'initial':[1]*5,'replacements':[6]*5}]},gm=True)
    assert 'queue' not in e.view(r)['seats'][1]
    r=e.apply(r,'startHand',{},gm=True,die=lambda:2)
    assert r['seats'][1]['dice']==[1]*5
    r=e.apply(r,'takeNPCAction',{'action':'bet'},gm=True,die=lambda:1)
    assert any(ev['name']=='gmNPCAction' for ev in r['events'])

def test_widowmaker_loses_to_high_bones():
    r=make(2);r['seats'][0]['dice']=[6,6,6,1,1];r['seats'][1]['dice']=[1,2,3,4,6]
    r=through(r);assert r['seats'][1]['balance']==10100

def test_every_kicker_category_and_ties():
    pairs=[([2]*5,[1]*5),([2,2,2,2,6],[2,2,2,2,5]),([3,3,3,2,2],[2,2,2,6,6]),([3,3,3,6,2],[3,3,3,5,4]),([4,4,3,3,6],[4,4,2,2,6]),([3,3,6,5,4],[3,3,6,5,2]),([1,2,4,5,6],[1,2,3,5,6])]
    for high,low in pairs:assert e.rank(high)>e.rank(low)
    assert e.rank([2,2,3,3,6])==e.rank([6,3,2,2,3])

def test_illegal_actions_are_atomic():
    r=make(2)
    with pytest.raises(e.RuleError): action(r,'call')
    r=action(r,'bet');old=repr(r)
    with pytest.raises(e.RuleError): action(r,'check')
    assert repr(r)==old

def test_session_money_many_hands():
    import random
    rng=random.Random(42);r=e.room('random',10)
    for i in range(6): e.add_seat(r,str(i),100000,npc=i==5)
    for _ in range(50):
        r=e.apply(r,'startHand',{},gm=True,die=lambda:rng.randint(1,6))
        while r['phase'] not in ('READY_NEXT_HAND','ADJUDICATION'):
            s=e.seat(r,r['actor']);phase=r['phase']
            if phase=='REROLL':a='setReroll';data={'indexes':rng.sample(range(5),rng.randint(0,5))}
            else:
                a=rng.choice(['fold','call' if s['commitment']<r['target'] else 'check']+(['raise' if r['target'] else 'bet'] if r['raises']<2 else []));data={}
            if s['npc']:r=e.apply(r,'takeNPCAction',{'action':a,'data':data},gm=True,die=lambda:rng.randint(1,6))
            else:r=e.apply(r,a,data,sid=s['id'],die=lambda:rng.randint(1,6))
            assert sum(x['balance'] for x in r['seats'])+r['pot']==600000
        if r['phase']=='ADJUDICATION':r=e.apply(r,'adjudicate',{'reason':'test refund'},gm=True)
        assert sum(x['balance'] for x in r['seats'])==600000

def test_campaign_settlement_example():
    r=e.room('settlement',1000)
    e.add_seat(r,'Adventurer',12500);e.add_seat(r,'Opponent',12500)
    r=e.apply(r,'startHand',{},gm=True,die=lambda:1)
    r=action(r,'check');r=action(r,'fold')
    assert r['seats'][0]['balance']==11500
    rolls=iter([6]*5+[1]*5)
    r=e.apply(r,'startHand',{},gm=True,die=lambda:next(rolls))
    r=action(r,'bet');r=action(r,'call');r=through(r)
    assert r['seats'][0]['balance']==13500
    assert sum(x['amountCp'] for x in r['ledger'] if x['seatId']=='1')==1000
