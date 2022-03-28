# -*- coding: utf-8 -*-
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
import platform
import tkinter as tk
from   tkinter import ttk
import tkinter.filedialog

# -------------------
# Third party imports
# -------------------

from pubsub import pub

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger
from twisted.internet import reactor
from twisted.application.service import Service
from twisted.internet import defer, threads

#--------------
# local imports
# -------------

from zptess import __version__

from zptess.logger import setLogLevel

# from zptess.gui.widgets.contrib import ToolTip
# from zptess.gui.widgets.combos  import ROICombo, CameraCombo, ObserverCombo, LocationCombo
# from zptess.gui.widgets.consent import ConsentDialog
# from zptess.gui.widgets.date import DateFilterDialog
from zptess.gui.preferences import Preferences

from zptess.gui import ABOUT_DESC_TXT, ABOUT_ACK_TXT, ABOUT_IMG, ABOUT_ICONS
from zptess.gui.widgets.about import AboutDialog
from zptess.gui.preferences   import Preferences

# ----------------
# Module constants
# ----------------

NAMESPACE = 'GUI  '

# -----------------------
# Module global variables
# -----------------------

# Support for internationalization
_ = gettext.gettext

log  = Logger(namespace=NAMESPACE)

# -----------------
# Application Class
# -----------------

class Application(tk.Tk):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title(f'ZPTESS {__version__}')
        self.protocol('WM_DELETE_WINDOW', self.quit)
        self.geometry("800x600+0+0")
        self.build()
        
    def quit(self):
        self.destroy()
        pub.sendMessage('quit', exit_code=0)

    def start(self):
        self.menuBar.start()
        self.mainArea.start()
        #self.statusBar.start()
        
    def build(self):
        self.menuBar  = MenuBar(self)
        self.menuBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.mainArea  = MainFrame(self)
        self.mainArea.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        #self.statusBar = StatusBar(self)
        #self.statusBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)

    # ----------------
    # Error conditions
    # ----------------

    def messageBoxInfo(self, who, message):
        tk.messagebox.showinfo(message=message, title=who)

    def messageBoxError(self, who, message):
        tk.messagebox.showerror(message=message, title=who)

    def messageBoxWarn(self, who, message):
        tk.messagebox.showwarning(message=message, title=who)

    def messageBoxAcceptCancel(self, who, message):
        return tk.messagebox.askokcancel(message=message, title=who)

    def openDirectoryDialog(self):
        return tk.filedialog.askdirectory()

    def saveFileDialog(self, title, filename, extension):
        return tk.filedialog.asksaveasfilename(
            title            = title,
            defaultextension = extension,
            initialfile      = filename,
            parent           = self,
            )

    def openConsentDialog(self):
        consent = ConsentDialog(
            title     = _("Consent Form"),
            text_path = CONSENT_TXT,
            logo_path = CONSENT_UCM,
            accept_event = 'save_consent_req',
            reject_event = 'quit',
            reject_code = 126,
        )
        

class MenuBar(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()
        self.preferences = None

    def start(self):
        pub.sendMessage('observer_list_req')
        pub.sendMessage('location_list_req')
        pub.sendMessage('camera_list_req')
        pub.sendMessage('roi_list_req')

    def build(self):
        menu_bar = tk.Menu(self.master)
        self.master.config(menu=menu_bar)

        # On OSX, you cannot put commands on the root menu. 
        # Apple simply doesn't allow it. 
        # You can only put other menus (cascades).
        if platform.system() == 'Darwin':
            root_menu_bar = menu_bar
            menu_bar = tk.Menu(menu_bar)

        # File submenu
        file_menu = tk.Menu(menu_bar, tearoff=False)
        file_menu.add_separator()
        file_menu.add_command(label=_("Preferences..."), command=self.onMenuPreferences)
        file_menu.add_command(label=_("Quit"), command=self.quit)
        menu_bar.add_cascade(label=_("File"), menu=file_menu)
       
        # About submenu
        about_menu = tk.Menu(menu_bar, tearoff=False)
        about_menu.add_command(label=_("Version"), command=self.onMenuAboutVersion)
        menu_bar.add_cascade(label=_("About"), menu=about_menu)

        # Completes the hack for OSX by cascading our menu bar
        if platform.system() == 'Darwin':
            root_menu_bar.add_cascade(label='ZPTESS', menu=menu_bar)
        

    def quit(self):
        '''This halts completely the main Twisted loop'''
        pub.sendMessage('quit', exit_code=0)


    def doAbout(self, db_version, db_uuid):
        version = _("Software version {0}\nDatabase version {1}\nUUID:{2}").format(__version__, db_version, db_uuid)
        about = AboutDialog(
            title      = _("About AZOTEA"),
            version    = version, 
            descr_path = ABOUT_DESC_TXT, 
            ack_path   = ABOUT_ACK_TXT, 
            img_path   = ABOUT_IMG, 
            logos_list = ABOUT_ICONS,
        )


    def onMenuAboutVersion(self):
        pub.sendMessage('database_version_req')


    def onMenuPreferences(self):
        preferences = Preferences(self)
        self.preferences = preferences
        preferences.start()


    

class MainFrame(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uiid = 0
        self.diid = 0
        self.build()

    def start(self):
        pass

    def build(self):
        pass

     


class StatusBar(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()

    def start(self):
        pass

    def build(self):
        # Process status items
        pass

    def clear(self):
        pass

    def update(self, what, detail, progress, error=False):
        pass
