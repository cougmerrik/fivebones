import React,{useEffect,useRef,useState} from 'react';
import music from '../../music.mp3';

export function BackgroundMusic({assetUrl=(url:string)=>url}:{assetUrl?:(url:string)=>string}) {
 const [enabled,setEnabled]=useState(true);
 const audio=useRef<HTMLAudioElement>(null),button=useRef<HTMLButtonElement>(null);
 useEffect(()=>{
  const player=audio.current;
  if(!player)return;
  if(!enabled){player.pause();return}
  const play=()=>{if(player.paused)void player.play().catch(()=>{/* Retry after a browser-authorized interaction. */})};
  const retry=(event:Event)=>{if(!event.composedPath().includes(button.current!))play()};
  play();
  const surface=player.parentElement!;
  surface.addEventListener('pointerdown',retry);
  surface.addEventListener('keydown',retry);
  return()=>{
   surface.removeEventListener('pointerdown',retry);
   surface.removeEventListener('keydown',retry);
   player.pause();
  };
 },[enabled]);
 function toggle(){
  if(enabled)audio.current?.pause();
  else void audio.current?.play().catch(()=>{});
  setEnabled(value=>!value);
 }
 return <><audio ref={audio} src={assetUrl(music)} loop preload="none"/><button ref={button} className="music-toggle" type="button" aria-pressed={!enabled} onClick={toggle}>{enabled?'Disable music':'Enable music'}</button></>;
}
