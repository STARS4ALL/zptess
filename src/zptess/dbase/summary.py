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

