import React,{useCallback,useEffect,useMemo,useRef,useState} from 'react';
import {FiveBonesApp} from './App';
import {Session} from '../contracts';
import {RulesHelp} from './RulesHelp';
import landscape from '../../landscape_bg.png';
import portrait from '../../portrait_bg.png';
import title from '../../title.png';

export interface CampaignStore {load:(key:string)=>Promise<unknown>;save:(key:string,value:unknown)=>Promise<void>}
interface Info {alias:string;roomId:string|null;available:boolean;ended:boolean;canJoin:boolean;playerUrl:string}
interface PendingJoin {expectedRoomId:string;joinKey:string;name:string;startingCp:number;dexterity:number}
type Props=React.ComponentProps<typeof FiveBonesApp>&{credentialStore?:CampaignStore;dmMode?:boolean};
interface Archive {roomId:string;hand:number;seats:{id:string;name:string;npc:boolean;opening:number;balance:number}[]}
const alias='belwether';
const validSession=(value:any):value is Session=>!!value&&typeof value.roomId==='string'&&typeof value.seatToken==='string';
const friendly:Record<string,string>={CAMPAIGN_UPGRADE_REQUIRED:'Ask the DM to finish this session and start a fresh Belwether session.',HOST_SECRET_REQUIRED:'That DM access key was not accepted.',END_CURRENT_SESSION_FIRST:'Finish the current session before starting a fresh one.',CAMPAIGN_CHANGED:'The session changed. Please try again.',SESSION_ENDED:'This session has finished. Wait for the DM to start a fresh one.',WRONG_PHASE:'A hand is in progress. Join between hands.',ROOM_FULL:'All player seats are occupied.',JOIN_DETAILS_CHANGED:'This join was already accepted with different details. Restore the original values to recover it.',DM_DEVICE_LIMIT:'The saved DM device limit has been reached.'};
class ApiError extends Error {constructor(public status:number,public code:string){super(friendly[code]||code)}}

