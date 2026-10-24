"""Exercise the local Compose API, restart it, retry a durable command, delete fixture."""
import json
import os
import subprocess
import time
import uuid
import httpx
from websockets.sync.client import connect

API=os.getenv('SMOKE_API_ORIGIN','http://localhost:8000')
BASE=API+'/api/v1'
WS_API=os.getenv('SMOKE_WS_ORIGIN',API.replace('http','ws',1))
ORIGIN=os.getenv('SMOKE_BROWSER_ORIGIN','http://localhost:5173')

def ready():
    for _ in range(100):
        try:
            if httpx.get(BASE+'/health').status_code==200:return
        except httpx.HTTPError:pass
        time.sleep(.2)
    raise RuntimeError('API did not become ready')

def post(path,data,token=None):
    r=httpx.post(BASE+path,json=data,headers={'Authorization':'Bearer '+token} if token else {})
    r.raise_for_status();return r.json()

def socket(rid,token):
    ws=connect(f'{WS_API}/api/v1/rooms/{rid}/ws',origin=ORIGIN,legacy=True)
    ws.send(json.dumps({'type':'authenticate','seatToken':token}));state=json.loads(ws.recv())['state']
    return ws,state

def command(ws,state,action,cid=None):
    cmd={'id':cid or str(uuid.uuid4()),'expectedVersion':state['version'],'action':action,'data':{}}
    ws.send(json.dumps(cmd));ack=json.loads(ws.recv());new=json.loads(ws.recv())['state'];assert ack['accepted'],ack
    return cmd,ack,new

def main():
    ready();host=post('/rooms',{'name':'Container restart acceptance','hostSecret':os.getenv('SMOKE_HOST_SECRET','')});rid=host['roomId']
    try:
        players=[post(f'/rooms/{rid}/join',{'inviteCode':host['inviteCode'],'name':f'Smoke {i}','startingCp':10000}) for i in range(2)]
        ws,state=socket(rid,host['seatToken']);_,_,state=command(ws,state,'startHand');ws.close()
        actor=next(p for p in players if p['seatId']==state['actor']);ws,state=socket(rid,actor['seatToken']);cmd,ack,state=command(ws,state,'bet');ws.close()
        restart=['docker','restart',os.environ['SMOKE_RESTART_CONTAINER']] if os.getenv('SMOKE_RESTART_CONTAINER') else ['docker','compose','restart','api']
        subprocess.run(restart,check=True,capture_output=True);ready()
        ws,recovered=socket(rid,actor['seatToken']);assert recovered==state
        ws.send(json.dumps(cmd));retry=json.loads(ws.recv());current=json.loads(ws.recv())['state'];assert retry==ack and current==state;ws.close()
        csv=httpx.get(BASE+f'/rooms/{rid}/ledger.csv',headers={'Authorization':'Bearer '+host['seatToken']});csv.raise_for_status();assert 'HAND_NET' in csv.text and 'TOTAL' in csv.text
        print('PASS: Docker HTTP, authenticated WebSocket, real API restart, identical private snapshot, durable wager retry, CSV export.')
    finally:
        post(f'/rooms/{rid}/delete',{'confirmed':True},host['seatToken'])
if __name__=='__main__':main()
