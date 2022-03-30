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

from zptess import TSTAMP_FORMAT, TSTAMP_SESSION_FMT, REF, TEST
from zptess.logger import setLogLevel


# ----------------
# Module constants
# ----------------

NAMESPACE = 'calib'

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

log = Logger(namespace='calib')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------    
# -----------------------------------------------------------------------------  


class CalibrationService(Service):

    NAME = "Calibration Service"

    def __init__(self, options):
        Service.__init__(self)
        self.options  = options
        
   
    def startService(self):
        '''
        Starts Calibration service
        '''
        setLogLevel(namespace=NAMESPACE, levelStr=self.options['log_level'])
        log.info("Starting {name} (Rounds = {r})", name=self.name, r=self.options['rounds'])
        self.nrounds  = self.options['rounds']
        self.curRound = 1
        self.best = {
            'zp'        : list(),
            'ref_freq'  : list(),
            'test_freq' : list(),
        }
        self.phot = {   # Photometer info
            'ref' : None,
            'test': None,
        }
        # Esto es lo nuevo
        self._stats = {
            'ref': None, 
            'test': None 
        }
        self.session = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)
        pub.sendMessage('calib_begin', session=self.session)
        pub.subscribe(self.onPhotometerInfo,  'phot_info')
        pub.subscribe(self.onIndividualStats, 'stats_info')
        super().startService()

       
    def stopService(self):
        log.info("Stopping {name}", name=self.name)
        pub.unsubscribe(self.onPhotometerInfo,  'phot_info')
        pub.unsubscribe(self.onIndividualStats, 'stats_info')
        return super().stopService()
    
    # ---------------
    # OPERATIONAL API
    # ---------------


    def onPhotometerInfo(self, role, info):
        self.phot[role] = info
        if role == 'ref':
            self.zp_abs  = info['zp_abs']
            self.zp_fict = info['zp']


    def onIndividualStats(self, role, stats_info):
        stats_info['session'] = self.session
        self._stats[role] = stats_info
        if (self._stats['ref'] is None) or (self._stats['test'] is None):
            return
        stats_ref  = self._stats['ref']
        stats_test = self._stats['test']
        if self.curRound <= self.nrounds:
            paired = self.pairStats(stats_ref, stats_test)
            if paired:
                self.calibrate(stats_ref, stats_test)
        else:
            summary_ref, summary_test = self.summary()
            pub.sendMessage('calib_summary_info', role='ref', stats_info=summary_ref)
            pub.sendMessage('calib_summary_info', role='test',stats_info=summary_test)
            pub.sendMessage('calib_end', session=self.session)


    
    # ---------------------------
    # Statistics Helper functions
    # ----------------------------

    def pairStats(self, stats_ref, stats_test):
        ref_round  = stats_ref.get('round', None)
        test_round = stats_test.get('round', None)
        if ref_round is not None:
            return False
        if test_round is not None:
            return False
        # Pair last statistics under the same round.
        stats_ref['round']  = self.curRound
        stats_test['round'] = self.curRound
        return True

    def calibrate(self, stats_ref, stats_test):
        '''Perform a calibration of a single round, accumulating best measurements'''
        magDiff = -2.5*math.log10(stats_ref['freq']/stats_test['freq'])
        zp = round(self.zp_abs + magDiff,2)
        if stats_ref['stddev'] != 0.0 and stats_test['stddev'] != 0.0:
            log.info('ROUND       {i:02d}: (ref-test) \u0394 Mag = {magDiff:0.2f}, ZP Fict = {zp_fict:0.2f}, ZP Abs = {zp_abs:0.2f}, ZP = {zp:0.2f}',
                    i        = self.curRound, 
                    magDiff = magDiff, 
                    zp_fict  = self.zp_fict, 
                    zp_abs   = self.zp_abs,
                    zp       = zp,
            )
            self.best['zp'].append(zp)          # Collect this info whether we need it or not
            self.best['ref_freq'].append(stats_ref['freq'])
            self.best['test_freq'].append(stats_test['freq'])
            stats_ref['zero_point']  = None
            stats_test['zero_point'] = zp
            stats_ref['mag_diff']  = None
            stats_test['mag_diff'] = magDiff
            pub.sendMessage('calib_round_info', role='ref',  round=self.curRound, stats_info=stats_ref)
            pub.sendMessage('calib_round_info', role='test', round=self.curRound, stats_info=stats_test)
            self.curRound += 1
        elif stats_ref['stddev'] == 0.0 and stats_test['stddev'] != 0.0:
            log.warn('FROZEN {lab}', lab=stats_ref['name'])
        elif stats_test['stddev'] == 0.0 and stats_ref['stddev'] != 0.0:
            log.warn('FROZEN {lab}', lab=stats_test['name'])
        else:
            log.warn('FROZEN {rLab} and {tLab}', rLab=stats_ref['name'], tLab=stats_test['name'])
        log.info("="*72)


    def summary(self):
        log.info("#"*72)
        log.info("Session = {session}",session=self.session)
        log.info("Best ZP        list is {bzp}",  bzp=self.best['zp'])
        log.info("Best {rLab} Freq list is {brf}",brf=self.best['ref_freq'],  rLab=REF)
        log.info("Best {tLab} Freq list is {btf}",btf=self.best['test_freq'], tLab=TEST)
        summary_ref  = dict()
        summary_test = dict()
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
        summary_ref['zero_point']  = float(self.phot['ref']['zp']) # Always the same, not choosen
        summary_test['mag']  = self.zp_fict - 2.5*math.log10(summary_test['freq'])
        summary_ref['mag']   = self.zp_fict - 2.5*math.log10(summary_ref['freq'])
        summary_test['mag_offset'] = -2.5*math.log10(summary_ref['freq']/summary_test['freq'])
        summary_ref['mag_offset']  = 0
        # prev_zp is the ZP we have read from the photometer when we contacted it.
        summary_test['prev_zp'] = float(self.phot['test']['zp'])                
        summary_ref['prev_zp']  = float(self.phot['ref']['zp']) # Always the same, not choosen
        log.info("{rLab} Freq. = {rF:0.3f} Hz , {tLab} Freq. = {tF:0.3f}, {rLab} Mag. = {rM:0.2f}, {tLab} Mag. = {tM:0.2f}, Diff {d:0.2f}", 
                rF= summary_ref['freq'], tF=summary_test['freq'], 
                rM=summary_ref['mag'],   tM=summary_test['mag'], d=summary_test['mag_offset'],
                rLab=REF, tLab=TEST)
        log.info("OLD {tLab} ZP = {old_zp:0.2f}, NEW {tLab} ZP = {new_zp:0.2f}", 
            old_zp=summary_test['prev_zp'], new_zp=summary_test['zero_point'], tLab=TEST)
        log.info("#"*72)
        # Additional metadata
        summary_test['upd_flag'] = 1 if self.options['update'] else 0
        summary_test['offset']   = self.options['offset']
        summary_test['nrounds']  = self.nrounds
        summary_test['author']   = self.options['author']
        summary_ref['upd_flag']  = 0
        summary_ref['offset']    = 0
        summary_ref['nrounds']   = self.nrounds
        summary_ref['author']    = self.options['author']
        return summary_ref, summary_test


__all__ = [ "StatsService" ]
