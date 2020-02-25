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

from zptess import STATS_SERVICE, TESSW, TESSP, TAS

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
        self.namespace      = 'refe' if reference else 'test'
        self.protoNamespace = 'REFE' if reference else 'TEST'
        setLogLevel(namespace=self.protoNamespace, levelStr=options['log_messages'])
        setLogLevel(namespace=self.namespace,      levelStr=options['log_level'])
        self.log = Logger(namespace=self.namespace)
        self.reference = reference  # Flag, is this instance for the reference photometer
        self.factory   = self.buildFactory()
        self.protocol  = None
        self.serport   = None
        self.info      = {} # Photometer info
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] != 'serial':
            endpoint = clientFromString(reactor, self.options['endpoint'])
            ClientService.__init__(self, endpoint, self.factory, retryPolicy=backoffPolicy())

    
    @inlineCallbacks
    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        Although it is technically a synchronous operation, it works well
        with inline callbacks
        '''
        self.log.info("starting Photometer Service")
        if not self.limitedStart():
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
                try:
                    info = yield self.protocol.readPhotometerInfo()
                   
                except Exception as e:
                    self.log.error("Timeout when reading photometer info")
                    reactor.callLater(0, reactor.stop)
                else:
                    self.gotInfo(info)
        else:
            #if not self.reference:
            #    self.info = self.readPhotometerInfo()   # synchronous operation
            ClientService.startService(self)
            protocol = yield self.whenConnected()
            self.gotProtocol(protocol)
            self.log.info("Using TCP endpopint {endpoint}", endpoint=self.options['endpoint'])
            try:
                info = yield self.protocol.readPhotometerInfo()
            except Exception as e:
                self.log.error("Timeout when reading photometer info")
                self.log.failure("{excp}",excp=e)
                reactor.callLater(0, reactor.stop)
            else:
                self.gotInfo(info)

            
            
    # --------------
    # Photometer API 
    # --------------

    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device. Returns a Deferred'''
        return self.protocol.writeZeroPoint(zero_point)

    def getPhotometerInfo(self):
        return self.info


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

    def limitedStart(self):
        '''Detects the case where only the Test photometer service is started'''
        if self.reference:
            return False
        return (self.options['dry_run'] or self.options['zero_point'] is not None) 

    
    def buildFactory(self):
        if self.options['model'] == TESSW:
            self.log.debug("Choosing a {model} factory", model=TESSW)
            import zptess.tessw
            factory = zptess.tessw.TESSProtocolFactory(self.protoNamespace)
        elif self.options['model'] == TESSP:
            self.log.debug("Choosing a {model} factory", model=TESSP)
            import zptess.tessp
            factory = zptess.tessp.TESSProtocolFactory(self.protoNamespace)
        else:
            self.log.debug("Choosing a {model} factory", model=TAS)
            import zptess.tas
            factory = zptess.tas.TESSProtocolFactory(self.protoNamespace)
        return factory


    def gotProtocol(self, protocol):
        
        def noop(msg): pass

        self.log.debug("got protocol")
        self.protocol  = protocol
        func = noop if self.limitedStart() else self.onReading
        self.protocol.setReadingCallback(func)
        self.protocol.setContext(self.options['endpoint'])

    @inlineCallbacks
    def gotInfo(self, info):
        self.log.debug("got photometer info {info}",info=info)
        self.info = info
        self.info['model'] = self.options['model']
        self.log.info("[TEST] Model     : {name}", name=self.info['model'])
        self.log.info("[TEST] Name      : {name}", name=info['name'])
        self.log.info("[TEST] MAC       : {name}", name=info['mac'])
        self.log.info("[TEST] Zero Point: {name:.02f} (old)", name=info['zp'])
        self.log.info("[TEST] Firmware  : {name}", name=info['firmware'])
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            reactor.callLater(0,reactor.stop)
        elif self.options['zero_point'] is not None:
            result = yield self.protocol.writeZeroPoint(self.options['zero_point'])
            self.log.info("[TEST] Writen ZP : {zp:0.2f}",zp = result['zp'])
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