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

from collections import deque

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
from twisted.internet.interfaces  import IPushProducer, IPullProducer, IConsumer
from zope.interface               import implementer

#--------------
# local imports
# -------------

from zptess          import STATS_SERVICE, TESSW, TESSP, TAS, VERSION_STRING
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

@implementer(IConsumer)
class CircularBuffer(object):

    def __init__(self, size):
        self._buffer = deque([], size)
        self._producer = None
        self._push     = None

    # -------------------
    # IConsumer interface
    # -------------------

    def registerProducer(self, producer, streaming):
        if streaming:
            self._producer = IPushProducer(producer)
        else:
            raise ValueError("IPullProducer not supported")
        producer.registerConsumer(self) # So the producer knows who to talk to
        producer.resumeProducing()

    def unregisterProducer(self):
        self._producer.stopProducing()
        self._producer = None

    def write(self, data):
        self._buffer.append(data)

    # -------------------
    # buffer API
    # -------------------

    def getBuffer(self):
        return self._buffer

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
        self.buffer    = CircularBuffer(options['size'])
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
        yield self.connect()
        self.info = yield self.getInfo()
        if not self.reference:
            yield self.initialActions()


    def stopService(self):
        self.log.info("stopping {name} service", name=self.name)
        try:
            reactor.callLater(0, reactor.stop)
        except Exception as e:
            log.error("could not stop the reactor")
        return defer.succeed(None)

            
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
                yield self.stopService()
            else:
                self.gotProtocol(self.protocol)
                self.log.info("Using serial port {tty} at {baud} bps", tty=endpoint[0], baud=endpoint[1])
        else:
            ClientService.startService(self)
            try:
                protocol = yield self.whenConnected(failAfterFailures=1)
            except Exception as e:
                self.log.error("{excp}",excp=e)
                yield self.stopService()
            else:
                self.gotProtocol(protocol)
                self.log.info("Using TCP endpoint {endpoint}", endpoint=self.options['endpoint'])


    @inlineCallbacks
    def getInfo(self):
        try:
            info = yield self.protocol.readPhotometerInfo()
        except Exception as e:
            self.log.error("Timeout when reading photometer info")
            info = self.fixIt()
            if info is None:
                yield self.stopService()
            else:
                returnValue(info)
        else:
            info['model'] = self.options['model']
            info['label'] = self.label
            self.log.info("[{label}] Model     : {value}", label=self.label, value=info['model'])
            self.log.info("[{label}] Name      : {value}", label=self.label, value=info['name'])
            self.log.info("[{label}] MAC       : {value}", label=self.label, value=info['mac'])
            self.log.info("[{label}] Zero Point: {value:.02f} (old)", label=self.label, value=info['zp'])
            self.log.info("[{label}] Firmware  : {value}", label=self.label, value=info['firmware'])
            returnValue(info)
       
    def fixIt(self):
        parts = chop(self.options['endpoint'], sep=':')
        if self.reference and (self.options['model'] == TESSW) and parts[0] == 'serial':
            info = {
                'model'    : TESSW,
                'label'    : self.label,
                'name'     : self.options['name'],
                'mac'      : self.options['mac'],
                'zp'       : 20.50,
                'firmware' : "",
            }
            self.log.error("Fixed photometer info with defaults {info}", info=info)
            return info
        else:
            return None

    @inlineCallbacks
    def initialActions(self):
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            yield self.stopService()
        elif self.options['zero_point'] is not None:
            try:
                result = yield self.protocol.writeZeroPoint(self.options['zero_point'])
            except Exception as e:
                self.log.error("Timeout when updating Zero Point")
                self.log.failure("{excp}",excp=e)
            else:
                self.log.info("[{label}] Writen ZP : {zp:0.2f}", label=self.label, zp = result['zp'])
            finally:
                yield self.stopService()
       

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
        self.log.debug("got protocol")
        protocol.setContext(self.options['endpoint'])
        self.buffer.registerProducer(protocol, True)
        if self.limitedStart():
            protocol.stopProducing()    # We don need to feed messages to the buffer
        self.protocol  = protocol


__all__ = [
    "PhotometerService",
]
