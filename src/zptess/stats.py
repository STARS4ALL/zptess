# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

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
from twisted.internet.defer  import inlineCallbacks, DeferredList
from twisted.internet.threads import deferToThread
from twisted.application.service import Service

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import TSTAMP_FORMAT
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


def mode(iterable):
    try:
        result = statistics.multimode(iterable)
        if len(result) != 1:     # To make it compatible with my previous software
            raise statistics.StatisticsError
        result = result[0]
    except AttributeError as e: # Previous to Python 3.8
        result = statistics.mode(iterable)
    return result


# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='read')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------    
# -----------------------------------------------------------------------------  


class StatsService(Service):

    NAME = "Statistical Service"

    def __init__(self, options):
        Service.__init__(self)
        setLogLevel(namespace='ReadingsService', levelStr=options['log_level'])
        self.options  = options
        self.period   = options['period']
        self.nrounds  = options['rounds']
        self.central  = options['central']
        self.size     = options['size']
        self.session  = options['session']
        self.phot = {
            'ref' : {'queue': None, 'info': None},
            'test': {'queue': None, 'info': None},
        }
        self.curRound = 1
        self.best = {
            'zp'       : list(),
            'ref_freq'  : list(),
            'test_freq' : list(),
        }
        # To be overriden when the ref photometer comes alive
        # this is useful only when activating the test photometer
        self.zp_abs  = 20.50
        self.zp_fict = 20.50 
        pub.subscribe(self.onPhotometerInfo, 'photometer_info')

   
    def startService(self):
        '''
        Starts Stats service
        '''
        log.info("starting {name}: Window Size= {w} samples, T = {t} secs, Rounds = {r}", 
            name=self.name, w=self.options['size'], t=self.options['period'],r=self.options['rounds'])
        Service.startService(self)
        self.statTask = task.LoopingCall(self._schedule)
        self.statTask.start(self.period, now=False)  # call every T seconds

       
    def stopService(self):
        log.info("stopping {name}", name=self.name)
        self.statTask.stop()
        return defer.succeed(None)
    
    # ---------------
    # OPERATIONAL API
    # ---------------

    def onPhotometerInfo(self, role, circ_buffer, info):
        self.phot[role]['info']   = info
        self.phot[role]['queue']  = circ_buffer.getBuffer()
        if role == 'ref':
            self.zp_abs  = info['zp_abs']
            self.zp_fict = info['zp']   # Ficticious ZP is the reference ZP

    # --------------------
    # Scheduler Activities
    # --------------------

    @inlineCallbacks
    def _schedule(self):  
        if self.curRound > self.nrounds:
            log.info("Finished readings")
            return(None)

        if 0 < self.curRound < self.nrounds:
            yield self._accumulateRounds()
            return(None)

        if self.curRound == self.nrounds:
            yield self._accumulateRounds()
            summary_ref, summary_test = self._choose()
            if self.options['update']:
                pub.sendMessage('update_zero_point', zero_point=summary_test['zero_point'])
            else:
                log.info("Not updating ZP to test photometer")
            pub.sendMessage('summary_stats_info', role='ref', stats_info=summary_ref)
            pub.sendMessage('summary_stats_info', role='test',stats_info=summary_test)
            reactor.callLater(0, self.parent.stopService)


    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def _computeZP(self, magDiff):
        return round(self.zp_abs + magDiff,2)
        
    def _accumulateRounds(self):
        log.info("="*72)
        tst_stats = None; ref_stats = None;
        if not self.isEmpty('ref'):
            ref_stats = self._statsFor('ref')
        if not  self.isEmpty('test'):
            tst_stats = self._statsFor('test')

        if tst_stats is not None and ref_stats is not None:
            difFreq = -2.5*math.log10(ref_stats['freq']/tst_stats['freq'])
            if ref_stats['stddev'] != 0.0 and tst_stats['stddev'] != 0.0:
                # Magnitude difference by -2.5*log(Freq[ref]/Freq[test])
                log.info('ROUND       {i:02d}: (ref-test) \u0394 Mag = {difFreq:0.2f}, ZP Fict = {zp_fict:0.2f}, ZP Abs = {zp_abs:0.2f}',
                    i=self.curRound, difFreq=difFreq, zp_fict=self.zp_fict, zp_abs=self.zp_abs)
                self.curRound += 1
                zp = self._computeZP(difFreq)
                self.best['zp'].append(zp)          # Collect this info wether we need it or not
                self.best['ref_freq'].append(ref_stats['freq'])
                self.best['test_freq'].append(tst_stats['freq'])
                ref_stats['zero_point'] = None
                tst_stats['zero_point'] = zp
                pub.sendMessage('round_stats_info', role='ref',  stats_info=ref_stats)
                pub.sendMessage('round_stats_info', role='test', stats_info=tst_stats)
            elif ref_stats['stddev'] == 0.0 and tst_stats['stddev'] != 0.0:
                log.warn('FROZEN {lab}', lab=ref_stats['name'])
            elif tst_stats['stddev'] == 0.0 and ref_stats['stddev'] != 0.0:
                log.warn('FROZEN {lab}', lab=tst_stats['name'])
            else:
                log.warn('FROZEN {rLab} and {tLab}', rLab=ref_stats['name'], tLab=tst_stats['name'])


    def isEmpty(self, tag):
        phot  = self.phot.get(tag, None)
        queue = phot.get('queue', None)
        return (phot is None) or (queue is None) or len(queue) == 0


    def _statsFor(self, tag):
        '''compute statistics for a given queue'''
        queue       = self.phot[tag]['queue']
        begin_tstamp = queue[0]['tstamp']
        end_tstamp  = queue[-1]['tstamp']
        size        = len(queue)
        label       = self.phot[tag]['info']['label']
        name        = self.phot[tag]['info']['name']
        mac         = self.phot[tag]['info']['mac']
        zp          = self.zp_fict
        start       = (begin_tstamp  + datetime.timedelta(seconds=0.5)).strftime("%H:%M:%S")
        end         = (end_tstamp + datetime.timedelta(seconds=0.5)).strftime("%H:%M:%S")
        duration    = (queue[-1]['tstamp'] - queue[0]['tstamp']).total_seconds()
        frequencies = [ item['freq'] for item in queue]

        log.debug("{label} Frequencies: {seq}", label=label, seq=frequencies)
        if size < self.size:      
            log.info('[{label}] {name:10s} waiting for enough samples, {n} remaining', 
                label=label, name=name, n=self.size-size)
            return None
        try:
            log.debug("queue = {q}",q=frequencies)
            if self.central == "mean":
                cFreq = statistics.mean(frequencies)
            elif self.central == "median":
                cFreq = statistics.median(frequencies)
            else:
                cFreq = statistics.mode(frequencies)
            stddev = statistics.stdev(frequencies, cFreq)
            cMag  = zp - 2.5*math.log10(cFreq)
        except statistics.StatisticsError as e:
            log.error("Statistics error: {e}", e=e)
            return None
        except ValueError as e:
            log.error("math.log10() error for {f}: {e}", e=e, f=cFreq)
            return None
        else: 
            log.info("[{label}] {name:8s} ({start}-{end})[{w:0.1f}s][{sz:d}] {clabel:6s} => m = {cMag:0.2f}, f = {cFreq:0.3f} Hz, \u03C3 = {stddev:0.3f} Hz",
                name=name, label=label, start=start, end=end, sz=size, zp=zp, clabel=self.central,
                cFreq=cFreq, cMag=cMag, stddev=stddev, w=duration)
            stats_info = {
                'round'       : self.curRound,
                'begin_tstamp': begin_tstamp.strftime(TSTAMP_FORMAT),
                'end_tstamp'  : end_tstamp.strftime(TSTAMP_FORMAT),
                'central'     : self.central,
                'freq'        : cFreq,
                'stddev'      : stddev,
                'mag'         : cMag,
                'zp_fict'     : zp,
                'nsamples'    : self.size,
                'duration'    : duration,
                'name'        : name,
            } 
            return stats_info



    def _choose(self):
        '''Choose the best statistics at the end of the round'''
        refLabel  = self.phot['ref']['info']['label']
        testLabel = self.phot['test']['info']['label']
        log.info("#"*72)
        log.info("Session = {session}",session=self.session)
        log.info("Best ZP        list is {bzp}",bzp=self.best['zp'])
        log.info("Best {rLab} Freq list is {brf}",brf=self.best['ref_freq'],  rLab=refLabel)
        log.info("Best {tLab} Freq list is {btf}",btf=self.best['test_freq'], tLab=testLabel)
        summary_ref = dict(); summary_test = dict()
        try:
            summary_ref['zero_point_method']  = None    # Not choosen, so no selection method
            summary_test['zero_point_method'] = 'mode'
            best_zp                      = mode(self.best['zp'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best zp using mode, selecting median instead")
            summary_test['zero_point_method'] = 'median'
            best_zp              = statistics.median(self.best['zp'])
        try:
            summary_ref['freq_method']   = 'mode'
            summary_ref['freq']   = mode(self.best['ref_freq'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best Ref. Freq. using mode, selecting median instead")
            summary_ref['freq_method']   = 'median'
            summary_ref['freq']  = statistics.median(self.best['ref_freq'])
        try:
            summary_test['freq_method']   = 'mode'
            summary_test['freq']  = mode(self.best['test_freq'])
        except statistics.StatisticsError as e:
            log.error("Error choosing best Test Freq. using mode, selecting median instead")
            summary_test['freq_method']   = 'median'
            summary_test['freq'] = statistics.median(self.best['test_freq'])
        offset   = self.options['offset']
        final_zp = best_zp + offset
        log.info("Final ZP ({fzp:0.2f}) = Best ZP ({bzp:0.2f}) + offset ({o:0.2f})",fzp=final_zp, bzp=best_zp,o=offset )
        summary_test['zero_point'] = final_zp
        summary_ref['zero_point']  = float(self.phot['ref']['info']['zp']) # Always the same, not choosen
        summary_test['mag']  = self.zp_fict - 2.5*math.log10(summary_test['freq'])
        summary_ref['mag']   = self.zp_fict - 2.5*math.log10(summary_ref['freq'])
        summary_test['mag_offset'] = -2.5*math.log10(summary_ref['freq']/summary_test['freq'])
        summary_ref['mag_offset']  = 0

        # prev_zp is the ZP we have read from the photometer when we contacted it.
        summary_test['prev_zp'] = float(self.phot['test']['info']['zp'])                
        summary_ref['prev_zp']  = float(self.phot['ref']['info']['zp']) # Always the same, not choosen
        log.info("{rLab} Freq. = {rF:0.3f} Hz , {tLab} Freq. = {tF:0.3f}, {rLab} Mag. = {rM:0.2f}, {tLab} Mag. = {tM:0.2f}, Diff {d:0.2f}", 
                rF= summary_ref['freq'], tF=summary_test['freq'], 
                rM=summary_ref['mag'],   tM=summary_test['mag'], d=summary_test['mag_offset'],
                rLab=refLabel, tLab=testLabel)
        log.info("OLD {tLab} ZP = {old_zp:0.2f}, NEW {tLab} ZP = {new_zp:0.2f}", 
            old_zp=summary_test['prev_zp'], new_zp=summary_test['zero_point'], tLab=testLabel)
        log.info("#"*72)
        # Additional metadata
        summary_test['upd_flag'] = 1 if self.options['update'] else 0
        summary_test['offset']   = self.options['offset']
        summary_test['nrounds']  = self.nrounds
        summary_ref['upd_flag']  = 0
        summary_ref['offset']    = 0
        summary_ref['nrounds']   = self.nrounds
        
        return summary_ref, summary_test


__all__ = [ "StatsService" ]
