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
import datetime
import gettext

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet import  reactor, defer
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import __version__
from zptess.logger  import startLogging, setLogLevel

from zptess                    import set_status_code, REF, TEST
from zptess.utils              import chop
from zptess.stats.service      import StatisticsService
from zptess.photometer.service import PhotometerService
from zptess.calibration.service        import CalibrationService

# ----------------
# Module constants
# ----------------

# Support for internationalization
_ = gettext.gettext

NAMESPACE = 'ctrl'

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------


# --------------
# Module Classes
# --------------

class CalibrationSettingsController:

    NAME = NAMESPACE

    # Default subscription QoS

    def __init__(self, parent, view, model):
        self.parent = parent
        self.config = model.config
        self.view = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        pub.subscribe(self.onSaveCalibConfigReq, 'save_calib_config_req')
        pub.subscribe(self.onLoadCalibConfigReq,'load_calib_config_req')

    # --------------
    # Event handlers
    # --------------
    
    @inlineCallbacks
    def onSaveCalibConfigReq(self, config):
        try:
            yield self.config.saveSection('calibration', config)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

 
    @inlineCallbacks
    def onLoadCalibConfigReq(self):
        try:
            result = yield self.config.loadSection('calibration')
            self.view.mainArea.calibPanel.settings.set(result)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)





class PhotometerPanelController:

    NAME = NAMESPACE

    def __init__(self, parent, view, model):
        self.parent = parent
        self.model = model
        self.view = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        reactor.callLater(0, self.start)

    @inlineCallbacks
    def start(self):
        # events coming from GUI
        log.info("Building underlaying service objects")
        pub.subscribe(self.onStartPhotometerReq, 'start_photometer_req')
        pub.subscribe(self.onStopPhotometerReq, 'stop_photometer_req')
        # Events coming from services
        pub.subscribe(self.onPhotometerInfo, 'phot_info')
        pub.subscribe(self.onPhotometerOffline, 'phot_firmware')
        pub.subscribe(self.onPhotometerOffline, 'phot_offline')
        pub.subscribe(self.onPhotometerEnd, 'phot_end')
        pub.subscribe(self.onStatisticsProgress, 'stats_progress')
        pub.subscribe(self.onStatisticsInfo, 'stats_info')

        phot1  = yield self._buildPhotometer(True)
        phot2  = yield self._buildPhotometer(False)
        stats1 = yield self._buildStatistics(True)
        stats2 = yield self._buildStatistics(False)
        self.calib = yield self._buildCalibration()
        self.phot = {
            'ref':  phot1,
            'test': phot2,
        }
        self.stats = {
            'ref':  stats1,
            'test': stats2,
        }


    # --------------
    # Event handlers
    # --------------

    @inlineCallbacks
    def onPhotometerFirmware(self, role, firmware):
        label = TEST if role == 'test' else REF
        if self._test_transport_method == 'tcp':
            log.critical("[{label}] Conflictive firmware '{firmware}' for TCP comms. Use UDP instead", label=label, firmware=firmware)
            yield self.parent.parent.stopService()

    @inlineCallbacks
    def onPhotometerEnd(self):
        set_status_code(0)
        yield self.parent.parent.stopService()

    def onPhotometerOffline(self, role):
        set_status_code(1)
        reactor.callLater(1, self.parent.parent.stopService)

    def onStatisticsProgress(self, role, stats_info):
        self.view.mainArea.updatePhotStats(role, stats_info)

    def onStatisticsInfo(self, role, stats_info):
        self.view.mainArea.updatePhotStats(role, stats_info)

    def onPhotometerInfo(self, role, info):
        label = TEST if role == 'test' else REF
        if info is None:
            log.warn("[{label}] No photometer info available. Is it Connected?", label=label)
        else:
            self.view.mainArea.updatePhotInfo(role, info)
      

    @inlineCallbacks
    def onStartPhotometerReq(self, role):
        try:
            log.info("onStartPhotometerReq({role})", role=role)
            yield self._startChain(role)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

 
    @inlineCallbacks
    def onStopPhotometerReq(self, role):
        try:
            log.info("onStopPhotometerReq({role})", role=role)
            yield self._stopChain(role)
            self.view.mainArea.clearPhotPanel(role)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    # ----------------
    # Auxiliar methods
    # ----------------

    @inlineCallbacks
    def _startChain(self, role):
        if not self.stats[role].running:
            self.stats[role].startService()
        else:
            log.warn("{name} already running",name=self.stats[role].name)
        if not self.phot[role].running:
            yield self.phot[role].startService()
        else:
            log.warn("{name} already running",name=self.phot[role].name)
      

    @inlineCallbacks
    def _stopChain(self, role):
        if not self.stats[role].running:
            log.warn("{name} was not not running",name=self.stats[role].name)
        else:
            yield self.stats[role].stopService()
        if not self.phot[role].running:
            log.warn("{name} was not not running",name=self.phot[role].name)
        else:
            yield self.phot[role].stopService()

    @inlineCallbacks
    def _startCalibration(self, role):
        if not self.calib.running:
            self.calib.startService()
        else:
            log.warn("{name} already running",name=self.calib.name)

    @inlineCallbacks
    def _stopCalibration(self, role):
        if not self.calib.running:
            log.warn("{name} was not not running",name=self.calib.name)
        else:
            yield self.calib.stopService()
       

    @inlineCallbacks
    def _buildPhotometer(self, isRef):
        if isRef:
            section   = 'ref-device'
            prefix    = REF
        else:
            section   = 'test-device'
            prefix    = TEST
        options = yield self.model.config.loadSection(section)
        options['model']        = options['model'].upper()
        options['log_level']    = 'info' # A capón de momento
        options['write_zero_point'] = None # A capón de momento
        options['log_messages'] = 'warn'  # A capón de momento
        options['config_dao']   = self.model.config
        proto, addr, port = chop(options['endpoint'], sep=':')
        self._test_transport_method = proto
        service = PhotometerService(options, isRef)
        service.setName(prefix + ' ' + PhotometerService.NAME)
        return service

    @inlineCallbacks
    def _buildStatistics(self, isRef, alone=True):
        if isRef:
            section   = 'ref-stats'
            prefix    = REF
        else:
            section   = 'test-stats'
            prefix    = TEST
        options = yield self.model.config.loadSection(section)
        options['samples'] = int(options['samples'])
        options['period']  = float(options['period'])
        options['log_level'] = 'info' # A capón de momento
        service = StatisticsService(options, isRef, alone=alone)
        service.setName(prefix + ' ' + StatisticsService.NAME)
        return service

    @inlineCallbacks
    def _buildCalibration(self):
        section = 'calibration'
        options = yield self.model.config.loadSection(section)
        options['update']    = False  # A capón de momento
        options['log_level'] = 'info' # A capón de momento
        service = CalibrationService(options)
        service.setName(CalibrationService.NAME)
        return service