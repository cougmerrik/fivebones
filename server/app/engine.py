"""Pure room state machine. Money is integer copper; RNG is injected by caller."""
from collections import Counter
from copy import deepcopy

class RuleError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise RuleError(message)

def rank(dice):
    require(len(dice) == 5 and all(type(d) is int and 1 <= d <= 6 for d in dice), 'INVALID_DICE')
    if sorted(dice) == [1, 1, 6, 6, 6]:
        return (-1,)
    groups = sorted(((n, face) for face, n in Counter(dice).items()), reverse=True)
    counts = [n for n, _ in groups]
    faces = tuple(face for _, face in groups)
    if counts == [5]: return (7, *faces)
    if counts == [4, 1]: return (6, *faces)
    if counts == [3, 2]: return (5, *faces)
    if sorted(dice) in ([1,2,3,4,5], [2,3,4,5,6]): return (4, max(dice))
    if counts == [3,1,1]: return (3, *faces)
    if counts == [2,2,1]: return (2, *faces)
    if counts == [2,1,1,1]: return (1, *faces)
    return (0, *sorted(dice, reverse=True))

def room(name, small=100, ante=None, ties='kickers', remainder='clockwise'):
    require(small in (10,100,1000), 'INVALID_STAKES')
    require(ante is None or type(ante) is int and 0 <= ante <= small, 'INVALID_ANTE')
    require(ties in ('kickers','category') and remainder in ('clockwise','counterclockwise'), 'INVALID_CONFIG')
    return dict(name=name, small=small, ante=small if ante is None else ante, ties=ties, remainder=remainder,
                seats=[], phase='LOBBY', version=0, hand=0, dealer=-1, actor=None, pot=0,
                events=[], ledger=[], audit=[], ended=False, revealed=[], receipts={})

def add_seat(r, name, balance, npc=False):
    require(r['phase'] in ('LOBBY','READY_NEXT_HAND') and not r['ended'], 'WRONG_PHASE')
    require(sum(s['npc'] == npc for s in r['seats']) < 5, 'ROOM_FULL')
    require(type(balance) is int and 0 <= balance <= 1000000000, 'INVALID_BALANCE')
    sid = str(len(r['seats']) + 1)
    r['seats'].append(dict(id=sid, name=name, npc=npc, opening=balance, balance=balance, queue=[],
                           dice=[], folded=True, contribution=0, commitment=0, rerollCount=None, nextHand=True, removed=False))
    return sid

def seat(r, sid):
    return next(s for s in r['seats'] if s['id'] == sid)

def active(r): return [s for s in r['seats'] if not s['folded']]

def order(r):
    seats = r['seats']; start = (r['dealer'] + 1) % len(seats)
    return seats[start:] + seats[:start]

def event(r, kind, **data):
    r['events'].append(dict(seq=len(r['events'])+1, hand=r['hand'], name=kind, **data))

def transfer(r, s, amount, kind):
    require(s['balance'] + amount >= 0, 'INSUFFICIENT_FUNDS')
    s['balance'] += amount
    r['pot'] -= amount
    r['ledger'].append(dict(hand=r['hand'], seatId=s['id'], amountCp=amount, kind=kind))
    event(r, kind, seatId=s['id'], amountCp=amount)

def pay(r, s, amount):
    transfer(r,s,-amount,'wager'); s['commitment'] += amount; s['contribution'] += amount

def settle(r, winners, refund=False):
    if refund:
        for s in r['seats']:
            if s['contribution']: transfer(r,s,s['contribution'],'refund')
    else:
        ordered = [s for s in order(r) if s['id'] in winners]
        if r['remainder'] == 'counterclockwise': ordered.reverse()
        share, rem = divmod(r['pot'],len(ordered))
        for i,s in enumerate(ordered): transfer(r,s,share+(i<rem),'payout')
    r['phase']='READY_NEXT_HAND'; r['actor']=None
    expire_cheats(r)
    event(r,'settlement',winners=winners, refund=refund)

