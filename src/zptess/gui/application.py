# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2020
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
# from zptess.gui.widgets.about import AboutDialog
# from zptess.gui.widgets.consent import ConsentDialog
# from zptess.gui.widgets.date import DateFilterDialog
# from zptess.gui.preferences import Preferences
from zptess.gui import ABOUT_DESC_TXT, ABOUT_ACK_TXT, ABOUT_IMG, ABOUT_ICONS

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
        self.build()
        
    def quit(self):
        self.destroy()
        pub.sendMessage('quit', exit_code=0)

    def start(self):
        return
        self.menuBar.start()
        self.toolBar.start()
        self.mainArea.start()
        self.statusBar.start()
        
    def build(self):
        return
        self.menuBar  = MenuBar(self)
        self.menuBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.toolBar = ToolBar(self)
        self.toolBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.mainArea  = MainFrame(self)
        self.mainArea.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)
        self.statusBar = StatusBar(self)
        self.statusBar.pack(side=tk.TOP, fill=tk.X, expand=True,  padx=10, pady=5)

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
        file_menu.add_command(label=_("Load images..."), state=tk.NORMAL, command=self.onMenuImageLoad)
        file_menu.add_command(label=_('Export to CSV...'), state=tk.NORMAL, command=self.onMenuGenerateCSV)
        file_menu.add_command(label=_('Publish Measurements...'), state=tk.NORMAL, command=self.onMenuPublish)
        file_menu.add_separator()
        file_menu.add_command(label=_("Quit"), command=self.quit)
        menu_bar.add_cascade(label=_("File"), menu=file_menu)

        # Options submenu
        options_menu = tk.Menu(menu_bar, tearoff=False)
        options_menu.add_command(label=_("Delete measurements..."), command=self.onMenuDeleteMeasurements)
        options_menu.add_separator()
        options_menu.add_command(label=_("Preferences..."), command=self.onMenuPreferences)
        menu_bar.add_cascade(label=_("Edit"), menu=options_menu)

        # Process submenu
        process_menu = tk.Menu(menu_bar, tearoff=False)
        process_menu.add_command(label=_("Sky Brightness..."), state=tk.NORMAL, command=self.onMenuSkyBrightness)
        menu_bar.add_cascade(label=_("Process"), menu=process_menu)
       
        # About submenu
        about_menu = tk.Menu(menu_bar, tearoff=False)
        about_menu.add_command(label=_("Version"), command=self.onMenuAboutVersion)
        menu_bar.add_cascade(label=_("About"), menu=about_menu)

        # Completes the hack for OSX by cascading our menu bar
        if platform.system() == 'Darwin':
            root_menu_bar.add_cascade(label='AZOTEA', menu=menu_bar)
        

    def quit(self):
        '''This halts completely the main Twisted loop'''
        pub.sendMessage('quit', exit_code=0)

    def doAbout(self, db_version):
        version = _("Version {0}\nDatabase version {1}").format(__version__, db_version)
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

    def onMenuImageLoad(self):
        pub.sendMessage('images_load_req')

    def onMenuSkyBrightness(self):
        pub.sendMessage('sky_brightness_stats_req')

    def onMenuDeleteMeasurements(self):
        dateFilter = DateFilterDialog(self, command=self.getDeleteSkyDate)

    def onMenuGenerateCSV(self):
        dateFilter = DateFilterDialog(self, command=self.getExportDate)

    def onMenuPublish(self):
        pub.sendMessage('publishing_publish_req')

    def getExportDate(self, date):
        pub.sendMessage('sky_brightness_csv_req', date=date)

    def getDeleteSkyDate(self, date):
        pub.sendMessage('sky_brightness_delete_req', date=date)



class ToolBar(ttk.Frame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()

    def start(self):
        pass

    def build(self):
        button1 = ttk.Button(self, text=_("STOP"), command=self.onStopButton)
        button1.pack(side=tk.LEFT, padx=5, pady=0)
        separ = ttk.Separator(self, orient=tk.VERTICAL)
        separ.pack(side=tk.LEFT, padx=5, pady=5)

        # TOP superframe
        subframe = ttk.Frame(self)
        subframe.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=5, pady=5)


    def onStopButton(self):
        pub.sendMessage("images_abort_load_req")
        pub.sendMessage("sky_brightness_abort_stats_req")

    

