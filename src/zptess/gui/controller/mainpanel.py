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
            self.view.mainArea.calibPanel.state.set(result)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)





class PhotometerPanelController:

    NAME = NAMESPACE

    def __init__(self, parent, view, model, messages):
        self.parent = parent
        self.model = model
        self.view = view
        self.messages = messages
        self._update_zp   = False
        self._write_to_db = False

        setLogLevel(namespace=NAMESPACE, levelStr='info')
        reactor.callLater(0, self.start)

    @inlineCallbacks
    def start(self):
        # events coming from GUI
        pub.subscribe(self.onStartPhotometerReq, 'start_photometer_req')
        pub.subscribe(self.onStopPhotometerReq, 'stop_photometer_req')
        pub.subscribe(self.onStartCalibrationReq, 'start_calibration_req')
        pub.subscribe(self.onStopCalibrationReq, 'stop_calibration_req')
        pub.subscribe(self.onWriteZeroPointReq, 'write_zero_point_req')
        pub.subscribe(self.onUpdatePhotometerReq, 'update_photometer_req')
        pub.subscribe(self.onUpdateDatabaseReq, 'update_database_req')

        # Events coming from services
        pub.subscribe(self.onPhotometerInfo, 'phot_info')
        pub.subscribe(self.onPhotometerFirmware, 'phot_firmware')
        pub.subscribe(self.onPhotometerOffline, 'phot_offline')
        pub.subscribe(self.onPhotometerEnd, 'phot_end')
        pub.subscribe(self.onStatisticsProgress, 'stats_progress')
        pub.subscribe(self.onStatisticsInfo, 'stats_info')
        pub.subscribe(self.onCalibrationRound, 'calib_round_info')
        pub.subscribe(self.onCalibrationLists, 'calib_summary_lists')
        pub.subscribe(self.onCalibrationSummary, 'calib_summary_info')
        pub.subscribe(self.onCalibrationEnd, 'calib_end')

        
        self.calib = yield self._buildCalibration()
        self.phot = {
            'ref':  None,
            'test': None,
        }
        self.stats = {
            'ref':  None,
            'test': None,
        }
        self.photinfo = {
            'ref':  None,
            'test': None,
        }
        result = yield self.model.config.load('test-device','endpoint')
        self.view.mainArea.photPanel['test'].setEndpoint(result['endpoint'])
        result = yield self.model.config.load('ref-device','endpoint')
        self.view.mainArea.photPanel['ref'].setEndpoint(result['endpoint'])

    # --------------
    # Event handlers
    # --------------

    def onUpdatePhotometerReq(self, flag):
        self._update_zp = flag
    
    def onUpdateDatabaseReq(self, flag):
        self._write_to_db = flag
        self.model.parent.setTestMode(not flag)

    @inlineCallbacks
    def onWriteZeroPointReq(self, zero_point):
        try:
            if not self.phot['test']:
                self.phot['test'] = yield self._buildPhotometer('test')
            if not self.phot['test'].running:
                yield self.phot['test'].startService()
            result = yield self.phot['test'].writeZeroPoint(zero_point)
            yield self.view.messageBoxInfo(
                title = _("Test Photometer"),
                message = _("New Zero Point written")
            )
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)



    @inlineCallbacks
    def onPhotometerFirmware(self, role, firmware):
        label = TEST if role == 'test' else REF
        if self._test_transport_method == 'tcp':
            message = _("Conflictive firmware '{0}' for TCP comms. Use UDP instead").format(firmware)
            yield self.view.messageBoxWarn(
                title = _("Test Photometer"),
                message = message
            )
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
        label = TEST if role == 'test' else REF
        log.info('[{label:4s}] {name:9s} waiting for enough samples, {pend:03d} remaining', 
            label = label, 
            name = stats_info['name'], 
            pend = stats_info['nsamples'] - stats_info['current'],
        )
        self.view.mainArea.photPanel[role].yellow()
        self.view.mainArea.photPanel[role].updatePhotStats(stats_info)

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
        if stats_info['stddev'] == 0.0:
            self.view.mainArea.photPanel[role].red()
        else:
            self.view.mainArea.photPanel[role].green()
        self.view.mainArea.photPanel[role].updatePhotStats(stats_info)

    def onPhotometerInfo(self, role, info):
        label = TEST if role == 'test' else REF
        self.photinfo[role] = info
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
            self.view.mainArea.photPanel[role].updatePhotInfo(info)
      
    @inlineCallbacks
    def onStartPhotometerReq(self, role, alone):
        try:
            #self.photinfo[role] = None
            if not self.stats[role]:
                self.stats[role] = yield self._buildStatistics(role, alone)
            if not self.phot[role]:
                self.phot[role] = yield self._buildPhotometer(role)
            if alone:
                self.stats[role].useOwnZP()
            else:
                self.stats[role].useFictZP()
            yield self._startChain(role)
            self.view.mainArea.photPanel[role].enable()
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

 
    @inlineCallbacks
    def onStopPhotometerReq(self, role):
        try:
            if self.calib.running:
                self.view.mainArea.photPanel[role].enable()
            else:
                yield self._stopChain(role)
                self.view.mainArea.photPanel[role].clear()
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    def onCalibrationRound(self, role, count, stats_info):
        #log.info("onCalibrationRound(stats_info={stats_info})", role=role, stats_info=stats_info)
        label = TEST if role == 'test' else REF
        if role == 'test':
            log.info('ROUND        {i:02d}: New ZP = {zp:0.2f} = \u0394(ref-test) Mag ({magDiff:0.2f}) + ZP Abs ({zp_fict:0.2f})',
                i        = count ,
                magDiff  = stats_info['mag_diff'], 
                zp_fict  = stats_info['zp_fict'], 
                zp       = stats_info['zero_point'],
            )
            log.info("="*72)
            self.view.mainArea.calibPanel.updateCalibration(count, stats_info)

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
            self.view.mainArea.calibPanel.updateSummary(stats_info)

    @inlineCallbacks
    def onStartCalibrationReq(self):
        if not self.calib.running:
            self.calib.startService()
        yield self.onStartPhotometerReq('test', alone=False)
        self.calib.onPhotometerInfo('test', self.photinfo['test'])
        yield self.onStartPhotometerReq('ref', alone=False)
        self.calib.onPhotometerInfo('ref', self.photinfo['ref'])
        self.view.mainArea.photPanel['test'].startCalibration()
        self.view.mainArea.photPanel['ref'].startCalibration()


    @inlineCallbacks
    def onStopCalibrationReq(self):
        if not self.calib.running:
            log.warn("{name} was not not running",name=self.calib.name)
        else:
            yield self.calib.stopService()
            yield self._stopChain('test')
            yield self._stopChain('ref')
        self.view.mainArea.photPanel['test'].stopCalibration()
        self.view.mainArea.photPanel['ref'].stopCalibration()
        self.view.mainArea.calibPanel.stopCalibration()

    @inlineCallbacks
    def onCalibrationEnd(self, session):
        messages = [_("Calibration process finsihed.") ]
        if self._update_zp:
            yield self.phot['test'].writeZeroPoint(self._zp_to_write)
            messages.append(_("Zero point updated."))
        yield self.model.parent.flush() # this takes care of itself when flushing in test mode
        if self._write_to_db:
            messages.append(_("Database updated."))
        yield self.calib.stopService()
        yield self._stopChain('test')
        yield self._stopChain('ref')
        self.view.mainArea.photPanel['test'].stopCalibration()
        self.view.mainArea.photPanel['ref'].stopCalibration()
        self.view.mainArea.calibPanel.stopCalibration()
        yield self.view.messageBoxInfo(
            title   = _("Calibration"),
            message = '\n'.join(messages)
        )

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
    def _buildPhotometer(self, role):
        if role == 'ref':
            section   = 'ref-device'
            prefix    = REF
            isRef     = True
        else:
            section   = 'test-device'
            prefix    = TEST
            isRef     = False
        options = yield self.model.config.loadSection(section)
        options['model']        = options['model'].upper()
        options['log_level']    = 'info' # A capón de momento
        options['write_zero_point'] = None # A capón de momento
        if self.messages == 'both' or self.messages == role:
            options['log_messages'] = 'info'
        else:
            options['log_messages'] = 'warn'  # A capón de momento
        options['config_dao']   = self.model.config
        proto, addr, port = chop(options['endpoint'], sep=':')
        self._test_transport_method = proto
        service = PhotometerService(options, isRef)
        service.setName(prefix + ' ' + PhotometerService.NAME)
        return service

    @inlineCallbacks
    def _buildStatistics(self, role, alone):
        if role == 'ref':
            section   = 'ref-stats'
            prefix    = REF
            isRef     = True
        else:
            section   = 'test-stats'
            prefix    = TEST
            isRef     = False
        options = yield self.model.config.loadSection(section)
        zp_fict =  yield self.model.config.load('calibration','zp_fict')
        options['samples'] = int(options['samples'])
        options['period']  = float(options['period'])
        options['zp_fict']  = float(zp_fict['zp_fict'])
        options['log_level'] = 'info' # A capón de momento
        service = StatisticsService(options, isRef, use_fict_zp= not alone)
        service.setName(prefix + ' ' + StatisticsService.NAME)
        return service

    @inlineCallbacks
    def _buildCalibration(self):
        section = 'calibration'
        options = yield self.model.config.loadSection(section)
        options['rounds'] = int(options['rounds'])
        options['offset'] = float(options['offset'])
        options['update'] = False  # A capón de momento, pero se necesita para el uupdate flag de la bbdd
        options['log_level'] = 'info' # A capón de momento
        service = CalibrationService(options)
        service.setName(CalibrationService.NAME)
        return service