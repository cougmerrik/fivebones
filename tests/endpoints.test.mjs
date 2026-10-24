import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resolveEndpoints} from '../packages/contracts/endpoints.ts';

test('local API derives the matching WebSocket endpoint',()=>{
 assert.deepEqual(resolveEndpoints('http://localhost:8000/'),{apiBaseUrl:'http://localhost:8000',wsBaseUrl:'ws://localhost:8000'});
});
test('HTTPS API derives secure WSS',()=>{
 assert.equal(resolveEndpoints('https://api.example/').wsBaseUrl,'wss://api.example');
});
test('explicit WebSocket origin can be configured independently',()=>{
 assert.equal(resolveEndpoints('https://api.example','wss://socket.example/').wsBaseUrl,'wss://socket.example');
});
test('local overlay testing allows loopback endpoints',()=>{
 assert.equal(resolveEndpoints('http://localhost:18000',undefined,'https:').wsBaseUrl,'ws://localhost:18000');
});
for(const [api,ws,protocol] of [
 ['https://api.example','ws://api.example','https:'],
 ['https://api.example','ws://localhost:8000','https:'],
 ['http://api.example',undefined,'https:'],
 ['https://user:secret@api.example',undefined,'https:'],
 ['https://api.example?token=secret',undefined,'https:'],
 ['https://api.example/api/v1',undefined,'https:'],
 ['https://api.example','wss://socket.example?token=secret','https:'],
 ['ftp://api.example',undefined,'http:'],
])test('reject invalid/insecure endpoint configuration '+api.replace(/secret/g,'REDACTED'),()=>assert.throws(()=>resolveEndpoints(api,ws,protocol)));