def showdown(r):
    r['revealed']=[s['id'] for s in active(r)]
    ranks={s['id']:rank(s['dice']) for s in active(r)}
    if all(v == (-1,) for v in ranks.values()):
        r['phase']='ADJUDICATION'; r['actor']=None; event(r,'allWidowmakers'); return
    if r['ties'] == 'category': ranks={k:v[:1] for k,v in ranks.items()}
    best=max(ranks.values()); settle(r,[k for k,v in ranks.items() if v==best])

def betting(r, phase):
    r['phase']=phase; r['target']=0; r['raises']=0
    for s in r['seats']: s['commitment']=0
    r['pending']=[s['id'] for s in order(r) if not s['folded']]
    r['actor']=r['pending'][0]

def advance(r):
    if len(active(r)) == 1:
        settle(r,[active(r)[0]['id']]); return
    if r['pending']:
        r['actor']=r['pending'][0]; return
    if r['phase']=='BETTING_1':
        r['phase']='REROLL'; r['pending']=[s['id'] for s in order(r) if not s['folded']]; r['actor']=r['pending'][0]
    elif r['phase']=='REROLL': betting(r,'BETTING_2')
    else: showdown(r)

CHEAT_PHASES = ('BETTING_1', 'REROLL', 'BETTING_2')

def ability_scores(dexterity):
    require(type(dexterity) is int and 1 <= dexterity <= 30, 'INVALID_ABILITY_SCORE')
    return dict(dexterity=dexterity)

def expire_cheats(r):
    for request in r.get('cheatRequests', []):
        if request['status'] in ('pending', 'applied') and (
            request['hand'] != r['hand'] or r['phase'] not in CHEAT_PHASES
            or seat(r, request['seatId'])['folded']
        ):
            request['status'] = 'expired'

def cheat_check(s, ability, randbelow):
    require(ability == 'dexterity', 'INVALID_ABILITY')
    scores = s.get('abilities')
    require(scores is not None, 'ABILITY_SCORES_REQUIRED')
    roll = randbelow(20) + 1
    modifier = (scores[ability] - 10) // 2
    return dict(ability=ability, score=scores[ability], roll=roll, modifier=modifier, total=roll + modifier)

def loaded_face(randbelow):
    # Exactly 165/500 = 33% for five; 67/500 = 13.4% for every other face.
    draw = randbelow(500)
    return 5 if draw < 165 else (1, 2, 3, 4, 6)[(draw - 165) // 67]

def change_die(r, s, index, face, reason, request_id=None, actor='gm'):
    require(type(index) is int and 0 <= index < 5, 'INVALID_DIE_INDEX')
    require(type(face) is int and 1 <= face <= 6, 'INVALID_DICE')
    require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 500, 'REASON_REQUIRED')
    before = s['dice'][index]
    s['dice'][index] = face
    record = dict(id=len(r.setdefault('diceChanges', [])) + 1, hand=r['hand'], seatId=s['id'],
                  dieIndex=index, before=before, after=face, reason=reason.strip(), requestId=request_id, actor=actor)
    r['diceChanges'].append(record)
    r.setdefault('audit', []).append(dict(kind='gmNPCCheatApplied' if actor=='gm:npc' else 'gmDiceChanged' if actor=='gm' else 'playerCheatApplied', **deepcopy(record)))
    return record

