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
# local imports
# -------------

from zptess.gui.preferences.refphot import RefPhotometerFrame
from zptess.gui.preferences.testphot import TestPhotometerFrame

# from zptess.gui.preferences.test import TestPhotometerFrame


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

class Preferences(tk.Toplevel):

    def __init__(self, owner, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner
        self.build()
        self.grab_set()
        pub.subscribe(self.close, 'gui_preferences_close')

    def start(self):
        self.referenceFrame.start()
        self.testFrame.start()
        
    def close(self):
        self._owner.preferences = None
        self.destroy()

    def build(self):
        self.title(_("Preferences"))
        self.protocol("WM_DELETE_WINDOW", self.close)
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)
        test_frame = TestPhotometerFrame(
            notebook,
            label         = _("Test Photometer"),
            initial_event = "test_config_load_req",
            save_event    = "test_config_save_req",
            cancel_event  = None,
            model_event   = 'test_model_change_req',
        )
        test_frame.pack(fill='both', expand=True)
        notebook.add(test_frame, text= _("Test Photometer"))
        ref_frame = RefPhotometerFrame(
            notebook,
            label         = _("Reference Photometer"),
            initial_event = "ref_config_load_req",
            save_event    = "ref_config_save_req",
            cancel_event  = None,
            model_event   = 'ref_model_change_req',
        )
        ref_frame.pack(fill='both', expand=True)
        notebook.add(ref_frame, text= _("Reference Photometer"))
        self.notebook       = notebook
        self.referenceFrame = ref_frame
        self.testFrame      = test_frame

        