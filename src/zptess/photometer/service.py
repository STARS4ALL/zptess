# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sys

from collections import deque

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, DeferredQueue
from twisted.internet.serialport  import SerialPort
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.application.service  import Service
from twisted.application.internet import ClientService, backoffPolicy
from twisted.internet.endpoints   import clientFromString
from twisted.internet.interfaces  import IPushProducer, IPullProducer, IConsumer
from zope.interface               import implementer, implements

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess          import TESSW, TESSP, TAS
from zptess.logger   import setLogLevel
from zptess.utils    import chop
from zptess.dbase.service import DatabaseService

# -----------------------
# Module global variables
# -----------------------

# ----------------
# Module constants
# ----------------

# ----------
# Exceptions
# ----------



# -------
# Classes
# -------

@implementer(IConsumer)
class CircularBuffer(object):

    def __init__(self, size, log):
        self._buffer   = deque([], size)
        self._buffer2  = DeferredQueue(backlog=1) # for database
        self._producer = None
        self.log       = log

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
        self._buffer.append(data)       # for in-memory stats calculation
        self._buffer2.put(data)         # For database writes

    # -------------------
    # buffer API
    # -------------------

    def getBuffer(self):
        return self._buffer

    def getBuffer2(self):
        return self._buffer2

@implementer(IConsumer, IPushProducer)
class Deduplicater:
    '''Removes duplicates readings in TESS JSON payloads'''
    #implements(IConsumer, IPushProducer)

    def __init__(self, log):
        self._producer = None
        self._consumer = None
        self.log       = log
        self._prev_seq = None

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
        cur_seq = data.get('udp', None)
        if cur_seq is not None and cur_seq != self._prev_seq:
            self._prev_seq = cur_seq
            self._consumer.write(data)


    # -----------------------
    # IPushProducer interface
    # -----------------------

    def pauseProducing(self):
       self._producer.pauseProducing() 

    def resumeProducing(self):
       self._producer.resumeProducing()

    def stopProducing(self):
       self._producer.stopProducing()

    def registerConsumer(self, consumer):
        '''
        This is not really part of the IPushProducer interface
        '''
        self._consumer = IConsumer(consumer)




# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class PhotometerService(ClientService):

    NAME = "Photometer Service"

    def __init__(self, options, reference):

        self.options   = options
        if reference:
            self.namespace = 'ref.'
            self.role = 'ref'
            self.NAME = "Ref. Photometer"
        else:
            self.NAME = "Test Photometer"
            self.namespace = 'test'
            self.role = 'test'

        self.label     = self.namespace.upper()
        setLogLevel(namespace=self.label,     levelStr=options['log_messages'])
        setLogLevel(namespace=self.namespace, levelStr=options['log_level'])
        self.log = Logger(namespace=self.namespace)
        self.reference = reference  # Flag, is this instance for the reference photometer
        self.old_protocol = options['old_protocol']
        self.factory   = self.buildFactory()
        self.protocol  = None
        self.info      = None # Photometer info
        self.buffer    = CircularBuffer(options['size'], self.log)
        self.deduplicater = Deduplicater(self.log)
        pub.subscribe(self.onUpdateZeroPoint, 'update_zero_point')
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
        pub.sendMessage('photometer_info', role=self.role, circ_buffer=self.buffer, info=self.info)
        if self.reference:
           return(None)

        # Now this is for the test photometer only
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            yield self.parent.stopService()
        elif self.info is None:
            yield self.parent.stopService()
        elif self.options['write_zero_point'] is not None:
            try:
                result = yield self.protocol.writeZeroPoint(self.options['write_zero_point'])
            except Exception as e:
                self.log.error("Timeout when updating Zero Point")
                self.log.failure("{excp}",excp=e)
            else:
                self.log.info("[{label}] Writen ZP : {zp:0.2f}", label=self.label, zp = result['zp'])
            finally:
                yield self.parent.stopService()


    def stopService(self):
        self.log.info("stopping {name} service", name=self.name)
        if self.protocol:
            self.protocol.stopProducing()
            if self.protocol.transport:
                self.log.info("Closing transport {e}", e=self.options['endpoint'])
                self.protocol.transport.loseConnection()
            self.protocol = None
        return defer.succeed(None)
            
    # --------------
    # Photometer API 
    # --------------

    def onUpdateZeroPoint(self, zero_point):
        if not self.reference:
            reactor.callLater(0, self.writeZeroPoint, zero_point)

    @inlineCallbacks
    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device.'''
        self.log.info("[{label}] Updating ZP : {zp:0.2f}", label=self.label, zp = zero_point)
        try:
            yield self.protocol.writeZeroPoint(zero_point)
        except Exception as e:
            self.log.error("Timeout when updating photometer zero point")


    def getPhotometerInfo(self):
        if self.protocol is None:
            self.log.warn("Requested photometer info but no protocol yet!")
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
                serport  = SerialPort(self.protocol, endpoint[0], reactor, baudrate=endpoint[1])
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
            info = yield self.fixIt()
            return(info)   # May be None
        else:
            if self.reference:
                serv =  self.parent.getServiceNamed(DatabaseService.NAME)
                info['zp_abs'] = yield serv.loadAbsoluteZeroPoint()
            info['model'] = self.options['model']
            info['label'] = self.label
            info['role']  = self.role
            self.log.info("[{label}] Role      : {value}", label=self.label, value=info['role'])
            self.log.info("[{label}] Model     : {value}", label=self.label, value=info['model'])
            self.log.info("[{label}] Name      : {value}", label=self.label, value=info['name'])
            self.log.info("[{label}] MAC       : {value}", label=self.label, value=info['mac'])
            self.log.info("[{label}] Zero Point: {value:.02f} (old)", label=self.label, value=info['zp'])
            self.log.info("[{label}] Firmware  : {value}", label=self.label, value=info['firmware'])
            return(info)
       
    @inlineCallbacks
    def fixIt(self):
        parts = chop(self.options['endpoint'], sep=':')
        if self.reference and (self.options['model'] == TESSW) and parts[0] == 'serial':
            serv =  self.parent.getServiceNamed(DatabaseService.NAME)
            info = yield serv.loadRefPhotDefaults()
            info['label']  = self.label
            info['role']   = self.role
            info['zp']     = float(info['zp'])
            info['zp_abs'] = float(info['zp_abs'])
            self.log.warn("Fixed photometer info with defaults")
            self.log.warn("[{label}] Role      : {value}", label=self.label, value=info['role'])
            self.log.warn("[{label}] Model     : {value}", label=self.label, value=info['model'])
            self.log.warn("[{label}] Name      : {value}", label=self.label, value=info['name'])
            self.log.warn("[{label}] MAC       : {value}", label=self.label, value=info['mac'])
            self.log.warn("[{label}] Zero Point: {value:.02f} (old)", label=self.label, value=info['zp'])
            self.log.warn("[{label}] Firmware  : {value}", label=self.label, value=info['firmware'])
            return(info)
        else:
            return(None)
       

    def limitedStart(self):
        '''Detects the case where only the Test photometer service is started'''
        if self.reference:
            return False
        return (self.options['dry_run'] or self.options['write_zero_point'] is not None) 

    
    def buildFactory(self):
        if self.options['model'] == TESSW:
            self.log.debug("Choosing a {model} factory", model=TESSW)
            import zptess.photometer.tessw
            factory = zptess.photometer.tessw.TESSProtocolFactory(self.label, self.old_protocol)
        elif self.options['model'] == TESSP:
            self.log.debug("Choosing a {model} factory", model=TESSP)
            import zptess.photometer.tessp
            factory = zptess.photometer.tessp.TESSProtocolFactory(self.label, self.old_protocol)
        else:
            self.log.debug("Choosing a {model} factory", model=TAS)
            import zptess.photometer.tas
            factory = zptess.photometer.tas.TESSProtocolFactory(self.label, self.old_protocol)
        return factory


    def gotProtocol(self, protocol):
        self.log.debug("got protocol")
        protocol.setContext(self.options['endpoint'])
        # Buld the chain of producers/consumers
        self.deduplicater.registerProducer(protocol, True)
        self.buffer.registerProducer(self.deduplicater, True)
        if self.limitedStart():
            protocol.stopProducing()    # We don need to feed messages to the buffer
        self.protocol  = protocol


__all__ = [
    "PhotometerService",
]
