# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor, defer
from twisted.internet.address     import IPv4Address
from twisted.internet.protocol    import DatagramProtocol, ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.internet.interfaces  import IPushProducer, IConsumer
from zope.interface               import implementer

#--------------
# local imports
# -------------

from zptess.logger       import setLogLevel as SetLogLevel
from zptess.photometer.protocol.interface import IPayloadDecoder, IPhotometerControl
from zptess.photometer.protocol.payload   import OldPayload, JSONPayload
from zptess.photometer.protocol.photinfo  import HTMLPhotometer, DBasePhotometer

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------


# ----------------
# Module functions
# ----------------



# ----------
# Exceptions
# ----------


# -------
# Classes
# -------

class TESSProtocolFactory(ClientFactory):

    def __init__(self, model, log, namespace, role, config_dao, old_payload, transport_method, tcp_deferred = None):
        self.log_msg = Logger(namespace=namespace)
        self.log     = log
        self.model = model
        self.old_payload = old_payload
        self.transport_method = transport_method
        self.config_dao = config_dao
        self.section = "ref-device" if role == 'ref' else 'test-device'
        self.tcp_deferred = tcp_deferred # Handles notification of client TCP connections

    def startedConnecting(self, connector):
        self.log.debug('Factory: Started to connect.')

    def clientConnectionLost(self, connector, reason):
        self.log.debug('Factory: Lost connection. Reason: {reason}', reason=reason)

    def clientConnectionFailed(self, connector, reason):
        self.log.debug('Factory: Connection failed. Reason: {reason}', reason=reason)

    def buildProtocol(self, addr):
        if isinstance(addr, IPv4Address):
            addr = addr.host

        if self.transport_method == 'serial' and self.section == 'ref-device':
            photinfo_obj = DBasePhotometer(
                config_dao = self.config_dao, 
                section    = self.section, 
                label      = self.model,
                log        = self.log,
                log_msg    = self.log_msg,
            )
        else:
            photinfo_obj = HTMLPhotometer(
                addr    = addr, 
                label   = self.model,
                log     = self.log,
                log_msg = self.log_msg
            )
        if self.transport_method == 'udp':
            payload_obj = JSONPayload(
                label   = self.model, 
                log     = self.log,
                log_msg = self.log_msg,
            )
            return TESSUDPProtocol(self, payload_obj, photinfo_obj, self.model)
        if self.old_payload:
             payload_obj = OldPayload(
                label   = self.model, 
                log     = self.log,
                log_msg = self.log_msg)
        else:
            payload_obj = JSONPayload(
                label   = self.model, 
                log     = self.log,
                log_msg = self.log_msg
            )
        return TESSStreamProtocol(
            factory      = self, 
            payload_obj  = payload_obj, 
            photinfo_obj = photinfo_obj, 
            label        = self.model
        )



