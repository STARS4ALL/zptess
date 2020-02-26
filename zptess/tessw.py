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


# ---------------
# Twisted imports
# ---------------

import treq

from twisted.logger               import Logger, LogLevel
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.internet.threads     import deferToThread

#--------------
# local imports
# -------------

import zptess.utils

from zptess.logger   import setLogLevel as SetLogLevel

# ----------------
# Module constants
# ----------------


GET_INFO = {
    # These apply to the /config page
    'name'  : re.compile(r"(stars\d+)"),       
    'mac'   : re.compile(r"MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),       
    'zp'    : re.compile(r"ZP: (\d{1,2}\.\d{1,2})"),
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
        'pattern' : r'^<fH (\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
    },
    {
        'name'    : 'mHz reading',
        'pattern' : r'^<fm (\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
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
    return "http://" + ip_address + "/config"

def make_save_url(endpoint, zp):
    ip_address = zptess.utils.chop(endpoint,':')[1]
    return "http://{0:s}/setconst?cons={1:0.2f}".format(ip_address, zp)


# ----------
# Exceptions
# ----------


class TESSError(Exception):
    '''Base class for all exceptions below'''
    pass



# -------
# Classes
# -------



# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class TESSProtocolFactory(ClientFactory):

    def __init__(self, namespace):
        self.namespace = namespace
        self.log = Logger(namespace=namespace)

    def startedConnecting(self, connector):
        self.log.debug('Factory: Started to connect.')

    def buildProtocol(self, addr):
        self.log.debug('Factory: Connected.')
        return TESSProtocol(self.namespace)

    def clientConnectionLost(self, connector, reason):
        self.self.log.debug('Factory: Lost connection. Reason: {reason}', reason=reason)

    def clientConnectionFailed(self, connector, reason):
        self.self.log.debug('Factory: Connection failed. Reason: {reason}', reason=reason)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class TESSProtocol(LineOnlyReceiver):


    # So that we can patch it in tests with Clock.callLater ...
    callLater = reactor.callLater

    # -------------------------
    # Twisted Line Receiver API
    # -------------------------

    def __init__(self, namespace):
        '''Sets the delimiter to the closihg parenthesis'''
        # LineOnlyReceiver.delimiter = b'\n'
        self._onReading = set()                # callback sets
        self.log = Logger(namespace=namespace)
        
      
    def connectionMade(self):
        self.log.debug("connectionMade()")


    def lineReceived(self, line):
        now = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
        line = line.decode('ascii')  # from bytearray to string
        self.log.info("<== TESS-W [{l:02d}] {line}", l=len(line), line=line)
        handled = self._handleUnsolicitedResponse(line, now)
    
    # =================
    # TESS Protocol API
    # =================

    def setLogLevel(self, level):
        SetLogLevel(namespace='proto', levelStr=level)


    def setReadingCallback(self, callback):
        '''
        API Entry Point
        '''
        self._onReading = callback


    def setContext(self, context):
        self.httpEndPoint = context


    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device. Returns a Deferred'''
        return deferToThread(self._writeZeroPoint,  zero_point, self.httpEndPoint)


    def readPhotometerInfo(self):
        '''
        Reads Info from the device. 
        Asynchronous operation
        '''
        self.log.info("CUCU6")
        return deferToThread(self._readPhotometerInfo, self.httpEndPoint)

    @inlineCallbacks
    def readPhotometerInfo(self):
        '''
        Reads Info from the device. 
        Asynchronous operation
        '''
        result = {}
        result['tstamp'] = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
        state_url = make_state_url(self.httpEndPoint)
        self.log.info("==> TESS-W [HTTP GET] {url}", url=state_url)
        resp = yield treq.get(state_url, timeout=4)
        text = yield treq.text_content(resp)
        self.log.info("<== TESS-W [HTTP GET] {url}", url=state_url)
        matchobj = GET_INFO['name'].search(text)
        result['name'] = matchobj.groups(1)[0]
        matchobj = GET_INFO['mac'].search(text)
        result['mac'] = matchobj.groups(1)[0]
        matchobj = GET_INFO['zp'].search(text)
        result['zp'] = float(matchobj.groups(1)[0])
        matchobj = GET_INFO['firmware'].search(text)
        result['firmware'] = matchobj.groups(1)[0]
        returnValue(result)

       
       

    # --------------
    # Helper methods
    # --------------

    
    def _readPhotometerInfo(self, endpoint):
        '''
        Reads Info from the device. 
        Synchronous operation performed before Twisted reactor is run
        '''
        self.log.warn("CUCU7")
        result = {}
        result['tstamp'] = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
        state_url = make_state_url(endpoint)
        self.log.info("==> TESS-W [HTTP GET] {url}", url=state_url)
        try:
            resp = requests.get(state_url, timeout=(4,8))
            self.log.warn("CUCU8")
            resp.raise_for_status()
        except Exception as e:
            self.log.failure("{excp}",excp=e)
        else:
            self.log.warn("CUCU9")
            self.log.info("<== TESS-W [HTTP GET] {url}", url=state_url)
            text  = resp.text
            matchobj = GET_INFO['name'].search(text)
            result['name'] = matchobj.groups(1)[0]
            matchobj = GET_INFO['mac'].search(text)
            result['mac'] = matchobj.groups(1)[0]
            matchobj = GET_INFO['zp'].search(text)
            result['zp'] = float(matchobj.groups(1)[0])
            matchobj = GET_INFO['firmware'].search(text)
            result['firmware'] = matchobj.groups(1)[0]
        return result


    def _writeZeroPoint(self, zp, endpoint):
        '''Flash new ZP. Synchronous request to be executed in a separate thread'''
        try:
            result = {}
            result['tstamp'] = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
            url = make_save_url(endpoint, zp)
            self.log.info("==> TESS-W [HTTP GET] {url}", url=url)
            resp = requests.get(url, timeout=(2,5))
            resp.raise_for_status()
            self.log.info("<== TESS-W [HTTP GET] {url}", url=url)
            text  = resp.text
        except Exception as e:
            self.log.error("{e}",e=e)
        else:
            matchobj = GET_INFO['flash'].search(text)
            if matchobj:
                result['zp'] = float(matchobj.groups(1)[0])
                return result


    def match_unsolicited(self, line):
        '''Returns matched command descriptor or None'''
        for regexp in UNSOLICITED_PATTERNS:
            matchobj = regexp.search(line)
            if matchobj:
                self.log.debug("matched {pattern}", pattern=UNSOLICITED_RESPONSES[UNSOLICITED_PATTERNS.index(regexp)]['name'])
                return UNSOLICITED_RESPONSES[UNSOLICITED_PATTERNS.index(regexp)], matchobj
        return None, None


    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle unsolicited responses from zptess.
        Returns True if handled, False otherwise
        '''
        ur, matchobj = self.match_unsolicited(line)
        if not ur:
            return False
        reading = {}
        reading['tbox']   = float(matchobj.group(2))/100.0
        reading['tsky']   = float(matchobj.group(3))/100.0
        reading['zp']     = float(matchobj.group(4))/100.0
        reading['tstamp'] = tstamp
        if ur['name'] == 'Hz reading':
            reading['freq']   = float(matchobj.group(1))/1.0
        elif ur['name'] == 'mHz reading':
            reading['freq'] = float(matchobj.group(1))/1000.0
        else:
            return False  
        self._onReading(reading)
        return True
        
        
#---------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------



__all__ = [
    "TESSError",
    "TESSProtocol",
    "TESSProtocolFactory",
]
