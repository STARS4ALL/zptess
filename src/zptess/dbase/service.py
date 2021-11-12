# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


import os
import sqlite3
import glob

# ---------------
# Twisted imports
# ---------------

from twisted.application.service import Service
from twisted.logger import Logger
from twisted.enterprise import adbapi


from twisted.internet import reactor, task, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR, TSTAMP_FORMAT

from zptess.logger import setLogLevel
from zptess.dbase.dao import DataAccesObject

# ----------------
# Module constants
# ----------------

NAMESPACE = 'dbase'

DATABASE_FILE = 'zptess.db'

SQL_TEST_STRING = "SELECT COUNT(*) FROM summary_t"

# -----------------------
# Module global variables
# -----------------------

log = Logger(NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------

def getPool(*args, **kargs):
    '''Get connetion pool for sqlite3 driver'''
    kargs['check_same_thread'] = False
    return adbapi.ConnectionPool("sqlite3", *args, **kargs)


def open_database(dbase_path):
    '''Creates a Database file if not exists and returns a connection'''
    output_dir = os.path.dirname(dbase_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(dbase_path):
        with open(dbase_path, 'w') as f:
            pass
        log.info("Created database file {0}".format(dbase_path))
    return sqlite3.connect(dbase_path)


def create_database(connection, schema_path, initial_data_dir_path, updates_data_dir, query):
    created = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
    except Exception:
        created = False
    if not created:
        with open(schema_path) as f: 
            lines = f.readlines() 
        script = ''.join(lines)
        connection.executescript(script)
        log.info("Created data model from {0}".format(os.path.basename(schema_path)))
        file_list = glob.glob(os.path.join(initial_data_dir_path, '*.sql'))
        for sql_file in file_list:
            log.info("Populating data model from {0}".format(os.path.basename(sql_file)))
            with open(sql_file) as f: 
                lines = f.readlines() 
            script = ''.join(lines)
            connection.executescript(script)
    else:
        file_list = glob.glob(os.path.join(updates_data_dir, '*.sql'))
        for sql_file in file_list:
            log.info("Applying updates to data model from {0}".format(os.path.basename(sql_file)))
            with open(sql_file) as f: 
                lines = f.readlines() 
            script = ''.join(lines)
            connection.executescript(script)
    connection.commit()

def read_database_version(connection):
    cursor = connection.cursor()
    query = 'SELECT value FROM config_t WHERE section = "database" AND property = "version";'
    cursor.execute(query)
    version = cursor.fetchone()[0]
    return version



# --------------
# Module Classes
# --------------

class DatabaseService(Service):

    # Service name
    NAME = NAMESPACE

    def __init__(self, options, *args, **kargs):
        super().__init__(*args, **kargs)   
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        self.path          = options['path']
        self.session       = options['session']
        self.test_mode     = options['test']
        self.author        = options['author']
        self.only_create   = options['create']
        self.pool          = None
        self.getPoolFunc   = getPool
        self.refSamples    = list()
        self.testSamples   = list()
        self.refRounds     = list()
        self.testRounds    = list()
        self.summary_stats = list()
        self.phot = {
            'ref' : {'info': None},
            'test': {'info': None},
        }
        pub.subscribe(self.onPhotometerInfo,  'photometer_info')
        pub.subscribe(self.onRoundStatInfo,   'round_stats_info')
        pub.subscribe(self.onSummaryStatInfo, 'summary_stats_info')
    
    #------------
    # Service API
    # ------------

    def startService(self):
        log.info("Starting Database Service on {database}", database=self.path)
        if self.test_mode:
            log.warn("Database won't be updated")
        connection = open_database(self.path)
        create_database(connection, SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR, SQL_TEST_STRING)
        version = read_database_version(connection)
        # Remainder Service initialization
        super().startService()
        connection.commit()
        connection.close()
        self.openPool()
        self.dao = DataAccesObject(self.pool, None)
        self.dao.version = version
        if self.only_create:
            reactor.callLater(0, self.parent.stopService)


    @inlineCallbacks
    def stopService(self):
        if self.test_mode:
            log.warn("Database is not being updated")
        else:
            if self.testSamples:
                n1 = len(self.testSamples)
                samples  = self.purge('test', self.testRounds, self.testSamples)
                n2 = len(samples)
                log.info("From {n1} test initial samples, saving {n2} samples only", n1=n1, n2=n2)
                yield self.dao.samples.savemany(samples)
            if self.refSamples:
                n1 = len(self.refSamples)
                samples  = self.purge('ref', self.refRounds, self.refSamples)
                n2 = len(samples)
                log.info("From {n1} ref. initial samples, saving {n2} samples only", n1=n1, n2=n2)
                yield self.dao.samples.savemany(samples)
            if self.refRounds:
                log.info("Saving {n} ref. rounds stats records", n=len(self.refRounds))
                yield self.dao.rounds.savemany(self.refRounds)
            if self.testRounds:
                log.info("Saving {n} test rounds stats records", n=len(self.testRounds))
                yield self.dao.rounds.savemany(self.testRounds)
            if self.summary_stats:
                log.info("Saving {n} summary stats records", n=len(self.summary_stats))
                yield self.dao.summary.savemany(self.summary_stats)
        self.closePool()
        log.info("Stopping Database Service")
        try:
            reactor.stop()
        except Exception as e:
            pass
            #os.kill(os.getpid(), signal.SIGINT)


    # ---------------
    # OPERATIONAL API
    # ---------------

    def onPhotometerInfo(self, role, circ_buffer, info):
        reactor.callLater(0, self._write, role, circ_buffer.getBuffer2(), info)

    def onRoundStatInfo(self, role, stats_info):
        stats_info['name']    = self.phot[role]['info']['name']
        stats_info['mac']     = self.phot[role]['info']['mac']
        stats_info['role']    = role
        stats_info['session'] = self.session
        if role == 'ref':
            self.refRounds.append(stats_info)
        else:
            self.testRounds.append(stats_info)


    def onSummaryStatInfo(self, role, stats_info):
        stats_info['model']    = self.phot[role]['info']['model']
        stats_info['name']     = self.phot[role]['info']['name']
        stats_info['mac']      = self.phot[role]['info']['mac']
        stats_info['firmware'] = self.phot[role]['info']['firmware']
        stats_info['role']     = role
        stats_info['session']  = self.session
        stats_info['author']   = self.author
        self.summary_stats.append(stats_info)

    @inlineCallbacks
    def loadRefPhotDefaults(self):
        ref = yield self.dao.config.loadSection('reference')
        return(ref)

    @inlineCallbacks
    def loadAbsoluteZeroPoint(self):
        ref = yield self.dao.config.load('reference','zp_abs')
        # Assume that we always have this loaded, no need for error check
        return(float(ref['zp_abs']))

    # -------------
    # Helper methods
    # --------------
    def purge(self, role, rounds, samples):
        indexes = list()
        log.debug("{n} {r} samples before purge", r=role, n=len(samples))
        # Finding the list of indices to slice the samples
        for r in rounds:
            start_index = None
            end_index  = None
            for i, s in enumerate(samples):
                ts = s['tstamp']
                if ts == r['begin_tstamp']:
                    start_index = i
                elif ts == r['end_tstamp']:
                    end_index = i
                if start_index is not None and end_index is not None:
                    log.debug("{r} found ({i},{j}) indexes", r=role, i=start_index, j=end_index)
                    indexes.append((start_index, end_index))
                    break
        # Carefully slice the samples taking care of overlapping
        t0 = indexes[0]
        result = list(samples[t0[0]:t0[1]+1]) 
        for t0, t1 in zip(indexes,indexes[1:]):
            if t0[1] < t1[0]:
                i, j =   t1[0],  t1[1]+1
                log.debug("{r} no overlap intervals {t0}, {t1}", r=role, t0=t0, t1=t1)
                log.debug("{r} slicing to [{i}:{j}]", r=role, i=i, j=j)
                result.extend(samples[i:j]) # No overlapping
            else:
                i, j =   t0[1]+1, t1[1]+1
                log.debug("purge {r} overlapping intervals {t0}, {t1}", r=role, t0=t0, t1=t1)
                log.debug("purge {r} slicing to [{i}:{j}]", r=role, i=i, j=j)
                result.extend(samples[i:j]) # Overlapping
        log.debug("{n} {r} samples after purge", r=role, n=len(result))
        return result



    @inlineCallbacks
    def _write(self, role, queue, info):
        '''Configuration from command line arguments'''
        self.phot[role]['info'] = info
        session = self.session
        while True:
            sample  = yield queue.get() # From a Deferre queue
            data = {
                'tstamp'  : sample['tstamp'].strftime(TSTAMP_FORMAT),
                'role'    : role,
                'session' : session,
                'seq'     : sample.get('udp', None),    # Only exists in JSON based messages
                'freq'    : sample['freq'],
                'temp_box': sample.get('tamb', None),   # Only exists in JSON based messages
            }
            if role == 'ref':
                self.refSamples.append(data)
            else:
                self.testSamples.append(data)


    # =============
    # Twisted Tasks
    # =============
   
        

      
    # ==============
    # Helper methods
    # ==============

    def openPool(self):
        # setup the connection pool for asynchronouws adbapi
        log.debug("Opening a DB Connection to {conn!s}", conn=self.path)
        self.pool  = self.getPoolFunc(self.path)
        log.debug("Opened a DB Connection to {conn!s}", conn=self.path)


    def closePool(self):
        '''setup the connection pool for asynchronouws adbapi'''
        log.debug("Closing a DB Connection to {conn!s}", conn=self.path)
        self.pool.close()
        log.debug("Closed a DB Connection to {conn!s}", conn=self.path)
