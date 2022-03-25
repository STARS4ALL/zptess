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

class StatisticsWidget(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Statistics"), **kwargs)
        self._samples = tk.IntVar()
        self._period  = tk.DoubleVar()
        self._central = tk.StringVar()
        self.build()

    def build(self):
        widget = ttk.Label(self, text= _("Samples"))
        widget.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        widget = ttk.Spinbox(self, textvariable=self._samples, width=5, from_= 3, to=625)
        widget.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        ToolTip(widget, _("# samples to average"))

        widget = ttk.Label(self, text= _("Period (sec.)"))
        widget.grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        widget = ttk.Entry(self, textvariable=self._period, width=5,)
        widget.grid(row=1, column=1, padx=10, pady=10, sticky=tk.W)
        ToolTip(widget, _("Calculate average each T seconds"))
        
        widget = ttk.Radiobutton(self, text=_("Average"), variable=self._central, value="mean")
        widget.grid(row=2, column=0, padx=10, pady=10, sticky=tk.E)
        widget = ttk.Radiobutton(self, text=_("Median"), variable=self._central, value="median")
        widget.grid(row=2, column=1, padx=10, pady=10, sticky=tk.E)

    def setValues(self, values):
        self._central.set(values['central'])
        self._samples.set(values['samples'])
        self._period.set(values['period'])
    

    def getValues(self):
        return {
            'central': self._central,
            'samples': self._samples,
            'period' : self._period
        }
    
class CommunicationsWidget(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Communication Methods"), **kwargs)
        self._method = tk.IntVar()
        self._old_proto  = tk.BooleanVar()
        self._addr = tk.StringVar()
        self._port = tk.IntVar()
        self.build()

    def build(self):
        
        # left frame elements
        left_frame  = ttk.Frame(self)
        comm_frame =  ttk.Frame(left_frame, borderwidth=1)
        widget = ttk.Radiobutton(comm_frame, text=_("Serial"), variable=self._method, value="serial")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        widget = ttk.Radiobutton(comm_frame, text=_("TCP"), variable=self._method, value="tcp")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        widget = ttk.Radiobutton(comm_frame, text=_("UDP"), variable=self._method, value="usp")
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        comm_frame.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        widget = ttk.Checkbutton(left_frame, text= _("Use old protocol"))
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        left_frame.pack(side=tk.LEFT,fill=tk.BOTH,  padx=5, pady=2)

        # right frame elements
        right_frame = ttk.Frame(self)
        self._addr_w = ttk.Label(self, text= _("IP Address"))
        self._addr_w.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        widget = ttk.Entry(self, textvariable=self._addr)
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        self._port_w = ttk.Label(self, text= _("TCP/UDP Port"))
        self._port_w.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        widget = ttk.Spinbox(self, textvariable=self._port, width=5, from_= 0, to=65535)
        widget.pack(side=tk.TOP,fill=tk.BOTH,  padx=5, pady=2)
        right_frame.pack(side=tk.LEFT,fill=tk.BOTH,  padx=5, pady=2)

       
     

    def setValues(self, values):
        pass
      
    

    def getValues(self):
        return {}
    
    

class BasePreferencesFrame(ttk.Frame):

    def __init__(self, parent, label, initial_event, save_event, cancel_event, **kwargs):
        super().__init__(parent, **kwargs)
        self._input   = {}
        self._control = {}
        self._label   = label
        self._initial_event = initial_event
        self._save_event    = save_event
        self._cancel_event  = cancel_event
        self.build()
        
    def start(self):
        pub.sendMessage(self._initial_event)

    def build(self):

        # Where to really put the children  widgets
        container_frame = ttk.Frame(self)
        container_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True,  padx=10, pady=5)
        self._container = container_frame

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.X, padx=10, pady=5)

        # Lower Buttons
        button = ttk.Button(bottom_frame, text=_("Save"), command=self.onSaveButton)
        button.pack(side=tk.LEFT,fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._control['save'] = button
       
        button = ttk.Button(bottom_frame, text=_("Cancel"), command=self.onCancelButton)
        button.pack(side=tk.RIGHT,fill=tk.BOTH, expand=True, padx=10, pady=5)
        self._control['cancel'] = button

    # ------------
    # Save Control
    # ------------

    # When pressing the save button
    def onSaveButton(self):
        pass

    # response from controller to save button
    def saveOkResp(self):
       pass

    # --------------
    # Cancel Control
    # --------------

    # When pressing the delete button
    def onCancelButton(self):
       pass

    # Ok response to delete request
    def deleteOkResponse(self, count):
       pass

 