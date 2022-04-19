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

class SamplesTable(Table):

    def export(self, session, role, roun):
        def _export(txn, sql, row):
            txn.execute(sql, row)
            return txn.fetchall()
        row = {'round': roun, 'session': session, 'role': role}
        sql = '''
            SELECT u.model, u.name, u.mac, u.session, u.role, r.round, s.tstamp, s.freq, s.temp_box, s.seq
            FROM samples_t AS s
            JOIN rounds_t  AS r USING(role, session)
            JOIN summary_t AS u USING(role, session)
            WHERE s.tstamp BETWEEN r.begin_tstamp AND r.end_tstamp
            AND r.session = :session
            AND r.role    = :role
            AND r.round   = :round
            ORDER BY s.tstamp ASC, r.role DESC, r.round ASC
        '''
        return self._pool.runInteraction(_export, sql, row)

