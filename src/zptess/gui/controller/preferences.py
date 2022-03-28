# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import sys
import datetime
import gettext

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet import  reactor, defer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import __version__
from zptess.logger  import startLogging, setLogLevel

# ----------------
# Module constants
# ----------------

# Support for internationalization
_ = gettext.gettext

NAMESPACE = 'ctrl'

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

class PreferencesController:

    NAME = NAMESPACE

    # Default subscription QoS

    def __init__(self, parent, view, model):
        self.parent = parent
        self.config = model
        self.view   = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        pub.subscribe(self.onRefConfigLoadReq, 'ref_config_load_req')
        pub.subscribe(self.onTestConfigLoadReq, 'test_config_load_req')
        pub.subscribe(self.onRefConfigSaveReq, 'ref_config_save_req')
        pub.subscribe(self.onTestConfigSaveReq, 'test_config_save_req')

    # --------------
    # Event handlers
    # --------------
    
    @inlineCallbacks
    def onRefConfigLoadReq(self):
        try:
            result1 = yield self.config.loadSection('ref-stats')
            result2 = yield self.config.loadSection('ref-device')
            result = {**result1, **result2}
            self.view.menuBar.preferences.referenceFrame.set(result)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)
     
    @inlineCallbacks
    def onTestConfigLoadReq(self):
        try:
            result1 = yield self.config.loadSection('test-stats')
            result2 = yield self.config.loadSection('test-device')
            result = {**result1, **result2}
            self.view.menuBar.preferences.testFrame.set(result)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)


    @inlineCallbacks
    def onRefConfigSaveReq(self, config):
        try:
            yield self.config.saveSection('ref-stats', config['ref-stats'])
            yield self.config.saveSection('ref-device', config['ref-device'])
            self.view.menuBar.preferences.referenceFrame.saveOkResp()
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    @inlineCallbacks
    def onTestConfigSaveReq(self, config):
        try:
            yield self.config.saveSection('test-stats', config['test-stats'])
            yield self.config.saveSection('test-device', config['test-device'])
            self.view.menuBar.preferences.testFrame.saveOkResp()
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

