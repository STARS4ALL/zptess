# ----------------------------------------------------------------------
# Copyright (c) 2022
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

from twisted.logger import Logger
from twisted.enterprise import adbapi


from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

#--------------
# local imports
# -------------

from zptess import SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR

from zptess.logger import setLogLevel
from zptess.dbase import tables
from zptess.dbase.batch import BatchTable
from zptess.dbase.summary import SummaryTable
from zptess.dbase.rounds import RoundsTable
from zptess.dbase.samples import SamplesTable

# ----------------
# Module constants
# ----------------

NAMESPACE = 'dbase'

# -----------------------
# Module global variables
# -----------------------

log = Logger(NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


# --------------
# Module Classes
# --------------

class DataAccesObject():

    def __init__(self, parent, pool, *args, **kargs):
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        self.parent = parent
        self.pool = pool
        self.start(*args)
        
       
    #------------
    # Service API
    # ------------

    def start(self, *args):
        log.info('Starting DAO')

        self.config = tables.ConfigTable(
            pool      = self.pool,
            log_level = 'info',
        )
        
        self.samples = SamplesTable(
            pool                = self.pool, 
            table               = 'samples_t',
            id_column           = 'rowid',
            natural_key_columns = ('role','tstamp'), 
            other_columns       = ('session','freq','seq','temp_box'),
            insert_mode         = tables.INSERT,
            log_level           = 'info',
        )

        self.rounds = RoundsTable(
            pool                = self.pool, 
            table               = 'rounds_t',
            id_column           = 'rowid',
            natural_key_columns = ('session','role','round'), 
            other_columns       = ('begin_tstamp','end_tstamp','central','freq','stddev','mag',
                                    'zp_fict', 'zero_point','nsamples','duration'),
            insert_mode         = tables.INSERT,
            log_level           = 'info',
        )

        self.summary = SummaryTable(
            pool                = self.pool, 
            table               = 'summary_t',
            id_column           = 'rowid',
            natural_key_columns = ('session','role'), 
            other_columns       = ('model','name','mac','firmware','sensor', 'prev_zp','author','nrounds',
                                    'freq','freq_method','mag','zero_point','zero_point_method',
                                    'offset', 'upd_flag',
                                    'calibration', 'calversion', 'filter', 'plug', 'box', 'collector','comment'),
            insert_mode         = tables.INSERT,
            log_level           = 'info',
        )

        self.batch = BatchTable(
            pool                = self.pool, 
            table               = 'batch_t',
            id_column           = 'rowid',
            natural_key_columns = ('begin_tstamp',), 
            other_columns       = ('end_tstamp','email_sent','calibrations'),
            insert_mode         = tables.INSERT,
            log_level           = 'info',
        )
        

        
        