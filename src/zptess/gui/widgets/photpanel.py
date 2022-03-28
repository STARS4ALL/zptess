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

# -------------
# Local imports
# -------------

from zptess.gui.widgets.contrib import ToolTip

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

class PhotometerInfoPanel(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._dev_name = tk.StringVar()
        self._mac   = tk.StringVar()
        self._zp    = tk.DoubleVar()
        self._firmware = tk.StringVar()
        self._freq_offset = tk.DoubleVar()
        self.build()

    def build(self):  

        widget = ttk.Label(self, text= _("Name"))
        widget.grid(row=1, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=16, textvariable=self._dev_name, justify=tk.LEFT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("MAC Address"))
        widget.grid(row=2, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=16, textvariable=self._mac, justify=tk.LEFT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Firmware"))
        widget.grid(row=3, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=25, textvariable=self._firmware, justify=tk.LEFT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=3, column=1, padx=0, pady=0, sticky=tk.E)

        widget = ttk.Label(self, text= _("Frequency Offset (Hz)"))
        widget.grid(row=4, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=6, textvariable=self._freq_offset, justify=tk.LEFT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=4, column=1, padx=0, pady=0, sticky=tk.E)
        ToolTip(widget, _("Sensor frequency offset"))

        widget = ttk.Label(self, text= _("Zero Point"))
        widget.grid(row=5, column=0, padx=0, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=6, textvariable=self._zp, justify=tk.RIGHT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=5, column=1, padx=0, pady=0, sticky=tk.E)
        ToolTip(widget, _("ZP used in the firmware"))

    def set(self, values):
        self._dev_name.set(values['name'])
        self._mac.set(values['mac'])
        self._zp.set(values['zp'])
        self._firmware.set(values['firmware'])
        self._freq_offset.set(values['freq_offset'])


class PhotometerProgressPanel(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._dev_name = tk.StringVar()
        self._progress = tk.StringVar()
        self._start_t  = tk.StringVar()
        self._end_t    = tk.StringVar()
        self._window   = tk.StringVar()
        self.build()

    def build(self):  

        # Upper sub-pabnel
        upper_panel  = ttk.Frame(self)
        upper_panel.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
        widget = ttk.Label(upper_panel, width=16, textvariable=self._dev_name, justify=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
        widget = ttk.Progressbar(upper_panel, 
            variable = self._progress,
            maximum  = 100,  # Express in percentage
            length   = 200, 
            mode     = 'determinate', 
            orient   = tk.HORIZONTAL, 
            value    = 0,
        )
        widget.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)

        # Lower sub-panel
        lower_pannel = ttk.Frame(self)
        lower_pannel.pack(side=tk.TOP, fill=tk.X, padx=2, pady=2)
        widget = ttk.Label(lower_pannel, width=16, textvariable=self._start_t, justify=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        widget = ttk.Label(lower_pannel, width=16, textvariable=self._start_t, justify=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        widget = ttk.Label(lower_pannel, width=16, textvariable=self._end_t, justify=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
     

    def setPending(self, stats_info):
        percent = int(100 * stats_info['current']//stats_info['size'],0)
        self._dev_name.set(stats_info['name'])
        self._progress.set(percent)

            
    def setFull(self, stats_info):
        self._dev_name.set(stats_info['name'])
        self._start_t,set(stats_info['begin_tstamp'].strftime("%H:%M:%S"))
        self._end_t,set(stats_info['end_tstamp'].strftime("%H:%M:%S"))
        self._window.set( f"{stats_info['duration']} sec.")


class PhotometerStatsPanel(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._freq    = tk.DoubleVar()
        self._stddev  = tk.DoubleVar()
        self._central = tk.StringVar()
        self._zp_fict = tk.DoubleVar()
        self._mag     = tk.DoubleVar()
        self.build()

    def build(self):
        widget = ttk.Label(self, width=6, text= _("Freq. (Hz)"))
        widget.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=12, textvariable=self._freq, justify=tk.RIGHT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=6, text= _("\u03C3. (Hz)"))
        widget.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=12, textvariable=self._stddev, justify=tk.RIGHT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=6, text= _("Mag. "))
        widget.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=12, textvariable=self._mag, justify=tk.RIGHT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=6, text= _("@ ZP. "))
        widget.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=12, textvariable=self._zp_fict, justify=tk.RIGHT, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=2, pady=2, sticky=tk.W)


    def setFull(self, stats_info):
        self._freq.set(stats_info['freq'])
        self._stddev,set(stats_info['stddev'])
        self._central,set(stats_info['central'])
        self._mag.set(stats_info['mag'])
        self._zp_fict.set(stats_info['zp_fict'])


class PhotometerPanel(ttk.LabelFrame):

    def __init__(self, parent, text, *args, **kwargs):
        super().__init__(parent, *args, text="Fix me", **kwargs)
        self._text = text
        self._enable = tk.BooleanVar()
        self.build()

    def build(self):
        self.info = PhotometerInfoPanel(self)
        self.info.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        self.progress = PhotometerProgressPanel(self)
        self.progress.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        self.stats = PhotometerStatsPanel(self)
        self.stats.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        widget = ttk.Checkbutton(self, text= self._text, variable=self._enable, command=self.onEnablePanel)
        self.configure(labelwidget=widget) 

    def onEnablePanel(self):
        pass
