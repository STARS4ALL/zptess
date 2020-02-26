# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import sys

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.application.service  import Service
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints   import clientFromString

#--------------
# local imports
# -------------

from zptess import STATS_SERVICE, TESSW, TESSP, TAS, VERSION_STRING

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

    def __init__(self, options, reference):

        self.options   = options
        self.namespace = 'ref.' if reference else 'test'
        self.label     = self.namespace.upper()
        setLogLevel(namespace=self.label,     levelStr=options['log_messages'])
        setLogLevel(namespace=self.namespace, levelStr=options['log_level'])
        self.log = Logger(namespace=self.namespace)
        self.reference = reference  # Flag, is this instance for the reference photometer
        self.factory   = self.buildFactory()
        self.protocol  = None
        self.serport   = None
        self.info      = None # Photometer info
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] == 'tcp':
            endpoint = clientFromString(reactor, self.options['endpoint'])
            ClientService.__init__(self, endpoint, self.factory,
                 retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0))
    
    
    @inlineCallbacks
    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        Although it is technically a synchronous operation, it works well
        with inline callbacks
        '''
        
        self.log.info("starting {name} service", name=self.name)
        if not self.limitedStart():
            self.statsService = self.parent.getServiceNamed(STATS_SERVICE)
        try:
            yield self.connect()
        except Exception as e:
            self.log.failure("{excp}",excp=e)
            #reactor.callLater(0, reactor.stop)
        else:
            if not (self.reference and self.options['model'] == TESSW):
                self.info = yield self.getInfo()
            if not self.reference:
                yield self.initialActions()

            
    # --------------
    # Photometer API 
    # --------------

    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device. Returns a Deferred'''
        return self.protocol.writeZeroPoint(zero_point)


    def getPhotometerInfo(self):
        if self.protocol is None:
            log.warn("Requested photometer info but no protocol yet!")
            return defer.fail()
        if self.info is None:
            return self.getInfo()
        else:
            return defer.succeed(self.info)

    def getLabel(self):
        return self.label

    # --------------
    # Helper methods
    # ---------------

    @inlineCallbacks
    def connect(self):
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] == 'serial':
            endpoint = parts[1:]
            self.protocol = self.factory.buildProtocol(0)
            try:
                self.serport  = SerialPort(self.protocol, endpoint[0], reactor, baudrate=endpoint[1])
            except Exception as e:
                self.log.error("{excp}",excp=e)
                raise
            else:
                self.gotProtocol(self.protocol)
                self.log.info("Using serial port {tty} at {baud} bps", tty=endpoint[0], baud=endpoint[1])
        else:
            ClientService.startService(self)
            try:
                protocol = yield self.whenConnected(failAfterFailures=1)
            except Exception as e:
                self.log.error("{excp}",excp=e)
                raise
            else:
                self.gotProtocol(protocol)
                self.log.info("Using TCP endpoint {endpoint}", endpoint=self.options['endpoint'])


    @inlineCallbacks
    def getInfo(self):
        try:
            info = yield self.protocol.readPhotometerInfo()
        except Exception as e:
            self.log.error("Timeout when reading photometer info")
            self.log.failure("{excp}",excp=e)
            #reactor.callLater(0, reactor.stop)
        else:
            info['model'] = self.options['model']
            self.log.info("[{label}] Model     : {value}", label=self.label, value=info['model'])
            self.log.info("[{label}] Name      : {value}", label=self.label, value=info['name'])
            self.log.info("[{label}] MAC       : {value}", label=self.label, value=info['mac'])
            self.log.info("[{label}] Zero Point: {value:.02f} (old)", label=self.label, value=info['zp'])
            self.log.info("[{label}] Firmware  : {value}", label=self.label, value=info['firmware'])
            returnValue(info)
       

    @inlineCallbacks
    def initialActions(self):
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            reactor.callLater(0,reactor.stop)
        elif self.options['zero_point'] is not None:
            try:
                result = yield self.protocol.writeZeroPoint(self.options['zero_point'])
            except Exception as e:
                self.log.error("Timeout when updating Zero Point")
                self.log.failure("{excp}",excp=e)
            else:
                self.log.info("[{label}] Writen ZP : {zp:0.2f}", label=self.label, zp = result['zp'])
            finally:
                reactor.callLater(0,reactor.stop)
       

    def limitedStart(self):
        '''Detects the case where only the Test photometer service is started'''
        if self.reference:
            return False
        return (self.options['dry_run'] or self.options['zero_point'] is not None) 

    
    def buildFactory(self):
        if self.options['model'] == TESSW:
            self.log.debug("Choosing a {model} factory", model=TESSW)
            import zptess.tessw
            factory = zptess.tessw.TESSProtocolFactory(self.label)
        elif self.options['model'] == TESSP:
            self.log.debug("Choosing a {model} factory", model=TESSP)
            import zptess.tessp
            factory = zptess.tessp.TESSProtocolFactory(self.label)
        else:
            self.log.debug("Choosing a {model} factory", model=TAS)
            import zptess.tas
            factory = zptess.tas.TESSProtocolFactory(self.label)
        return factory


    def gotProtocol(self, protocol):
        
        def noop(msg): pass

        self.log.debug("got protocol")
        self.protocol  = protocol
        func = noop if self.limitedStart() else self.onReading
        self.protocol.setReadingCallback(func)
        self.protocol.setContext(self.options['endpoint'])



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
