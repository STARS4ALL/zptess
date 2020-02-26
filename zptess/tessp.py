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


# ----------------
# Module constants
# ----------------
# <fH 04606><tA +2987><tO +2481><mZ -0000>

# <fH 41666><tA 02468><tO 02358><aX -0016><aY -0083><aZ 00956><mX 00099><mY -0015><mZ -0520>
# {"seq":239, "rev":3, "name":"TSP206", "ci":20.20, "freq":37037.04, "mag":8.78, "tamb":24.69, "tsky":23.41, "alt":0.48, "azi":144.00}
# <fH 37037><tA 02468><tO 02340><aX -0008><aY -0086><aZ 00957><mX 00097><mY -0020><mZ -0519>
# {"seq":240, "rev":3, "name":"TSP206", "ci":20.20, "freq":37037.04, "mag":8.78, "tamb":24.71, "tsky":23.21, "alt":0.60, "azi":146.00}
# <fH 37037><tA 02470><tO 02320><aX -0010><aY -0088><aZ 00956><mX 00100><mY -0014><mZ -0521>
# {"seq":241, "rev":3, "name":"TSP206", "ci":20.20, "freq":40000.00, "mag":8.69, "tamb":24.71, "tsky":23.39, "alt":0.36, "azi":148.00}
# <fH 40000><tA 02470><tO 02339><aX -0006><aY -0084><aZ 00959><mX 00099><mY -0014><mZ -0521>
# {"seq":242, "rev":3, "name":"TSP206", "ci":20.20, "freq":38461.54, "mag":8.74, "tamb":24.67, "tsky":23.51, "alt":0.54, "azi":146.00}
# <fH 38461><tA 02467><tO 02351><aX -0009><aY -0090><aZ 00951><mX 00100><mY -0015><mZ -0522>
# {"seq":243, "rev":3, "name":"TSP206", "ci":20.20, "freq":40000.00, "mag":8.69, "tamb":24.67, "tsky":23.35, "alt":0.78, "azi":145.00}
# <fH 40000><tA 02467><tO 02335><aX -0013><aY -0085><aZ 00956><mX 00097><mY -0015><mZ -0522>
# {"seq":244, "rev":3, "name":"TSP206", "ci":20.20, "freq":41666.67, "mag":8.65, "tamb":24.67, "tsky":23.51, "alt":0.36, "azi":146.00}
# <fH 41666><tA 02467><tO 02351><aX -0006><aY -0086><aZ 00955><mX 00101><mY -0017><mZ -0522>
# {"seq":245, "rev":3, "name":"TSP206", "ci":20.20, "freq":41666.67, "mag":8.65, "tamb":24.69, "tsky":23.45, "alt":0.42, "azi":144.00}
# <fH 41666><tA 02468><tO 02345><aX -0007><aY -0086><aZ 00954><mX 00096><mY -0018><mZ -0522>
# {"seq":246, "rev":3, "name":"TSP206", "ci":20.20, "freq":38461.54, "mag":8.74, "tamb":24.75, "tsky":23.41, "alt":0.54, "azi":146.00}
# <fH 38461><tA 02474><tO 02340><aX -0009><aY -0087><aZ 00959><mX 00098><mY -0015><mZ -0522>
# {"seq":247, "rev":3, "name":"TSP206", "ci":20.20, "freq":40000.00, "mag":8.69, "tamb":24.69, "tsky":23.47, "alt":0.60, "azi":147.00}
# <fH 40000><tA 02468><tO 02346><aX -0010><aY -0086><aZ 00955><mX 00100><mY -0014><mZ -0521>
# {"seq":248, "rev":3, "name":"TSP206", "ci":20.20, "freq":38461.54, "mag":8.74, "tamb":24.69, "tsky":23.47, "alt":0.48, "azi":145.00}
# <fH 38461><tA 02468><tO 02346><aX -0008><aY -0085><aZ 00958><mX 00098><mY -0018><mZ -0521>
# {"seq":249, "rev":3, "name":"TSP206", "ci":20.20, "freq":37037.04, "mag":8.78, "tamb":24.75, "tsky":23.39, "alt":0.71, "azi":144.00}
# <fH 37037><tA 02474><tO 02339><aX -0012><aY -0085><aZ 00963><mX 00097><mY -0018><mZ -0520> 
# -----------------------------------------------
# Compiled Dec 16 2019  13:57:17
# MAC: 206714A4AE30
# TSP SN: TSP206
# Actual CI: 20.20
# -----------------------------------------------

# New CI: 20.45
# Write EEPROM done!

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
        'pattern' : r'^TSP SN: (TSP\w{3})',       
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
        self.log.info("<== TESS-P [{l:02d}] {line}", l=len(line), line=line)
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
        self.log.info(" ==> TESS-P [{l:02d}] {line}", l=len(line), line=line)
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
        self.log.info(" ==> TESS-P [{l:02d}] {line}", l=len(line), line=line)
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