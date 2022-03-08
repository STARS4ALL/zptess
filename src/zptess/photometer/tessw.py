# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import re
import datetime
import sys
import json

# ---------------
# Twisted imports
# ---------------

import treq

from twisted.logger               import Logger
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.internet.threads     import deferToThread
from twisted.internet.interfaces  import IPushProducer, IConsumer
from zope.interface               import implementer

#--------------
# local imports
# -------------

import zptess.utils

from zptess.logger       import setLogLevel as SetLogLevel
from zptess.photometer.tessbase  import TESSBaseProtocolFactory

# ----------------
# Module constants
# ----------------


GET_INFO = {
    # These apply to the /config page
    'name'  : re.compile(r"(stars\d+)"),       
    'mac'   : re.compile(r"MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),       
    'zp'    : re.compile(r"(ZP|CI): (\d{1,2}\.\d{1,2})"),
    #'zp'    : re.compile(r"Const\.: (\d{1,2}\.\d{1,2})"),
    'firmware' : re.compile(r"Compiled: (.+?)<br>"),  # Non-greedy matching until <br>
    # This applies to the /setconst?cons=nn.nn page
    'flash' : re.compile(r"New Zero Point (\d{1,2}\.\d{1,2})") 
}


# <fH 04606><tA +2987><tO +2481><mZ -0000>
# Unsolicited Responses Patterns
UNSOLICITED_RESPONSES = (
    {
        'name'    : 'Hz reading',
        'pattern' : r'^<fH([ +]\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
    },
    {
        'name'    : 'mHz reading',
        'pattern' : r'^<fm([ +]\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
    },
)


UNSOLICITED_PATTERNS = [ re.compile(ur['pattern']) for ur in UNSOLICITED_RESPONSES ]


# -----------------------
# Module global variables
# -----------------------


# ----------------
# Module functions
# ----------------

def make_state_url(endpoint):
    ip_address = zptess.utils.chop(endpoint,':')[1]
    return "http://{0:s}/config".format(ip_address)

def make_save_url(endpoint):
    ip_address = zptess.utils.chop(endpoint,':')[1]
    return "http://{0:s}/setconst".format(ip_address)


# ----------
# Exceptions
# ----------


# -------
# Classes
# -------


class TESSProtocolFactory(TESSBaseProtocolFactory):

    def buildProtocol(self, addr):
        if self.old_protocol:
            return TESSOldProtocol(self.namespace)
        else:
            return TESSJsonProtocol(self.namespace)



@implementer(IPushProducer)
class TESSOldProtocol(LineOnlyReceiver):

    # So that we can patch it in tests with Clock.callLater ...
    callLater = reactor.callLater
    conflicting_firmware = ('Nov 25 2021 v 3.2',)

    # -------------------------
    # Twisted Line Receiver API
    # -------------------------

    def __init__(self, namespace):
        '''Sets the delimiter to the closihg parenthesis'''
        # LineOnlyReceiver.delimiter = b'\n'
        self.log = Logger(namespace=namespace)
        self._consumer = None
        self._paused   = True
        self._stopped  = False
        self.log.info("Created protocol {who}",who=self.__class__.__name__)


    def connectionMade(self):
        self.log.debug("{who} connectionMade()", who=self.__class__.__name__)


    def lineReceived(self, line):
        self.log.debug("{who} lineReceived()",who=self.__class__.__name__)
        now = datetime.datetime.now(datetime.timezone.utc)
        line = line.decode('latin_1')  # from 'bytes' to 'str'
        self.log.info("<== TESS-W [{l:02d}] {line}", l=len(line), line=line)
        handled, reading = self._handleUnsolicitedResponse(line, now)
        if handled:
            self._consumer.write(reading)
    
    # -----------------------
    # IPushProducer interface
    # -----------------------

    def stopProducing(self):
        """
        Stop producing data.
        """
        self._stopped     = False


    def pauseProducing(self):
        """
        Pause producing data.
        """
        self._paused    = True


    def resumeProducing(self):
        """
        Resume producing data.
        """
        self._paused    = False


    def registerConsumer(self, consumer):
        '''
        This is not really part of the IPushProducer interface
        '''
        self._consumer = IConsumer(consumer)


    # =================
    # TESS Protocol API
    # =================

    def setContext(self, context):
        self.httpEndPoint = context


    @inlineCallbacks
    def writeZeroPoint(self, zero_point):
        '''
        Writes Zero Point to the device. 
        Asynchronous operation
        '''
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        url = make_save_url(self.httpEndPoint)
        self.log.info("==> TESS-W [HTTP GET] {url}", url=url)
        params = [('cons', '{0:0.2f}'.format(zero_point))]
        resp = yield treq.get(url, params=params, timeout=4)
        text = yield treq.text_content(resp)
        self.log.info("<== TESS-W [HTTP GET] {url}", url=url)
        matchobj = GET_INFO['flash'].search(text)
        result['zp'] = float(matchobj.groups(1)[0])
        return(result)


    @inlineCallbacks
    def readPhotometerInfo(self):
        '''
        Reads Info from the device. 
        Asynchronous operation
        '''
        result = {}
        result['tstamp'] = datetime.datetime.now(datetime.timezone.utc)
        url = make_state_url(self.httpEndPoint)
        self.log.info("==> TESS-W [HTTP GET] {url}", url=url)
        resp = yield treq.get(url, timeout=4)
        text = yield treq.text_content(resp)
        self.log.info("<== TESS-W [HTTP GET] {url}", url=url)
        matchobj = GET_INFO['name'].search(text)
        if not matchobj:
            self.log.error("TESS-W name not found!. Check unit's name")
        result['name'] = matchobj.groups(1)[0]
        matchobj = GET_INFO['mac'].search(text)
        if not matchobj:
            self.log.error("TESS-W MAC not found!")
        result['mac'] = matchobj.groups(1)[0]
        matchobj = GET_INFO['zp'].search(text)
        if not matchobj:
            self.log.error("TESS-W ZP not found!")
        result['zp'] = float(matchobj.groups(1)[1]) # Beware the seq index, it is not 0 as usual. See the regexp!
        matchobj = GET_INFO['firmware'].search(text)
        if not matchobj:
            self.log.error("TESS-W Firmware not found!")
        result['firmware'] = matchobj.groups(1)[0]
        firmware = result['firmware']
        if firmware in self.conflicting_firmware:
            self.delimiter = b'}'
            self.lineReceived = self.adhoc_lineReceived
        return(result)

       
    # --------------
    # Helper methods
    # --------------

    def _match_unsolicited(self, line):
        '''Returns matched command descriptor or None'''
        for regexp in UNSOLICITED_PATTERNS:
            matchobj = regexp.search(line)
            if matchobj:
                i = UNSOLICITED_PATTERNS.index(regexp)
                #self.log.debug("matched {pattern}", pattern=UNSOLICITED_RESPONSES[UNSOLICITED_PATTERNS.index(regexp)]['name'])
                return UNSOLICITED_RESPONSES[i], matchobj
        return None, None


    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle unsolicited responses from zptess.
        Returns True if handled, False otherwise
        '''
        if self._paused or self._stopped:
            self.log.debug("Producer either paused({p}) or stopped({s})", p=self._paused, s=self._stopped)
            return False, None
        ur, matchobj = self._match_unsolicited(line)
        if not ur:
            return False, None
        reading = {}
        reading['tbox']   = float(matchobj.group(2))/100.0
        reading['tsky']   = float(matchobj.group(3))/100.0
        reading['zp']     = float(matchobj.group(4))/100.0
        reading['tstamp'] = tstamp
        if ur['name'] == 'Hz reading':
            reading['freq']   = float(matchobj.group(1))/1.0
            self.log.debug("Matched {name}", name=ur['name'])
        elif ur['name'] == 'mHz reading':
            reading['freq'] = float(matchobj.group(1))/1000.0
            self.log.debug("Matched {name}", name=ur['name'])
        else:
            return False, None
        return True, reading
        



@implementer(IPushProducer)
class TESSJsonProtocol(TESSOldProtocol):

   
    def adhoc_lineReceived(self, line):
        '''This is only for a btach of TESS-W where the JSON comes without <LF><CR>'''
        self.log.debug("{who} lineReceived()",who=self.__class__.__name__)
        now = datetime.datetime.now(datetime.timezone.utc)
        line += b'}'
        line = line.decode('latin_1')  # from 'bytes' to 'str'
        self.log.info("<== TESS-W [{l:02d}] {line}", l=len(line), line=line)
        handled, reading = self._handleUnsolicitedResponse(line, now)
        if handled:
            self._consumer.write(reading)
    
       
    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle unsolicited responses from zptess.
        Returns True if handled, False otherwise
        '''
        if self._paused or self._stopped:
            self.log.debug("Producer either paused({p}) or stopped({s})", p=self._paused, s=self._stopped)
            return False, None
        try:
            reading = json.loads(line)
        except Exception as e:
            return False, None
        else:
            if type(reading) == dict:
                reading['tstamp'] = tstamp
                return True, reading
            else:
                return False, None

#---------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------



__all__ = [
    "TESSProtocol",
    "TESSProtocolFactory",
]