def apply_cheat(r, action, data, gm, sid, randbelow, npc=False):
    """Private, GM-adjudicated actions. No cheat detail enters the public event log."""
    if action in ('setAbilities', 'setNPCDexterity'):
        if action == 'setNPCDexterity':
            require(gm, 'UNAUTHORIZED')
            sid = data['seatId']
        else:
            require(sid is not None and not gm, 'UNAUTHORIZED')
        s = seat(r, sid)
        require(s['npc'] == (action == 'setNPCDexterity'), 'UNAUTHORIZED')
        require(s.get('abilities') is None, 'DEXTERITY_LOCKED')
        require(r['phase'] in ('LOBBY', 'READY_NEXT_HAND') or
                (s.get('abilities') is None and sid == r['actor'] and r['phase'] in CHEAT_PHASES), 'WRONG_PHASE')
        s['abilities'] = ability_scores(data['dexterity'])
        return r
    require(r['phase'] in CHEAT_PHASES, 'WRONG_PHASE')
    requests = r.setdefault('cheatRequests', [])
    if action == 'requestCheat':
        require((npc and gm) or (not npc and sid is not None and not gm), 'UNAUTHORIZED')
        require(sid == r['actor'], 'NOT_YOUR_TURN')
        s = seat(r, sid)
        require(not s['folded'] and s['npc'] == npc, 'UNAUTHORIZED')
        require(not any(q['seatId'] == sid and q['hand'] == r['hand'] for q in requests), 'CHEAT_ALREADY_USED')
        kind = data.get('kind')
        require(kind in ('loadedDie', 'changeDie', 'other'), 'INVALID_CHEAT')
        q = dict(id=str(len(requests) + 1), hand=r['hand'], phase=r['phase'], seatId=sid,
                 kind=kind, status='pending', check=None)
        if kind == 'other':
            require(set(data) == {'kind', 'description'}, 'INVALID_DATA')
            description = data.get('description')
            require(isinstance(description, str) and 1 <= len(description.strip()) <= 500, 'DESCRIPTION_REQUIRED')
            q['description'] = description.strip()
        else:
            require(set(data) == ({'kind', 'dieIndex', 'face'} if kind == 'changeDie' else {'kind', 'dieIndex'}), 'INVALID_DATA')
            index = data.get('dieIndex')
            require(type(index) is int and 0 <= index < 5, 'INVALID_DIE_INDEX')
            q['dieIndex'] = index
            if kind == 'changeDie':
                face = data.get('face')
                require(type(face) is int and 1 <= face <= 6, 'INVALID_DICE')
                q['face'] = face
            q['check'] = cheat_check(s, 'dexterity', randbelow)
            face = loaded_face(randbelow) if kind == 'loadedDie' else q['face']
            if kind == 'loadedDie': s.setdefault('loadedIndexes', []).append(index)
            q['change'] = change_die(r, s, index, face, 'Loaded die swap' if kind == 'loadedDie' else 'Changed die face', q['id'], actor='gm:npc' if npc else sid)
            q['status'] = 'applied'
        requests.append(q)
        r.setdefault('audit', []).append(dict(kind='gmNPCCheatRequested' if npc else 'cheatRequested', request=deepcopy(q)))
        return r
    require(gm, 'UNAUTHORIZED')
    if action == 'gmChangeDie':
        s = seat(r, data['seatId'])
        require(not s['folded'], 'FOLDED')
        change_die(r, s, data['dieIndex'], data['face'], data['reason'])
        return r
    q = next((q for q in requests if q['id'] == data.get('requestId')), None)
    require(q is not None, 'REQUEST_NOT_FOUND')
    require(q['hand'] == r['hand'] and q['status'] in ('pending', 'applied'), 'REQUEST_CLOSED')
    s = seat(r, q['seatId'])
    require(not s['folded'], 'FOLDED')
    if action == 'rollCheatCheck':
        require(q['kind'] == 'other' and q['check'] is None, 'CHECK_ALREADY_ROLLED')
        q['check'] = cheat_check(s, data['ability'], randbelow)
        r.setdefault('audit', []).append(dict(kind='gmCheatCheck', hand=r['hand'], requestId=q['id'], check=deepcopy(q['check'])))
        return r
    require(data.get('decision') == 'noted', 'INVALID_DECISION')
    reason = data.get('reason')
    require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 500, 'REASON_REQUIRED')
    q.update(status='adjudicated' if q['kind']=='other' else 'acknowledged', reason=reason.strip())
    r.setdefault('audit', []).append(dict(kind='gmCheatResolved', hand=r['hand'], request=deepcopy(q)))
    return r