export function CampaignApp({credentialStore,dmMode,...app}:Props) {
 const api=app.api.replace(/\/$/,'');
 const storage=useMemo<CampaignStore>(()=>credentialStore||{load:async key=>JSON.parse(localStorage.getItem('fivebones:campaign:'+api+':'+alias+':'+key)||'null'),save:async(key,value)=>localStorage.setItem('fivebones:campaign:'+api+':'+alias+':'+key,JSON.stringify(value))},[credentialStore,api]);
 const [ready,setReady]=useState(false),[role,setRole]=useState<'player'|'dm'>(dmMode?'dm':'player'),[dmToken,setDmToken]=useState(''),[session,setSession]=useState<Session|null>(null),[info,setInfo]=useState<Info|null>(null);
 const [name,setName]=useState(''),[gold,setGold]=useState('125'),[dex,setDex]=useState(''),[secret,setSecret]=useState(''),[stakes,setStakes]=useState('100'),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[manual,setManual]=useState(false),[pendingJoin,setPendingJoin]=useState<PendingJoin|null>(null),[history,setHistory]=useState<Archive[]>([]);
 const flow=useRef(0);
 const pendingStart=useRef<{id:string;expectedRoomId:string|null;smallBetCp:number}|null>(null);
 const request=useCallback(async(path:string,options:RequestInit={})=>{
  const response=await fetch(api+'/api/v1/campaigns/'+alias+path,{cache:'no-store',...options});
  const value=await response.json();if(!response.ok)throw new ApiError(response.status,typeof value.detail==='string'?value.detail:'Server request failed');return value;
 },[api]);
 useEffect(()=>{let active=true;Promise.all([storage.load('player'),storage.load('dm'),storage.load('role'),storage.load('pending-join')]).then(([saved,token,mode,pending])=>{
  if(!active)return;
  const nextRole=dmMode===undefined?(mode==='dm'?'dm':'player'):(dmMode?'dm':'player');setRole(nextRole);
  if(typeof token==='string'&&token.length<=100)setDmToken(token);
  if(nextRole==='player'&&validSession(saved))setSession(saved);
  const p=pending as PendingJoin|null;
  if(p&&typeof p.expectedRoomId==='string'&&typeof p.joinKey==='string'&&/^[0-9a-f]{64}$/.test(p.joinKey)&&typeof p.name==='string'&&Number.isInteger(p.startingCp)&&Number.isInteger(p.dexterity)){
   setPendingJoin(p);setName(p.name);setGold(String(p.startingCp/100));setDex(String(p.dexterity));
  }
  setReady(true);
 }).catch(()=>{if(active){setError('Unable to read saved access on this device.');setReady(true)}});return()=>{active=false}},[storage,dmMode]);
 useEffect(()=>{
  if(!ready||manual)return;let active=true,running=false;
  const sync=async()=>{if(running)return;running=true;const epoch=flow.current;try{
   const next:Info=await request('');if(!active||epoch!==flow.current)return;setInfo(next);
   if(role==='dm'&&dmToken){
    const value=await request('/dm-session',{headers:{Authorization:'Bearer '+dmToken}});if(!active||epoch!==flow.current)return;
    setSession(old=>value.session?(old&&old.roomId===value.session.roomId&&old.seatToken===value.session.seatToken?old:value.session):null);
   }
  }catch(err){if(!active||epoch!==flow.current)return;if(err instanceof ApiError&&err.status===401&&role==='dm'){
   setDmToken('');setSession(null);void storage.save('dm',null);setError('Enter the DM access key once to reconnect this device.');
  }else setError(err instanceof ApiError?err.message:'Unable to reach the Five Bones server. Retrying…')
  }finally{running=false}};
  void sync();const timer=setInterval(sync,3000);return()=>{active=false;clearInterval(timer)};
 },[ready,manual,role,dmToken,request,storage]);
 const setMode=async(mode:'player'|'dm')=>{if(busy)return;flow.current++;setError('');setNotice('');setSession(null);setRole(mode);await storage.save('role',mode);if(mode==='player'){const saved=await storage.load('player');if(validSession(saved))setSession(saved)}};
 const onSession=useCallback((next:Session|null)=>{if(next!==null)return;flow.current++;setSession(null);setError('');if(role==='dm'){setDmToken('');void storage.save('dm',null)}else{void storage.save('player',null);void storage.save('pending-join',null);setPendingJoin(null)}},[role,storage]);
 async function access(){setBusy(true);setError('');try{const value=await request('/dm-access',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hostSecret:secret})});await storage.save('dm',value.dmToken);await storage.save('role','dm');setDmToken(value.dmToken);setSecret('')}catch(err){setError(err instanceof Error?err.message:'Unable to unlock DM access.')}finally{setBusy(false)}}
 async function start(){setBusy(true);setError('');try{
  const current:Info=await request('');setInfo(current);
  if(current.available&&!current.ended)throw new ApiError(409,'END_CURRENT_SESSION_FIRST');
  if(current.available&&!confirm('Start a fresh session? The finished session and its ledger will remain available.'))return;
  if(!pendingStart.current||pendingStart.current.expectedRoomId!==current.roomId)pendingStart.current={id:crypto.randomUUID(),expectedRoomId:current.roomId,smallBetCp:Number(stakes)};
  const next=await request('/sessions',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+dmToken},body:JSON.stringify(pendingStart.current)});
  flow.current++;pendingStart.current=null;setSession(next);setInfo(await request(''));
 }catch(err){setError(err instanceof Error?err.message:'Unable to start the session.')}finally{setBusy(false)}}
 const cp=Math.round(Number(gold)*100),validGold=/^\d+(\.\d{1,2})?$/.test(gold)&&Number.isFinite(cp)&&cp<=1000000000;
 const validDex=/^\d+$/.test(dex)&&Number(dex)>=1&&Number(dex)<=30;
 async function join(){if(!info?.roomId)return;setBusy(true);setError('');try{
  let attempt=pendingJoin;
  if(!attempt||attempt.expectedRoomId!==info.roomId||attempt.name!==name||attempt.startingCp!==cp||attempt.dexterity!==Number(dex)){
   const random=crypto.getRandomValues(new Uint8Array(32));attempt={expectedRoomId:info.roomId,joinKey:Array.from(random,b=>b.toString(16).padStart(2,'0')).join(''),name,startingCp:cp,dexterity:Number(dex)};
   await storage.save('pending-join',attempt);setPendingJoin(attempt);
  }
  const next=await request('/join',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(attempt)});
  await storage.save('player',next);await storage.save('pending-join',null);flow.current++;setPendingJoin(null);setSession(next);
 }catch(err){setError(err instanceof Error?err.message:'Unable to join the session.')}finally{setBusy(false)}}
 async function copyLink(dm=false){try{await navigator.clipboard.writeText((info?.playerUrl||'')+(dm?'&isdm=1':''));setNotice('Link copied.')}catch{setNotice('Open the room link shown below to copy it.')}}
 async function loadHistory(){try{const result=await request('/history',{headers:{Authorization:'Bearer '+dmToken}});setHistory(result.sessions)}catch(err){setError(err instanceof Error?err.message:'Unable to load previous summaries.')}}
 const controls=<section className="campaign-controls" aria-label="Belwether room controls"><strong>Belwether</strong>{role==='dm'?<><label>Next session stakes<select value={stakes} onChange={e=>setStakes(e.target.value)}><option value="10">1 sp / 2 sp</option><option value="100">1 gp / 2 gp</option><option value="1000">10 gp / 20 gp</option></select></label><button disabled={busy||!info||info.available&&!info.ended} onClick={start}>Start fresh belwether session</button><button onClick={()=>void copyLink()}>Copy player link</button><button onClick={()=>void copyLink(true)}>Copy DM link</button><button disabled={busy} onClick={()=>void setMode('player')}>Switch to player</button><details className="campaign-history" onToggle={e=>{if(e.currentTarget.open)void loadHistory()}}><summary>Previous session summaries</summary>{history.length?history.map(old=><article key={old.roomId}><h3>Room {old.roomId} · {old.hand} hands</h3>{old.seats.map(s=><p key={s.id}>{s.name}: started {(s.opening/100).toFixed(2)} gp, finished {(s.balance/100).toFixed(2)} gp, net {s.balance-s.opening>0?'+':''}{((s.balance-s.opening)/100).toFixed(2)} gp.</p>)}</article>):<p>No finished sessions yet.</p>}</details></>:<><button disabled={busy} onClick={()=>void setMode('dm')}>DM access</button>{info?.available&&!info.ended&&info.roomId!==session?.roomId&&<button onClick={()=>{flow.current++;setSession(null);setPendingJoin(null);setName('');setGold('');setDex('');void storage.save('player',null);void storage.save('pending-join',null)}}>Join new belwether session</button>}</>}{error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}{notice&&info?.playerUrl&&<small className="campaign-url">Player link: {info.playerUrl}</small>}</section>;
 if(manual)return <FiveBonesApp {...app} campaignControls={<button className="campaign-return" onClick={()=>setManual(false)}>Use belwether room</button>}/>;
 if(session)return <FiveBonesApp {...app} key={session.roomId+':'+role} isolatedSession={session} onSession={onSession} campaignControls={controls}/>;
 const asset=app.assetUrl||((path:string)=>path);
 return <main className="bones" style={{'--landscape-background':`url("${asset(landscape)}")`,'--portrait-background':`url("${asset(portrait)}")`} as React.CSSProperties}><header><h1 className="brand-title"><img className="title-art" src={asset(title)} alt="Five Bones"/></h1></header><section className="entry campaign-entry"><div className="entry-tools"><RulesHelp state={null} assetUrl={asset}/></div><h2>{role==='dm'?'Belwether · DM':'Join Belwether'}</h2>{error&&<p role="alert">{error}</p>}{!ready?<p>Loading saved access…</p>:role==='dm'?dmToken?<><p>DM access is remembered on this device.</p><p>{info?.available?'Reconnect to the current session, or start fresh after finishing it.':'Start the session; players will find it automatically.'}</p><label>Table stakes<select value={stakes} onChange={e=>setStakes(e.target.value)}><option value="10">1 sp / 2 sp</option><option value="100">1 gp / 2 gp</option><option value="1000">10 gp / 20 gp</option></select></label><button disabled={busy||!info||info.available&&!info.ended} onClick={start}>Start belwether session</button></>:<><p>Enter your host invitation secret once. DM access will be remembered on this device.</p><label>DM access key<input type="password" autoComplete="off" value={secret} onChange={e=>setSecret(e.target.value)}/></label><button disabled={busy} onClick={access}>Remember DM access</button></>:<><p>{!info?'Finding the current session…':!info.available||info.ended?'Waiting for the DM to start a session. This panel updates automatically.':info.canJoin?'Room setup is ready. Enter your character details and join.':'A hand is in progress. You can join between hands.'}</p><label>Character name<input value={name} onChange={e=>setName(e.target.value)} maxLength={40}/></label><label>Starting GP (manual snapshot)<input inputMode="decimal" value={gold} onChange={e=>setGold(e.target.value)}/></label><label>Dexterity score<input type="number" min="1" max="30" step="1" value={dex} onChange={e=>setDex(e.target.value)}/></label><button disabled={busy||!name.trim()||!validGold||!validDex||!info?.available||info.ended||!info.canJoin&&pendingJoin?.expectedRoomId!==info.roomId} onClick={join}>Join belwether</button></>}<div className="campaign-entry-links"><button className="subtle" disabled={busy} onClick={()=>void setMode(role==='dm'?'player':'dm')}>{role==='dm'?'Join as player instead':'DM access'}</button><details><summary>Other room or recovery</summary><button disabled={busy} onClick={()=>setManual(true)}>Open manual connection</button></details></div></section></main>;
}
