from contextlib import contextmanager
import os
import pytest
from sqlalchemy.exc import OperationalError
from app import main as m
from app import settings, storage, start


def test_origins_are_exact_and_trimmed():
    assert settings.origins(' https://game.example/,https://app.roll20.net,,https://game.example ')==['https://game.example','https://app.roll20.net']
    for value in ('*','https://*.example','https://game.example/path','https://user:secret@game.example','wss://game.example'):
        with pytest.raises(ValueError):settings.origins(value)


def production():
    return dict(APP_ENV='production',DATABASE_URL='postgresql://user:password@postgres/game',
                HOST_INVITE_SECRET='x'*32,APP_BASE_URL='https://game.example',ALLOWED_ORIGINS='https://game.example,https://app.roll20.net')


def test_production_guards():
    settings.validate_production(production())
    for key,value in [('DATABASE_URL',''),('DATABASE_URL','sqlite:///prod.db'),('HOST_INVITE_SECRET','short'),('APP_BASE_URL','http://game.example'),('APP_BASE_URL','https://game.example/path'),('ALLOWED_ORIGINS','*'),('WS_ALLOWED_ORIGINS','http://game.example'),('WEB_CONCURRENCY','2')]:
        env=production();env[key]=value
        with pytest.raises(ValueError):settings.validate_production(env)


def test_port_and_single_worker(monkeypatch):
    monkeypatch.setenv('APP_ENV','development');monkeypatch.setenv('PORT','18234')
    calls=[];monkeypatch.setattr(start.uvicorn,'run',lambda *a,**kw:calls.append((a,kw)))
    start.main();assert calls[0][1]['host']=='0.0.0.0' and calls[0][1]['port']==18234 and calls[0][1]['workers']==1


def test_storage_url_selection(tmp_path):
    assert storage.normalize_url('postgres://u:p@host/db')=='postgresql+psycopg://u:p@host/db'
    assert storage.normalize_url('postgresql://u:p@host/db')=='postgresql+psycopg://u:p@host/db'
    assert storage.normalize_url('',str(tmp_path/'game.db')).startswith('sqlite:///')
    with pytest.raises(ValueError):storage.normalize_url('mysql://user:password@host/db')


def test_health_and_readiness_failure(client,monkeypatch):
    assert client.get('/health').status_code==200 and client.get('/live').status_code==200
    @contextmanager
    def broken():
        raise OperationalError('SELECT 1',(),Exception('private-database-credential'))
        yield
    monkeypatch.setattr(m,'db',broken)
    response=client.get('/api/v1/health')
    assert response.status_code==503 and response.json()=={'detail':'DATABASE_UNAVAILABLE'}
    assert 'credential' not in response.text and client.get('/live').status_code==200


def test_cors_preflight_and_distinct_ws_origins(client,monkeypatch):
    good=client.options('/api/v1/rooms',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'POST'})
    assert good.status_code==200 and good.headers['access-control-allow-origin']=='http://localhost:5173'
    bad=client.options('/api/v1/rooms',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'})
    assert bad.status_code==400 and 'access-control-allow-origin' not in bad.headers
    host=client.post('/api/v1/rooms',json={'name':'Origins'}).json()
    monkeypatch.setattr(m,'WS_ORIGINS',['https://extension-host.example'])
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/rooms/{host['roomId']}/ws",headers={'origin':'http://localhost:5173'}) as ws:ws.receive_json()
    with client.websocket_connect(f"/api/v1/rooms/{host['roomId']}/ws",headers={'origin':'https://extension-host.example'}) as ws:
        ws.send_json({'type':'authenticate','seatToken':host['seatToken']});assert ws.receive_json()['state']['role']=='gm'


def test_sqlite_migration_to_postgres(client,tmp_path,monkeypatch,capsys):
    if not m.DATABASE_URL.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        pytest.skip('PostgreSQL migration integration requires TEST_DATABASE_URL')
    import json,sqlite3,sys
    from app import migrate
    source=tmp_path/'source.sqlite3'
    with sqlite3.connect(source) as c:
        c.execute('CREATE TABLE rooms (id TEXT PRIMARY KEY,state TEXT,credentials TEXT,invite TEXT,created REAL)')
        c.execute('INSERT INTO rooms VALUES (?,?,?,?,?)',('migration-room',json.dumps({'privateDice':[1,2,3,4,5]}),'{"hashed-token":{"gm":true}}','invite-hash',1234.56789))
    monkeypatch.setenv('DATABASE_URL',m.DATABASE_URL)
    monkeypatch.setattr(sys,'argv',['migrate','--source-sqlite',str(source),'--confirm'])
    migrate.main()
    with m.db() as c:
        row=c.execute('SELECT state,credentials,created FROM rooms WHERE id=?',('migration-room',)).fetchone()
        assert json.loads(row[0])['privateDice']==[1,2,3,4,5] and row[2]==1234.56789
    assert 'Migrated 1 rooms' in capsys.readouterr().out
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):migrate.main()
    with m.db() as c:assert c.execute('SELECT COUNT(*) FROM rooms').fetchone()[0]==1
