"""Transactional aggregate store shared by SQLite development and PostgreSQL production."""
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from sqlalchemy import Column, Float, MetaData, Table, Text, create_engine
from sqlalchemy.pool import NullPool

metadata = MetaData()
rooms = Table('rooms', metadata,
    Column('id', Text, primary_key=True),
    Column('state', Text, nullable=False),
    Column('credentials', Text, nullable=False),
    Column('invite', Text, nullable=False),
    Column('created', Float(precision=53), nullable=False),
)
campaigns = Table('campaigns', metadata,
    Column('alias', Text, primary_key=True),
    Column('room_id', Text, nullable=True),
    Column('credentials', Text, nullable=False),
    Column('receipts', Text, nullable=False),
)
_engines = {}
_lock = Lock()


def normalize_url(database_url='', sqlite_path='fivebones.sqlite3'):
    if not database_url:
        return 'sqlite:///' + str(Path(sqlite_path).resolve())
    if database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql+psycopg://', 1)
    if database_url.startswith('postgresql://'):
        return database_url.replace('postgresql://', 'postgresql+psycopg://', 1)
    if database_url.startswith(('postgresql+psycopg://', 'sqlite:///')):
        return database_url
    raise ValueError('DATABASE_URL must use PostgreSQL or SQLite')


def engine_for(database_url='', sqlite_path='fivebones.sqlite3'):
    url = normalize_url(database_url, sqlite_path)
    with _lock:
        if url not in _engines:
            sqlite = url.startswith('sqlite:')
            options = dict(poolclass=NullPool, connect_args={'timeout':10, 'check_same_thread':False}) if sqlite else dict(
                pool_pre_ping=True, pool_recycle=300, pool_size=5, max_overflow=5, connect_args={'connect_timeout':5})
            engine = create_engine(url, **options)
            try:
                metadata.create_all(engine)
            except Exception:
                engine.dispose()
                raise
            _engines[url] = engine
        return _engines[url]


class Connection:
    def __init__(self, connection):
        self.raw = connection
        self.postgres = connection.dialect.name == 'postgresql'

    def execute(self, statement, parameters=()):
        # All application SQL uses positional parameters. Values remain driver-bound.
        if self.postgres:
            statement = statement.replace('?', '%s')
        return self.raw.exec_driver_sql(statement, tuple(parameters))


@contextmanager
def transaction(database_url='', sqlite_path='fivebones.sqlite3'):
    engine = engine_for(database_url, sqlite_path)
    with engine.connect() as connection:
        try:
            if engine.dialect.name == 'sqlite':
                connection.exec_driver_sql('BEGIN IMMEDIATE')
            else:
                connection.begin()
            yield Connection(connection)
            connection.commit()
        except Exception:
            connection.rollback()
            raise


def dispose(database_url='', sqlite_path='fivebones.sqlite3'):
    url = normalize_url(database_url, sqlite_path)
    with _lock:
        engine = _engines.pop(url, None)
        if engine is not None:
            engine.dispose()
