# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import sys

# -------------------
# Third party imports
# -------------------

from pubsub import pub

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet import  tksupport, reactor, defer, task
from twisted.application.service import Service
from twisted.internet.defer import inlineCallbacks



#--------------
# local imports
# -------------

from zptess import set_status_code
from zptess.logger  import setLogLevel
from zptess.dbase.service   import DatabaseService
from zptess.gui.application import Application
from zptess.gui.controller.application import ApplicationController


# ----------------
# Module constants
# ----------------

NAMESPACE = 'gui'

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------




# --------------
# Module Classes
# --------------

class GraphicalService(Service):

    NAME = 'Graphical Service'

    # Default subscription QoS
    

    def __init__(self, **kargs):
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        #self.task    = task.LoopingCall(self.heartBeat)
        pub.subscribe(self.quit,  'quit')

    # -----------
    # Service API
    # -----------
    
    def startService(self):
        log.info('Starting {name}',name=self.name)
        
        self.application = Application()
        self.dbaseService = self.parent.getServiceNamed(DatabaseService.NAME)
        self.controllers = (
            # ApplicationController(
            #     parent  = self, 
            #     view    = self.application, 
            #     model   = self.dbaseService.dao,
            # ),
            
        )
        # Dirty monkey patching
        

        tksupport.install(self.application)
        #self.task.start(3, now=False) # call every T seconds
        # Start application controller 
        pub.sendMessage('bootstrap_req')

    def stopService(self):
        log.info('Stopping Graphical User Interface Service')
        #self.task.stop()
        return super().stopService()

    def quit(self, exit_code):
        set_status_code(exit_code)
        reactor.callLater(0, self.parent.stopService)