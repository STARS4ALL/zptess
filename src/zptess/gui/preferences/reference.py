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





class ReferenceFrame(BasePreferencesFrame):

    def __init__(self, parent,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def build(self):
        super().build()
        container = self._container
        self.stats = StatisticsWidget(container)
        self.stats.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.comms = CommunicationsWidget(container)
        self.comms.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)

      

       