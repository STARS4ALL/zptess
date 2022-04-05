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
from zptess.gui.widgets.validators import float_validator, ip_validator, mac_validator

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

        vcmd  = (self.register(mac_validator), '%P')
        ivcmd = (self.register(self.invalid_mac),)
        widget = ttk.Label(self, text= _("MAC Address"))
        widget.grid(row=2, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=16, textvariable=self._mac, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=2, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Firmware"))
        widget.grid(row=3, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=25, textvariable=self._firmware)
        widget.grid(row=3, column=1, padx=0, pady=0, sticky=tk.E)

        vcmd = (self.register(float_validator), '%P')
        ivcmd = (self.register(self.invalid_freq_off),)
        widget = ttk.Label(self, text= _("Frequency Offset (Hz)"))
        widget.grid(row=4, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._freq_offset, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=4, column=1, padx=0, pady=0, sticky=tk.E)
        ToolTip(widget, _("Sensor frequency offset"))

        ivcmd = (self.register(self.invalid_zp),)
        widget = ttk.Label(self, text= _("Zero Point"))
        widget.grid(row=5, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._zp, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=5, column=1, padx=0, pady=0, sticky=tk.E)
        ToolTip(widget, _("Determined calibrated against a SQM photometer"))


    def invalid_mac(self):
        self._mac.set('AA:BB:CC:DD:EE:FF')

    def invalid_zp(self):
        self._zp.set(0)

    def invalid_freq_off(self):
        self._freq_offset.set(0)

    def set(self, values):
        self._dev_name.set(values['name'])
        self._mac.set(values['mac'])
        self._zp.set(values['zp'])
        self._firmware.set(values['firmware'])
        self._freq_offset.set(values['freq_offset'])

    def get(self):
        return {
            'name': self._dev_name.get(),
            'mac': self._mac.get(),
            'zp': self._zp.get(),
            'firmware': self._firmware.get(),
            'freq_offset': self._freq_offset.get()
        }

        

class RefPhotometerFrame(BasePreferencesFrame):

    def __init__(self, parent,  *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def set(self, config):
        self._model.set(config['model'])
        self.stats.set(config)
        self.comms.set(config)
        self.devinfo.set(config)

    def build(self):
        super().build()
        self._control['model'].config(values="TESS-W")
        container = self._container
        self.stats = StatisticsWidget(container)
        self.stats.pack(side=tk.TOP, fill=tk.BOTH, expand=False, padx=2, pady=2)
        self.comms = CommunicationsWidget(container)
        self.comms.pack(side=tk.TOP, fill=tk.BOTH, expand=False, ipadx=4, ipady=2, padx=2, pady=2)
        self.devinfo = DeviceInfoWidget(container)
        self.devinfo.pack(side=tk.TOP, fill=tk.BOTH, expand=False, ipadx=2, ipady=4, padx=2, pady=2)

    # When pressing the save button
    def onSaveButton(self):
        config = dict()
        config['ref-stats'] = self.stats.get()
        config1 = self.comms.get()
        config2 = self.devinfo.get()
        config['ref-device'] = {**config1, **config2, "model":self._model.get()}
        pub.sendMessage(self._save_event, config=config)
      