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
from zptess.gui.widgets.validators import float_validator, ip_validator

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

# -----------------------
# Module global functions
# -----------------------

# -----------------------
# Module auxiliar classes
# -----------------------

class StatisticsWidget(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Statistics"), **kwargs)
        self._samples = tk.IntVar()
        self._period  = tk.DoubleVar()
        self._central = tk.StringVar()
        self.build()

    def build(self):
        widget = ttk.Label(self, text= _("Samples"))
        widget.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Spinbox(self, textvariable=self._samples, width=5, justify=tk.RIGHT, from_= 3, to=625)
        widget.grid(row=0, column=1, padx=2, pady=2, sticky=tk.E)
        ToolTip(widget, _("# samples to average"))

        vcmd  = (self.register(float_validator), '%P')
        ivcmd = (self.register(self.invalid_period),)
        widget = ttk.Label(self, text= _("Period (sec.)"))
        widget.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Entry(self, textvariable=self._period, width=5, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=1, column=1, padx=2, pady=2, sticky=tk.E)
        ToolTip(widget, _("Calculate average each T seconds"))
        
        widget = ttk.Radiobutton(self, text=_("Average"), variable=self._central, value="mean")
        widget.grid(row=2, column=0, padx=2, pady=2, sticky=tk.E)
        widget = ttk.Radiobutton(self, text=_("Median"), variable=self._central, value="median")
        widget.grid(row=2, column=1, padx=2, pady=2, sticky=tk.E)

    def invalid_period(self):
        self._period.set(5.0)

    def set(self, values):
        self._central.set(values['central'])
        self._samples.set(values['samples'])
        self._period.set(values['period'])

    def get(self):
        return {
            'central': self._central.get(),
            'samples': self._samples.get(),
            'period' : self._period.get()
        }
    
class CommunicationsWidget(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Communication Methods"), **kwargs)
        self._method = tk.StringVar()
        self._old_proto  = tk.BooleanVar()
        self._addr = tk.StringVar()
        self._port = tk.IntVar()
        self.build()

    def build(self):
        
        # left frame elements
        left_frame  = ttk.Frame(self)
        comm_frame =  ttk.Frame(left_frame, borderwidth=1)
        widget = ttk.Radiobutton(comm_frame, text=_("Serial"), variable=self._method, command=self.changeLabels, value="serial")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        widget = ttk.Radiobutton(comm_frame, text=_("TCP"), variable=self._method, command=self.changeLabels, value="tcp")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        widget = ttk.Radiobutton(comm_frame, text=_("UDP"), variable=self._method, command=self.changeLabels, value="udp")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        comm_frame.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        widget = ttk.Checkbutton(left_frame, text= _("Old protocol"),  variable=self._old_proto)
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=6)
        ToolTip(widget, _("use old style messages instead of JSON messages"))
        left_frame.pack(side=tk.LEFT,fill=tk.BOTH,  padx=0, pady=0)

        # right frame elements
        # we cannot validate IP addresses because the Entry widget is also being used for serial port text strings
        right_frame = ttk.Frame(self)
        self._addr_w = ttk.Label(right_frame, text= _("IP Address"))
        self._addr_w.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        widget = ttk.Entry(right_frame, width=12, textvariable=self._addr)
        ToolTip(widget, _("IP Address or Serial Port Name"))
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        self._port_w = ttk.Label(right_frame, text= _("TCP/UDP Port"))
        self._port_w.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        widget = ttk.Spinbox(right_frame, textvariable=self._port, justify=tk.RIGHT, width=5, from_= 0, to=65535)
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=2, pady=2)
        ToolTip(widget, _("TCP/UDP port or baud rate"))
        right_frame.pack(side=tk.LEFT,fill=tk.BOTH,  padx=0, pady=0)

    def changeLabels(self):
        method = self._method.get()
        if method == "serial":
            self._addr_w.configure(text= _("Serial Port name"))
            self._port_w.configure(text= _("Baud rate"))
        elif method == "tcp":
            self._addr_w.configure(text= _("IP Address"))
            self._port_w.configure(text= _("TCP Port"))
        else:
            self._addr_w.configure(text= _("IP Address"))
            self._port_w.configure(text= _("UDP Port"))

    def set(self, values):
        proto, addr, port = chop(values['endpoint'], sep=':')
        self._method.set(proto)
        self._addr.set(addr)
        self._port.set(port)
        self._old_proto.set(values['old_proto'])
        self.changeLabels()

    def get(self):
        endpoint = f"{self._method.get()}:{self._addr.get()}:{self._port.get()}"
        return {
            'endpoint': endpoint,
            'old_proto': 1 if self._old_proto.get() else 0
        }
    
    

class BasePreferencesFrame(ttk.Frame):

    def __init__(self, parent, label, initial_event, save_event, cancel_event, model_event, **kwargs):
        super().__init__(parent, **kwargs)
        self._input   = {}
        self._control = {}
        self._label   = label
        self._initial_event = initial_event
        self._save_event    = save_event
        self._cancel_event  = cancel_event
        self._model_event   = model_event
        self._model = tk.StringVar()
        self.build()
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def build(self):

        vcmd  = (self.register(self.onModelChange), '%P')
        widget = ttk.Label(self, text= _("Model"))
        widget.pack(side=tk.TOP, fill=tk.X, expand=False,  padx=10, pady=1)
        widget = ttk.Combobox(self, state='readonly', textvariable=self._model, 
            values=("TESS-W","TESS-P","TAS"), validate='focusin', validatecommand=vcmd) # 'focusin' is essential
        widget.pack(side=tk.TOP, fill=tk.X, expand=False,  padx=10, pady=1)
        self._control['model'] = widget

        # Where to really put the children  widgets
        container_frame = ttk.Frame(self)
        container_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True,  padx=10, pady=5)
        self._container = container_frame

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.X, padx=10, pady=5)

        # Lower Buttons
        button = ttk.Button(bottom_frame, text=_("Save"), command=self.onSaveButton)
        button.pack(side=tk.LEFT,fill=tk.X, expand=True, padx=10, pady=5)
        self._control['save'] = button
       
        button = ttk.Button(bottom_frame, text=_("Cancel"), command=self.onCancelButton)
        button.pack(side=tk.RIGHT,fill=tk.X, expand=True, padx=10, pady=5)
        self._control['cancel'] = button

    def onModelChange(self, value):
        '''When changing TESS model'''
        pub.sendMessage(self._model_event, model=value)
        return True

    # ------------
    # Save Control
    # ------------
    
    # To be subclassed
    def onSaveButton(self):
        '''When pressing the save button'''
        raise NotImplementedError()

    # May be be subclassed
    def saveOkResp(self):
        '''response from controller to save button'''
        pub.sendMessage('gui_preferences_close')


    # --------------
    # Cancel Control
    # --------------

    def onCancelButton(self):
        '''When pressing the cancel button'''
        pub.sendMessage('gui_preferences_close')

 