@implementer(IPushProducer, IPhotometerControl)
class TESSStreamProtocol(LineOnlyReceiver):

    # So that we can patch it in tests with Clock.callLater ...
    callLater = reactor.callLater
    conflicting_firmware = ('Nov 25 2021 v 3.2',)
  
    def __init__(self, factory, payload_obj, photinfo_obj, label):
        '''Sets the delimiter to the closihg parenthesis'''
        # LineOnlyReceiver.delimiter = b'\n'
        self._consumer = None
        self._paused   = True
        self._stopped  = False
        self._payload  = payload_obj
        self._phot     = photinfo_obj
        self.factory   = factory
        self.log       = factory.log
        self.label     = label
        self.log.info("{label:6s} Created protocol {who}", label=label, who=self.__class__.__name__)

    # -------------------------
    # Twisted Line Receiver API
    # -------------------------

    def connectionMade(self):
        self.log.debug("{who} connectionMade()", who=self.__class__.__name__)
        if self.factory.tcp_deferred:
            self.factory.tcp_deferred.callback(self)
            self.factory.tcp_deferred = None


    def lineReceived(self, line):
        now = datetime.datetime.now(datetime.timezone.utc)
        if self._paused or self._stopped:
            self.log.warn("Producer either paused({p}) or stopped({s})", p=self._paused, s=self._stopped)
            return
        self.log.debug("{who} lineReceived()",who=self.__class__.__name__)
        line = line.decode('latin_1')  # from 'bytes' to 'str'
        handled = self._phot.onPhotommeterInfoResponse(line, now)
        if not handled:
            handled, reading = self._payload.onDataReceived(line, now)
            if handled:
                self._consumer.write(reading)

    
    # -----------------------
    # IPushProducer interface
    # -----------------------

    def stopProducing(self):
        """
        Stop producing data.
        """
        self._stopped     = False


    def pauseProducing(self):
        """
        Pause producing data.
        """
        self._paused    = True


    def resumeProducing(self):
        """
        Resume producing data.
        """
        self._paused    = False


    def registerConsumer(self, consumer):
        '''
        This is not really part of the IPushProducer interface
        '''
        self._consumer = IConsumer(consumer)


    # ----------------------------
    # IPhotometerControl interface
    # ----------------------------

   
    def writeZeroPoint(self, zero_point, timeout=5):
        '''
        Writes Zero Point to the device. 
        Asynchronous operation, returns a Deferred
        '''
        return self._phot.writeZeroPoint(zero_point, timeout)


    def getPhotometerInfo(self, timeout=5):
        '''
        Reads Info from the device. 
        Asynchronous operation, returns a Deferred
        '''
        return self._phot.getPhotometerInfo(timeout)


    def onPhotommeterInfoResponse(self, line, tstamp):
        raise NotImplementedError("Doesn't make sense tho call this here")



@implementer(IPushProducer)
class TESSUDPProtocol(DatagramProtocol):

    # So that we can patch it in tests with Clock.callLater ...
    callLater = reactor.callLater
  
    def __init__(self, factory, payload_obj, photinfo_obj, label):
        self._consumer = None
        self._paused   = True
        self._stopped  = False
        self._payload  = payload_obj
        self._phot     = photinfo_obj
        self.label     = label
        self.factory   = factory
        self.log       = factory.log
        self.log.info("{label:6s} Created protocol {who}", label=label, who=self.__class__.__name__)


    def datagramReceived(self, data, addr):
        now = datetime.datetime.now(datetime.timezone.utc)
        if self._paused or self._stopped:
            self.log.warn("Producer either paused({p}) or stopped({s})", p=self._paused, s=self._stopped)
            return
        self.log.debug("{who} datagramReceived()",who=self.__class__.__name__)
        data = data.decode('latin_1')  # from 'bytes' to 'str'
        handled = self._phot.onPhotommeterInfoResponse(data, now)
        if not handled:
            handled, reading = self._payload.onDataReceived(data, now)
            if handled:
                self._consumer.write(reading)
    
    # -----------------------
    # IPushProducer interface
    # -----------------------

    def stopProducing(self):
        """
        Stop producing data.
        """
        self._stopped     = False


    def pauseProducing(self):
        """
        Pause producing data.
        """
        self._paused    = True


    def resumeProducing(self):
        """
        Resume producing data.
        """
        self._paused    = False


    def registerConsumer(self, consumer):
        '''
        This is not really part of the IPushProducer interface
        '''
        self._consumer = IConsumer(consumer)

    #----------------------------
    # IPhotometerControl interface
    # ----------------------------

    def writeZeroPoint(self, zero_point, timeout=5):
        '''
        Writes Zero Point to the device. 
        Asynchronous operation, returns a Deferred
        '''
        return self._phot.writeZeroPoint(zero_point, timeout)


    def getPhotometerInfo(self, timeout=5):
        '''
        Reads Info from the device. 
        Asynchronous operation, returns a Deferred
        '''
        return self._phot.getPhotometerInfo(timeout)


    def onPhotommeterInfoResponse(self, line, tstamp):
        raise NotImplementedError("Doesn't make sense tho call this here")

    

  

#---------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------


__all__ = [
    "TESSProtocolFactory",
]
