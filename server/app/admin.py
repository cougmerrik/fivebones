"""Offline operational commands; stop the API before credential rotation/purge."""
import argparse
import json
import os
import secrets
import time
from .main import db, digest

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['rotate-host','purge'])
    parser.add_argument('--room');parser.add_argument('--days',type=int,default=int(os.getenv('RETENTION_DAYS','30')))
    parser.add_argument('--confirm',action='store_true');args=parser.parse_args()
    if not args.confirm: parser.error('--confirm is required; back up the database first')
    with db() as c:
        if args.action=='purge':
            if args.days<1:parser.error('--days must be positive')
            rows=c.execute('SELECT id,state FROM rooms WHERE created < ?',(time.time()-args.days*86400,)).fetchall()
            count=0
            for rid,state in rows:
                if json.loads(state)['ended']:
                    c.execute('DELETE FROM rooms WHERE id=?',(rid,));count+=1
            print(f'Deleted {count} ended rooms older than {args.days} days')
        else:
            if not args.room:parser.error('--room is required')
            row=c.execute('SELECT credentials FROM rooms WHERE id=?',(args.room,)).fetchone()
            if not row:parser.error('room not found')
            creds={k:v for k,v in json.loads(row[0]).items() if not v['gm']}
            token=secrets.token_urlsafe(32);creds[digest(token)]=dict(gm=True,sid=None,key=secrets.token_hex(8))
            c.execute('UPDATE rooms SET credentials=? WHERE id=?',(json.dumps(creds),args.room))
            print('New private GM recovery token:',token)
if __name__=='__main__':main()
