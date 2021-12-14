#!/usr/bin/env python3

# Generic database interface for writing batches of records to a
# postgres database from a list of dicts that map column name to a
# value.

import os
import psycopg2
import psycopg2.extras
import sys
import threading
import time

# project libraries
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from util import say

class DatabaseBatcher(threading.Thread):
    def __init__(self, dbname, tablename):
        threading.Thread.__init__(self)
        self.cache = []
        self.tablename = tablename
        self.lock = threading.Lock()
        self.db = psycopg2.connect(database=dbname)
        self.start()

    def get_raw_db(self):
        return self.db

    # 'record' is a single record, a dict that maps column name to value
    def insert(self, record):
        with self.lock:
            self.cache.append(record)

    def insert_batch(self, recordlist):
        columns = set()
        for rec in recordlist:
            columns.update(rec.keys())
        columns = list(columns)

        quoted_col_list = [f'"{col}"' for col in columns]
        stmt = f'insert into {self.tablename} ({",".join(quoted_col_list)}) values %s'

        values = []
        for rec in recordlist:
            values.append([rec[col] if col in rec else None for col in columns])

        cursor = self.db.cursor()

        try:
            psycopg2.extras.execute_values(
                cursor,
                stmt,
                values,
                template=None,
            )
            say(f"{len(recordlist)} records committed to db")
        except Exception as e:
            say(f"could not commit records: {str(e)}")
        finally:
            self.db.commit()

    def run(self):
        say("db thread running")
        while True:
            # Move cache into a temp var so the insert can run in parallel without the lock held
            to_insert = []
            with self.lock:
                to_insert.extend(self.cache)
                self.cache.clear()

            if len(to_insert) > 0:
                self.insert_batch(to_insert)

            time.sleep(2)
