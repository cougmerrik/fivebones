import React, {useState} from 'react';
import type {CheatRequest, Seat, State} from '../contracts';

type Send = (action:string, data:Record<string,unknown>)=>void;
const live = (state:State)=>['BETTING_1','REROLL','BETTING_2'].includes(state.phase)&&!state.ended;
const names = {loadedDie:'Loaded die',changeDie:'Change die',other:'Other'};
function Check({request}:{request:CheatRequest}) {
 const check=request.check;
 return check?<p className="check-result">Dexterity check: <strong>{check.roll} {check.modifier<0?'−':'+'} {Math.abs(check.modifier)} = {check.total}</strong></p>:<p>No check rolled. The DM may request one.</p>;
}

export function PlayerCheats({state,seat,send,disabled,npcMode=false}:{state:State;seat:Seat;send:Send;disabled:boolean;npcMode?:boolean}) {
 const [kind,setKind]=useState<'loadedDie'|'changeDie'|'other'>('loadedDie');
 const [index,setIndex]=useState('0'),[face,setFace]=useState('5'),[description,setDescription]=useState('');
 const [dexterity,setDexterity]=useState(String(seat.abilities?.dexterity??''));
 const requests=(state.cheatRequests||[]).filter(q=>q.hand===state.hand&&q.seatId===seat.id);
 const turn=live(state)&&state.actor===seat.id&&!seat.folded;
 const maySave=!state.ended&&(['LOBBY','READY_NEXT_HAND'].includes(state.phase)||turn&&!seat.abilities);
 return <section className={npcMode?'panel private-cheats npc-cheats':'panel private-cheats'} aria-label={npcMode?'NPC private actions':'Your private actions'}>
  <h2>{npcMode?`NPC private actions · ${seat.name}`:'Private actions'}</h2>
  {seat.abilities?<p className="dexterity-locked">Dexterity {seat.abilities.dexterity} · modifier {Math.floor((seat.abilities.dexterity-10)/2)} · locked for this session</p>:<details open><summary>Add Dexterity</summary>
   <label>Dexterity score<input type="number" min="1" max="30" step="1" value={dexterity} onChange={e=>setDexterity(e.target.value)}/></label>
   <button disabled={disabled||!maySave||!/^\d+$/.test(dexterity)||Number(dexterity)<1||Number(dexterity)>30} onClick={()=>send(npcMode?'setNPCDexterity':'setAbilities',{dexterity:Number(dexterity),...(npcMode?{seatId:seat.id}:{})})}>Save Dexterity</button>
   <p className="hint">Enter this missing score once. It is locked for the session after saving.</p>
  </details>}
  {requests.length===0?<>
   <p className="hint">{npcMode?"Once per hand, on the NPC’s turn. Visible only to the DM.":'Once per hand, on your turn. Private to you and the DM.'}</p>
   <div className="cheat-inputs"><label>Cheat action<select aria-label="Cheat action" value={kind} onChange={e=>setKind(e.target.value as typeof kind)}><option value="loadedDie">Loaded die</option><option value="changeDie">Change die</option><option value="other">Other</option></select></label>
   {kind!=='other'?<div className="cheat-fields"><label>Which die?<select aria-label="Which die?" value={index} onChange={e=>setIndex(e.target.value)}>{[0,1,2,3,4].map(i=><option key={i} value={i}>Die {i+1}{seat.dice?.[i]?` · ${seat.dice[i]}`:''}</option>)}</select></label>
    {kind==='changeDie'&&<label>New face<select aria-label="New face" value={face} onChange={e=>setFace(e.target.value)}>{[1,2,3,4,5,6].map(n=><option key={n}>{n}</option>)}</select></label>}
   </div>:<label className="other-action">What do you do?<textarea value={description} onChange={e=>setDescription(e.target.value)} maxLength={500}/></label>}</div>
   <p>{kind==='loadedDie'?'Loaded this hand: 33% chance of a 5. Swap now, roll Dexterity, and notify the DM.':kind==='changeDie'?'Choose a face, roll Dexterity, and notify the DM.':'Describe your action. The DM adjudicates and may ask for a Dexterity roll.'}</p>
   <button disabled={disabled||!turn||kind!=='other'&&!seat.abilities||kind==='other'&&!description.trim()} onClick={()=>send(npcMode?'requestNPCCheat':'requestCheat',kind==='other'?{kind,description}:{kind,dieIndex:Number(index),...(kind==='changeDie'?{face:Number(face)}:{})})}>{kind==='other'?'Send action to DM':'Cheat & roll Dexterity'}</button>
   {!turn&&<p className="hint">Available on your turn during a hand.</p>}
  </>:requests.map(q=><article key={q.id}><h3>{names[q.kind]} · {q.status}</h3>{q.description&&<p>{q.description}</p>}<Check request={q}/>{q.change&&<p>Die {q.change.dieIndex+1}: {q.change.before} → {q.change.after}</p>}{q.reason&&<p>DM: {q.reason}</p>}</article>)}
  {(state.diceChanges||[]).filter(c=>c.hand===state.hand&&c.seatId===seat.id&&c.actor==='gm').map(c=><p key={c.id} className="check-result">DM changed die {c.dieIndex+1}: {c.before} → {c.after}. {c.reason}</p>)}
 </section>;
}

