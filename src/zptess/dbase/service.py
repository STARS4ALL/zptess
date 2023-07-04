# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------


import os
import sys
import glob
import uuid
import datetime
import sqlite3

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

from zptess import SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR, TSTAMP_FORMAT, TSTAMP_SESSION_FMT
from zptess.logger import setLogLevel
from zptess.dbase import NAMESPACE, log 
from zptess.dbase.utils import create_database, create_schema
from zptess.dbase.dao import DataAccesObject

# ----------------
# Module constants
# ----------------

SQL_TEST_STRING = "SELECT COUNT(*) FROM summary_t"


# ------------------------
# Module Utility Functions
# ------------------------

# SQLite has a default datetime.datetime adapter built in but
# we like to write in our own ISO format
def timestamp_adapter(tstamp):
    return tstamp.strftime(TSTAMP_FORMAT)

sqlite3.register_adapter(datetime.datetime, timestamp_adapter)

def getPool(*args, **kargs):
    '''Get connetion pool for sqlite3 driver (Twisted only)'''
    kargs['check_same_thread'] = False
    return adbapi.ConnectionPool("sqlite3", *args, **kargs)


def read_database_version(connection):
    cursor = connection.cursor()
    query = 'SELECT value FROM config_t WHERE section = "database" AND property = "version";'
    cursor.execute(query)
    version = cursor.fetchone()[0]
    return version

def write_database_uuid(connection):
    guid = str(uuid.uuid4())
    cursor = connection.cursor()
    param = {'section': 'database','property':'uuid','value': guid}
    cursor.execute(
        '''
        INSERT INTO config_t(section,property,value) 
        VALUES(:section,:property,:value)
        ''',
        param
    )
    connection.commit()
    return guid

def make_database_uuid(connection):
    cursor = connection.cursor()
    query = 'SELECT value FROM config_t WHERE section = "database" AND property = "uuid";'
    cursor.execute(query)
    guid = cursor.fetchone()
    if guid:
        try:
            uuid.UUID(guid[0])  # Validate UUID
        except ValueError:
            guid = write_database_uuid(connection)
        else:
            guid = guid[0]
    else:
        guid = write_database_uuid(connection)
    return guid


def read_configuration(connection):
     cursor = connection.cursor()
     cursor.execute("SELECT section, property, value FROM config_t ORDER BY section")
     return cursor.fetchall()

# --------------
# Module Classes
# --------------

