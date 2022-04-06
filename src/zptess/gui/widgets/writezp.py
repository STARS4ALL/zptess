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

import math
import gettext
import tkinter as tk
from   tkinter import ttk

# -------------------
# Third party imports
# -------------------

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# -------------------
# Third party imports
# -------------------

from pubsub import pub

# -------------
# local imports
# -------------

from zptess.gui.widgets.validators import float_validator
from zptess.gui.widgets.contrib import ToolTip

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

# -----------------
# Application Class
# -----------------

class WriteZeroPointDialog(tk.Toplevel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._zp = tk.DoubleVar()
        self._zp.set(20.50)
        self.build()
        self.grab_set()
        
    def build(self):
        self.title(_("Write Zero Point"))
        # Frames
        top_frame = ttk.Frame(self)
        top_frame.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
        bottom_frame = ttk.Frame(self,  borderwidth=2, relief=tk.GROOVE)
        bottom_frame.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)

        # Upper contents frame
        vcmd = (self.register(float_validator), '%P')
        ivcmd = (self.register(self.invalid_zp),)
        widget = ttk.Label(top_frame, text= _("New Zero Point"))
        widget.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
        widget = ttk.Entry(top_frame, width=6, textvariable=self._zp, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
        ToolTip(widget, _("New Zero Point to Flash in photometer"))

        # Lower Buttons
        button = ttk.Button(bottom_frame, text=_("Flash"), command=self.onSaveButton)
        button.pack(side=tk.LEFT, padx=10, pady=5)
        button = ttk.Button(bottom_frame, text=_("Cancel"), command=self.onCancelButton)
        button.pack(side=tk.LEFT, padx=10, pady=5)


    def invalid_zp(self):
        self._zp.set(20.50)

    # Buttons callbacks
    def onCancelButton(self):
       self.destroy()
    
    # Buttons callbacks
    def onSaveButton(self):
        pub.sendMessage('write_zero_point_req', zero_point=self._zp.get())
        self.destroy()

   
