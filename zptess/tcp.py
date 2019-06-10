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

from zope.interface               import implementer

from twisted.logger               import Logger, LogLevel
from twisted.internet             import reactor, task, defer
from twisted.internet.defer       import inlineCallbacks, returnValue
from twisted.internet.protocol    import ClientFactory
from twisted.protocols.basic      import LineOnlyReceiver
from twisted.application.service  import Service
from twisted.application.internet import ClientService
from twisted.internet.endpoints   import clientFromString

#--------------
# local imports
# -------------

from zptess.service.interfaces import IReloadable
from zptess.logger   import setLogLevel
from zptess.utils    import chop
from zptess.protocol import TESSProtocolFactory


# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='tcp')

# ----------
# Exceptions
# ----------



# -------
# Classes
# -------



# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------


@implementer(IReloadable)
class MyTCPService(ClientService):

    # Service name
    NAME = 'TCP Service'


    def __init__(self, options):

        def backoffPolicy(initialDelay=4.0, maxDelay=60.0, factor=2):
            '''Custom made backoff policy to exit after a number of reconnection attempts'''
            def policy(attempt):
                delay = min(initialDelay * (factor ** attempt), maxDelay)
                if attempt > 3:
                    self.stopService()
                return delay
            return policy

        self.options    = options    
        protocol_level  = 'info' if self.options['log_messages'] else 'warn'
        setLogLevel(namespace='tcp', levelStr=self.options['log_level'])
        setLogLevel(namespace='protoc', levelStr=protocol_level)
        parts = chop(self.options['endpoint'], sep=':')
        self.endpoint = clientFromString(reactor, self.options['endpoint'])
        self.factory   = None
        self.factory   = TESSProtocolFactory()
        self.protocol  = None
        ClientService.__init__(self, self.endpoint, self.factory, retryPolicy=backoffPolicy())


    
    def startService(self):
        '''
        Starts the TCP Service that listens to a TESS through a TCP connection
        By exception, this returns a deferred that is handled by parent service
        '''
        log.info("starting TCP Service")
        ClientService.startService(self)
        d = self.whenConnected()
        d.addCallback(self.gotProtocol)
        log.info("Using TCP endpopint {endpoint}", endpoint=self.endpoint)
        return d

       
    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, options):
        options = options['tcp']
        protocol_level  = 'debug' if options['log_messages'] else 'info'
        setLogLevel(namespace='tcp', levelStr=options['log_level'])
        log.info("new log level is {lvl}", lvl=options['log_level'])
        self.options = options

   

    # --------------
    # Helper methods
    # ---------------

    def setFactory(self, factory):
        self.factory = factory


    def gotProtocol(self, protocol):
        log.debug("TCP: Got Protocol")
        self.protocol  = protocol
        self.protocol.addReadingCallback(self.onReading)


    # ----------------------------
    # Event Handlers from Protocol
    # -----------------------------

    def onReading(self, reading):
        '''
        Pass it onwards when a new reading is made
        '''
        self.parent.onReading(reading, self)
       

    

__all__ = [
    "MyTCPService",
]