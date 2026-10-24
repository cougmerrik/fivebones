"""Copy a stopped SQLite game's aggregates to PostgreSQL without overwriting rooms."""
import argparse
import os
from pathlib import Path
import sqlite3
from . import storage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-sqlite',required=True)
    parser.add_argument('--confirm',action='store_true')
    args=parser.parse_args()
    url=os.getenv('DATABASE_URL','')
    if not args.confirm:parser.error('--confirm is required; stop the source API and back up both databases first')
    if not url.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        parser.error('Target DATABASE_URL must be PostgreSQL')
    source=Path(args.source_sqlite).resolve()
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as old:
        records=old.execute('SELECT id,state,credentials,invite,created FROM rooms').fetchall()
    with storage.transaction(url) as new:
        for record in records:
            # A collision aborts the entire transaction; existing rooms are never replaced.
            new.execute('INSERT INTO rooms (id,state,credentials,invite,created) VALUES (?,?,?,?,?)',record)
    print(f'Migrated {len(records)} rooms; original tokens remain valid. No source rows were modified.')


if __name__=='__main__':main()