def _apply(original, action, data, gm=False, sid=None, die=None, randbelow=None):
    """Returns a new aggregate, leaving original untouched on any rejection."""
    r=deepcopy(original)
    require(not r['ended'], 'SESSION_ENDED')
    if action == 'setParticipation':
        require(sid is not None or gm, 'UNAUTHORIZED')
        target = data.get('seatId') if gm else sid
        require(gm or 'seatId' not in data, 'UNAUTHORIZED')
        s = next((x for x in r['seats'] if x['id'] == target), None)
        require(s is not None, 'SEAT_NOT_FOUND')
        require(gm or not s['npc'], 'UNAUTHORIZED')
        require(not s.get('removed', False), 'SEAT_REMOVED')
        require(type(data.get('participating')) is bool, 'INVALID_PARTICIPATION')
        s['nextHand'] = data['participating']
        event(r, 'participationChanged', seatId=target, participating=s['nextHand'])
        return r
    if action in ('removeSeat', 'restoreSeat'):
        require(gm, 'UNAUTHORIZED')
        s = next((x for x in r['seats'] if x['id'] == data.get('seatId')), None)
        require(s is not None, 'SEAT_NOT_FOUND')
        if action == 'restoreSeat':
            require(s.get('removed', False), 'SEAT_NOT_REMOVED')
            s.update(removed=False, nextHand=True)
            event(r, 'seatRestored', seatId=s['id'])
            return r
        require(data.get('confirmed') is True, 'CONFIRMATION_REQUIRED')
        require(r['phase'] != 'ADJUDICATION', 'ADJUDICATION_REQUIRED')
        require(not s.get('removed', False), 'SEAT_REMOVED')
        s.update(removed=True, nextHand=False)
        event(r, 'seatRemoved', seatId=s['id'])
        r['audit'].append(dict(kind='gmSeatRemoved', hand=r['hand'], seatId=s['id']))
        if r['phase'] in CHEAT_PHASES and not s['folded']:
            s['folded'] = True
            r['pending'] = [x for x in r['pending'] if x != s['id']]
            advance(r)
            expire_cheats(r)
        return r
    if action == 'requestNPCCheat':
        require(gm, 'UNAUTHORIZED')
        require(r['actor'] is not None and seat(r, r['actor'])['npc'], 'NOT_NPC_TURN')
        return apply_cheat(r, 'requestCheat', data, gm, r['actor'], randbelow, npc=True)
    if action in ('setAbilities', 'setNPCDexterity', 'requestCheat', 'gmChangeDie', 'rollCheatCheck', 'resolveCheat'):
        return apply_cheat(r, action, data, gm, sid, randbelow)
    if action=='addNPC':
        require(gm,'UNAUTHORIZED')
        scores=ability_scores(data.get('dexterity',10))
        npc_id=add_seat(r,data['name'],data['startingCp'],True)
        seat(r,npc_id)['abilities']=scores
        event(r,'npcAdded'); return r
    if action=='scriptNPC':
        require(gm,'UNAUTHORIZED'); s=seat(r,data['seatId']); require(s['npc'],'UNAUTHORIZED')
        queue=data['queue']; require(type(queue) is list and len(queue)<=10,'INVALID_QUEUE')
        for item in queue:
            require(type(item) is dict and 'initial' in item and set(item)<= {'initial','replacements'} and type(item['initial']) is list,'INVALID_QUEUE'); rank(item['initial'])
            require(type(item.get('replacements',[])) is list and len(item.get('replacements',[]))<=5 and all(type(v) is int and 1<=v<=6 for v in item.get('replacements',[])),'INVALID_QUEUE')
        s['queue']=queue; r['audit'].append(dict(hand=r['hand'],seatId=s['id'],kind='npcScriptAuthorized',queue=deepcopy(queue))); event(r,'npcScriptAuthorized',seatId=s['id']); return r
    if action=='startHand':
        require(gm,'UNAUTHORIZED'); require(r['phase'] in ('LOBBY','READY_NEXT_HAND'),'WRONG_PHASE')
        entrants=[s for s in r['seats'] if s.get('nextHand', True) and not s.get('removed', False) and s['balance']>=r['ante'] and s['balance']>0]
        require(len(entrants)>=2,'INSUFFICIENT_SEATS')
        r['hand']+=1; r['dealer']=(r['dealer']+1)%len(r['seats']); r['revealed']=[]
        for s in r['seats']:
            s.update(loadedIndexes=[], folded=s not in entrants, contribution=0, commitment=0, rerollCount=None, dice=[], replacements=[])
            if not s['folded']:
                pay(r,s,r['ante'])
                script=s['queue'].pop(0) if s['npc'] and s['queue'] else None
                s['dice']=script['initial'][:] if script else [die() for _ in range(5)]
                s['replacements']=script.get('replacements',[])[:] if script else []
        betting(r,'BETTING_1'); expire_cheats(r); event(r,'handStarted'); return r
    if action=='adjudicate':
        require(gm,'UNAUTHORIZED'); require(r['phase']=='ADJUDICATION','WRONG_PHASE')
        require(isinstance(data.get('reason'),str) and 1<=len(data['reason'])<=200,'REASON_REQUIRED')
        event(r,'gmAdjudication',reason=data['reason']); settle(r,[],True); return r
    if action=='endSession':
        require(gm,'UNAUTHORIZED'); require(r['phase'] in ('LOBBY','READY_NEXT_HAND'),'WRONG_PHASE')
        r['ended']=True; event(r,'sessionEnded'); return r
    if action=='takeNPCAction':
        require(gm,'UNAUTHORIZED'); sid=r['actor']; require(sid is not None and seat(r,sid)['npc'],'NOT_NPC_TURN')
        action=data['action']; data=data.get('data',{}); event(r,'gmNPCAction',seatId=sid,action=action)
    if action=='forceFold':
        require(gm and data.get('confirmed') is True,'CONFIRMATION_REQUIRED')
        sid=r['actor']; action='fold'; event(r,'gmForceFold',seatId=sid)
    require(r['phase'] in ('BETTING_1','REROLL','BETTING_2'),'WRONG_PHASE')
    require(sid is not None and sid==r['actor'],'NOT_YOUR_TURN'); s=seat(r,sid)
    require(not s['folded'],'FOLDED')
    if action=='fold': s['folded']=True
    elif r['phase']=='REROLL':
        require(action=='setReroll' and s['rerollCount'] is None,'INVALID_REROLL')
        indexes=data.get('indexes'); require(isinstance(indexes,list) and len(indexes)<=5 and all(type(i) is int and 0<=i<5 for i in indexes) and len(set(indexes))==len(indexes),'INVALID_REROLL')
        for i in indexes: s['dice'][i]=loaded_face(randbelow) if i in s.get('loadedIndexes',[]) else s['replacements'].pop(0) if s['replacements'] else die()
        s['rerollCount']=len(indexes); event(r,'rerollCount',seatId=sid,count=len(indexes))
    else:
        due=r['target']-s['commitment']; increment=r['small']*(2 if r['phase']=='BETTING_2' else 1)
        if action=='check': require(due==0,'CANNOT_CHECK')
        elif action=='call': require(due>0,'NOTHING_TO_CALL'); pay(r,s,due)
        elif action in ('bet','raise'):
            require((action=='bet' and r['target']==0) or (action=='raise' and r['target']>0 and r['raises']<2),'RAISE_CAP_OR_INVALID_BET')
            pay(r,s,due+increment); r['target']+=increment
            if action=='raise': r['raises']+=1
            r['pending']=[x['id'] for x in order(r) if not x['folded'] and x['id']!=sid]
            # Action continues clockwise after the bettor, not from dealer.
            ids=[x['id'] for x in r['seats']]; k=ids.index(sid)
            cycle=ids[k+1:]+ids[:k]; r['pending']=[x for x in cycle if x in r['pending']]
        else: raise RuleError('INVALID_ACTION')
        event(r,action,seatId=sid)
    r['pending']=[x for x in r['pending'] if x!=sid and not seat(r,x)['folded']]
    advance(r); expire_cheats(r); return r

