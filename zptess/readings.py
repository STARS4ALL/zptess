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

log = Logger(namespace='read')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------    
# -----------------------------------------------------------------------------  


class ReadingsService(Service):

    def __init__(self, options):
        Service.__init__(self)
        setLogLevel(namespace='ReadingsService', levelStr=options['log_level'])
        self.options = options
        self.period  = self.options['period']
        self.nrounds = self.options['rounds']
        self.curRound = 1
        self.queue   = {}
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
        self.refPhotometer = self.parent.getServiceNamed(REF_PHOTOMETER_SERVICE)
        self.queue['test']      = self.testPhotometer.buffer.getBuffer()
        self.queue['reference'] = self.refPhotometer.buffer.getBuffer()
       

       
    def stopService(self):
        log.info("stopping {name}", name=self.name)
        self.statTask.stop()
        reactor.callLater(0,reactor.stop)
        return Service.stopService(self)
    
    
    # --------------------
    # Scheduler Activities
    # --------------------

    @inlineCallbacks
    def _schedule(self):  
        if self.curRound > self.nrounds:
            log.info("Finished readings")
        elif self.curRound == 1:
            info = yield self.refPhotometer.getPhotometerInfo()
            self.refname  = info['name']
            self.refLabel = info['label']
            self.refzp    = info['zp'] if info['zp'] != 0 else self.options['zp_abs']
            self.info     = info
            info = yield self.testPhotometer.getPhotometerInfo()
            self.testname  = info['name']
            self.testLabel = info['label']
            self.testzp    = info['zp']
            yield self._accumulateRounds()
        elif 1 < self.curRound < self.nrounds:
            yield self._accumulateRounds()
        else:
            yield self._accumulateRounds()
            yield self.stopService()

    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def _accumulateRounds(self):
        log.info("="*72)
        refFreq,  refStddev  = self._statsFor(self.queue['reference'], self.refLabel, self.refname)
        testFreq, testStddev = self._statsFor(self.queue['test'],      self.testLabel, self.info['name'])
        if refFreq is not None and testFreq is not None:
            diffFreq = 2.5*math.log10(testFreq/refFreq)
            refMag  = self.refzp  - 2.5*math.log10(refFreq)
            testMag = self.testzp - 2.5*math.log10(testFreq)
            diffMag = refMag - testMag
            if refStddev != 0.0 and testStddev != 0.0:
                log.info('ROUND {i:02d}: {rLab} Mag = {rM:0.2f}. {tLab} Mag = {tM:0.2f}, Diff = {dif:0.3f} => {tLab} ZP = {zp:0.2f}',
                    i=self.curRound, 
                    rLab=self.refLabel, tLab=self.testLabel,
                    rM=refMag, tM=testMag, 
                    dif=diffMag, zp=self.testzp)
                self.curRound += 1
            elif refStddev == 0.0 and testStddev != 0.0:
                log.warn('FROZEN {rLab} Mag = {rM:0.2f}, {tLab} Mag = {tM:0.2f}', 
                    rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)
            elif testStddev == 0.0 and refStddev != 0.0: 
                log.warn('{rLab} Mag = {rM:0.2f}, FROZEN {tLab} Mag = {tM:0.2f}', 
                    rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)
            else:
                log.warn('FROZEN {rLab} Mag = {rM:0.2f}, FROZEN {tLab} Mag = {tM:0.2f}', 
                    rLab=self.refLabel, tLab=self.testLabel, rM=refMag, tM=testMag)



    def _statsFor(self, queue, label, name):
        '''compute statistics for a given queue'''
        size = len(queue)
        seq =  [ item['freq'] for item in queue]
        log.debug("{label} Frequencies: {lista}", label=label, lista=seq)
        if size < self.options['size']:
            log.info('[{label}] {name:10s} waiting for enough samples, {n} remaining', 
                label=label, name=name, n=self.options['size']-size)
            return None, None
        try:
            log.debug("queue = {q}",q=seq)
            median  = statistics.median(seq)
            mean    = statistics.mean(seq) 
            #clabel  = "Mean" if self.central == "mean" else "Median"
            stddev  = statistics.stdev(seq, mean)
            start   = queue[0]['tstamp'].strftime("%H:%M:%S")
            end     = queue[-1]['tstamp'].strftime("%H:%M:%S")
            window  = (queue[-1]['tstamp'] - queue[0]['tstamp']).total_seconds()
        except statistics.StatisticsError as e:
            log.error("Fallo estadistico: {e}",e=e)
        else: 
            log.info("[{label}] {name:10s} ({start}-{end})[{w:0.1f}s] => median = {median:0.3f} mean = {mean:0.3f} Hz, StDev = {stddev:0.2e} Hz",
                name=name, label=label, start=start, end=end, median=median, mean=mean, stddev=stddev, w=window)
            return median, stddev


    


__all__ = [ "StatsService" ]