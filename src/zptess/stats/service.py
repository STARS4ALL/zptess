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
import math
import random
import statistics

from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks
from twisted.internet.threads     import deferToThread
from twisted.application.service  import Service

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess          import TSTAMP_FORMAT, REF, TEST
from zptess.logger   import setLogLevel

# -----------------------
# Module global variables
# -----------------------

# ----------------
# Module constants
# ----------------

NAMESPACE = 'stats'

# ----------
# Exceptions
# ----------



# -------
# Classes
# -------

class CircularBuffer(object):

    def __init__(self, tag, size, central, zp, log):
        self.log          = log
        self._tag         = tag
        self._nsamples    = size
        self._buffer      = deque([], size)
        self._zp          = zp
        self._freq_offset = None
        self._central = central
        if central == "mean":
            self._central_func = statistics.mean
        elif central == "median":
            self._central_func = statistics.median
        else:
            self._central_func = statistics.mode

    # -------------------
    # buffer API
    # -------------------

    def fixZeroPoint(self, zp):
        self._zp = zp

    def fixFreqOffset(self, freq_offset):
        self._freq_offset = freq_offset

    def curSize(self):
        return len(self._buffer)

    def write(self, data):
        self._buffer.append(data)

    def isFull(self):
        return not len(self._buffer) < self._nsamples

    def getProgressInfo(self):
        ring  = self._buffer
        freq_offset = self._freq_offset
        begin_tstamp= ring[0]['tstamp']  if len(ring) else None
        end_tstamp  = ring[-1]['tstamp'] if len(ring) else None
        return {
            'nsamples': self._nsamples,
            'current' : len(self._buffer),
            'begin_tstamp': begin_tstamp,
            'end_tstamp'  : end_tstamp,
            'duration': (end_tstamp - begin_tstamp).total_seconds() if begin_tstamp is not None else None,
        }

    def getStats(self):
        tag         = self._tag
        ring        = self._buffer
        N           = len(self._buffer)
        zp          = self._zp
        central     = self._central
        freq_offset = self._freq_offset
        begin_tstamp= ring[0]['tstamp']
        end_tstamp  = ring[-1]['tstamp']
        duration    = (end_tstamp - begin_tstamp).total_seconds()
        frequencies = [item['freq'] for item in ring]
        try:
            self.log.debug("[{tag}] ring = {q}", q=frequencies, tag=tag)
            cFreq  = self._central_func(frequencies)
            sFreq  = statistics.stdev(frequencies, cFreq)
            cMag   = zp - 2.5*math.log10(cFreq - freq_offset)
        except statistics.StatisticsError as e:
            self.log.error("[{tag}] Statistics error: {e}", e=e, tag=tag)
            return None
        except ValueError as e:
            self.log.error("[{tag}] math.log10() error for freq={f}, freq_offset={foff}: {e}", 
                e=e, f=cFreq, foff=freq_offset, tag=tag)
            return None
        else: 
            stats_info = {
                'nsamples'    : self._nsamples,
                'current'     : N,
                'central'     : central,
                'zp_fict'     : zp,
                'begin_tstamp': begin_tstamp, # native datetime object
                'end_tstamp'  : end_tstamp,   # native datetime object
                'freq'        : cFreq,
                'stddev'      : sFreq,
                'mag'         : cMag,
                'duration'    : duration,
            } 
            return stats_info


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class StatisticsService(Service):

    NAME    = 'Statistics Service'
    T       = 1.50    # Progress task period

    def __init__(self, options, isRef, use_fict_zp):
        self.options = options
        self._use_fict_zp = use_fict_zp
        if isRef:
            self._role = 'ref'
            self._label = REF
        else:
            self._role = 'test'
            self._label = TEST
        self._freq_offset = None # Not known yet, must come from photometer Info
        self._dev_name    = None # Not known yet, must come from photometer Info
        self.log = Logger(namespace=NAMESPACE)
        self.statTask = task.LoopingCall(self._compute)
        self.progressTask = task.LoopingCall(self._progress)
        
    # -----------
    # Service API
    # -----------

    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        Although it is technically a synchronous operation, it works well
        with inline callbacks
        '''
        setLogLevel(namespace=NAMESPACE, levelStr=self.options['log_level'])
        self._freq_offset = None # Not known yet, must come from photometer Info
        self._dev_name    = None # Not known yet, must come from photometer Info

        self.log.info("[{label:4s}] {name:9s} Starting {service} (T = {T} secs.), (fict zp = {zp}, usage = {usage})",
            label   = self._label,
            name    = '?????' if self._dev_name is None else self._dev_name,
            service = self.name,
            T       = self.options['period'],
            zp      = self.options['zp_fict'],
            usage   = self._use_fict_zp
        )
        self._buffer = CircularBuffer(
            tag         = self._label,
            size        = self.options['samples'],
            central     = self.options['central'],
            zp          = self.options['zp_fict'],
            log         = self.log
        )
        pub.subscribe(self.onSampleReceived, 'phot_sample')
        pub.subscribe(self.onPhotometerInfo, 'phot_info')
        t = random.uniform(0, self.T/2)
        reactor.callLater(t, self.progressTask.start, self.T, now=False)
        self.log.info("[{label:4s}] {name:9s} Starting buffer fill monitoring task",
            label   = self._label,
            name    = '?????' if self._dev_name is None else self._dev_name
        )
        super().startService() # se we can handle the 'running' attribute
        

    def stopService(self):
        self.log.info("[{label:4s}] {name:9s} Stopping {service}",
            label   = self._label,
            name    = '????'if self._dev_name is None else self._dev_name,
            service = self.name,
        )
        pub.unsubscribe(self.onSampleReceived, 'phot_sample')
        pub.unsubscribe(self.onPhotometerInfo, 'phot_info')
        if self.progressTask.running:
            self.log.info("[{label:4s}] {name:9s} Stopping buffer fill monitoring task",
                label   = self._label,
                name    = '?????' if self._dev_name is None else self._dev_name
            )
            self.progressTask.stop()
        if self.statTask.running:
            self.log.info("[{label:4s}] {name:9s} Stopping statistics task",
                label   = self._label,
                name    = '?????' if self._dev_name is None else self._dev_name
            )
            self.statTask.stop()
        return super().stopService() # se we can handle the 'running' attribute
            
    # --------------
    # Statistics API 
    # --------------

    def useFictZP(self):
        self.log.info("[{label:4s}] {name:9s} Using ficticious ZP {zp}",
            label   = self._label,
            name    = '?????' if self._dev_name is None else self._dev_name,
            zp      = self.options['zp_fict']
        )
        self._use_fict_zp = True

    def useOwnZP(self):
        self.log.info("[{label:4s}] {name:9s} Using ZP stored in photometer",
            label   = self._label,
            name    = '?????' if self._dev_name is None else self._dev_name,
        )
        self._use_fict_zp = False

    def onPhotometerInfo(self, role, info):
        if role == self._role:
            self._dev_name    = info['name']    # Only changes its own device
            self._freq_offset = info['freq_offset']
            self._buffer.fixFreqOffset(info['freq_offset'])
            if not self._use_fict_zp:
                self.log.info("[{label:4s}] {name:9s} Using device ZP ({zp}) instead of ficticious ZP",
                    label   = self._label,
                    name    = '?????' if self._dev_name is None else self._dev_name,
                    zp      = info['zp']
                 )
                self._buffer.fixZeroPoint(info['zp']) 
        
    def onSampleReceived(self, role, sample):
        if role == self._role:
            self._buffer.write(sample) # Stores samples from its own device


    def _progress(self):
        '''Progress task'''
        if self._buffer.isFull() and self.progressTask.running:
            self.log.info("[{label:4s}] {name:9s} Stopping buffer fill monitoring task",
                label   = self._label,
                name    = '?????' if self._dev_name is None else self._dev_name
            )
            self.progressTask.stop() # Self stop this task
            self.log.info("[{label:4s}] {name:9s} Starting statistics task",
                label   = self._label,
                name    = '?????' if self._dev_name is None else self._dev_name
            )
            self.statTask.start(self.options['period'], now=True)
            return
        stats_info = self._buffer.getProgressInfo()
        stats_info['name'] = '?????' if not self._dev_name else self._dev_name
        stats_info['role'] = self._role
        pub.sendMessage('stats_progress', role=self._role, stats_info=stats_info)
        

    @inlineCallbacks
    def _compute(self): 
        '''Compute statistics task''' 
        stats_info = yield deferToThread(self._buffer.getStats)
        if stats_info is None:
            return
        stats_info['name'] = self._dev_name
        stats_info['role'] = self._role
        pub.sendMessage('stats_info', role=self._role, stats_info=stats_info)


    # --------------
    # Helper methods
    # ---------------

    
__all__ = [
    "StatsService",
]