def apply(original, action, data, gm=False, sid=None, die=None, randbelow=None):
    result = _apply(original, action, data, gm, sid, die, randbelow)
    # Only public actions update this recap. Private cheats and scripts never do.
    ordinary = data.get('action') if action == 'takeNPCAction' else action
    actor_id = original.get('actor') if gm else sid
    if action == 'forceFold': actor_id = original.get('actor')
    if action == 'removeSeat': actor_id = data.get('seatId')
    actor = next((s for s in result['seats'] if s['id'] == actor_id), None)
    text = None
    if ordinary in ('check', 'call', 'bet', 'raise', 'fold', 'setReroll') or action == 'forceFold':
        name = actor['name']
        paid = -sum(x['amountCp'] for x in result['ledger'][len(original['ledger']):]
                    if x['seatId'] == actor_id and x['kind'] == 'wager')
        if action == 'forceFold': text = f"The GM folded {name}."
        elif ordinary == 'setReroll':
            count = seat(result, actor_id)['rerollCount']
            text = f"{name} stood pat." if count == 0 else f"{name} rerolled {count} dice."
        elif ordinary == 'check': text = f"{name} checked."
        elif ordinary == 'fold': text = f"{name} folded."
        elif ordinary == 'raise': text = f"{name} raised, paying {paid / 100:.2f} gp."
        else: text = f"{name} {'called' if ordinary == 'call' else 'bet'} {paid / 100:.2f} gp."
    elif action == 'removeSeat': text = f"The GM removed {actor['name']} from play."
    elif action == 'startHand': text = f"Hand {result['hand']} began. Antes were collected and private dice rolled."
    elif action == 'endSession': text = f"The GM finished the session after {result['hand']} hands."
    elif action == 'adjudicate': text = 'The GM refunded the hand after adjudicating the Widowmakers.'
    if text and result['phase'] != original['phase']:
        if result['phase'] == 'READY_NEXT_HAND':
            settlement = next(x for x in reversed(result['events']) if x['name'] == 'settlement')
            text += ' Contributions were refunded.' if settlement['refund'] else ' Hand complete; winner' + ('s: ' if len(settlement['winners']) > 1 else ': ') + ', '.join(seat(result, x)['name'] for x in settlement['winners']) + '.'
        elif result['phase'] == 'REROLL': text += ' Rerolls begin.'
        elif result['phase'] == 'BETTING_2': text += ' Betting 2 begins.'
        elif result['phase'] == 'ADJUDICATION': text += ' All remaining hands are Widowmakers; GM adjudication is required.'
    if text: result['lastTurn'] = text
    return result

