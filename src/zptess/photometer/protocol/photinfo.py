# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import re
import datetime

# ---------------
# Twisted imports
# ---------------

import treq
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks
from zope.interface               import implementer

# ---------------------
# Third party libraries
# ---------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess.utils import chop
from zptess.photometer.protocol.interface import IPhotometerControl


# -----------------------
# Module global variables
# -----------------------


# ----------------
# Module functions
# ----------------

def formatted_mac(mac):
    ''''Corrects TESS-W MAC strings to be properly formatted'''
    return ':'.join(f"{int(x,16):02X}" for x in mac.split(':'))

# ----------
# Exceptions
# ----------


# -------
# Classes
# -------

@implementer(IPhotometerControl)
class HTMLPhotometer:
    """
    Get the photometer by parsing the HTML photometer home page.
    Set the new ZP by using the same URL as the HTML form displayed for humans
    """
    CONFLICTIVE_FIRMWARE = ('Nov 25 2021 v 3.2',)

    GET_INFO = {
        # These apply to the /config page
        'name'  : re.compile(r"(stars\d+)"),       
        'mac'   : re.compile(r"MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),       
        'zp'    : re.compile(r"(ZP|CI|CI 1): (\d{1,2}\.\d{1,2})"),
         #'zp'    : re.compile(r"Const\.: (\d{1,2}\.\d{1,2})"),
        'freq_offset': re.compile(r"Offset mHz: (\d{1,2}\.\d{1,2})"),
        'firmware' : re.compile(r"Compiled: (.+?)<br>"),  # Non-greedy matching until <br>
        # This applies to the /setconst?cons=nn.nn or /SetZP?nZP1=nn.nn pages
        'flash' : re.compile(r"New Zero Point (\d{1,2}\.\d{1,2})|CI 4 chanels:"),   
    }

    def __init__(self, addr, label, log, log_msg):
        self.log = log_msg
        self.addr = addr
        self.label = label
        self.glog = log # Global log for the module, not object instance
        self.glog.info("{label:6s} Using {who} Info", label=self.label, who=self.__class__.__name__)

    # ---------------------
    # IPhotometerControl interface
    # ---------------------

    @inlineCallbacks
    def writeZeroPoint(self, zero_point, timeout):
        '''
        Writes Zero Point to the device. 
        Asynchronous operation
        '''
        label = self.label
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        urls = (self._make_save_url(), self._make_save_url2())
        params = ( [('cons', '{0:0.2f}'.format(zero_point))], # For first URL
                  [('nZP1', '{0:0.2f}'.format(zero_point))])  # For second URL
        written_zp = False
        for i, (url, param) in enumerate(zip(urls, params), start=1):
            resp = yield treq.get(url, params=param, timeout=4)
            text = yield treq.text_content(resp)
            matchobj = self.GET_INFO['flash'].search(text)
            if matchobj:
                self.glog.info("==> {label:6s} [HTTP GET] {url} {params}", url=url, label=label, params=param)
                result['zp'] = float(matchobj.groups(1)[0]) if i == 1 else zero_point
                written_zp = True
                break
        if not written_zp:
            raise IOError("{:6s} ZP not written!".format(label))
        return(result)

    @inlineCallbacks
    def getPhotometerInfo(self, timeout):
        '''
        Get photometer information. 
        Asynchronous operation
        '''
        label = self.label
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        url = self._make_state_url()
        self.log.info("==> {label:6s} [HTTP GET] {url}", label=label,url=url)
        resp = yield treq.get(url, timeout=timeout)
        text = yield treq.text_content(resp)
        self.log.info("<== {label:6s} [HTTP GET] {url}", label=label, url=url)
        matchobj = self.GET_INFO['name'].search(text)
        if not matchobj:
            self.log.error("{label:6s} name not found!. Check unit's name", label=label)
        result['name'] = matchobj.groups(1)[0]
        matchobj = self.GET_INFO['mac'].search(text)
        if not matchobj:
            self.log.error("{label:6s} MAC not found!", label=label)
        result['mac'] = formatted_mac(matchobj.groups(1)[0])
        matchobj = self.GET_INFO['zp'].search(text)
        if not matchobj:
            self.log.error("{label:6s} ZP not found!", label=label)
        result['zp'] = float(matchobj.groups(1)[1]) # Beware the seq index, it is not 0 as usual. See the regexp!
        matchobj = self.GET_INFO['firmware'].search(text)
        if not matchobj:
            self.log.error("{label:6s} Firmware not found!", label=label)
        result['firmware'] = matchobj.groups(1)[0]
        firmware = result['firmware']
        if firmware in self.CONFLICTIVE_FIRMWARE:
            pub.sendMessage('phot_firmware', role='test', firmware=firmware)
        matchobj = self.GET_INFO['freq_offset'].search(text)
        if not matchobj:
            self.log.warn("{label:6s} Frequency offset not found, defaults to 0.0 mHz", label=label)
            result['freq_offset'] = 0.0
        else:
            result['freq_offset'] = float(matchobj.groups(1)[0])/1000.0
        return(result)

    def onPhotommeterInfoResponse(self, line, tstamp):
        return False

    # --------------
    # Helper methods
    # --------------

    def _make_state_url(self):
        return f"http://{self.addr}/config"

    def _make_save_url(self):
        return f"http://{self.addr}/setconst"

    def _make_save_url2(self):
        '''New Write ZP URL from firmware version starting on 16 June 2023'''
        return f"http://{self.addr}/SetZP"


@implementer(IPhotometerControl)
class CLIPhotometer:

    """
    Get the photometer by sending commands through a line oriented interface (i.e a serial port).
    Set the new ZP by sending commands through a line oriented interface (i.e a serial port)
    """

    SOLICITED_RESPONSES = [
        {
            'name'    : 'firmware',
            'pattern' : r'^Compiled (.+)',       
        },
        {
            'name'    : 'mac',
            'pattern' : r'^MAC: ([0-9A-Za-z]{12})',       
        },
        {
            'name'    : 'zp',
            'pattern' : r'^Actual CI: (\d{1,2}.\d{1,2})',       
        },
        {
            'name'    : 'written_zp',
            'pattern' : r'^New CI: (\d{1,2}.\d{1,2})',       
        },
    ]

    SOLICITED_PATTERNS = [ re.compile(sr['pattern']) for sr in SOLICITED_RESPONSES ]


    def __init__(self, label, log, log_msg):
        self.log = log_msg
        self.glog = log
        self.label = label
        self.parent = None
        self.read_deferred = None
        self.write_deferred = None
        self.glog.info("{label:6s} Using {who} Info", label=self.label, who=self.__class__.__name__)

    def setParent(self, protocol):
        self.parent = protocol

    # ---------------------
    # IPhotometerControl interface
    # ---------------------

    def writeZeroPoint(self, zero_point, timeout):
        '''
        Writes Zero Point to the device. 
        Returns a Deferred
        '''
        line = 'CI{0:04d}'.format(int(round(zero_point*100,2)))
        self.glog.info("==> {label:6} [{l:02d}] {line}", label=self.label, l=len(line), line=line)
        self.parent.sendLine(line.encode('ascii'))
        self.write_deferred = defer.Deferred()
        self.write_deferred.addTimeout(timeout, reactor)
        self.write_response = {}
        return self.write_deferred


    def getPhotometerInfo(self, timeout):
        '''
        Reads Info from the device.
        Returns a Deferred
        '''
        line = '?'
        self.log.info("==> {label:6} [{l:02d}] {line}", label=self.label, l=len(line), line=line)
        self.parent.sendLine(line.encode('ascii'))
        self.read_deferred = defer.Deferred()
        self.read_deferred.addTimeout(timeout, reactor)
        self.cnt = 0
        self.read_response = {}
        return self.read_deferred


    def onPhotommeterInfoResponse(self, line, tstamp):
        '''
        Handle solicted responses from photometer.
        Returns True if handled, False otherwise
        '''
        sr, matchobj = self._match_solicited(line)
        if not sr:
            return False
        self.read_response['freq_offset'] = 0 # This is hardwired until we can query this on the CLI
        if sr['name'] == 'name':
            self.read_response['tstamp'] = tstamp
            self.read_response['name'] = str(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'mac':
            self.read_response['tstamp'] = tstamp
            self.read_response['mac'] = formatted_mac(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'firmware':
            self.read_response['tstamp'] = tstamp
            self.read_response['firmware'] = str(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'zp':
            self.read_response['tstamp'] = tstamp
            self.read_response['zp'] = float(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'written_zp':
            self.write_response['tstamp'] = tstamp
            self.write_response['zp'] = float(matchobj.group(1))
        else:
            return False
        self._maybeTriggerCallbacks()
        return True

    # --------------
    # Helper methods
    # --------------

    def _maybeTriggerCallbacks(self):
        # trigger pending callbacks
        if self.read_deferred and self.cnt == 4: 
            self.read_deferred.callback(self.read_response)
            self.read_deferred = None
            self.cnt = 0

        if self.write_deferred and 'zp' in self.write_response: 
            self.write_deferred.callback(self.write_response)
            self.write_deferred = None

    def _match_solicited(self, line):
        '''Returns matched command descriptor or None'''
        for i, regexp in enumerate(self.SOLICITED_PATTERNS, 0):
            matchobj = regexp.search(line)
            if matchobj:
                self.log.debug("matched {pattern}", pattern=self.SOLICITED_RESPONSES[i]['name'])
                return self.SOLICITED_RESPONSES[i], matchobj
        return None, None

      

@implementer(IPhotometerControl)
class DBasePhotometer:

    def __init__(self, config_dao, section, label, log, log_msg):
        self.log = log_msg
        self.config_dao = config_dao
        self.section = section
        self.label = label
        log.info("{label:6s} Using {who} Info", label=self.label, who=self.__class__.__name__)


    # ---------------------
    # IPhotometerControl interface
    # ---------------------

    def writeZeroPoint(self, zero_point, timeout):
        '''
        Writes Zero Point to the device. 
        Asynchronous operation
        '''
        return defer.fail(NotImplementedError("It doesn't make sense"))


    @inlineCallbacks
    def getPhotometerInfo(self, timeout):
        '''
        Get photometer information. 
        Asynchronous operation
        '''
        label = self.label
        self.log.info("==> {label:6s} [SQL] from config_t, section '{section}'", label=label, section=self.section)
        result = yield self.config_dao.loadSection(self.section)
        self.log.info("<== {label:6s} [SQL] returns {result}", label=label, result=result)
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        result['zp']    = float(result['zp'])
        result['freq_offset'] = float(result['freq_offset'])
        result['old_proto'] = int(result['old_proto'])
        return(result)


    def onPhotommeterInfoResponse(self, line, tstamp):
        return False



#---------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------


__all__ = [
    "HTMLPhotometer",
    "CLIPhotometer",
]