function DMNotice({request,state,send,disabled}:{request:CheatRequest;state:State;send:Send;disabled:boolean}) {
 const [reason,setReason]=useState('');
 const current=live(state)&&request.hand===state.hand&&['pending','applied'].includes(request.status);
 const owner=state.seats.find(s=>s.id===request.seatId);
 return <article className="dm-notice"><h3>{owner?.name} · {names[request.kind]} · Hand {request.hand}</h3><p>Status: {request.status}</p>
  {request.description&&<p>{request.description}</p>}
  {request.dieIndex!==undefined&&<p>Die {request.dieIndex+1}{request.face!==undefined?` · requested face ${request.face}`:''}</p>}
  <Check request={request}/>{request.change&&<p>Applied immediately: die {request.change.dieIndex+1}, {request.change.before} → {request.change.after}.</p>}
  {request.reason&&<p>DM note: {request.reason}</p>}
  {current&&<>{request.kind==='other'&&!request.check&&<button disabled={disabled||!owner?.abilities} onClick={()=>send('rollCheatCheck',{requestId:request.id,ability:'dexterity'})}>Roll Dexterity for {owner?.name}</button>}
   {request.kind==='other'&&!owner?.abilities&&<p>The player must enter a Dexterity score before a check can be rolled.</p>}
   <label>DM note for {owner?.name}<textarea maxLength={500} value={reason} onChange={e=>setReason(e.target.value)}/></label>
   <button disabled={disabled||!reason.trim()} onClick={()=>send('resolveCheat',{requestId:request.id,decision:'noted',reason})}>{request.kind==='other'?'Record adjudication':'Acknowledge notification'}</button>
  </>}
 </article>;
}

export function DMCheats({state,send,disabled}:{state:State;send:Send;disabled:boolean}) {
 const [selected,setSelected]=useState(''),[index,setIndex]=useState('0'),[face,setFace]=useState('5'),[reason,setReason]=useState('');
 const eligible=state.seats.filter(s=>!s.folded);
 const target=eligible.some(s=>s.id===selected)?selected:eligible[0]?.id||'';
 const requests=state.cheatRequests||[];
 const recent=requests.filter(q=>q.hand===state.hand);
 return <section className="panel dm-cheats" aria-label="DM private adjudication">
  <h2>DM private actions {recent.some(q=>['pending','applied'].includes(q.status))?'· New':''}</h2>
  {!recent.length&&<p>No private actions this hand.</p>}
  {[...recent].reverse().map(q=><DMNotice key={q.id} request={q} state={state} send={send} disabled={disabled}/>)}
  <details><summary>Change a player's die</summary><p>Choose a die position and face. Each edit records your reason, the old face and the new face privately for you and that player.</p>
   <label>Player to adjust<select aria-label="Player to adjust" value={target} onChange={e=>setSelected(e.target.value)}>{eligible.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}</select></label>
   <div className="cheat-fields"><label>Die position<select aria-label="Die position" value={index} onChange={e=>setIndex(e.target.value)}>{[0,1,2,3,4].map(i=><option key={i} value={i}>Die {i+1}</option>)}</select></label><label>Set face<select aria-label="Set face" value={face} onChange={e=>setFace(e.target.value)}>{[1,2,3,4,5,6].map(n=><option key={n}>{n}</option>)}</select></label></div>
   <label>Reason for dice change<textarea value={reason} onChange={e=>setReason(e.target.value)} maxLength={500}/></label>
   <button disabled={disabled||!live(state)||!target||!reason.trim()} onClick={()=>send('gmChangeDie',{seatId:target,dieIndex:Number(index),face:Number(face),reason})}>Apply dice change</button>
  </details>
  <details><summary>Private action history</summary>{[...requests].reverse().map(q=><DMNotice key={q.id} request={q} state={state} send={send} disabled={disabled}/>)}
   {(state.diceChanges||[]).filter(c=>c.actor==='gm').map(c=><p key={c.id}>Hand {c.hand} · {state.seats.find(s=>s.id===c.seatId)?.name} · die {c.dieIndex+1}: {c.before} → {c.after} · {c.reason}</p>)}
  </details>
 </section>;
}
