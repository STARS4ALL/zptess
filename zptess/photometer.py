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

from zptess.logger   import setLogLevel
from zptess.utils    import chop
from zptess.config   import loglevel

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


    def __init__(self, options, cmdopts, reference):

        def backoffPolicy(initialDelay=4.0, maxDelay=60.0, factor=2):
            '''Custom made backoff policy to exit after a number of reconnection attempts'''
            def policy(attempt):
                delay = min(initialDelay * (factor ** attempt), maxDelay)
                if attempt > 3:
                    self.stopService()
                return delay
            return policy

        self.namespace = 'refe' if reference else 'test'
        self.log = Logger(namespace=self.namespace)
        setLogLevel(namespace=self.namespace, levelStr=loglevel(cmdopts))
        protocol_level  = 'info' if options['log_messages'] else 'warn'
        setLogLevel(namespace='protoc', levelStr=protocol_level)
        self.reference = reference  # Flag, is this instance for the reference photometer
        self.options   = options
        self.cmdopts   = cmdopts
        self.serport   = None
        self.protocol  = None
        self.buildFactory()
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] == 'serial':
            self.endpoint = parts[1:]
            self.usingSerial = True
            if not self.reference and self.cmdopts.tcp:
                self.log.error("Inconsistency between command line option and endpoint spec")
                reactor.callLater(0,reactor.stop)
                return
        else:
            if not self.reference and self.cmdopts.serial:
                self.log.error("Inconsistency between command line option and endpoint spec")
                reactor.callLater(0,reactor.stop)
                return
            self.endpoint = clientFromString(reactor, self.options['endpoint'])
            self.usingSerial = False
            ClientService.__init__(self, self.endpoint, self.factory, retryPolicy=backoffPolicy())

    
    def buildFactory(self):
        if self.reference:
            self.log.debug("Choosing a TESS-W factory fro the reference")
            from zptess.tessw import TESSProtocolFactory
            self.factory = TESSProtocolFactory()
        elif self.cmdopts.tess_w:
            self.log.debug("Choosing a TESS-W factory")
            from zptess.tessw import TESSProtocolFactory
            self.factory = TESSProtocolFactory()
        elif self.cmdopts.tess_p:
            self.log.debug("Choosing a TESS-P factory")
            from zptess.tessp import TESSProtocolFactory
            self.factory = TESSProtocolFactory()
        else:
            self.log.debug("Choosing a TAS factory")
            from zptess.tas import TESSProtocolFactory
            self.factory = TESSProtocolFactory()


    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        '''
        self.log.info("starting Photometer Service")
        if self.usingSerial:
            self.protocol = self.factory.buildProtocol(0)
            self.serport  = SerialPort(self.protocol, self.endpoint[0], reactor, baudrate=self.endpoint[1])
            self.gotProtocol(self.protocol)
            self.log.info("Using serial port {tty} at {baud} bps", tty=self.endpoint[0], baud=self.endpoint[1])
        else:
            ClientService.startService(self)
            d = self.whenConnected()
            d.addCallback(self.gotProtocol)
            self.log.info("Using TCP endpopint {endpoint}", endpoint=self.endpoint)
            return d 
            

    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, options):
        options = options['serial']
        protocol_level  = 'debug' if options['log_messages'] else 'info'
        setLogLevel(namespace='serial', levelStr=options['log_level'])
        setLogLevel(namespace='protoc', levelStr=protocol_level)
        self.log.info("new log level is {lvl}", lvl=options['log_level'])
        self.options = options

    # --------------
    # Periodic task
    # ---------------

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

    def setFactory(self, factory):
        self.factory = factory


    def gotProtocol(self, protocol):
        self.log.debug("got protocol")
        self.protocol  = protocol
        self.protocol.setReadingCallback(self.onReading)

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