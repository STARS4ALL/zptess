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
from twisted.internet.defer       import inlineCallbacks, DeferredQueue, TimeoutError as DeferredTimeoutError
from twisted.internet.error       import ConnectError
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

from zptess          import TESSW, TESSP, TAS, REF, TEST
from zptess.logger   import setLogLevel
from zptess.utils    import chop

from zptess.photometer.protocol.tessw import TESSUDPProtocol

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
class Deduplicater:
    '''Removes duplicates readings in TESS JSON payloads'''

    def __init__(self, role, log):
        self._producer = None
        self._role     = role
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
            pub.sendMessage('phot_sample', role=self._role, sample=data)
        elif cur_seq is None:
            pub.sendMessage('phot_sample', role=self._role, sample=data) # old prtocol, not JSON protocol


# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


class PhotometerService(ClientService):

    NAME = "Photometer Service"

    def __init__(self, options, isRef):
        self.options = options
        self.isRef   = isRef  # Flag, is this instance for the reference photometer
        if isRef: 
            self.role = 'ref'
            self.label = REF.lower()
            self.msgspace = REF.upper()
        else:
           
            self.role = 'test'
            self.label = TEST.lower()
            self.msgspace = REF.upper()
        self.log = Logger(namespace=self.label)
        proto, addr, port = chop(self.options['endpoint'], sep=':')
        self.factory   = self.buildFactory(options['old_proto'], proto)
        if proto == 'tcp':
            endpoint = clientFromString(reactor, options['endpoint'])
            ClientService.__init__(self, endpoint, self.factory,
                 retryPolicy=backoffPolicy(initialDelay=0.5, factor=3.0))
    
    @inlineCallbacks
    def startService(self):
        '''
        Starts the photometer service listens to a TESS
        Although it is technically a synchronous operation, it works well
        with inline callbacks
        '''
        self.log.info("Starting {name}", name=self.name)
        setLogLevel(namespace=self.msgspace, levelStr=self.options['log_messages'])
        setLogLevel(namespace=self.label,    levelStr=self.options['log_level'])
        self.protocol  = None
        self.info      = None # Photometer info
        self.deduplicater = Deduplicater(self.role, self.log)
        pub.subscribe(self.onUpdateZeroPoint, 'update_zero_point')
        # Async part form here ...
        try:
            self.info = None
            yield self.connect()
            self.info = yield self.getPhotometerInfo()
        except DeferredTimeoutError as e:
            self.log.critical("{excp}",excp=e)
            pub.sendMessage('photometer_off', role=self.role)
            return(None)
        except ConnectError as e:
            self.log.critical("{excp}",excp=e)
            pub.sendMessage('photometer_off', role=self.role)
            return(None)
        except Exception as e:
            self.log.failure("{excp}",excp=e)
            pub.sendMessage('photometer_off', role=self.role)
            return(None)
        if self.info is None:
            pub.sendMessage('photometer_off', role=self.role)
            return(None)
        pub.sendMessage('phot_info', role=self.role, info=self.info)
        if self.isRef:
           return(None)
        # Now this is for the test photometer only
        if self.options['dry_run']:
            self.log.info('Dry run. Will stop here ...') 
            pub.sendMessage('photometer_end')
            return(None)
        if self.options['write_zero_point'] is not None:
            result = yield self.protocol.writeZeroPoint(self.options['write_zero_point'])
            pub.sendMessage('photometer_end')
        return(None)



    def stopService(self):
        self.log.info("Stopping {name}", name=self.name)
        if self.protocol:
            self.protocol.stopProducing()
            if self.protocol.transport:
                self.log.info("Closing transport {e}", e=self.options['endpoint'])
                self.protocol.transport.loseConnection()
            self.protocol = None
            pub.unsubscribe(self.onUpdateZeroPoint, 'update_zero_point')
        return defer.succeed(None)
            
    # --------------
    # Photometer API 
    # --------------

    def onUpdateZeroPoint(self, zero_point):
        if not self.isRef:
            reactor.callLater(0, self.writeZeroPoint, zero_point)


    @inlineCallbacks
    def writeZeroPoint(self, zero_point):
        '''Writes Zero Point to the device.'''
        self.log.info("[{label}] Updating ZP : {zp:0.2f}", label=self.label, zp = zero_point)
        try:
            yield self.protocol.writeZeroPoint(zero_point)
        except DeferredTimeoutError as e:
            self.log.error("Timeout when reading photometer info ({e})",e=e)
        except Exception as e:
            self.log.failure("{e}",e=e)
        else:
            self.log.info("[{label}] Writen ZP : {zp:0.2f}", label=self.label, zp = zero_point)

    # --------------
    # Helper methods
    # ---------------

    @inlineCallbacks
    def connect(self):
        proto, addr, port = chop(self.options['endpoint'], sep=':')
        if proto == 'serial':
            protocol = self.factory.buildProtocol(addr)
            serport  = SerialPort(protocol, addr, reactor, baudrate=int(port))
            self.gotProtocol(protocol)
            self.log.info("Using serial port {tty} at {baud} bps", tty=addr, baud=port)
        elif proto == 'tcp':
            ClientService.startService(self)
            protocol = yield self.whenConnected(failAfterFailures=1)
            self.gotProtocol(protocol)
            self.log.info("Using TCP endpoint {endpoint}", endpoint=self.options['endpoint'])
        else:
            protocol = self.factory.buildProtocol(addr)
            reactor.listenUDP(int(port), protocol)
            self.gotProtocol(protocol)
            self.log.info("listening on UCP endpoint {endpoint}", endpoint=self.options['endpoint'])


    @inlineCallbacks
    def getPhotometerInfo(self):
        info = yield self.protocol.getPhotometerInfo()
        if self.isRef:
            info['zp_abs'] = float(self.options['zp_abs'])
        info['model'] = self.options['model']
        info['label'] = self.label
        info['role']  = self.role
        return(info)
       

    def isLimitedStart(self):
        '''Detects the case where only the Test photometer service is started'''
        if self.isRef:
            return False
        return (self.options['dry_run'] or self.options['write_zero_point'] is not None) 

    
    def buildFactory(self, old_payload, proto):
        if self.options['model'] == TESSW:
            import zptess.photometer.protocol.tessw
            factory = zptess.photometer.protocol.tessw.TESSProtocolFactory(
                model       = TESSW,
                log         = self.log,
                namespace   = self.msgspace, 
                role        = self.role, 
                config_dao  = self.options['config_dao'],  
                old_payload = old_payload, 
                transport_method = proto, 
            )
        elif self.options['model'] == TESSP:
            import zptess.photometer.protocol.tessp
            factory = zptess.photometer.protocol.tessp.TESSProtocolFactory(
                model     = TESSP, 
                log       = self.log,
                namespace = self.msgspace,
            )
        else:
            import zptess.photometer.protocol.tas
            factory = zptess.photometer.protocol.tas.TESSProtocolFactory(
                model     = TAS, 
                log       = self.log,
                namespace = self.msgspace,
            )
        return factory


    def gotProtocol(self, protocol):
        self.log.debug("got protocol")
        self.deduplicater.registerProducer(protocol, True)
        if self.isLimitedStart():
            protocol.stopProducing()    # We don need to feed messages to the buffer
        self.protocol  = protocol


__all__ = [
    "PhotometerService",
]
