import {build} from 'esbuild';
import {mkdir,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const api=(process.env.VITE_API_BASE_URL||'http://localhost:8000').replace(/\/$/,'');
const ws=(process.env.VITE_WS_BASE_URL||api.replace(/^http/,'ws')).replace(/\/$/,'');
if(!/^https?:\/\//.test(api)||!/^wss?:\/\//.test(ws))throw Error('Use HTTP(S) API and WS(S) WebSocket endpoints');
for(const value of [api,ws]){const url=new URL(value);if(url.username||url.password||url.search||url.hash||url.pathname!=='/')throw Error('Endpoints cannot contain credentials/query/fragment')}
for(const value of [api,ws]){const url=new URL(value);if(['http:','ws:'].includes(url.protocol)&&!['localhost','127.0.0.1','[::1]'].includes(url.hostname))throw Error('Public extension endpoints require HTTPS/WSS')}
if(api.startsWith('https:')&&!ws.startsWith('wss:'))throw Error('HTTPS API requires a WSS endpoint');
const out=process.env.FIVE_BONES_EXTENSION_OUT||path.join(root,'extension/dist');
await mkdir(out,{recursive:true});
await build({entryPoints:[path.join(root,'extension/content.tsx')],bundle:true,outfile:out+'/content.js',format:'iife',minify:true,define:{'process.env.NODE_ENV':'"production"','FIVE_BONES_API':JSON.stringify(api),'FIVE_BONES_WS':JSON.stringify(ws)},assetNames:'assets/[name]-[hash]',loader:{'.css':'text','.png':'file','.mp3':'file'}});
await writeFile(out+'/manifest.json',JSON.stringify({manifest_version:3,name:'Five Bones',version:'1.0.0',description:'A private fantasy dice table overlay. Manual character entry; no Roll20 sheet access.',permissions:['storage'],web_accessible_resources:[{resources:['assets/*.png','assets/*.mp3'],matches:['https://app.roll20.net/*']}],content_scripts:[{matches:['https://app.roll20.net/editor/','https://app.roll20.net/editor/*'],js:['content.js'],run_at:'document_idle',all_frames:false}],content_security_policy:{extension_pages:"script-src 'self'; object-src 'none'; connect-src "+api+' '+ws}},null,2));
