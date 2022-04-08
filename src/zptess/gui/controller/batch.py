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
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import __version__, TSTAMP_SESSION_FMT
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

def get_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)

# --------------
# Module Classes
# --------------

class BatchController:

    NAME = NAMESPACE

    def __init__(self, parent, view, model):
        self.parent = parent
        self.model = model
        self.view = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        self.start()

    def start(self):
        # events coming from GUI
        pub.subscribe(self.onOpenBatchReq, 'open_batch_req')
        pub.subscribe(self.onCloseBatchReq, 'close_batch_req')
        pub.subscribe(self.onPurgeBatchReq, 'purge_batch_req')
        pub.subscribe(self.onExportBatchReq, 'export_batch_req')
      
    @inlineCallbacks
    def onOpenBatchReq(self):
        try:
            log.info("onOpenBatchReq()")
            isOpen = yield self.model.batch.isOpen()
            if isOpen:
                self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("Batch already open")
                )
            else:
                tstamp = get_timestamp()
                yield self.model.batch.open(tstamp)
                result = yield self.model.batch.latest()
                self.view.statusBar.set(result)   
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)
    
    @inlineCallbacks
    def onCloseBatchReq(self):
        try:
            log.info("onCloseBatchReq()")
            isOpen = yield self.model.batch.isOpen()
            if not isOpen:
                self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("No open batch to close")
                )
            else:
                result = yield self.model.batch.latest()
                begin_tstamp = result['begin_tstamp']
                end_tstamp = get_timestamp()
                N = yield self.model.summary.numSessions(begin_tstamp, end_tstamp)
                yield self.model.batch.close(end_tstamp, N)
                result = yield self.model.batch.latest()
                self.view.statusBar.set(result)   
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    @inlineCallbacks
    def onPurgeBatchReq(self):
        try:
            log.info("onPurgeBatchReq()")
            yield  self.model.batch.purge()
            result = yield self.model.batch.latest()
            self.view.statusBar.set(result)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    def onExportBatchReq(self):
        try:
            log.info("onOpenBatchReq()")
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)


