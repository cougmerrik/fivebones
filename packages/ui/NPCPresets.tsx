import React,{useEffect,useMemo,useState} from 'react';

export interface NPCPreset {id:string;name:string;gold:string;dexterity:string}
export interface NPCPresetStore {load:()=>Promise<unknown>;save:(presets:NPCPreset[])=>Promise<void>}
export function NPCPresets({api,store,name,gold,dexterity,valid,onLoad}:{api:string;store?:NPCPresetStore;name:string;gold:string;dexterity:string;valid:boolean;onLoad:(preset:NPCPreset)=>void}) {
 const storage=useMemo<NPCPresetStore>(()=>store||{
  load:async()=>JSON.parse(localStorage.getItem('fivebones:npc-presets:'+api)||'[]'),
  save:async presets=>localStorage.setItem('fivebones:npc-presets:'+api,JSON.stringify(presets)),
 },[api,store]);
 const [presets,setPresets]=useState<NPCPreset[]>([]),[selected,setSelected]=useState(''),[ready,setReady]=useState(false),[saving,setSaving]=useState(false),[message,setMessage]=useState('');
 useEffect(()=>{let current=true;setReady(false);storage.load().then(value=>{
  if(!Array.isArray(value)||value.length>30||value.some(p=>!p||typeof p.id!=='string'||typeof p.name!=='string'||p.name.length>40||!p.name.trim()||typeof p.gold!=='string'||!/^\d+(\.\d{1,2})?$/.test(p.gold)||Number(p.gold)>10000000||typeof p.dexterity!=='string'||!/^\d+$/.test(p.dexterity)||Number(p.dexterity)<1||Number(p.dexterity)>30))throw Error('Invalid saved presets');
  if(current){setPresets(value);setReady(true)}
 }).catch(()=>{if(current)setMessage('Could not load NPC presets. Manual NPC entry still works.')});return()=>{current=false}},[storage]);
 async function persist(next:NPCPreset[],id:string,note:string){setSaving(true);try{await storage.save(next);setPresets(next);setSelected(id);setMessage(note)}catch{setMessage('Could not save NPC presets.')}finally{setSaving(false)}}
 function save(){const existing=presets.find(p=>p.name===name.trim());if(!existing&&presets.length>=30){setMessage('Keep up to 30 NPC presets. Delete one before adding another.');return}const preset={id:existing?.id||crypto.randomUUID(),name:name.trim(),gold,dexterity};void persist([...presets.filter(p=>p.id!==preset.id),preset],preset.id,'NPC preset saved in this browser or extension.')}
 return <div className="npc-presets"><h3>Saved NPC presets</h3><p className="hint">Reuse a name, starting gold, and Dexterity across rooms. Loading a preset fills the form; seating the NPC still requires the GM action below.</p><label>Saved NPC preset<select aria-label="Saved NPC preset" value={selected} disabled={!ready||saving} onChange={e=>setSelected(e.target.value)}><option value="">Choose a preset</option>{presets.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><div className="actions"><button disabled={!ready||saving||!selected} onClick={()=>{const p=presets.find(p=>p.id===selected);if(p){onLoad(p);setMessage('Preset loaded. Review the form before seating this NPC.')}}}>Load NPC preset</button><button disabled={!ready||saving||!valid||!name.trim()} onClick={save}>Save NPC preset</button><button disabled={!ready||saving||!selected} onClick={()=>void persist(presets.filter(p=>p.id!==selected),'','NPC preset deleted.')}>Delete NPC preset</button></div>{message&&<p role="status">{message}</p>}</div>
}
