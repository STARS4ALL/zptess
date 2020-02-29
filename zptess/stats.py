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


class StatsService(Service):

    def __init__(self, options):
        Service.__init__(self)
        setLogLevel(namespace='ReadingsService', levelStr=options['log_level'])
        self.options  = options
        self.period   = options['period']
        self.nrounds  = options['rounds']
        self.central  = options['central']
        self.size     = options['size']
        self.readMode = options['read']
        self.phot = {
            'ref' : {'queue': None, 'info': None},
            'test': {'queue': None, 'info': None},
        }
        self.curRound = 1
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
            if not self.readMode:
                self.phot['ref']['info']['zp']  = self.options['zp_fict']
                self.phot['test']['info']['old_zp'] = self.phot['test']['info']['zp']
                self.phot['test']['info']['zp'] = self.options['zp_fict']
            yield self._accumulateRounds()
        elif 1 < self.curRound < self.nrounds:
            yield self._accumulateRounds()
        else:
            yield self._accumulateRounds()
            if not self.readMode:
                stats = self._choose()
                yield self._maybeUpdateZeroPoint(stats['zp'])
                newkeys = self._addMetadata(stats)
                yield deferToThread(self._exportCSV, stats, newkeys)
            yield self.stopService()

    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def _computeZP(self, magDiff):
        return round(self.options['zp_abs'] + magDiff,2)
     
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
                log.info('ROUND       {i:02d}: Diff by -2.5*log(Freq[ref]/Freq[test]) = {difFreq:0.2f},    Diff by Mag[ref]-Mag[test]) = {difMag:0.2f}',
                    i=self.curRound, difFreq=difFreq, difMag=difMag)
                self.curRound += 1
                self.best['zp'].append(self._computeZP(difMag))          # Collect this info wether we need it or not
                self.best['refFreq'].append(refFreq)
                self.best['testFreq'].append(tstFreq)
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
            log.info("[{label}] {name:8s} ({start}-{end})[{w:0.1f}s][{sz:d}] & ZP {zp:0.2f} =>> Mag {cMag:0.2f}, {clabel} Freq {cFreq:0.3f} Hz, StDev {stddev:0.3f} Hz",
                name=name, label=label, start=start, end=end, sz=size, zp=zp, clabel=clabel, cFreq=cFreq, cMag=cMag, stddev=stddev, w=window)
            return cFreq, cMag, stddev


    def _choose(self):
        '''Choose the best statistics at the end of the round'''
        refLabel  = self.phot['ref']['info']['label']
        testLabel = self.phot['test']['info']['label']
        log.info("#"*72) 
        log.info("Best ZP        list is {bzp}",bzp=self.best['zp'])
        log.info("Best {rLab} Freq list is {brf}",brf=self.best['refFreq'],  rLab=refLabel)
        log.info("Best {tLab} Freq list is {btf}",btf=self.best['testFreq'], tLab=testLabel)
        final = dict()
        old_zp = float(self.phot['test']['info']['old_zp'])
        final['old_zp'] = old_zp
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
                rLab=refLabel, tLab=testLabel)
        log.info("OLD {tLab} ZP = {old_zp:0.2f}, NEW {tLab} ZP = {new_zp:0.2f}", old_zp=old_zp, new_zp= final['zp'], tLab=testLabel)
        log.info("#"*72)
        return final



    def _addMetadata(self, stats):
        # Adding metadata to the estimation
        stats['tess']     = self.phot['test']['info']['name']
        stats['mac']      = self.phot['test']['info']['mac']  
        stats['model']    = self.phot['test']['info']['model']  
        stats['firmware'] = self.phot['test']['info']['firmware']
        stats['tstamp']   = (datetime.datetime.utcnow() + datetime.timedelta(seconds=0.5)).strftime(TSTAMP_FORMAT)
        stats['author']   = self.options['author']
        stats['updated']  = self.options['update']
        # transform dictionary into readable header columns for CSV export
        oldkeys = ['model','tess', 'tstamp', 'testMag', 'testFreq', 'refMag', 'refFreq', 'magDiff', 'zp', 'mac', 'old_zp', 'author', 'firmware', 'updated']
        newkeys = ['Model','Name', 'Timestamp', 'Magnitud TESS.', 'Frecuencia', 'Magnitud Referencia', 'Frec Ref', 'Offset vs stars3', 'ZP', 'Station MAC', 'OLD ZP', 'Author', 'Firmware', 'Updated']
        for old,new in zip(oldkeys,newkeys):
            stats[new] = stats.pop(old)
        return newkeys


    @inlineCallbacks
    def _maybeUpdateZeroPoint(self, zp):
        # Adding metadata to the estimation
        name = self.phot['test']['info']['name']
        if self.options['update']:
            log.info("updating {tess} ZP to {zp}", tess=name, zp=zp)
            try:
                yield self.tstPhotometer.writeZeroPoint(zp)
            except Exception as e:
                log.error("Timeout when updating photometer zero point")
        else:
            log.info("Not writting ZP to {tess} photometer",tess=name)


    def _exportCSV(self, stats, newkeys):
        '''Exports summary statistics to a common CSV file'''
        log.debug("Appending to CSV file {file}",file=self.options['csv_file'])
        # Adding metadata to the estimation
        # transform dictionary into readable header columns for CSV export
        # CSV file generation
        writeheader = not os.path.exists(self.options['csv_file'])
        try:
            with open(self.options['csv_file'], mode='a+') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=newkeys, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
                if writeheader:
                    writer.writeheader()
                writer.writerow(stats)
            log.info("updated CSV file {file}",file=self.options['csv_file'])
        except Exception as e:
            log.warn("Could not update  CSV file {file}", file=self.options['csv_file'])
            log.error("{excp}",excp = e)

    


__all__ = [ "StatsService" ]