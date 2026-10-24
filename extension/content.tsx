import React from 'react';
import {createRoot} from 'react-dom/client';
import {FiveBonesApp} from '../packages/ui/App';
import css from '../packages/ui/style.css';
declare const FIVE_BONES_API:string;
declare const FIVE_BONES_WS:string;
declare const chrome:any;
if(window===window.top&&!document.getElementById('five-bones-overlay')){
 const host=document.createElement('div');host.id='five-bones-overlay';host.style.cssText='position:fixed;inset:0;z-index:2147483000;pointer-events:none';document.documentElement.append(host);
 const root=host.attachShadow({mode:'closed'});const style=document.createElement('style');
 style.textContent=css+` :host{all:initial}.launcher{position:fixed;right:20px;bottom:20px;pointer-events:auto;background:#30261b;color:#f2d193;border:1px solid #d1ad69;padding:12px 18px;border-radius:8px;font:16px Georgia;cursor:pointer}.window{pointer-events:auto;position:fixed;right:20px;top:30px;width:850px;height:650px;max-width:96vw;max-height:94vh;min-width:320px;min-height:220px;resize:both;overflow:auto;background:#171512;border:2px solid #b88c43;border-radius:8px;box-shadow:0 12px 45px #0008}.bar{display:flex;position:sticky;top:0;z-index:2;background:#32271c;color:#f2d193;padding:8px;gap:8px;touch-action:none}.bar button{font:14px system-ui;color:#f2d193;background:#171512;border:1px solid #c6a46b;padding:8px;cursor:pointer}.handle{cursor:move;flex:1;text-align:left}.window[hidden]{display:none}`;
 root.append(style);const launcher=document.createElement('button');launcher.className='launcher';launcher.textContent='⚄ Five Bones';root.append(launcher);
 const panel=document.createElement('section');panel.className='window';panel.hidden=true;panel.setAttribute('aria-label','Five Bones game overlay');root.append(panel);
 const bar=document.createElement('div');bar.className='bar';const drag=document.createElement('button');drag.className='handle';drag.textContent='Five Bones · drag / arrow keys to move';bar.append(drag);
 const minimize=document.createElement('button');minimize.textContent='Minimize';bar.append(minimize);const close=document.createElement('button');close.textContent='Close';bar.append(close);panel.append(bar);
 const mount=document.createElement('div');panel.append(mount);chrome.storage.local.get('session:'+FIVE_BONES_API,(data:any)=>{createRoot(mount).render(<FiveBonesApp assetUrl={path=>chrome.runtime.getURL(path)} api={FIVE_BONES_API} wsApi={FIVE_BONES_WS} npcPresetStore={{load:()=>new Promise((resolve,reject)=>chrome.storage.local.get('npc-presets:'+FIVE_BONES_API,(data:any)=>chrome.runtime.lastError?reject(Error(chrome.runtime.lastError.message)):resolve(data['npc-presets:'+FIVE_BONES_API]||[]))),save:presets=>new Promise<void>((resolve,reject)=>chrome.storage.local.set({['npc-presets:'+FIVE_BONES_API]:presets},()=>chrome.runtime.lastError?reject(Error(chrome.runtime.lastError.message)):resolve()))}} isolatedSession={data['session:'+FIVE_BONES_API]||null} onSession={session=>chrome.storage.local.set({['session:'+FIVE_BONES_API]:session})}/>)});
 const save=()=>chrome.storage.local.set({layout:{left:panel.offsetLeft,top:panel.offsetTop,width:panel.offsetWidth,height:panel.offsetHeight}});
 chrome.storage.local.get('layout',(data:any)=>{const l=data.layout;if(l){panel.style.left=Math.max(0,Math.min(l.left,innerWidth-100))+'px';panel.style.top=Math.max(0,Math.min(l.top,innerHeight-60))+'px';panel.style.width=l.width+'px';panel.style.height=l.height+'px';panel.style.right='auto'}});
 launcher.onclick=()=>{panel.hidden=false;drag.focus()};minimize.onclick=close.onclick=()=>{panel.hidden=true;launcher.focus();save()};
 let point:{x:number;y:number;l:number;t:number}|null=null;
 drag.onpointerdown=ev=>{point={x:ev.clientX,y:ev.clientY,l:panel.offsetLeft,t:panel.offsetTop};drag.setPointerCapture(ev.pointerId)};
 drag.onpointermove=ev=>{if(!point)return;panel.style.left=Math.max(0,Math.min(innerWidth-100,point.l+ev.clientX-point.x))+'px';panel.style.top=Math.max(0,Math.min(innerHeight-60,point.t+ev.clientY-point.y))+'px';panel.style.right='auto'};
 drag.onpointerup=()=>{point=null;save()};drag.onkeydown=ev=>{const steps:Record<string,number[]>={ArrowLeft:[-20,0],ArrowRight:[20,0],ArrowUp:[0,-20],ArrowDown:[0,20]};const s=steps[ev.key];if(s){ev.preventDefault();panel.style.left=Math.max(0,Math.min(innerWidth-100,panel.offsetLeft+s[0]))+'px';panel.style.top=Math.max(0,Math.min(innerHeight-60,panel.offsetTop+s[1]))+'px';panel.style.right='auto';save()}};
 new ResizeObserver(()=>{if(!panel.hidden)save()}).observe(panel);
}
