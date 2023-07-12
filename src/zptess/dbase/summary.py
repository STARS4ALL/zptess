# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sqlite3
import datetime

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

from zptess.logger import setLogLevel
from zptess.dbase.tables import Table

# ----------------
# Module constants
# ----------------

# The order in this sequence matters because it will be dumped in a CSV file
EXPORT_HEADERS = ("model","name", "mac","firmware", "sensor", "session" ,"calibration", "calversion", "ref_mag", "ref_freq", "test_mag", "test_freq",  
                    "mag_diff", "raw_zero_point", "offset", "zero_point",  "prev_zp", 
                    "filter", "plug", "box", "collector","author", "comment")

EXPORT_ADD_HEADERS = ("nrounds","zero_point_method","test_freq_method","ref_freq_method" )

# ----------------
# helper functions
# ----------------

def dyn_sql(columns, updated, begin_tstamp):
    all_columns = ",".join(columns)
    if begin_tstamp is None and updated is None:
        sql = f"SELECT {all_columns} FROM summary_v WHERE name LIKE 'stars%' ORDER BY CAST(substr(name, 6) AS INT) ASC, session ASC"
    elif begin_tstamp is None and updated is not None:
        sql = f"SELECT {all_columns} FROM summary_v WHERE name LIKE 'stars%' AND upd_flag = :updated ORDER BY CAST(substr(name, 6) AS INT) ASC, session ASC"
    elif begin_tstamp is not None and updated is None:
        sql = f"SELECT {all_columns} FROM summary_v WHERE session BETWEEN :begin_tstamp AND :end_tstamp ORDER BY session ASC"
    else:
        sql = f"SELECT {all_columns} FROM summary_v WHERE upd_flag = :updated AND session BETWEEN :begin_tstamp AND :end_tstamp ORDER BY session ASC"
    return sql


class SummaryTable(Table):

    def numSessions(self, begin_tstamp, end_tstamp, updated=None):
        row = {'begin_tstamp': begin_tstamp + 'Z', 'end_tstamp': end_tstamp + 'Z','updated': updated} 
        def _numSessions(txn, row):
            if updated is not None:
                sql = '''
                SELECT count(*) 
                FROM summary_v 
                WHERE session BETWEEN :begin_tstamp AND :end_tstamp
                AND upd_flag = :updated
                '''
            else:
                sql = '''
                SELECT count(*) 
                FROM summary_v 
                WHERE session BETWEEN :begin_tstamp AND :end_tstamp
                '''
            txn.execute(sql, row)
            return txn.fetchone()[0]
        return self._pool.runInteraction(_numSessions, row)


    def sessions(self, updated, begin_tstamp, end_tstamp):
        row = {'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp, 'updated': updated}
        if updated is not None:
            sql = '''
                SELECT DISTINCT session FROM summary_t WHERE session BETWEEN :begin_tstamp AND :end_tstamp AND upd_flag = :updated
            '''
        else:
            sql = '''
                SELECT DISTINCT session FROM summary_t WHERE session BETWEEN :begin_tstamp AND :end_tstamp
            '''
        def _sessions(txn, sql, row):
            txn.execute(sql, row)
            return txn.fetchall()
        return self._pool.runInteraction(_sessions, sql, row)


    def export(self, extended, updated, begin_tstamp, end_tstamp):
        def _export(txn, sql, row):
            txn.execute(sql, row)
            return txn.fetchall()
        headers = EXPORT_HEADERS + EXPORT_ADD_HEADERS if extended else EXPORT_HEADERS
        row = {'updated': updated, 'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp}
        sql = dyn_sql(headers, updated, begin_tstamp)
        return self._pool.runInteraction(_export, sql, row)


    def getDeviceInfo(self, session, role):
        def _getDeviceInfo(txn, sql, row):
            txn.execute(sql, row)
            return txn.fetchone()
        row = {'session': session, 'role': role}
        sql = "SELECT model, name, nrounds FROM summary_t WHERE session = :session AND role = :role"
        return self._pool.runInteraction(_getDeviceInfo, sql, row)
