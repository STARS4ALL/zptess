# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import sys
import datetime
import os.path
import math
import statistics
import csv

from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet import task, reactor, defer
from twisted.internet.defer  import inlineCallbacks, returnValue, DeferredList
from twisted.internet.threads import deferToThread
from twisted.application.service import Service

#--------------
# local imports
# -------------

from . import TEST_PHOTOMETER_SERVICE, REF_PHOTOMETER_SERVICE, TSTAMP_FORMAT

from zptess.logger import setLogLevel


# ----------------
# Module constants
# ----------------


# ----------
# Exceptions
# ----------

class TESSEstimatorError(ValueError):
    '''Estimator is not median or mean'''
    def __str__(self):
        s = self.__doc__
        if self.args:
            s = "{0}: '{1}'".format(s, self.args[0])
        s = '{0}.'.format(s)
        return s

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='stats')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------    
# -----------------------------------------------------------------------------  


class StatsService(Service):

    def __init__(self, options):
        Service.__init__(self)
        setLogLevel(namespace='stats', levelStr=options['log_level'])
        self.options = options
        self.refname = self.options['refname']
        self.period  = self.options['period']
        self.qsize   = self.options['size']
        self.central = self.options['central']
        self.nrounds = self.options['rounds']
        self.curRound = 1
        if self.central not in ['mean','median']:
            throw 
        self.queue       = { 
            'test'      : deque([], self.qsize), 
            'reference' : deque([], self.qsize), 
        } 
        self.best = {
            'zp'       : list(),
            'refFreq'  : list(),
            'testFreq' : list(),
        }

   

    def startService(self):
        '''
        Starts Stats service
        '''
        log.info("starting {name}: Window Size= {w} samples, T = {t} secs, Rounds = {r}", 
            name=self.name, w=self.options['size'], t=self.options['period'],r=self.options['rounds'])
        Service.startService(self)
        self.statTask = task.LoopingCall(self._schedule)
        self.statTask.start(self.period, now=False)  # call every T seconds
        self.testPhotometer = self.parent.getServiceNamed(TEST_PHOTOMETER_SERVICE)
        self.testLabel = self.testPhotometer.getLabel()
        self.refPhotometer = self.parent.getServiceNamed(REF_PHOTOMETER_SERVICE)
        self.refLabel = self.refPhotometer.getLabel()

       
    def stopService(self):
        log.info("stopping Stats Service")
        self.statTask.stop()
        return Service.stopService(self)
    
    
    # --------------------
    # Scheduler Activities
    # --------------------

    @inlineCallbacks
    def _schedule(self):  
        if self.curRound > self.nrounds:
            log.info("Not computing statistics anymore")
        elif self.curRound < self.nrounds:
            yield self._accumulateRounds()
        else:
            yield self._accumulateRounds()
            self._onStatsComplete(self._choose())

    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def _doAccumulateRounds(self):
        zpabs = self.options['zp_abs']
        zpf = self.options['zp_fict']
        log.info("-"*72)
        refFreq,  refStddev  = self._statsFor(self.queue['reference'], self.refLabel, self.refname)
        testFreq, testStddev = self._statsFor(self.queue['test'], self.testLabel, self.info['name'])
        if refFreq is not None and testFreq is not None:
            diff = 2.5*math.log10(testFreq/refFreq)
            refMag  = zpf - 2.5*math.log10(refFreq)
            testMag = zpf - 2.5*math.log10(testFreq)
            testZP = round(zpabs + diff,2)     
            if refStddev != 0.0 and testStddev != 0.0:
                log.info('ROUND {i:02d}: {rLab} Mag = {rM:0.2f}. {tLab} Mag = {tM:0.2f}, Diff = {d:0.3f} => {tLab} ZP = {zp:0.2f}',
                rLab=self.refLabel, tLab=self.testLabel, i=self.curRound, rM=refMag, tM=testMag, d=diff, zp=testZP)
                self.best['zp'].append(testZP)
                self.best['refFreq'].append(refFreq)
                self.best['testFreq'].append(testFreq)
                self.curRound += 1
            elif refStddev == 0.0 and testStddev != 0.0:
                log.warn('FROZEN {rLab} Mag = {rM:0.2f}, {tLab} Mag = {tM:0.2f}', rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)
            elif testStddev == 0.0 and refStddev != 0.0: 
                log.warn('{rLab} Mag = {rM:0.2f}, FROZEN {tLab} Mag = {tM:0.2f}', rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)
            else:
                log.warn('FROZEN {rLab} Mag = {rM:0.2f}, FROZEN {tLab} Mag = {tM:0.2f}', rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)


    @inlineCallbacks
    def _accumulateRounds(self):
        try:
            self.info = yield self.testPhotometer.getPhotometerInfo()
        except:
            reactor.callLater(0, reactor.stop)
        else:
            self._doAccumulateRounds()

    def _choose(self):
        '''Choose the best statistics at the end of the round'''
        log.info("#"*72) 
        log.info("Best ZP        list is {bzp}",bzp=self.best['zp'])
        log.info("Best {rLab} Freq list is {brf}",brf=self.best['refFreq'], rLab=self.refLabel)
        log.info("Best {tLab} Freq list is {btf}",btf=self.best['testFreq'], tLab=self.testLabel)
        final = dict()
        old_zp = float(self.testPhotometer.info['zp'])
        try:
            final['zp']       = statistics.mode(self.best['zp'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best zp using mode, selecting median instead")
            final['zp']        = statistics.median(self.best['zp'])
        try:
             final['refFreq']   = statistics.mode(self.best['refFreq'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best Ref. Freq. using mode, selecting median instead")
            final['refFreq']  = statistics.median(self.best['refFreq'])
        try:
             final['testFreq']  = statistics.mode(self.best['testFreq'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best Test Freq. using mode, selecting median instead")
            final['testFreq'] = statistics.median(self.best['testFreq'])

        final['refMag']   = round(self.options['zp_fict'] - 2.5*math.log10(final['refFreq']),2)
        final['testMag']  = round(self.options['zp_fict'] - 2.5*math.log10(final['testFreq']),2)
        final['magDiff']  = round(2.5*math.log10(final['testFreq']/final['refFreq']),2)
        log.info("{rLab} Freq. = {rF:0.3f} Hz , {tLab} Freq. = {tF:0.3f}, {rLab} Mag. = {rM:0.2f}, {tLab} Mag. = {tM:0.2f}, Diff {d:0.2f}", 
                rF= final['refFreq'], tF=final['testFreq'], rM=final['refMag'], tM=final['testMag'], d=final['magDiff'],
                rLab=self.refLabel, tLab=self.testLabel)
        log.info("OLD {tLab} ZP = {old_zp:0.2f}, NEW {tLab} ZP = {new_zp:0.2f}", old_zp=old_zp, new_zp= final['zp'], tLab=self.testLabel)
        log.info("#"*72)
        return final


    def _statsFor(self, queue, label, name):
        '''compute statistics for a given queue'''
        s = len(queue)
        l =  [ item['freq'] for item in queue]
        log.debug("{label} Frequencies: {lista}", label=label, lista=l)
        if s < self.options['size']:
            log.info('[{label}] {name:10s} waiting for enough samples, {n} remaining', 
                label=label, name=name, n=self.options['size']-s)
            return None, None
        try:
            log.debug("queue = {q}",q=l)
            central = statistics.mean(l) if self.central == "mean" else statistics.median(l)
            clabel  = "Mean" if self.central == "mean" else "Median"
            stddev  = statistics.stdev(l, central)
            start   = queue[0]['tstamp'].strftime("%H:%M:%S")
            end     = queue[-1]['tstamp'].strftime("%H:%M:%S")
            window  = (queue[-1]['tstamp'] - queue[0]['tstamp']).total_seconds()
        except statistics.StatisticsError as e:
            log.error("Fallo estadistico: {e}",e=e)
        else: 
            log.info("[{label}] {name:10s} ({start}-{end})[{w:0.1f}s] => {clabel} = {central:0.3f} Hz, StDev = {stddev:0.2e} Hz",
                name=name, label=label, start=start, end=end, clabel=clabel, central=central, stddev=stddev, w=window)
            return central, stddev

    # ----------------------
    # Other Helper functions
    # ----------------------

    def _exportCSV(self, stats):
        '''Exports summary statistics to a common CSV file'''
        log.debug("Appending to CSV file {file}",file=self.options['csv_file'])
        # Adding metadata to the estimation
        stats['mac']      = self.info['mac']  
        stats['model']    = self.info['model']  
        stats['firmware'] = self.info['firmware']
        stats['tstamp']   = (datetime.datetime.utcnow() + datetime.timedelta(seconds=0.5)).strftime(TSTAMP_FORMAT)
        stats['author']   = self.options['author']
        stats['tess']     = self.info['name']
        stats['updated']  = self.options['update']
        stats['old_zp']   = self.info['zp'] 
        # transform dictionary into readable header columns for CSV export
        oldkeys = ['model','tess', 'tstamp', 'testMag', 'testFreq', 'refMag', 'refFreq', 'magDiff', 'zp', 'mac', 'old_zp', 'author', 'firmware', 'updated']
        newkeys = ['Model','Name', 'Timestamp', 'Magnitud TESS.', 'Frecuencia', 'Magnitud Referencia', 'Frec Ref', 'Offset vs stars3', 'ZP', 'Station MAC', 'OLD ZP', 'Author', 'Firmware', 'Updated']
        for old,new in zip(oldkeys,newkeys):
            stats[new] = stats.pop(old)
        # CSV file generation
        writeheader = not os.path.exists(self.options['csv_file'])
        with open(self.options['csv_file'], mode='a+') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=newkeys, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            if writeheader:
                writer.writeheader()
            writer.writerow(stats)
        log.info("updated CSV file {file}",file=self.options['csv_file'])


    @inlineCallbacks
    def _onStatsComplete(self, stats):
        yield self.stopService()
        if self.options['update']:
            log.info("updating {tess} ZP to {zp}", tess=self.info['name'], zp=stats['zp'])
            # This should not be synchronous, but I could not make it work either with
            # the Twisted Agent or even deferring to thread
            try:
                yield self.testPhotometer.writeZeroPoint(stats['zp'])
            except Exception as e:
                log.error("Timeout when updating photometer zero point")
                reactor.callLater(0, reactor.stop)
            else:
                yield deferToThread(self._exportCSV, stats)
        else:
            log.info("skipping updating of {tess} ZP",tess=self.info['name'])
            yield deferToThread(self._exportCSV, stats)
        reactor.callLater(0,reactor.stop)
        

    


    


__all__ = [ "StatsService" ]