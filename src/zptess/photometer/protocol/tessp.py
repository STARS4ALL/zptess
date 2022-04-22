# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import re
import datetime


# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet.protocol    import ClientFactory

#--------------
# local imports
# -------------

from zptess.photometer.protocol.tessbase   import TESSBaseProtocol, TESSBaseProtocolFactory

#--------------------
# System wide imports
# -------------------


# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet             import reactor

from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.internet.interfaces  import IPushProducer, IConsumer
from zope.interface               import implementer

#--------------
# local imports
# -------------

from zptess.logger       import setLogLevel as SetLogLevel
from zptess.photometer.protocol.interface import IPayloadDecoder, IPhotometerControl
from zptess.photometer.protocol.payload   import OldPayload, JSONPayload
from zptess.photometer.protocol.photinfo  import CLIPhotometer
from zptess.photometer.protocol.tessw     import TESSStreamProtocol

# -------
# Classes
# -------

class TESSProtocolFactory(ClientFactory):

    def __init__(self, model, log, namespace):
        self.model   = model
        self.log     = log
        self.log_msg = Logger(namespace=namespace)
        self.tcp_deferred = None

    def startedConnecting(self, connector):
        self.log.debug('Factory: Started to connect.')

    def clientConnectionLost(self, connector, reason):
        self.log.debug('Factory: Lost connection. Reason: {reason}', reason=reason)

    def clientConnectionFailed(self, connector, reason):
        self.log.debug('Factory: Connection failed. Reason: {reason}', reason=reason)

    def buildProtocol(self, addr):

        photinfo_obj = TESSPPhotometerInfo(
            label   = self.model,
            log     = self.log, 
            log_msg = self.log_msg
        )
    
        payload_obj = JSONPayload(
            label   = self.model, 
            log     = self.log,
            log_msg = self.log_msg
        )
        protocol     = TESSPStreamProtocol(
            factory      = self, 
            payload_obj  = payload_obj, 
            photinfo_obj = photinfo_obj, 
            label        = self.model
        )
        photinfo_obj.setParent(protocol)
        return protocol


class TESSPPhotometerInfo(CLIPhotometer):

    def __init__(self, label, log, log_msg):
        super().__init__(label, log, log_msg)
        self.SOLICITED_RESPONSES.append({
            'name'    : 'name',
            'pattern' : r'^TSP SN: (TSP\w{3})',       
        })
        self.SOLICITED_PATTERNS = [ re.compile(sr['pattern']) for sr in self.SOLICITED_RESPONSES ]


class TESSPStreamProtocol(TESSStreamProtocol):
    '''Identical implementation to TESSStreamProtocol'''
    pass



__all__ = [
    "TESSProtocolFactory",
]