class MainFrame(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uiid = 0
        self.diid = 0
        self.build()

    def start(self):
        pass

    def build(self):

        pannedWindow = ttk.PanedWindow(self, orient=tk.VERTICAL)
        pannedWindow.pack(side=tk.TOP, fill=tk.BOTH, pady=10)

        uframe = tk.LabelFrame(pannedWindow, text=_("New loaded images"))
        #uframe.pack(side=tk.TOP, fill=tk.BOTH, pady=10)
        pannedWindow.add(uframe)

        lframe = tk.LabelFrame(pannedWindow, text=_("New sky brightness measurements"))
        #lframe.pack(side=tk.TOP, fill=tk.BOTH, pady=10)
        pannedWindow.add(lframe)



        uframe1 = tk.Frame(uframe)
        uframe1.pack(side=tk.TOP, fill=tk.BOTH, pady=10)

        uframe2 = tk.Frame(uframe)
        uframe2.pack(side=tk.TOP, fill=tk.BOTH, pady=10)

        camcombo = CameraCombo(uframe1, text=_("Camera"), command=self.onCamComboSelection)
        camcombo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.cameraCombo = camcombo

        loccombo = LocationCombo(uframe1, text=_("Location"), width=30, command=self.onLocComboSelection)
        loccombo.grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.locationCombo = loccombo

        obscombo = ObserverCombo(uframe1, text=_("Observer"), command=self.onObsComboSelection)
        obscombo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        self.observerCombo = obscombo

        uframe2 = tk.Frame(uframe)
        uframe2.pack(side=tk.TOP, fill=tk.BOTH, pady=10)


        # Set the upper treeview
        utree = ttk.Treeview(uframe2, 
            columns=( 'Model', 'Date', 'Time', 'FL', 'f/', 'Exposure', 'ISO'),
            selectmode='none',
            height=10,
        )
        utree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)
        # Add a vertical scroll bar
        vsb = ttk.Scrollbar(uframe2, orient=tk.VERTICAL, command=utree.yview)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        utree.configure(yscrollcommand=vsb.set)
       
        self.upperTree = utree
 
        # Configure upper tree columns
        utree.heading('#0', text=_("Name"))
        utree.column('#0', stretch=tk.YES, width=250, anchor='w')

        utree.heading('#1', text=_("Model"))
        utree.column('#1', stretch=tk.YES, width=150, anchor='center')
      
        utree.heading('#2', text=_("Date"))
        utree.column('#2', stretch=tk.YES, width=100, anchor='center')

        utree.heading('#3', text=_("Time"))
        utree.column('#3', stretch=tk.YES, width=80, anchor='center')

        utree.heading('#4', text=_("FL (mm)"))
        utree.column('#4', stretch=tk.YES, width=80, anchor='center')

        utree.heading('#5', text=_("f/"))
        utree.column('#5', stretch=tk.YES, width=80, anchor='center')
        
        utree.heading('#6', text=_("Exposure"))
        utree.column('#6', stretch=tk.YES, width=80, anchor='center')

        utree.heading('#7', text=_("ISO"))
        utree.column('#7', stretch=tk.YES, width=80, anchor='center')
        

        lframe1 = tk.Frame(lframe)
        lframe1.pack(side=tk.TOP, fill=tk.BOTH, pady=10)

        roicombo = ROICombo(lframe1, text=_("Region of interest"), command=self.onROIComboSelection)
        roicombo.pack(side=tk.LEFT,fill=tk.X, padx=5, pady=5)
        self.ROICombo = roicombo

        self.ROIComment = roiCommentVar = tk.StringVar()
        roicomment = tk.Label(lframe1, textvariable=roiCommentVar)
        roicomment.pack(side=tk.RIGHT,fill=tk.X, padx=5, pady=5)

        lframe2 = tk.Frame(lframe)
        lframe2.pack(side=tk.TOP, fill=tk.BOTH, pady=10)

        # Set the lower treeview
        ltree = ttk.Treeview(lframe2, 
            columns=( 'Date', 'Time', 'Exposure', 'R','VAR(R)','G1','VAR(G1)','G2','VAR(G2)','B','VAR(B)'),
            selectmode='none',
            height=10,
        )
        ltree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=10, pady=10)
         # Add a vertical scroll bar
        vsb = ttk.Scrollbar(lframe2, orient=tk.VERTICAL, command=ltree.yview)
        vsb.pack(side=tk.LEFT, fill=tk.Y)
        ltree.configure(yscrollcommand=vsb.set)
        
        self.lowerTree = ltree

         # Configure lower tree columns
        ltree.heading('#0', text=_("Name"))
        ltree.column('#0', stretch=tk.YES, width=250, anchor='w')
      
        ltree.heading('#1', text=_("Date"))
        ltree.column('#1', stretch=tk.YES, width=100, anchor='center')

        ltree.heading('#2', text=_("Time"))
        ltree.column('#2', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#3', text=_("Exposure"))
        ltree.column('#3', stretch=tk.YES, width=80, anchor='center')
      
        ltree.heading('#4', text="R1")
        ltree.column('#4', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#5', text="G2")
        ltree.column('#5', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#6', text="G3")
        ltree.column('#6', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#7', text="B4")
        ltree.column('#7', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#8', text="\u03C3^2 R1")
        ltree.column('#8', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#9', text="\u03C3^2 G2")
        ltree.column('#9', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#10', text="\u03C3^2 G3")
        ltree.column('#10', stretch=tk.YES, width=80, anchor='center')

        ltree.heading('#11', text="\u03C3^2 B4")
        ltree.column('#11', stretch=tk.YES, width=80, anchor='center')


    def onObsComboSelection(self, item):
        data = self.observerCombo.get()
        pub.sendMessage('observer_set_default_req', data=data)

    def onLocComboSelection(self, item):
        data = self.locationCombo.get()
        pub.sendMessage('location_set_default_req', data=data)

    def onROIComboSelection(self, item):
        data = self.ROICombo.get()
        pub.sendMessage('roi_set_default_req', data=data)

    def onCamComboSelection(self, item):
        data = self.cameraCombo.get()
        pub.sendMessage('camera_set_default_req', data=data)    
    

    def clearImageDataView(self):
        for child in self.upperTree.get_children():
            self.upperTree.delete(child)

    def clearSkyMeasurementView(self):
        for child in self.lowerTree.get_children():
            self.lowerTree.delete(child)

    def displayImageData(self, name, row):
        self.upperTree.insert('', 0, 
            iid    = self.uiid, 
            text   = name,
            values = [row[key] for key in (
                'model',
                'widget_date',
                'widget_time',
                'focal_length',
                'f_number',
                'exptime',
                'iso',
                )
            ]
        )
        self.uiid +=  1


    def displaySkyMeasurement(self, name, row):
        self.lowerTree.insert('', 0, 
            iid    = self.diid, 
            text   = name,
            values = [row[key] for key in (
                'widget_date',
                'widget_time',
                'exptime',
                'aver_signal_R',
                'aver_signal_G1',
                'aver_signal_G2',
                'aver_signal_B',
                'vari_signal_R',
                'vari_signal_G1',
                'vari_signal_G2',
                'vari_signal_B',
                )
            ]
        )
        self.diid +=  1
     
     


class StatusBar(ttk.Frame):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()

    def start(self):
        pass

    def build(self):
        # Process status items
        self.progress = tk.IntVar()
        self.progress_ctrl= ttk.Progressbar(self, 
            variable = self.progress,
            length   = 300, 
            mode     = 'determinate', 
            orient   = 'horizontal', 
            value    = 0,
        )
        self.progress_ctrl.pack(side=tk.RIGHT, fill=tk.X)
        ToolTip(self.progress_ctrl, text=_('Current process progress'))

        self.detail = tk.StringVar()
        self.detail_ctrl = ttk.Label(self, textvariable=self.detail, justify=tk.RIGHT, width=30, borderwidth=1, relief=tk.SUNKEN)
        self.detail_ctrl.pack(side=tk.RIGHT, fill=tk.X, padx=2, pady=2)
        ToolTip(self.detail_ctrl, text=_("process detail"))

        self.process = tk.StringVar()
        self.process_ctrl = ttk.Label(self, textvariable=self.process, width=16, borderwidth=1, relief=tk.SUNKEN)
        self.process_ctrl.pack(side=tk.RIGHT, fill=tk.X, padx=2, pady=2)
        ToolTip(self.process_ctrl, text=_("process under way"))

    def clear(self):
        self.process.set('')
        self.detail.set('')
        self.progress.set(0)
        self.process_ctrl.configure(background='#d9d9d9') # The default color

    def update(self, what, detail, progress, error=False):
        self.process.set(what)
        self.detail.set(detail)
        self.progress.set(progress)
        if error:
            self.process_ctrl.configure(background='#ff0000')
        else:
            self.process_ctrl.configure(background='#00ff00')
