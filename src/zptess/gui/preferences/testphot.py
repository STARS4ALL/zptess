# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#################################
## APPLICATION SPECIFIC WIDGETS #
#################################

#--------------------
# System wide imports
# -------------------

import os
import gettext
import tkinter as tk
from   tkinter import ttk

# -------------------
# Third party imports
# -------------------

from pubsub import pub

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

#--------------
# local imports
# -------------

from zptess.utils import chop
from zptess.gui.widgets.contrib import ToolTip, LabelInput
from zptess.gui.preferences.base import BasePreferencesFrame, StatisticsWidget, CommunicationsWidget

# ----------------
# Module constants
# ----------------

# Support for internationalization
_ = gettext.gettext

NAMESPACE = 'gui'

# -----------------------
# Module global variables
# -----------------------


log  = Logger(namespace=NAMESPACE)


class TestPhotometerFrame(BasePreferencesFrame):

    def __init__(self, parent,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def set(self, config):
        self._model.set(config['model'])
        self.stats.set(config)
        self.comms.set(config)

    def build(self):
        super().build()
        container = self._container
        self.stats = StatisticsWidget(container)
        self.stats.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.comms = CommunicationsWidget(container)
        self.comms.pack(side=tk.TOP, fill=tk.BOTH, expand=False, ipadx=4, ipady=2, padx=2, pady=2)

    # ------------
    # Save Control
    # ------------

    # When pressing the save button
    def onSaveButton(self):
        config = dict()
        config['test-stats'] = self.stats.get()
        config['test-device'] = self.comms.get()
        config['test-device']['model'] = self._model.get()
        pub.sendMessage(self._save_event, config=config)
     