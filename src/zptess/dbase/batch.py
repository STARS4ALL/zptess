# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

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

    def open(self, tstamp):
        row = {'tstamp': tstamp}
        def _open(txn):
            sql = '''
                INSERT INTO batch_t(begin_tstamp, end_tstamp) VALUES(:tstamp, NULL)
            '''
            txn.execute(sql,row)
        return self._pool.runInteraction(_open)

    def isOpen(self):
        def _isOpen(txn):
            sql = '''
                SELECT count(*) FROM batch_t WHERE begin_tstamp IS NOT NULL AND end_tstamp IS NULL
            '''
            txn.execute(sql)
            n = txn.fetchone()[0]
            return n > 0
        return self._pool.runInteraction(_isOpen)


    def close(self, end_tstamp, N):
        row = {'end_tstamp': end_tstamp, 'N': N}
        def _close(txn, row):
            sql = '''
                UPDATE batch_t
                SET end_tstamp = :end_tstamp, calibrations = :N
                WHERE begin_tstamp = (SELECT begin_tstamp WHERE end_tstamp IS NULL)
                '''
            txn.execute(sql, row)
        return self._pool.runInteraction(_close, row)


    def purge(self):
        def _purge(txn):
            sql = '''
                DELETE FROM batch_t WHERE calibrations = 0
                '''
            txn.execute(sql)
        return self._pool.runInteraction(_purge)


    def emailed(self, begin_tstamp, flag):
        def _emailed(txn, row):
            sql = '''
                UPDATE batch_t SET email_sent = :flag WHERE begin_tstamp = :tstamp
                '''
            txn.execute(sql, row)
        row = {'tstamp': begin_tstamp, 'flag': flag}
        return self._pool.runInteraction(_emailed, row)
