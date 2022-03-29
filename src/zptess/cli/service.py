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
import glob

# ---------------
# Twisted imports
# ---------------

from twisted.application.service import MultiService
from twisted.logger import Logger


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

from zptess                    import FULL_VERSION_STRING, TSTAMP_SESSION_FMT, REF, TEST
from zptess                    import set_status_code
from zptess.utils              import chop
from zptess.logger             import setLogLevel
from zptess.dbase.service      import DatabaseService
from zptess.stats.service      import StatisticsService
from zptess.photometer.service import PhotometerService
from zptess.calibration        import CalibrationService


# ----------------
# Module constants
# ----------------

NAMESPACE = 'batch'

# -----------------------
# Module global variables
# -----------------------

log = Logger(NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------

# --------------
# Module Classes
# --------------


class CommandLineService(MultiService):

    # Service name
    NAME = 'Command Line Service'

    def __init__(self, options):
        super().__init__()   
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        self._cmd_options = vars(options)
        self._test_transport_method = None
        log.info("{o}",o=self._cmd_options)
    #------------
    # Service API
    # ------------

    def startService(self):
        # 'zptess' calzado a pelo poque parece que no se captura de la command line
        log.warn("zptess {full_version}",full_version=FULL_VERSION_STRING)
        self.dbaseServ = self.parent.getServiceNamed(DatabaseService.NAME)
        self.dbaseServ.setTestMode(self._cmd_options['test'])
        pub.subscribe(self.onPhotometerInfo, 'phot_info')
        pub.subscribe(self.onCalibrationEnd, 'calib_end')
        pub.subscribe(self.onPhotometerOffline, 'phot_offline')
        pub.subscribe(self.onPhotometerEnd, 'phot_end')
        pub.subscribe(self.onPhotometerFrimware, 'phot_firmware')
        self.build()
        super().startService()

    def stopService(self):
        log.info("Stopping {name}", name=self.name)
        pub.unsubscribe(self.onPhotometerInfo, 'phot_info')
        pub.unsubscribe(self.onCalibrationEnd, 'calib_end')
        pub.unsubscribe(self.onPhotometerOffline, 'phot_offline')
        pub.unsubscribe(self.onPhotometerEnd, 'phot_end')
        pub.unsubscribe(self.onPhotometerFrimware, 'phot_firmware')
        return super().stopService()

    # ---------------
    # OPERATIONAL API
    # ---------------

    def quit(self, exit_code = 0):
        '''Gracefully exit Twisted program'''
        set_status_code(exit_code)
        reactor.callLater(0, self.parent.stopService)

    def onCalibrationEnd(self):
        set_status_code(0)
        reactor.callLater(0, self.parent.stopService)

    def onPhotometerFrimware(self, role, firmware):
        label = TEST if role == 'test' else REF
        if self._test_transport_method == 'tcp':
            log.critical("[{label}] Conflictive firmware '{firmware}' for TCP comms. Use UDP instead", label=label, firmware=firmware)
            reactor.callLater(0, self.parent.stopService)

    def onPhotometerEnd(self):
        set_status_code(0)
        reactor.callLater(0, self.parent.stopService)

    def onPhotometerOffline(self, role):
        set_status_code(1)
        reactor.callLater(1, self.parent.stopService)

    def onPhotometerInfo(self, role, info):
        label = TEST if role == 'test' else REF
        if info is None:
            log.warn("[{label}] No photometer info available. Is it Connected?", label=label)
        else:
            log.info("[{label}] Role         : {value}", label=label, value=info['role'])
            log.info("[{label}] Model        : {value}", label=label, value=info['model'])
            log.info("[{label}] Name         : {value}", label=label, value=info['name'])
            log.info("[{label}] MAC          : {value}", label=label, value=info['mac'])
            log.info("[{label}] Zero Point   : {value:.02f} (old)", label=label, value=info['zp'])
            log.info("[{label}] Offset Freq. : {value}", label=label, value=info['freq_offset'])
            log.info("[{label}] Firmware     : {value}", label=label, value=info['firmware'])
      
    # ==============
    # Helper methods
    # ==============


    def buildChain(self, isRef, prefix, alone):
        self.buildStatistics(isRef, prefix, alone)
        self.buildPhotometer(isRef, prefix)

    def buildBoth(self):
        self.buildStatistics(isRef=True, prefix=REF,   alone=False)
        self.buildStatistics(isRef=False, prefix=TEST, alone=False)
        self.buildPhotometer(isRef=True, prefix=REF)
        self.buildPhotometer(isRef=False, prefix=TEST)

    def build(self):
        if self._cmd_options['dry_run']:
            self.buildPhotometer(isRef=False, prefix=TEST)
        elif self._cmd_options['write_zero_point']:
            self.buildPhotometer(isRef=False, prefix=TEST)
        elif self._cmd_options['read'] == "ref":
            self.buildChain(isRef=True,  prefix=REF, alone=True)
        elif self._cmd_options['read'] == "test":
            self.buildChain(isRef=False, prefix=TEST, alone=True)
        elif self._cmd_options['read'] == "both":
            self.buildBoth()
        else:
            self.buildCalibration()
            self.buildBoth()
            

    def buildCalibration(self):
        section = 'calibration'
        options = self.dbaseServ.getInitialConfig(section)
        options['rounds'] = self._cmd_options['rounds'] or int(options['rounds'])
        options['author'] = " ".join(self._cmd_options['author']) or options['author']
        options['offset'] = self._cmd_options['offset'] or float(options['offset'])
        options['update'] = self._cmd_options['update']
        options['log_level'] = 'info' # A capón de momento
        service = CalibrationService(options)
        service.setName(CalibrationService.NAME)
        service.setServiceParent(self)


    def buildStatistics(self, isRef, prefix, alone):
        section = 'ref-stats' if isRef else 'test-stats'
        options = self.dbaseServ.getInitialConfig(section)
        options['samples'] = self._cmd_options['samples'] or int(options['samples'])
        options['central'] = self._cmd_options['central'] or options['central']
        options['period']  = self._cmd_options['period']  or float(options['period'])
        options['log_level'] = 'info' # A capón de momento
        service = StatisticsService(options, isRef, alone)
        service.setName(prefix + ' ' + StatisticsService.NAME)
        service.setServiceParent(self)

    def buildPhotometer(self, isRef, prefix):
        if isRef:
            modelkey  = 'ref_model'
            endpoikey = 'ref_endpoint'
            oldprokey = 'ref_old_proto'
            section   = 'ref-device'
            prefix    = REF
        else:
            modelkey  = 'test_model'
            endpoikey = 'test_endpoint'
            oldprokey = 'test_old_proto'
            section   = 'test-device'
            prefix    = TEST
        options = self.dbaseServ.getInitialConfig(section)
        options['model']        = self._cmd_options[modelkey]  or options['model']
        options['model']        = options['model'].upper()
        options['endpoint']     = self._cmd_options[endpoikey] or options['endpoint']
        options['old_proto']    = self._cmd_options[oldprokey] or int(options['old_proto'])
        options['dry_run']      = self._cmd_options['dry_run']
        options['write_zero_point'] = self._cmd_options['write_zero_point']
        options['log_level']    = 'info' # A capón de momento
        options['log_messages'] = 'warn'
        options['config_dao']   = self.dbaseServ.dao.config
        msgs = self._cmd_options['messages']
        if isRef:
            if msgs == 'both' or msgs == 'ref':
                options['log_messages'] = 'info'
        else:
            if msgs == 'both' or msgs == 'test':
                options['log_messages'] = 'info'
            proto, addr, port = chop(options['endpoint'], sep=':')
            self._test_transport_method = proto
        service = PhotometerService(options, isRef)
        service.setName(prefix + ' ' + PhotometerService.NAME)
        service.setServiceParent(self)
    
