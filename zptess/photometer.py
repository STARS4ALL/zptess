# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger, LogLevel
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.application.service  import Service
from twisted.application.internet import ClientService
from twisted.internet.endpoints   import clientFromString

#--------------
# local imports
# -------------

from . import STATS_SERVICE

from zptess.logger   import setLogLevel
from zptess.utils    import chop

# -----------------------
# Module global variables
# -----------------------


# ----------
# Exceptions
# ----------


# -------
# Classes
# -------


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class PhotometerService(ClientService):

    # Service name
    NAME = 'Photometer Service'


    def __init__(self, options, reference):

        def backoffPolicy(initialDelay=4.0, maxDelay=60.0, factor=2):
            '''Custom made backoff policy to exit after a number of reconnection attempts'''
            def policy(attempt):
                delay = min(initialDelay * (factor ** attempt), maxDelay)
                if attempt > 2:
                    self.stopService()
                return delay
            return policy

        self.options   = options
        self.namespace = 'refe' if reference else 'test'
        self.log = Logger(namespace=self.namespace)
        setLogLevel(namespace=self.namespace, levelStr=options['log_level'])
        protocol_level  = 'debug' if options['log_messages'] else 'info'
        setLogLevel(namespace='proto', levelStr=protocol_level)
        self.reference = reference  # Flag, is this instance for the reference photometer
        self.factory   = self.buildFactory()
        self.protocol  = None
        self.serport   = None
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] != 'serial':
            endpoint = clientFromString(reactor, self.options['endpoint'])
            ClientService.__init__(self, endpoint, self.factory, retryPolicy=backoffPolicy())

    

    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        '''
        self.log.info("starting Photometer Service")
        self.statsService = self.parent.getServiceNamed(STATS_SERVICE)
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] == 'serial':
            endpoint = parts[1:]
            self.protocol = self.factory.buildProtocol(0)
            self.serport  = SerialPort(self.protocol, endpoint[0], reactor, baudrate=endpoint[1])
            self.gotProtocol(self.protocol)
            self.log.info("Using serial port {tty} at {baud} bps", tty=endpoint[0], baud=endpoint[1])
            if not self.reference:
                self.log.info("Requesting photometer info")
                d = self.protocol.readPhotometerInfo()
                d.addCallback(self.gotInfo)
        else:
            #if not self.reference:
            #    self.info = self.readPhotometerInfo()   # synchronous operation
            ClientService.startService(self)
            d = self.whenConnected()
            d.addCallback(self.gotProtocol)
            if not self.reference:
                d.addTimeout(3, reactor).addCallback(self.readPhotometerInfo2)
            self.log.info("Using TCP endpopint {endpoint}", endpoint=self.options['endpoint'])
            
            
    # --------------
    # Photometer API 
    # --------------

    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device. Returns a Deferred'''
        return self.protocol.writeZeroPoint(zero_point)


    def printStats(self):
        total  = self.protocol.nreceived
        nresponse = self.protocol.nresponse
        nunsolici = self.protocol.nunsolici
        nunknown = self.protocol.nunknown 
        quality = (nresponse + nunsolici)*100 / total if total != 0 else None 
        self.log.info("Serial port statistics: Total = {tot:03d}, Unknown = {nunk:03d}", 
            tot=total, nunk=nunknown)
        self.log.info("Serial link quality = {q:0.4f}%", q=quality)
        self.protocol.resetStats()


    # --------------
    # Helper methods
    # ---------------


    def buildFactory(self):
        if self.options['model'] == "TESS-W":
            self.log.debug("Choosing a TESS-W factory")
            import zptess.tessw
            factory = zptess.tessw.TESSProtocolFactory()
        elif self.options['model'] == "TESS-P":
            self.log.debug("Choosing a TESS-P factory")
            import zptess.tessp
            factory = zptess.tessp.TESSProtocolFactory()
        else:
            self.log.debug("Choosing a TAS factory")
            import zptess.tas
            factory = zptess.tas.TESSProtocolFactory()
        return factory


    def gotProtocol(self, protocol):
        self.log.debug("got protocol")
        self.protocol  = protocol
        self.protocol.setReadingCallback(self.onReading)
        self.protocol.setContext(self.options['endpoint'])

    def gotInfo(self, info):
        self.log.debug("got photometer info {info}",info=info)
        self.info = info
        self.log.info("[TEST] TESS-W name    : {name}", name=info['name'])
        self.log.info("[TEST] TESS-W MAC     : {name}", name=info['mac'])
        self.log.info("[TEST] TESS-W ZP      : {name} (old)", name=info['zp'])
        self.log.info("[TEST] TESS-W Firmware: {name}", name=info['firmware'])
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            reactor.callLater(0,reactor.stop)


    # ----------------------------
    # Event Handlers from Protocol
    # -----------------------------

    def onReading(self, reading):
        '''
        Adds last visual magnitude estimate
        and pass it upwards
        '''
        if self.reference:
            self.statsService.queue['reference'].append(reading)
        else:
            self.statsService.queue['test'].append(reading)


__all__ = [
    "PhotometerService",
]