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

from zptess import __version__, TESSW, TAS, TESSP
from zptess.gui import DEF_REF_TESSW_ENDPOINT, DEF_TEST_TESSW_ENDPOINT, DEF_TEST_TESSP_ENDPOINT, DEF_TEST_TAS_ENDPOINT
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
        self.config = model.config
        self.view   = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        pub.subscribe(self.onRefConfigLoadReq, 'ref_config_load_req')
        pub.subscribe(self.onTestConfigLoadReq, 'test_config_load_req')
        pub.subscribe(self.onRefConfigSaveReq, 'ref_config_save_req')
        pub.subscribe(self.onTestConfigSaveReq, 'test_config_save_req')
        pub.subscribe(self.onRefModelChangeReq, 'ref_model_change_req')
        pub.subscribe(self.onTestModelChangeReq, 'test_model_change_req')

    # --------------
    # Event handlers
    # --------------

    def onRefModelChangeReq(self, model):
        pass    # By design decission, we do not force values here.

    def onTestModelChangeReq(self, model):
        '''Present some reasonable defaults that can be changed and stored as preferfences'''
        try:
            log.info("Test photometer model changed to {model}",model=model)
            if model == TAS:
                value = {'endpoint': DEF_TEST_TAS_ENDPOINT, 'old_proto': 0}
            elif model == TESSP:
                value = {'endpoint': DEF_TEST_TESSP_ENDPOINT, 'old_proto': 0}
            else:
                value = {'endpoint': DEF_TEST_TESSW_ENDPOINT, 'old_proto': 0}
            self.view.menuBar.preferences.testFrame.comms.set(value)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)
    
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
            yield self.view.messageBoxWarn(
                title = _("ZPTESS"),
                message = _("Preferences changed.\nMust close the whole application!")
            )
            pub.sendMessage('quit', exit_code = 0)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

