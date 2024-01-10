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

from zptess                    import FULL_VERSION_STRING, TSTAMP_SESSION_FMT, REF, TEST, __version__
from zptess                    import set_status_code
from zptess.utils              import chop
from zptess.logger             import setLogLevel
from zptess.dbase.service      import DatabaseService
from zptess.stats.service      import StatisticsService
from zptess.photometer.service import PhotometerService
from zptess.calibration.service        import CalibrationService


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
        pub.subscribe(self.onCalibrationRoundInfo, 'calib_round_info')
        pub.subscribe(self.onCalibrationLists, 'calib_summary_lists')
        pub.subscribe(self.onCalibrationSummary, 'calib_summary_info')
        pub.subscribe(self.onPhotometerOffline, 'phot_offline')
        pub.subscribe(self.onPhotometerFirmware, 'phot_firmware')
        pub.subscribe(self.onStatisticsProgress, 'stats_progress')
        pub.subscribe(self.onStatisticsInfo, 'stats_info')
        self.build()
        super().startService() # se we can handle the 'running' attribute

    def stopService(self):
        log.info("Stopping {name}", name=self.name)
        pub.unsubscribe(self.onPhotometerInfo, 'phot_info')
        pub.unsubscribe(self.onCalibrationEnd, 'calib_end')
        pub.unsubscribe(self.onCalibrationRoundInfo, 'calib_round_info')
        pub.unsubscribe(self.onCalibrationLists, 'calib_summary_lists')
        pub.unsubscribe(self.onCalibrationSummary, 'calib_summary_info')
        pub.unsubscribe(self.onPhotometerOffline, 'phot_offline')
        pub.unsubscribe(self.onPhotometerFirmware, 'phot_firmware')
        pub.unsubscribe(self.onStatisticsProgress, 'stats_progress')
        pub.unsubscribe(self.onStatisticsInfo, 'stats_info')
        return super().stopService() # se we can handle the 'running' attribute

    # ---------------
    # OPERATIONAL API
    # ---------------

    @inlineCallbacks
    def quit(self, exit_code = 0):
        '''Gracefully exit Twisted program'''
        set_status_code(exit_code)
        yield self.parent.stopService()

    @inlineCallbacks
    def onCalibrationEnd(self, session):
        set_status_code(0)
        if self._cmd_options['update']:
            self._zp_to_write = round(self._zp_to_write, 2)
            yield self.testPhotometer.writeZeroPoint(self._zp_to_write)
            info = yield self.testPhotometer.getPhotometerInfo()
            if self._zp_to_write != info['zp']:
                log.critical("ZP Write verification failed: ZP to Write ({zp_wr}) does not match with ZP subsequently read ({zp_re})",
                    zp_wr=self._zp_to_write, zp_re=info['zp'])
                yield self.quit(exit_code=1)
                return
            else:
                log.info("ZP Write verification Ok.")
        yield self.dbaseServ.flush()
        yield self.parent.stopService()

    @inlineCallbacks
    def onPhotometerFirmware(self, role, firmware):
        label = TEST if role == 'test' else REF
        if self._test_transport_method == 'tcp':
            log.critical("[{label}] Conflictive firmware '{firmware}' for TCP comms. Use UDP instead", label=label, firmware=firmware)
            yield self.parent.stopService()

    def onPhotometerOffline(self, role):
        set_status_code(1)
        reactor.callLater(1, self.parent.stopService)

    def onStatisticsProgress(self, role, stats_info):
        label = TEST if role == 'test' else REF
        log.info('[{label:4s}] {name:9s} waiting for enough samples, {pend:03d} remaining', 
            label = label, 
            name = stats_info['name'], 
            pend = stats_info['nsamples'] - stats_info['current'],
        )

    def onStatisticsInfo(self, role, stats_info):
        label = TEST if role == 'test' else REF
        log.info("[{label:4s}] {name:9s} ({start}-{end})[{w:05.1f}s][{sz:03d}] {central:6s} f = {cFreq:0.3f} Hz, \u03C3 = {sFreq:0.3f} Hz, m = {cMag:0.2f} @ {zp:0.2f}",
            label   = label, 
            name    = stats_info['name'], 
            start   = stats_info['begin_tstamp'].strftime("%H:%M:%S"),
            end     = stats_info['end_tstamp'].strftime("%H:%M:%S"), 
            sz      = stats_info['nsamples'],
            zp      = stats_info['zp_fict'], 
            central = stats_info['central'],
            cFreq   = stats_info['freq'], 
            cMag    = stats_info['mag'], 
            sFreq   = stats_info['stddev'],
            w       = stats_info['duration']
        )

    def onCalibrationRoundInfo(self, role, count, stats_info):
        label = TEST if role == 'test' else REF
        if role == 'test':
            log.info('ROUND        {i:02d}: New ZP = {zp:0.2f} = \u0394(ref-test) Mag ({magDiff:0.2f}) + ZP Abs ({zp_fict:0.2f})',
                i        = count ,
                magDiff  = stats_info['mag_diff'], 
                zp_fict  = stats_info['zp_fict'], 
                zp       = stats_info['zero_point'],
            )
            log.info("="*72)


    def onCalibrationLists(self, session, zp_list, ref_freqs, test_freqs):
        log.info("#"*72)
        log.info("Session = {session}",session=session)
        log.info("Best ZP        list is {bzp}",  bzp=zp_list)
        log.info("Best {rLab} Freq list is {brf}",brf=ref_freqs,  rLab=REF)
        log.info("Best {tLab} Freq list is {btf}",btf=test_freqs, tLab=TEST)


    def onCalibrationSummary(self, role, stats_info):
        label = TEST if role == 'test' else REF
        log.info("{label} Best Freq. = {freq:0.3f} Hz, Mag. = {mag:0.2f}, Diff {diff:0.2f}", 
            freq  = stats_info['freq'],
            mag   = stats_info['mag'],  
            diff  = stats_info['mag_offset'],
            label = label
        )
        if role == 'test':
            final_zp = stats_info['zero_point']
            offset   = stats_info['offset']
            best_zp  = final_zp - offset
            log.info("Final {label} ZP ({fzp:0.2f}) = Best ZP ({bzp:0.2f}) + ZP offset ({o:0.2f})",
                fzp   = final_zp, 
                bzp   = best_zp, 
                o     = offset, 
                label = label
            )
            log.info("Old {label} ZP = {old_zp:0.2f}, NEW {label} ZP = {new_zp:0.2f}", 
                old_zp = stats_info['prev_zp'], 
                new_zp = final_zp, 
                label  = label
            )
            log.info("#"*72)
            self._zp_to_write = stats_info['zero_point']

        # log.info("{rLab} Freq. = {rF:0.3f} Hz , {tLab} Freq. = {tF:0.3f}, {rLab} Mag. = {rM:0.2f}, {tLab} Mag. = {tM:0.2f}, Diff {d:0.2f}", 
        #         rF= summary_ref['freq'], tF=summary_test['freq'], 
        #         rM=summary_ref['mag'],   tM=summary_test['mag'], d=summary_test['mag_offset'],
        #         rLab=REF, tLab=TEST)


    @inlineCallbacks
    def onPhotometerInfo(self, role, info):
        label = TEST if role == 'test' else REF
        if info is None:
            log.warn("[{label}] No photometer info available. Is it Connected?", label=label)
        else:
            log.info("[{label}] Role            : {value}", label=label, value=info['role'])
            log.info("[{label}] Model           : {value}", label=label, value=info['model'])
            log.info("[{label}] Sensor          : {value}", label=label, value=info['sensor'])
            log.info("[{label}] Name            : {value}", label=label, value=info['name'])
            log.info("[{label}] MAC             : {value}", label=label, value=info['mac'])
            log.info("[{label}] Zero Point      : {value:.02f} (old)", label=label, value=info['zp'])
            log.info("[{label}] Firmware        : {value}", label=label, value=info['firmware'])
            log.info("[{label}] Dark Freq. (Hz) : {value}", label=label, value=info['freq_offset'])
        if role == 'test' and self._cmd_options['dry_run']:
            log.info('Dry run. Will stop here ...') 
            set_status_code(0)
            yield self.parent.stopService()
        elif role == 'test' and self._cmd_options['write_zero_point'] is not None:
            result = yield self.testPhotometer.writeZeroPoint(self._cmd_options['write_zero_point'])
            set_status_code(0)
            yield self.parent.stopService()

    # ==============
    # Helper methods
    # ==============

    def buildChain(self, isRef, prefix, alone):
        phot  = self.buildStatistics(isRef, prefix, alone)
        stats = self.buildPhotometer(isRef, prefix)
        if isRef:
            self.refStatistics = stats
            self.refPhotometer = phot
        else:
            self.testStatistics = stats
            self.testPhotometer = phot

    def buildBoth(self):
        self.refStatistics  = self.buildStatistics(isRef=True, prefix=REF,   alone=False)
        self.testStatistics  = self.buildStatistics(isRef=False, prefix=TEST, alone=False)
        self.refPhotometer  = self.buildPhotometer(isRef=True, prefix=REF)
        self.testPhotometer = self.buildPhotometer(isRef=False, prefix=TEST)

    def build(self):
        if self._cmd_options['dry_run']:
            self.testPhotometer = self.buildPhotometer(isRef=False, prefix=TEST)
        elif self._cmd_options['write_zero_point']:
            self.testPhotometer = self.buildPhotometer(isRef=False, prefix=TEST)
        elif self._cmd_options['read'] == "ref":
            self.buildChain(isRef=True,  prefix=REF, alone=True)
        elif self._cmd_options['read'] == "test":
            self.buildChain(isRef=False, prefix=TEST, alone=True)
        elif self._cmd_options['read'] == "both":
            self.buildBoth()
        else:
            self.calib = self.buildCalibration()
            self.buildBoth()
            

    def buildCalibration(self):
        section = 'calibration'
        options = self.dbaseServ.getInitialConfig(section)
        options['rounds'] = self._cmd_options['rounds'] or int(options['rounds'])
        options['author'] = " ".join(self._cmd_options['author']) or options['author']
        options['offset'] = self._cmd_options['offset'] or float(options['offset'])
        options['update'] = self._cmd_options['update'] # siempre en linea de comando
        options['log_level'] = 'info' # A capón de momento
        options['calibration'] = 'AUTO'
        options['calversion'] = __version__
        options['filter'] =  self._cmd_options['filter']
        options['plug'] =  self._cmd_options['plug']
        options['box'] =  " ".join(self._cmd_options['box']) # Box has a default options value
        options['collector'] =  " ".join(self._cmd_options['collector']) or None
        options['comment'] =  " ".join(self._cmd_options['comment']) or None
        service = CalibrationService(options)
        service.setName(CalibrationService.NAME)
        service.setServiceParent(self)
        return service


    def buildStatistics(self, isRef, prefix, alone):
        section = 'ref-stats' if isRef else 'test-stats'
        options = self.dbaseServ.getInitialConfig(section)
        cal_options =  self.dbaseServ.getInitialConfig('calibration')
        zp_fict = cal_options['zp_fict']
        options['samples'] = self._cmd_options['samples'] or int(options['samples'])
        options['central'] = self._cmd_options['central'] or options['central']
        options['period']  = self._cmd_options['period']  or float(options['period'])
        options['zp_fict'] = self._cmd_options['zp_fict'] or float(zp_fict)
        options['log_level'] = 'info' # A capón de momento
        service = StatisticsService(options, isRef, use_fict_zp=not alone)
        service.setName(prefix + ' ' + StatisticsService.NAME)
        service.setServiceParent(self)
        return service

    def buildPhotometer(self, isRef, prefix):
        if isRef:
            modelkey  = 'ref_model'
            endpoikey = 'ref_endpoint'
            oldprokey = 'ref_old_proto'
            sensorkey = 'ref_sensor'
            section   = 'ref-device'
            prefix    = REF
        else:
            modelkey  = 'test_model'
            endpoikey = 'test_endpoint'
            oldprokey = 'test_old_proto'
            sensorkey = 'test_sensor'
            section   = 'test-device'
            prefix    = TEST
        options = self.dbaseServ.getInitialConfig(section)
        options['model']        = self._cmd_options[modelkey]  or options['model']
        options['model']        = options['model'].upper()
        options['sensor']       = self._cmd_options[sensorkey] or options['sensor']
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
        return service
    
