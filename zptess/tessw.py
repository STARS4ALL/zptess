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

import requests

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger, LogLevel
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver

#--------------
# local imports
# -------------

import zptess.utils

# ----------------
# Module constants
# ----------------


GET_INFO = {
    # These apply to the /config page
    'name'  : re.compile(r".+(stars\d+)"),       
    'mac'   : re.compile(r".+MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),       
    'zp'    : re.compile(r".+ZP: (\d{1,2}\.\d{1,2})"),  
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

log = Logger(namespace='proto')

# ----------------
# Module functions
# ----------------


def match_unsolicited(line):
    '''Returns matched command descriptor or None'''
    for regexp in UNSOLICITED_PATTERNS:
        matchobj = regexp.search(line)
        if matchobj:
            log.debug("matched {pattern}", pattern=UNSOLICITED_RESPONSES[UNSOLICITED_PATTERNS.index(regexp)]['name'])
            return UNSOLICITED_RESPONSES[UNSOLICITED_PATTERNS.index(regexp)], matchobj
    return None, None


def make_state_url(endpoint):
    ip_address = zptess.utils.chop(endpoint,':')[1]
    return "http://" + ip_address + "/config"

def make_save_url(endpoint):
    ip_address = zptess.utils.chop(endpoint,':')[1]
    return "http://" + ip_address + "/setconst"


def readPhotometerInfo(endpoint):
        '''
        Reads Info from the device. 
        Synchronous operation performed before Twisted reactor is run
        '''
        result = {}
        state_url = make_state_url(endpoint)
        log.debug("requesting URL {url}", url=state_url)
        resp = requests.get(state_url, timeout=(2,5))
        resp.raise_for_status()
        text  = resp.text
        matchobj = GET_INFO['name'].search(text)
        result['name'] = matchobj.groups(1)[0]
        log.info("[TEST] TESS-W name: {name}", name=result['name'])
        matchobj = GET_INFO['mac'].search(self.text)
        result['mac'] = matchobj.groups(1)[0]
        log.info("[TEST] TESS-W MAC : {name}", name=result['mac'])
        matchobj = GET_INFO['zp'].search(self.text)
        result['zero_point'] = float(matchobj.groups(1)[0])
        log.info("[TEST] TESS-W ZP  : {name} (old)", name=result['zero_point'])
        return result

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

    def startedConnecting(self, connector):
        log.debug('Factory: Started to connect.')

    def buildProtocol(self, addr):
        log.debug('Factory: Connected.')
        return TESSProtocol()

    def clientConnectionLost(self, connector, reason):
        log.debug('Factory: Lost connection. Reason: {reason}', reason=reason)

    def clientConnectionFailed(self, connector, reason):
        log.debug('Factory: Connection failed. Reason: {reason}', reason=reason)

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class TESSProtocol(LineOnlyReceiver):


    # So that we can patch it in tests with Clock.callLater ...
    callLater = reactor.callLater

    # -------------------------
    # Twisted Line Receiver API
    # -------------------------

    def __init__(self):
        '''Sets the delimiter to the closihg parenthesis'''
        # LineOnlyReceiver.delimiter = b'\n'
        self._onReading = set()                # callback sets
        # stat counters
        self.nreceived = 0
        self.nunsolici = 0
        self.nunknown  = 0
      
    def connectionMade(self):
        log.debug("connectionMade()")


    def lineReceived(self, line):
        now = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
        log.debug("<== REF [{l:02d}] {line}", l=len(line), line=line)
        self.nreceived += 1
        handled = self._handleUnsolicitedResponse(line, now)
        if handled:
            self.nunsolici += 1
            return
        self.nunknown += 1
        #log.warn("Unknown/Unexpected message {line}", line=line)

    # =================
    # TESS Protocol API
    # =================


    def setReadingCallback(self, callback):
        '''
        API Entry Point
        '''
        self._onReading = callback

    def resetStats(self):
        '''
        Reset statistics counters.
        '''
        self.nreceived = 0
        self.nresponse = 0
        self.nunsolici = 0
        self.nunknown  = 0

    def writeZeroPoint(self, sero_point, context):
        '''Writes Zero Point to the device. Returns a Deferred'''
        pass

    def readPhotometerInfo(self, endpoint):
        '''
        Reads Info from the device. 
        Synchronous operation performed before Twisted reactor is run
        '''
        try:
            state_url = make_state_url(endpoint)
            log.debug("requesting URL {url}", url=state_url)
            resp = requests.get(state_url, timeout=(2,5))
            resp.raise_for_status()
            self.text  = resp.text
        except Exception as e:
            log.error("{e}",e=e)
            sys.exit(1)
        else:
            result = {}
            matchobj = GET_INFO['name'].search(self.text)
            result['name'] = matchobj.groups(1)[0]
            log.info("[TEST] TESS-W name: {name}", name=self.tess_name)
            matchobj = GET_INFO['mac'].search(self.text)
            result['mac'] = matchobj.groups(1)[0]
            log.info("[TEST] TESS-W MAC : {name}", name=self.tess_mac)
            matchobj = GET_INFO['zp'].search(self.text)
            result['zero_point'] = float(matchobj.groups(1)[0])
            log.info("[TEST] TESS-W ZP  : {name} (old)", name=self.old_zp)
        return result


    # --------------
    # Helper methods
    # --------------


    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle unsolicited responses from zptess.
        Returns True if handled, False otherwise
        '''
        ur, matchobj = match_unsolicited(line)
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