class DatabaseService(Service):

    # Service name
    NAME = 'Database Service'

    def __init__(self, path, *args, **kargs):
        super().__init__(*args, **kargs)
        self.path = path
        self.getPoolFunc = getPool
        self.create_only = False

    #------------
    # Service API
    # ------------

    def createOnly(self, flag):
        '''must be called before start service'''
        self.create_only = flag

    def startService(self):
        setLogLevel(namespace=NAMESPACE, levelStr='warn')
        self.session       = None
        self.test_mode     = True # Assume a safe state
        self.refSamples    = list()
        self.testSamples   = list()
        self.refRounds     = list()
        self.testRounds    = list()
        self.summary_stats = list()
        self.phot = {
            'ref' : {'info': None},
            'test': {'info': None},
        }
        pub.subscribe(self.onPhotometerInfo,  'phot_info')
        pub.subscribe(self.onRoundStatInfo,   'calib_round_info')
        pub.subscribe(self.onSummaryStatInfo, 'calib_summary_info')
        pub.subscribe(self.onSampleReceived,  'phot_sample')
        pub.subscribe(self.onCalibrationStart,'calib_begin')

        connection, new_database = create_database(self.path)
        if new_database:
            log.warn("Created new database file at {f}",f=self.path)
        just_created, file_list = create_schema(connection, SQL_SCHEMA, SQL_INITIAL_DATA_DIR, SQL_UPDATES_DATA_DIR, SQL_TEST_STRING)
        if just_created:
            for sql_file in file_list:
                log.warn("Populating data model from {f}", f=os.path.basename(sql_file))
        else:
            for sql_file in file_list:
                log.warn("Applying updates to data model from {f}", f=os.path.basename(sql_file))
        #levels  = read_debug_levels(connection)
        version = read_database_version(connection)
        guid    = make_database_uuid(connection)
        log.warn("Starting {service} on {database}, version = {version}, UUID = {uuid}", 
            database = self.path, 
            version  = version,
            service  = self.name,
            uuid     = guid,
        )
    
        # Remainder Service initialization
        super().startService() # se we can handle the 'running' attribute
        self._initial_config = read_configuration(connection)
        connection.commit()
        connection.close()
        if self.create_only:
            log.warn("Stopping {service} on {database}, version = {version}, UUID = {uuid}", 
                database = self.path, 
                version  = version,
                service  = self.name,
                uuid     = guid,
            )
            sys.exit(0)
        else:
            self.openPool()
            self.dao = DataAccesObject(self, self.pool)
            self.dao.version = version
            self.dao.uuid = guid


    @inlineCallbacks
    def stopService(self):
        log.info("Stopping {name}", name=self.name)
        pub.unsubscribe(self.onPhotometerInfo,  'phot_info')
        pub.unsubscribe(self.onRoundStatInfo,   'calib_round_info')
        pub.unsubscribe(self.onSummaryStatInfo, 'calib_summary_info')
        pub.unsubscribe(self.onSampleReceived,  'phot_sample')
        pub.unsubscribe(self.onCalibrationStart,'calib_begin')
        self.closePool()
        try:
            reactor.stop()
        except Exception as e:
            log.failure("{e}",e=e)
        finally:
            yield super().stopService() # se we can handle the 'running' attribute


    # ---------------
    # OPERATIONAL API
    # ---------------

    @inlineCallbacks
    def flush(self):
        '''Flushes samples to database'''
        if self.test_mode:
            log.warn("Test mode: Database not being updated")
            self._clearBuffers()
            return
       
        if self.testSamples:
            n1 = len(self.testSamples)
            samples  = self._purge('test', self.testRounds, self.testSamples)
            n2 = len(samples)
            log.info("From {n1} test initial samples, saving {n2} samples only", n1=n1, n2=n2)
            yield self.dao.samples.savemany(samples)
        if self.refSamples:
            n1 = len(self.refSamples)
            samples  = self._purge('ref', self.refRounds, self.refSamples)
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
        self._clearBuffers()
       

    def setTestMode(self, test_mode):
        self.test_mode   = test_mode
    
    def getInitialConfig(self, section):
        '''For service startup, avoiding async code'''
        g = filter(lambda i: True if i[0] == section else False, self._initial_config)
        return dict(map(lambda i: (i[1], i[2]) ,g))

    # --------------
    # Event handlers
    # --------------

    def onCalibrationStart(self, session):
        self.session = session
    
    def onPhotometerInfo(self, role, info):
        self.phot[role]['info'] = info

    def onRoundStatInfo(self, role, count, stats_info):
        if self.session is None:    # Discard rounds info not bound to sessions
            return
        stats_info['mac']     = self.phot[role]['info']['mac']
        stats_info['session'] = self.session
        if role == 'ref':
            self.refRounds.append(stats_info)
        else:
            self.testRounds.append(stats_info)


    def onSummaryStatInfo(self, role, stats_info):
        if self.session is None:    # Discard summary info info not bound to sessions
            return
        stats_info['model']    = self.phot[role]['info']['model']
        stats_info['name']     = self.phot[role]['info']['name']
        stats_info['mac']      = self.phot[role]['info']['mac']
        stats_info['firmware'] = self.phot[role]['info']['firmware']
        stats_info['sensor']   = self.phot[role]['info']['sensor']
        stats_info['role']     = role
        stats_info['session']  = self.session
        self.summary_stats.append(stats_info)


    def onSampleReceived(self, role, sample):
        '''Get new sample from photometers'''
        if self.session is None:    # Discard samples not bound to sessions
            return
        data = {
            'tstamp'  : sample['tstamp'],   # native datetime object
            'session' : self.session,
            'role'    : role,
            'seq'     : sample.get('udp', None),    # Only exists in JSON based messages
            'freq'    : sample['freq'],
            'temp_box': sample.get('tamb', None),   # Only exists in JSON based messages
        }
        if role == 'ref':
            self.refSamples.append(data)
        else:
            self.testSamples.append(data)

    # -------------
    # Helper methods
    # --------------

    def _clearBuffers(self):
        self.session       = None
        self.refSamples    = list()
        self.testSamples   = list()
        self.refRounds     = list()
        self.testRounds    = list()
        self.summary_stats = list()


    def _purge(self, role, rounds, samples):
        indexes = list()
        log.debug("{n} {r} samples before purge", r=role, n=len(samples))
        # Finding the list of indices to slice the samples
        for r in rounds:
            start_index = None
            end_index  = None
            # This is valid for both ISO strings or native datetime objects
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
        if not indexes:
            return list()   # No samples to purge
        # Carefully slice the samples taking care of overlapping
        t0 = indexes[0]
        result = list(samples[t0[0]:t0[1]+1]) 
        for t0, t1 in zip(indexes,indexes[1:]):
            if t0[1] < t1[0]:
                i, j =   t1[0],  t1[1]+1
                log.debug("{r} no overlap intervals {t0}, {t1}", r=role, t0=t0, t1=t1)
                log.debug("{r} slicing to [{i}:{j}]", r=role, i=i, j=j)
            else:
                i, j =   t0[1]+1, t1[1]+1
                log.debug("purge {r} overlapping intervals {t0}, {t1}", r=role, t0=t0, t1=t1)
                log.debug("purge {r} slicing to [{i}:{j}]", r=role, i=i, j=j)
            result.extend(samples[i:j]) # Overlapping
        log.debug("{n} {r} samples after purge", r=role, n=len(result))
        return result



    


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
        if self.pool:
            self.pool.close()
        self.pool = None
        log.debug("Closed a DB Connection to {conn!s}", conn=self.path)
