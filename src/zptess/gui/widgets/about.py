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
import tkinter.filedialog

# -------------------
# Third party imports
# -------------------

from PIL import Image, ImageTk

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# -------------
# local imports
# -------------


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

class AboutDialog(tk.Toplevel):

    def __init__(self, title, version, descr_path, ack_path, img_path, logos_list, *args, ncols=3, **kwargs):
        super().__init__(*args, **kwargs)
        self._title = title
        self._version = version
        self._descr_path = descr_path
        self._ack_path = ack_path
        self._img_path = img_path
        self._logos_list = logos_list
        self._ncols = ncols
        self.build()
        self.grab_set()
        
    def build(self):
        self.title(self._title)

        # TOP superframe
        top_frame = ttk.Frame(self,  borderwidth=2, relief=tk.GROOVE)
        top_frame.pack(side=tk.TOP, expand=True, fill=tk.X, padx=5, pady=5)
        # Bottom frame
        bottom_frame = ttk.Frame(self,  borderwidth=2, relief=tk.GROOVE)
        bottom_frame.pack(side=tk.BOTTOM, expand=True, fill=tk.X, padx=5, pady=5)
        # Lower Button
        button = ttk.Button(bottom_frame, text=_("Close"), command=self.onCloseButton)
        button.pack(side=tk.BOTTOM, padx=10, pady=5)


        # Right Frame
        ri_frame = ttk.Frame(top_frame)
        ri_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)

        text  = self._version
        label = ttk.Label(ri_frame, text=text)
        label.pack(side=tk.TOP,  anchor=tk.W, expand=False, fill=tk.BOTH, padx=5, pady=5)

        txt = self.loadText(ri_frame, self._descr_path)
        txt.pack(side=tk.TOP,   anchor=tk.W, expand=False, fill=tk.BOTH, padx=5, pady=5)

        br_frame = ttk.LabelFrame(ri_frame, text=_("Acknowledgements"))
        br_frame.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        txt = self.loadText(br_frame, self._ack_path)
        txt.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Left Frame
        le_frame = ttk.Frame(top_frame)
        le_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        img = self.loadIcon(le_frame, self._img_path)
        img.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)

        #  List of logos in a lower left frame with grid
        ll_frame = ttk.Frame(le_frame)
        ll_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)
        nrows = math.ceil(len(self._logos_list)/self._ncols)
        infoiter = iter(self._logos_list)
        for row in range(nrows):
            for col in range(self._ncols):
                try:
                    tip, path = next(infoiter)
                    img = self.loadIcon(ll_frame, path)
                    ToolTip(img, tip)
                    img.grid(row=row, column=col, padx=2, pady=2)
                except StopIteration:
                    break

    # Buttons callbacks
    def onCloseButton(self):
       self.destroy()

    def loadIcon(self, parent, path):
        img = ImageTk.PhotoImage(Image.open(path))
        icon = ttk.Label(parent, image = img)
        icon.photo = img
        return icon

    def loadText(self, parent, path):
        with open(path) as fd:
            text = ' '.join(fd.readlines())
        txt = tk.Message(parent, justify=tk.LEFT, text=text)
        return txt


