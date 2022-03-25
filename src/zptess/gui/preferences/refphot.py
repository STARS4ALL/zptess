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



class DeviceInfoWidget(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Default device Information"), **kwargs)
        self._dev_name = tk.StringVar()
        self._mac   = tk.StringVar()
        self._zp    = tk.DoubleVar()
        self._zp_abs = tk.DoubleVar()
        self._firmware = tk.StringVar()
        self._freq_offset = tk.DoubleVar()
        self.build()

    def build(self):
        
        # widget = ttk.Label(self, text= _("Model"))
        # widget.grid(row=0, column=0, padx=2, pady=0, sticky=tk.W)
        # widget = ttk.Entry(self, width=10, textvariable=self._model)
        # widget.grid(row=0, column=1, padx=2, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Name"))
        widget.grid(row=1, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=16, textvariable=self._dev_name)
        widget.grid(row=1, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("MAC Address"))
        widget.grid(row=2, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=16, textvariable=self._mac)
        widget.grid(row=2, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Firmware"))
        widget.grid(row=3, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=25, textvariable=self._firmware)
        widget.grid(row=3, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Frequency Offset (Hz)"))
        widget.grid(row=4, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._freq_offset)
        widget.grid(row=4, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Zero Point"))
        widget.grid(row=5, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._zp)
        widget.grid(row=5, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Absolute Zero Point"))
        widget.grid(row=6, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._zp_abs)
        widget.grid(row=6, column=1, padx=0, pady=0, sticky=tk.E)

    def set(self, values):
        self._dev_name = values['name']
        self._mac = values['mac']
        self._zp = values['zp']
        self._zp_abs = values['zp_abs']
        self._firmware = values['firmware']
        self._freq_offset = values['freq_offset']

    def get(self):
        return {
            'name': self._dev_name.get(),
            'mac': self._mac.get(),
            'zp': self._zp.get(),
            'zp_abs': self._zp_abs.get(),
            'firmware': self._firmware.get(),
            'freq_offset': self._freq_offset.get()
        }

        

class RefPhotometerFrame(BasePreferencesFrame):

    def __init__(self, parent,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def build(self):
        super().build()
        container = self._container
        self.stats = StatisticsWidget(container)
        self.stats.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.comms = CommunicationsWidget(container)
        self.comms.pack(side=tk.TOP, fill=tk.BOTH, expand=False, ipadx=4, ipady=2, padx=2, pady=2)
        self.devinfo = DeviceInfoWidget(container)
        self.devinfo.pack(side=tk.TOP, fill=tk.BOTH, expand=False, ipadx=2, ipady=4, padx=2, pady=2)
       