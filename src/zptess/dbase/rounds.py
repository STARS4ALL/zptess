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

# ----------------
# helper functions
# ----------------

class RoundsTable(Table):

    def export(self, session, role, updated):
        def _export(txn, sql, row):
            txn.execute(sql, row)
            return txn.fetchall()
        row = {'session': session, 'role':role, 'updated': updated}
        if updated is None:
            sql = '''SELECT model, name, mac, session, role, round, freq, stddev, mag, zero_point, nsamples, duration
            FROM rounds_v
            WHERE session = :session
            AND role = :role
            ORDER BY round ASC
            '''
        else:
            sql = '''SELECT model, name, mac, session, role, round, freq, stddev, mag, zero_point, nsamples, duration
            FROM rounds_v
            WHERE session = :session
            AND role = :role
            AND upd_flag = :updated
            ORDER BY round ASC
            '''
        return self._pool.runInteraction(_export, sql, row)


