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
import random
import os
import math
import statistics

from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted          import __version__ as __twisted_version__
from twisted.logger   import Logger, LogLevel
from twisted.internet import task, reactor, defer
from twisted.internet.defer  import inlineCallbacks, returnValue, DeferredList
from twisted.internet.threads import deferToThread
from twisted.application.service import Service
#--------------
# local imports
# -------------

from zptess import __version__
from zptess.config import VERSION_STRING, loadCfgFile
from zptess.logger import setLogLevel
from zptess.config import loglevel


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

    # Service name
    NAME = 'Statistics Service'


    def __init__(self, options, cmdopts):
        Service.__init__(self)
        setLogLevel(namespace='stats', levelStr=loglevel(cmdopts))
        self.options = options
        self.cmdopts = cmdopts
        self.refname = self.options['refname']
        self.period  = self.options['period']
        self.qsize   = self.options['size']
        self.central = self.options['central']
        self.nrounds = self.options['rounds']
        self.curRound = 1
        self.testname = None
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
        log.info("starting Stats Service: Window Size= {w} samples, T = {t} secs, Rounds = {r}", 
            w=self.options['size'], t=self.options['period'],r=self.options['rounds'])
        Service.startService(self)
        self.statTask = task.LoopingCall(self._schedule)
        self.statTask.start(self.period, now=False)  # call every T seconds
        self.photomService = self.parent.getServiceNamed('test')

       
    def stopService(self):
        log.info("stopping Stats Service")
        self.statTask.stop()
        return Service.stopService(self)
    
    
    # --------------------
    # Scheduler Activities
    # --------------------

    
    def _schedule(self):  
        if self.curRound > self.nrounds:
            log.info("Not computing statistics anymore")
        elif self.curRound < self.nrounds:
            self.accumulateRounds()
        else:
            self.accumulateRounds()
            self.onStatsComplete(self.choose())

    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def accumulateRounds(self):
        zpc = self.options['zp_calib']
        zpf = self.options['zp_fict']
        log.info("-"*72)
        refFreq,  refStddev  = self.statsFor(self.queue['reference'], "REF.", self.refname)
        testFreq, testStddev = self.statsFor(self.queue['test'], "TEST", self.testname)
        if refFreq is not None and testFreq is not None:
            diff = 2.5*math.log10(testFreq/refFreq)
            refMag  = zpf - 2.5*math.log10(refFreq)
            testMag = zpf - 2.5*math.log10(testFreq)
            testZP = round(zpc + diff,2)     
            if refStddev != 0.0 and testStddev != 0.0:
                log.info('ROUND {i:02d}: REF. Mag = {rM:0.2f}. TEST Mag = {tM:0.2f}, Diff = {d:0.3f} => TEST ZP = {zp:0.2f}',
                i=self.curRound, rM=refMag, tM=testMag, d=diff, zp=testZP)
                self.best['zp'].append(testZP)
                self.best['refFreq'].append(refFreq)
                self.best['testFreq'].append(testFreq)
                self.curRound += 1
            elif refStddev == 0.0 and testStddev != 0.0:
                log.warn('FROZEN REF. Mag = {rM:0.2f}, TEST Mag = {tM:0.2f}', rM=refMag, tM=testMag)
            elif testStddev == 0.0 and refStddev != 0.0: 
                log.warn('REF. Mag = {rM:0.2f}, FROZEN TEST Mag = {tM:0.2f}',rM=refMag, tM=testMag)
            else:
                log.warn('FROZEN REF. Mag = {rM:0.2f}, FROZEN TEST Mag = {tM:0.2f}',rM=refMag, tM=testMag)


    def choose(self):
        '''Choose the best statistics at the end of the round'''
        log.info("#"*72) 
        log.info("Best ZP        list is {bzp}",bzp=self.best['zp'])
        log.info("Best Ref  Freq list is {brf}",brf=self.best['refFreq'])
        log.info("Best Test Freq list is {btf}",btf=self.best['testFreq'])
        final = dict()
        old_zp = float(self.parent.old_zp)
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
        log.info("Ref. Freq. = {rF:0.3f} Hz ,Test Freq. = {tF:0.3f}, Ref. Mag. = {rM:0.2f}, Test Mag. = {tM:0.2f}, Diff {d:0.2f}", 
                rF= final['refFreq'], tF=final['testFreq'], rM=final['refMag'], tM=final['testMag'], d=final['magDiff'])
        log.info("OLD TEST ZP = {old_zp:0.2f}, NEW TEST ZP = {new_zp:0.2f}", old_zp=old_zp, new_zp= final['zp'])
        log.info("#"*72)
        return final



    def statsFor(self, queue, label, name):
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
        stats['mac']     = self.tess_mac    # Is it station or AP MAC ?????
        stats['tstamp']  = (datetime.datetime.utcnow() + datetime.timedelta(seconds=0.5)).strftime(TSTAMP_FORMAT)
        stats['author']  = self.author
        stats['tess']    = self.tess_name
        stats['updated'] = self.update
        stats['old_zp']  = self.old_zp
        # transform dictionary into readable header columns for CSV export
        oldkeys = ['tess', 'tstamp', 'testMag', 'testFreq', 'refMag', 'refFreq', 'magDiff', 'zp', 'mac', 'old_zp', 'author', 'updated']
        newkeys = ['Name', 'Timestamp', 'Magnitud TESS.', 'Frecuencia', 'Magnitud Referencia', 'Frec Ref', 'Offset vs stars3', 'ZP', 'Station MAC', 'OLD ZP', 'Author', 'Updated']
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


    def _flashZeroPoint(self, zp):
        '''Flash new ZP. Synchronous request to be executed in a separate thread'''
        try:
            url = "{0:s}?cons={1:0.2f}".format(self.options['save_url'], zp)
            log.debug("requesting URL {url}", url=url)
            resp = requests.get(url, timeout=(2,5))
            resp.raise_for_status()
        except Exception as e:
            log.error("{e}",e=e)
        else:
            matchobj = REGEXP['flash'].search(self.text)
            if matchobj:
                flashed_zp = float(matchobj.groups(1)[0])
                log.info("Flashed ZP of {tess} is {fzp}", tess=self.tess_name, fzp=flashed_zp)

    @inlineCallbacks
    def onStatsComplete(self, stats):
        yield self.stopService()
        if self.update:
            log.info("updating {tess} ZP to {zp}", tess=self.tess_name, zp=stats['zp'])
            # This should not be synchronous, but I could not make it work either with
            # the Twisted Agent or even deferring to thread
            self._flashZeroPoint(stats['zp'])   
        else:
            log.info("skipping updating of {tess} ZP",tess=self.tess_name)

        yield deferToThread(self._exportCSV, stats)
        yield self.stopService()

    


    


__all__ = [ "StatsService" ]