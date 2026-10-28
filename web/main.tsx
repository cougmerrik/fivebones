import React from 'react';
import {BackgroundMusic} from '../packages/ui/BackgroundMusic';
import {createRoot} from 'react-dom/client';
import {FiveBonesApp} from '../packages/ui/App';
import {CampaignApp} from '../packages/ui/CampaignApp';
import '../packages/ui/style.css';
import {resolveEndpoints} from '../packages/contracts/endpoints';
const root=document.getElementById('root')!;
const api=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000';
const ws=import.meta.env.VITE_WS_BASE_URL||undefined;
try {
 resolveEndpoints(api,ws,location.protocol);
 const params=new URLSearchParams(location.search);
 const campaign=params.get('room')==='belwether'||params.get('isdm')==='1';
 createRoot(root).render(<div className="music-surface"><BackgroundMusic/>{campaign?<CampaignApp api={api} wsApi={ws} dmMode={params.get('isdm')==='1'}/>:<FiveBonesApp api={api} wsApi={ws}/>}</div>);
} catch(error) {
 root.setAttribute('role','alert');
 root.textContent='Unable to connect: '+String(error)+'. Check the public API and WebSocket build variables.';
}