def view(r, sid=None, gm=False):
    seats=[]
    for s in r['seats']:
        public={k:s[k] for k in ('id','name','npc','opening','balance','folded','contribution','commitment','rerollCount')}
        public.update(nextHand=s.get('nextHand', True), removed=s.get('removed', False))
        if s['id']==sid or s['id'] in r['revealed'] or (gm and s['npc']): public['dice']=s['dice']
        if s['id'] in r['revealed']: public['handRank']={-1:'Widowmaker',0:'High bones',1:'One pair',2:'Two pair',3:'Three of a kind',4:'Straight',5:'Full house',6:'Four of a kind',7:'Five of a kind'}[rank(s['dice'])[0]]
        if gm and s['npc']: public['queue']=s['queue']
        if s['id']==sid or gm:
            public['abilities']=s.get('abilities')
            public['loadedIndexes']=s.get('loadedIndexes',[])
        seats.append(public)
    keys=('name','small','ante','ties','remainder','phase','version','hand','dealer','actor','pot','events','ledger','ended')
    result={k:r[k] for k in keys}; result.update(seats=seats, role='gm' if gm else 'player' if sid else 'spectator', seatId=sid)
    result['cheatRequests']=[deepcopy(q) for q in r.get('cheatRequests',[]) if gm or q['seatId']==sid]
    result['diceChanges']=[deepcopy(c) for c in r.get('diceChanges',[]) if gm or c['seatId']==sid]
    if gm: result['audit']=r.get('audit',[])
    result['lastTurn']=r.get('lastTurn', 'No turn has been taken yet.')
    result['target']=r.get('target',0); result['raises']=r.get('raises',0)
    return result
