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
        self.period  = options['period']
        self.nrounds = options['rounds']
        self.central = options['central']
        self.size    = options['size']
        self.phot = {
            'ref' : {'queue': None, 'info': None},
            'test': {'queue': None, 'info': None},
        }
        self.curRound = 1

   
    def startService(self):
        '''
        Starts Stats service
        '''
        log.info("starting {name}: Window Size= {w} samples, T = {t} secs, Rounds = {r}", 
            name=self.name, w=self.options['size'], t=self.options['period'],r=self.options['rounds'])
        Service.startService(self)
        self.statTask = task.LoopingCall(self._schedule)
        self.statTask.start(self.period, now=False)  # call every T seconds
        self.tstPhotometer = self.parent.getServiceNamed(TEST_PHOTOMETER_SERVICE)
        self.refPhotometer = self.parent.getServiceNamed(REF_PHOTOMETER_SERVICE)
        self.phot['test']['queue'] = self.tstPhotometer.buffer.getBuffer()
        self.phot['ref']['queue']  = self.refPhotometer.buffer.getBuffer()

       
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
            self.phot['ref']['info'] = info
            self.phot['ref']['info']['zp'] = info['zp'] if info['zp'] != 0 else self.options['zp_abs']
            info = yield self.tstPhotometer.getPhotometerInfo()
            self.phot['test']['info'] = info
            yield self._accumulateRounds()
        elif 1 < self.curRound < self.nrounds:
            yield self._accumulateRounds()
        else:
            yield self._accumulateRounds()
            yield self.stopService()

    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def _computeZP(self, refFreq, tstFreq, zpfict, zpabs):
        diff = 2.5*math.log10(testFreq/refFreq)
        refMag  = zpfict - 2.5*math.log10(refFreq)
        testMag = zpfict - 2.5*math.log10(testFreq)
        testZP = round(zpabs + diff,2)
        return testZP 

    def _accumulateRounds(self):
        log.info("="*72)
        refFreq,  refMag, refStddev  = self._statsFor('ref')
        tstFreq, testMag, testStddev = self._statsFor('test')
        rLab = self.phot['ref']['info']['name']
        tLab = self.phot['ref']['info']['name']
        if refFreq is not None and tstFreq is not None:
            difFreq = -2.5*math.log10(refFreq/tstFreq)
            difMag = refMag - testMag
            if refStddev != 0.0 and testStddev != 0.0:
                log.info('ROUND         {i:02d}: Diff by -2.5*log(Freq[ref]/Freq[test]) = {difFreq:0.3f},    Diff by Mag[ref]-Mag[test]) = {difMag:0.2f}',
                    i=self.curRound, difFreq=difFreq, difMag=difMag)
                self.curRound += 1
            elif refStddev == 0.0 and testStddev != 0.0:
                log.warn('FROZEN {lab}', lab=rLab)
            elif testStddev == 0.0 and refStddev != 0.0:
                log.warn('FROZEN {lab}', lab=tLab)
            else:
                log.warn('FROZEN {rLab} and {tLab}', rLab=rLab, tLab=tLab)



    def _statsFor(self, tag):
        '''compute statistics for a given queue'''
        queue       = self.phot[tag]['queue']
        size        = len(queue)
        if size == 0:
            return None, None, None
        label       = self.phot[tag]['info']['label']
        name        = self.phot[tag]['info']['name']
        zp          = self.phot[tag]['info']['zp']
        start       = queue[0]['tstamp'].strftime("%H:%M:%S")
        end         = queue[-1]['tstamp'].strftime("%H:%M:%S")
        window      = (queue[-1]['tstamp'] - queue[0]['tstamp']).total_seconds()
        frequencies = [ item['freq'] for item in queue]
        clabel      = "Mean" if self.central == "mean" else "Median"
        log.debug("{label} Frequencies: {seq}", label=label, seq=frequencies)
        if size < self.size:      
            log.info('[{label}] {name:10s} waiting for enough samples, {n} remaining', 
                label=label, name=name, n=self.size-size)
            return None, None, None
        try:
            log.debug("queue = {q}",q=frequencies)
            cFreq   = statistics.mean(frequencies) if self.central == "mean" else statistics.median(frequencies)
            stddev  = statistics.stdev(frequencies, cFreq)
            cMag    = zp  - 2.5*math.log10(cFreq)
        except statistics.StatisticsError as e:
            log.error("Fallo estadistico: {e}",e=e)
            return None, None, None
        else: 
            log.info("[{label}] {name:10s} ({start}-{end})[{w:0.1f}s] & ZP = {zp:0.2f} =>  Mag {cMag:0.2f}, {clabel} Freq {cFreq:0.3f} Hz, StDev = {stddev:0.3f} Hz",
                name=name, label=label, start=start, end=end, zp=zp, clabel=clabel, cFreq=cFreq, cMag=cMag, stddev=stddev, w=window)
            return cFreq, cMag, stddev

    


__all__ = [ "StatsService" ]