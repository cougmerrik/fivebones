import React from 'react';
import {createRoot} from 'react-dom/client';
import {FiveBonesApp} from '../packages/ui/App';
import '../packages/ui/style.css';
import {resolveEndpoints} from '../packages/contracts/endpoints';
const root=document.getElementById('root')!;
const api=import.meta.env.VITE_API_BASE_URL||'http://localhost:8000';
const ws=import.meta.env.VITE_WS_BASE_URL||undefined;
try {
 resolveEndpoints(api,ws,location.protocol);
 createRoot(root).render(<FiveBonesApp api={api} wsApi={ws}/>);
} catch(error) {
 root.setAttribute('role','alert');
 root.textContent='Unable to connect: '+String(error)+'. Check the public API and WebSocket build variables.';
}
