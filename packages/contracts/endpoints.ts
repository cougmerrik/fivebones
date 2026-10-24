/** Public endpoints only. No credentials belong in either URL. */
export function resolveEndpoints(apiValue:string, wsValue?:string, pageProtocol='http:') {
 const api=new URL(apiValue);
 const ws=new URL(wsValue||apiValue.replace(/^http/,'ws'));
 for(const url of [api,ws]) {
  if(url.username||url.password||url.search||url.hash||url.pathname!=='/')throw Error('Endpoints must not contain credentials, queries or fragments');
 }
 if(!['http:','https:'].includes(api.protocol)||!['ws:','wss:'].includes(ws.protocol))throw Error('Use HTTP(S) for API and WS(S) for WebSocket endpoints');
 const loopback=(url:URL)=>['localhost','127.0.0.1','[::1]'].includes(url.hostname);
 if((api.protocol==='https:'||pageProtocol==='https:'&&!loopback(ws))&&ws.protocol!=='wss:')throw Error('Production WebSockets require wss://');
 if(pageProtocol==='https:'&&api.protocol!=='https:'&&!loopback(api))throw Error('Production API requires https://');
 return {apiBaseUrl:api.href.replace(/\/$/,''),wsBaseUrl:ws.href.replace(/\/$/,'')};
}
