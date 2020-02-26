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
import json

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver

#--------------
# local imports
# -------------

from zptess.logger   import setLogLevel as SetLogLevel


'''
Sample strings from serial port

{"seq":218, "rev":3, "name":"TASD00", "ci":20.20, "freq":1926.78, "mag":11.99, "tamb":17.89, "tsky":23.65, "vbat":0.01, "alt":0.00, "azi":0.00}
<fH 02083><tA 01792><tO 02379><mZ 00000>
{"seq":219, "rev":3, "name":"TASD00", "ci":20.20, "freq":2083.33, "mag":11.90, "tamb":17.93, "tsky":23.79, "vbat":0.02, "alt":0.00, "azi":0.00}
<fH 02040><tA 01792><tO 02351><mZ 00000>
{"seq":220, "rev":3, "name":"TASD00", "ci":20.20, "freq":2040.82, "mag":11.93, "tamb":17.93, "tsky":23.51, "vbat":0.01, "alt":0.00, "azi":0.00}
<fH 01956><tA 01795><tO 02362><mZ 00000>
{"seq":221, "rev":3, "name":"TASD00", "ci":20.20, "freq":1956.95, "mag":11.97, "tamb":17.95, "tsky":23.63, "vbat":0.01, "alt":0.00, "azi":0.00}
<fH 01792><tA 01792><tO 02357><mZ 00000>
{"seq":222, "rev":3, "name":"TASD00", "ci":20.20, "freq":1792.11, "mag":12.07, "tamb":17.93, "tsky":23.57, "vbat":0.02, "alt":0.00, "azi":0.00}
<fH 01219><tA 01795><tO 02362><mZ 00000>
{"seq":223, "rev":3, "name":"TASD00", "ci":20.20, "freq":1219.51, "mag":12.48, "tamb":17.95, "tsky":23.63, "vbat":0.01, "alt":0.00, "azi":0.00}
<fH 01189><tA 01792><tO 02364><mZ 00000>
{"seq":224, "rev":3, "name":"TASD00", "ci":20.20, "freq":1189.06, "mag":12.51, "tamb":17.93, "tsky":23.65, "vbat":0.01, "alt":0.00, "azi":0.00}


-----------------------------------------------
Compiled Feb 11 2020  11:21:38
MAC: D0019D286F24
TAS SN: TASD00
Actual CI: 20.20
-----------------------------------------------

'''

# ----------------
# Module constants
# ----------------

# SOLICITED Responses Patterns
SOLICITED_RESPONSES = (
    {
        'name'    : 'firmware',
        'pattern' : r'^Compiled (.+)',       
    },
    {
        'name'    : 'mac',
        'pattern' : r'^MAC: ([0-9A-Za-z]{12})',       
    },
    {
        'name'    : 'name',
        'pattern' : r'^TAS SN: (TAS\w{3})',       
    },
    {
        'name'    : 'zp',
        'pattern' : r'^Actual CI: (\d{1,2}.\d{1,2})',       
    },
    {
        'name'    : 'written_zp',
        'pattern' : r'^New CI: (\d{1,2}.\d{1,2})',       
    },
)

SOLICITED_PATTERNS = [ re.compile(sr['pattern']) for sr in SOLICITED_RESPONSES ]


# -----------------------
# Module global variables
# -----------------------



# ----------------
# Module functions
# ----------------

def format_mac(mac):
    '''Formats MAC strings as returned from the device into well-known MAC format'''
    return ':'.join(map(''.join, zip(*[iter(mac)]*2)))
    




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
        self.write_deferred = None
        self.read_deferred  = None
        self.write_response = None
        self.read_response  = None
        self.log = Logger(namespace=namespace)

      
    def connectionMade(self):
        self.log.debug("connectionMade()")


    def lineReceived(self, line):
        now = datetime.datetime.utcnow().replace(microsecond=0) + datetime.timedelta(seconds=0.5)
        line = line.decode('latin_1')  # from bytearray to string
        self.log.info("<==  TAS   [{l:02d}] {line}", l=len(line), line=line)
        handled = self._handleUnsolicitedResponse(line, now)
        if handled:
            return
        handled = self._handleSolicitedResponse(line, now)

    # ================
    # TESS Protocol API
    # ================

    def setLogLevel(self, level):
        SetLogLevel(namespace='proto', levelStr=level)


    def setReadingCallback(self, callback):
        '''
        API Entry Point
        '''
        self._onReading = callback


    def setContext(self, context):
        pass


    def writeZeroPoint(self, zero_point):
        '''
        Writes Zero Point to the device. 
        Returns a Deferred
        '''
        line = 'CI{0:04d}'.format(int(round(zero_point*100,2)))
        self.log.info(" ==> TAS   [{l:02d}] {line}", l=len(line), line=line)
        self.sendLine(line.encode('ascii'))
        self.write_deferred = defer.Deferred()
        self.write_deferred.addTimeout(2, reactor)
        self.write_response = {}
        return self.write_deferred


    def readPhotometerInfo(self):
        '''
        Reads Info from the device. 
        Returns a Deferred
        '''
        line = '?'
        self.log.info(" ==> TAS   [{l:02d}] {line}", l=len(line), line=line)
        self.sendLine(line.encode('ascii'))
        self.read_deferred = defer.Deferred()
        self.read_deferred.addTimeout(2, reactor)
        self.cnt = 0
        self.read_response = {}
        return self.read_deferred

    # --------------
    # Helper methods
    # --------------

    def match_solicited(self, line):
        '''Returns matched command descriptor or None'''
        for regexp in SOLICITED_PATTERNS:
            matchobj = regexp.search(line)
            if matchobj:
                self.log.debug("matched {pattern}", pattern=SOLICITED_RESPONSES[SOLICITED_PATTERNS.index(regexp)]['name'])
                return SOLICITED_RESPONSES[SOLICITED_PATTERNS.index(regexp)], matchobj
        return None, None


    def _handleSolicitedResponse(self, line, tstamp):
        '''
        Handle Solicted responses from zptess.
        Returns True if handled, False otherwise
        '''
        sr, matchobj = self.match_solicited(line)
        if not sr:
            return False

        if sr['name'] == 'name':
            self.read_response['tstamp'] = tstamp
            self.read_response['name'] = str(matchobj.group(1))
            self.cnt += 1
        elif sr['name'] == 'mac':
            self.read_response['tstamp'] = tstamp
            self.read_response['mac'] = format_mac(matchobj.group(1))
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
        
        # trigger pending callbacks
        if self.read_deferred and self.cnt == 4: 
            self.read_deferred.callback(self.read_response)
            self.read_deferred = None
            self.cnt = 0

        if self.write_deferred and 'zp' in self.write_response: 
            self.write_deferred.callback(self.write_response)
            self.write_deferred = None

        return True


    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle Unsolicted responses from zptess.
        Returns True if handled, False otherwise
        '''
        try:
            reading = json.loads(line)
        except Exception as e:
            return False
        else:
            reading['tstamp'] = tstamp
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