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
from twisted.internet.serialport  import SerialPort
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


# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='serial')

# ----------
# Exceptions
# ----------




# -------
# Classes
# -------



# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------



@implementer(IReloadable)
class SerialService(Service):

    # Service name
    NAME = 'Serial Service'


    def __init__(self, options):
        Service.__init__(self)
        self.options    = options    
        protocol_level  = 'info' if self.options['log_messages'] else 'warn'
        setLogLevel(namespace='protoc', levelStr=protocol_level)
        setLogLevel(namespace='serial', levelStr=self.options['log_level'])
        self.serport   = None
        self.protocol  = None
        self.endpoint  = None
        self.factory   = None
    
    def startService(self):
        '''
        Starts the Serial Service that listens to a TESS
        By exception, this returns a deferred that is handled by emaservice
        '''
        log.info("starting Serial Service")
        parts = chop(self.options['endpoint'], sep=':')
        if parts[0] == 'serial':
            self.endpoint = parts[1:]
            if self.serport is None:
                self.protocol = self.factory.buildProtocol(0)
                self.serport  = SerialPort(self.protocol, self.endpoint[0], reactor, baudrate=self.endpoint[1])
            self.gotProtocol(self.protocol)
            log.info("Using serial port {tty} at {baud} bps", tty=self.endpoint[0], baud=self.endpoint[1])
        else:
            raise 
            

    #---------------------
    # Extended Service API
    # --------------------

    def reloadService(self, options):
        options = options['serial']
        protocol_level  = 'debug' if options['log_messages'] else 'info'
        setLogLevel(namespace='serial', levelStr=options['log_level'])
        setLogLevel(namespace='protoc', levelStr=protocol_level)
        log.info("new log level is {lvl}", lvl=options['log_level'])
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
        log.info("Serial port statistics: Total = {tot:03d}, Unknown = {nunk:03d}", 
            tot=total, nunk=nunknown)
        log.info("Serial link quality = {q:0.4f}%", q=quality)
        self.protocol.resetStats()


    # --------------
    # Helper methods
    # ---------------

    def setFactory(self, factory):
        self.factory = factory


    def gotProtocol(self, protocol):
        log.debug("Serial: Got Protocol")
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
    "EMATimeoutError",
    "EMAProtocol",
    "EMAProtocolFactory",
    "SerialService",
]