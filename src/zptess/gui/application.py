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
from zptess.gui import ABOUT_DESC_TXT, ABOUT_ACK_TXT, ABOUT_IMG, ABOUT_ICONS
from zptess.gui.preferences import Preferences
from zptess.gui.widgets.contrib import ToolTip
from zptess.gui.widgets.mainpanel import PhotometerPanel, CalibrationPanel, BatchManagemetPanel
from zptess.gui.widgets.about import AboutDialog
from zptess.gui.widgets.writezp import WriteZeroPointDialog

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
        #self.geometry("800x600+0+0")
        self.build()
        
    def quit(self):
        self.destroy()
        pub.sendMessage('quit', exit_code=0)

    def start(self):
        self.menuBar.start()
        self.mainArea.start()
        self.statusBar.start()
        
    def build(self):
        self.menuBar  = MenuBar(self)
        self.menuBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.mainArea  = MainFrame(self)
        self.mainArea.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.statusBar = StatusBar(self)
        self.statusBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)

    # ----------------
    # Error conditions
    # ----------------

    def messageBoxInfo(self, title, message):
        tk.messagebox.showinfo(message=message, title=title) # Someday, it will be replaced with a non blocking dialog
        return defer.succeed(None)

    def messageBoxError(self, title, message):
        tk.messagebox.showerror(message=message, title=title) # Someday, it will be replaced with a non blocking dialog
        return defer.succeed(None)

    def messageBoxWarn(self, title, message):
        tk.messagebox.showwarning(message=message, title=title) # Someday, it will be replaced with a non blocking dialog
        return defer.succeed(None)

    def messageBoxAcceptCancel(self, title, message):
        flag = tk.messagebox.askokcancel(message=message, title=title) # Someday, it will be replaced with a non blocking dialog
        return defer.succeed(flag)

    def openDirectoryDialog(self):
        base_dir = tk.filedialog.askdirectory() # Someday, it will be replaced with a non blocking dialog
        return defer.succeed(base_dir)

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
        pass
        # pub.sendMessage('observer_list_req')
        # pub.sendMessage('location_list_req')
        # pub.sendMessage('camera_list_req')
        # pub.sendMessage('roi_list_req')

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

        # Tools submenu
        tools_menu = tk.Menu(menu_bar, tearoff=False)
        tools_menu.add_command(label=_("Write Zero Point ..."), command=self.onMenuWriteZeroPoint)
        menu_bar.add_cascade(label=_("Tools"), menu=tools_menu)
      
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
            title      = _("About ZPTESS"),
            version    = version, 
            descr_path = ABOUT_DESC_TXT, 
            ack_path   = ABOUT_ACK_TXT, 
            img_path   = ABOUT_IMG, 
            logos_list = ABOUT_ICONS,
        )

    def doWriteZeroPoint(self):
        writezp = WriteZeroPointDialog()


    def onMenuAboutVersion(self):
        pub.sendMessage('database_version_req')


    def onMenuPreferences(self):
        preferences = Preferences(self)
        self.preferences = preferences
        preferences.start()

    def onMenuWriteZeroPoint(self):
        writezp = WriteZeroPointDialog()


    

class MainFrame(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        left_panel = ttk.Frame(self)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=8, pady=0, ipadx=0, ipady=0)
        right_panel = ttk.Frame(self)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=8, pady=0, ipadx=0, ipady=0)
        self.photPanel = {
            'ref':  PhotometerPanel(left_panel, role='ref', text= _("Reference Photometer")),
            'test': PhotometerPanel(left_panel, role='test', text= _("Test Photometer")),
        }
        self.photPanel['test'].pack(side=tk.TOP, fill=tk.BOTH, padx=0, pady=10, ipadx=5, ipady=5)
        self.photPanel['ref'].pack(side=tk.TOP, fill=tk.BOTH, padx=0, pady=10)
        self.calibPanel = CalibrationPanel(right_panel)
        self.calibPanel.pack(side=tk.TOP, fill=tk.BOTH, padx=0, pady=0)
        self.batchPanel = BatchManagemetPanel(right_panel)
        self.batchPanel.pack(side=tk.TOP, fill=tk.BOTH, padx=5, pady=5)

    def start(self):
        self.photPanel['test'].start()
        self.photPanel['ref'].start()
        self.calibPanel.start()
        self.batchPanel.start()

    def clearPhotPanel(self, role):
        self.photPanel[role].clear()

    def updatePhotInfo(self, role, phot_info):
        self.photPanel[role].updatePhotInfo(phot_info)

    def updatePhotStats(self, role, stats_info):
        self.photPanel[role].updatePhotStats(stats_info)

    def startCalibration(self):
        self.photPanel['test'].startCalibration()
        self.photPanel['ref'].startCalibration()

    def stopCalibration(self):
        self.photPanel['test'].stopCalibration()
        self.photPanel['ref'].stopCalibration()
        self.calibPanel.stopCalibration()

    def updateCalibration(self, count, stats_info):
        self.calibPanel.updateCalibration(count, stats_info)

    def updateSummary(self, summary_info):
        self.calibPanel.updateSummary(summary_info)
    


    def build(self):
        pass


class StatusBar(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()

    def start(self):
        pub.sendMessage('status_bar_req') # This may be missed, we'll try later in the controller

    def build(self):
        # Process status items
        self.batch_start = tk.StringVar()
        widget = ttk.Label(self, textvariable=self.batch_start, justify=tk.LEFT, width=30, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        ToolTip(widget, text=_("Last batch start timestamp"))

        self.batch_end = tk.StringVar()
        widget = ttk.Label(self, textvariable=self.batch_end, justify=tk.LEFT, width=30, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        ToolTip(widget, text=_("Last batch end timestamp"))

        self.batch_number = tk.StringVar()
        widget = ttk.Label(self, textvariable=self.batch_number, justify=tk.RIGHT, width=3, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        ToolTip(widget, text=_("Photometers calibrated"))

        self.emailed = tk.StringVar()
        widget = ttk.Label(self, textvariable=self.emailed, justify=tk.LEFT, width=12, borderwidth=1, relief=tk.SUNKEN)
        widget.pack(side=tk.LEFT, fill=tk.X, padx=2, pady=2)
        ToolTip(widget, text=_("Was batch emailed?"))

    def clear(self):
        pass

    def set(self, batch_info):
        N = batch_info['calibrations']
        self.batch_start.set(f"Started @ {batch_info['begin_tstamp']}")
        self.batch_end.set(f"Ended @ {batch_info['end_tstamp']}")
        self.batch_number.set(N if N else 0)
        self.emailed.set("Emailed" if batch_info['email_sent'] else "Not Emailed")
