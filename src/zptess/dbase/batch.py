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

class BatchTable(Table):

    def latest(self):
        '''Lookup roi id by given comment'''
        def _latest(txn):
            dict_keys = self._natural_key_columns + self._other_columns
            sql = '''
                SELECT begin_tstamp, end_tstamp, email_sent, calibrations 
                FROM batch_t 
                WHERE begin_tstamp = (SELECT MAX(begin_tstamp) FROM batch_t)
            '''
            txn.execute(sql)
            result = txn.fetchone()
            if result:
                result = dict(zip(dict_keys, result))
            return result
        return self._pool.runInteraction(_latest)
