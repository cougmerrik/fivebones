import os
from urllib.parse import urlencode
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app import main as m
from app import storage


@pytest.fixture(params=['sqlite']+(['postgresql'] if os.getenv('TEST_DATABASE_URL') else []))
def client(request,tmp_path,monkeypatch):
    """Each PostgreSQL integration test gets a fresh, uniquely named schema."""
    monkeypatch.setenv('APP_ENV','development')
    monkeypatch.setattr(m,'DB',str(tmp_path/'test.db'))
    monkeypatch.setattr(m,'WS_ORIGINS',['http://localhost:5173'])
    m.rates.clear()
    url=''
    control=None
    schema=None
    if request.param=='postgresql':
        import psycopg
        from psycopg import sql
        base=os.environ['TEST_DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)
        control=psycopg.connect(base,autocommit=True)
        schema='fivebones_test_'+uuid4().hex
        control.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        url=base+('&' if '?' in base else '?')+urlencode({'options':'-csearch_path='+schema})
    monkeypatch.setattr(m,'DATABASE_URL',url)
    try:
        with TestClient(m.app) as test_client:
            yield test_client
    finally:
        storage.dispose(url,str(tmp_path/'test.db'))
        if control:
            from psycopg import sql
            control.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
            control.close()
