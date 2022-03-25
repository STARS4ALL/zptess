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

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# -------------
# local imports
# -------------

from zptess.gui.preferences.reference import ReferenceFrame
# from zptess.gui.preferences.test import TestFrame


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

    def start(self):
        self.referenceFrame.start()
        #self.testFrame.start()
        
    def close(self):
        self._owner.preferences = None
        self.destroy()

    def build(self):
        self.title(_("Preferences"))
        self.protocol("WM_DELETE_WINDOW", self.close)
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True)
        ref_frame = ReferenceFrame(
            notebook,
            label         = _("Reference Photometer"),
            initial_event = "referece_info_load_req",
            save_event    = "referece_info_save_req",
            cancel_event  = None,
        )
        ref_frame.pack(fill='both', expand=True)
        notebook.add(ref_frame, text=_("Reference Phot."))
        # test_frame = TestFrame(
        #     notebook,
        #     label= _("Test Photometer"),
        #     initial_event="observer_list_req",
        #     detail_event="observer_details_req",
        #     default_event="observer_set_default_req",
        #     save_event="observer_save_req",
        #     delete_event="observer_delete_req",
        #     purge_event=None,
        # )
        # test_frame.pack(fill='both', expand=True)
        # notebook.add(test_frame, text=_("Test Photometer"))

        self.notebook       = notebook
        self.referenceFrame = ref_frame
        # self.testFrame      = test_frame
        