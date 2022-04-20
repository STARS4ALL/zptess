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
import tkinter.filedialog
from   tkinter import ttk

# -------------------
# Third party imports
# -------------------

from pubsub import pub
from PIL import Image, ImageTk

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger

# -------------
# Local imports
# -------------

from zptess.gui import YELLOW_ICON, GREEN_ICON, GRAY_ICON, RED_ICON
from zptess.gui.widgets.contrib import ToolTip
from zptess.gui.widgets.validators import float_validator


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

# ============================================================================
#                        PHOTOMETER PANEL WIDGETS
# ============================================================================

class PhotometerInfoPanel(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Device information"), **kwargs)
        self._dev_name = tk.StringVar()
        self._mac   = tk.StringVar()
        self._zp    = tk.DoubleVar()
        self._firmware = tk.StringVar()
        self._freq_offset = tk.DoubleVar()
        self.build()

    def start(self):
        pass

    def build(self):  

        widget = ttk.Label(self, text= _("Name"))
        widget.grid(row=1, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=16, textvariable=self._dev_name, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=0, pady=2, sticky=tk.E)

        widget = ttk.Label(self, text= _("MAC Address"))
        widget.grid(row=2, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=16, textvariable=self._mac, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=0, pady=2, sticky=tk.E)

        widget = ttk.Label(self, text= _("Firmware"))
        widget.grid(row=3, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=16, textvariable=self._firmware, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=3, column=1, padx=0, pady=2, sticky=tk.E)

        widget = ttk.Label(self, text= _("Frequency Offset (Hz)"))
        widget.grid(row=4, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=6, textvariable=self._freq_offset, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=4, column=1, padx=0, pady=2, sticky=tk.E)
        ToolTip(widget, _("Sensor frequency offset in complete darkness"))

        widget = ttk.Label(self, text= _("Zero Point"))
        widget.grid(row=5, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=6, textvariable=self._zp, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=5, column=1, padx=0, pady=2, sticky=tk.E)
        ToolTip(widget, _("ZP used in the firmware when computing magnitudes"))

    def set(self, values):
        self._dev_name.set(values['name'])
        self._mac.set(values['mac'])
        self._zp.set(values['zp'])
        self._firmware.set(values['firmware'])
        self._freq_offset.set(values['freq_offset'])

    def clear(self):
        self._dev_name.set('')
        self._mac.set('')
        self._zp.set(0)
        self._firmware.set('')
        self._freq_offset.set(0)

# ----------------------------------------------------------------------------

class PhotometerProgressPanel(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Buffer"), **kwargs)
        self._dev_name = tk.StringVar()
        self._progress = tk.StringVar()
        self._start_t  = tk.StringVar()
        self._samples  = tk.IntVar()
        self._end_t    = tk.StringVar()
        self._window   = tk.StringVar()
        self.build()

    def start(self):
        pass

    def build(self):  

        widget = ttk.Label(self, width=9, text=_("Start"), anchor=tk.W)
        widget.grid(row=0, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=10, textvariable=self._start_t, anchor=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=1, padx=0, pady=0, sticky=tk.W)
        
        widget = ttk.Label(self, width=9, text=_("Duration"), anchor=tk.W)
        widget.grid(row=1, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=10, textvariable=self._window, anchor=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=0, pady=0, sticky=tk.W)

        widget = ttk.Label(self, width=9, text=_("Samples"), anchor=tk.W)
        widget.grid(row=2, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=10, textvariable=self._samples, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=0, pady=0, sticky=tk.W)
       
        widget = ttk.Label(self, width=9, text=_("End"), anchor=tk.W)
        widget.grid(row=3, column=0, padx=5, pady=0, sticky=tk.W)
        widget = ttk.Label(self, width=10, textvariable=self._end_t, anchor=tk.CENTER, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=3, column=1, padx=0, pady=0, sticky=tk.W)

        widget = ttk.Progressbar(self, 
            variable = self._progress,
            maximum  = 100,  # Express in percentage
            length   = 100, 
            mode     = 'determinate', 
            orient   = tk.VERTICAL, 
            value    = 0,
        )
        widget.grid(row=0, column=2, rowspan=4, padx=6, pady=0, sticky=tk.N)


    def set(self, stats_info):
        begin_tstamp = stats_info['begin_tstamp']
        end_tstamp   = stats_info['end_tstamp']
        duration     = str(round(stats_info['duration'],1)) if stats_info['duration'] else ''
        self._dev_name.set(stats_info['name'])
        self._start_t.set(begin_tstamp.strftime("%H:%M:%S") if begin_tstamp else '')
        self._end_t.set(end_tstamp.strftime("%H:%M:%S") if end_tstamp else '')
        self._window.set( f"{duration} sec.")
        self._samples.set(stats_info['current'])
        percent = int(100 * stats_info['current']//stats_info['nsamples'])
        self._progress.set(percent)

    def clear(self):
        self._progress.set(0)
        self._dev_name.set('')
        self._start_t.set('')
        self._end_t.set('')
        self._window.set('')
        self._samples.set(0)

# ----------------------------------------------------------------------------

class PhotometerStatsPanel(ttk.LabelFrame):

    T = 50 # millieseconds for the animated progress bar

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Statistics"), **kwargs)
        self._freq    = tk.DoubleVar()
        self._stddev  = tk.DoubleVar()
        self._central = tk.StringVar()
        self._zp_fict = tk.DoubleVar()
        self._mag     = tk.DoubleVar()
        self._progress = tk.DoubleVar()
        self._first_event = True
        self.build()

    def start(self):
        pass

    def build(self):
        widget = ttk.Label(self, width=10, text= _("Freq. (Hz)"))
        widget.grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=8, textvariable=self._freq, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=1, padx=0, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=10, text= _("\u03C3 (Hz)"))
        widget.grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=8, textvariable=self._stddev, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=0, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=6, text= _("Mag. "))
        widget.grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=8, textvariable=self._mag, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=0, pady=2, sticky=tk.W)

        widget = ttk.Label(self, width=6, text= _("@ ZP. "))
        widget.grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        widget = ttk.Label(self, width=8, textvariable=self._zp_fict, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=3, column=1, padx=0, pady=2, sticky=tk.W)

        self._progressW = ttk.Progressbar(self, 
            variable = self._progress,
            maximum  = 100,  # device period in milliseconds / self.T
            length   = 130, 
            mode     = 'indeterminate', 
            orient   = tk.HORIZONTAL, 
            value    = 0,
        )
        self._progressW.grid(row=4, column=0, columnspan=2, padx=0, pady=2, sticky=tk.E)


    def set(self, stats_info):
        if 'freq' in stats_info.keys():
            if self._first_event:
                self._first_event = False
                self._progressW.start(self.T)
            self._freq.set(stats_info['freq'])
            self._stddev.set(round(stats_info['stddev'],3))
            self._central,set(stats_info['central'])
            self._mag.set(round(stats_info['mag'],2))
            self._zp_fict.set(stats_info['zp_fict'])
    
    def clear(self):
        self._freq.set(0)
        self._stddev.set(0)
        self._central.set('')
        self._mag.set(0)
        self._zp_fict.set(0)
        self._progress.set(0)
        self._progressW.stop()
        self._first_event = True


# ----------------------------------------------------------------------------

class PhotometerPanel(ttk.LabelFrame):

    def __init__(self, parent, role, text, *args, **kwargs):
        super().__init__(parent, *args, text="Fix me", borderwidth=4, **kwargs)
        self._text = text
        self._role = role
        self._enable  = tk.BooleanVar()
        self._own_zp  = tk.BooleanVar()
        self._endpoint = tk.StringVar()
        self.build()

    def start(self):
        self.info.start()
        self.progress.start()
        self.stats.start()


    def build(self):
        upper_frame = ttk.Frame(self)
        upper_frame.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0, ipadx=0, ipady=0,)
        lower_frame = ttk.Frame(self)
        lower_frame.pack(side=tk.TOP, fill=tk.X, padx=0, pady=0, ipadx=0, ipady=0,)

        widget = ttk.Checkbutton(upper_frame, text= _("Use device's stored zero point\nfor magnitude display"),  variable=self._own_zp)
        widget.pack(side=tk.LEFT,fill=tk.BOTH,  padx=22, pady=2)
        
        minipanel = ttk.LabelFrame(upper_frame, text=_("Communicates via"))
        minipanel.pack(side=tk.LEFT,fill=tk.BOTH,  padx=2, pady=2, ipadx=5, ipady=5)
        widget = ttk.Label(minipanel, width=25, textvariable=self._endpoint)
        widget.pack(side=tk.TOP, fill=tk.BOTH,  anchor=tk.E, padx=12, pady=2)

        self._red   = ImageTk.PhotoImage(Image.open(RED_ICON))
        self._gray   = ImageTk.PhotoImage(Image.open(GRAY_ICON))
        self._green  = ImageTk.PhotoImage(Image.open(GREEN_ICON))
        self._yellow = ImageTk.PhotoImage(Image.open(YELLOW_ICON))
        self._semaphore = widget = ttk.Label(upper_frame, image = self._gray )
        widget.pack(side=tk.RIGHT, fill=tk.BOTH,  anchor=tk.E, padx=16, pady=4)
       

        self.info = PhotometerInfoPanel(lower_frame)
        self.info.pack(side=tk.LEFT, fill=tk.X, padx=10, pady=2, ipadx=0, ipady=5,)
        self.progress = PhotometerProgressPanel(lower_frame)
        self.progress.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=2, ipadx=5, ipady=5,)
        self.stats = PhotometerStatsPanel(lower_frame)
        self.stats.pack(side=tk.LEFT, fill=tk.X, padx=5, pady=2, ipadx=5, ipady=5,)
        widget = ttk.Checkbutton(self, text= self._text, variable=self._enable, command=self.onEnablePanel)
        self.configure(labelwidget=widget)
       
    def clear(self):
        self.info.clear()
        self.progress.clear()
        self.stats.clear()
        self._own_zp.set(False)
        self._semaphore.configure(image=self._gray)

    def updatePhotInfo(self, phot_info):
        self.info.set(phot_info)

    def updatePhotStats(self, stats_info):
        self.progress.set(stats_info)
        self.stats.set(stats_info)

    def yellow(self):
         self._semaphore.configure(image=self._yellow)

    def green(self):
         self._semaphore.configure(image=self._green)

    def red(self):
         self._semaphore.configure(image=self._red)

    def gray(self):
        self._semaphore.configure(image=self._gray)

    def disable(self):
        self._enable.set(False)
        self.gray()

    def enable(self):
        self._enable.set(True)

    def setEndpoint(self, endpoint):
        self._endpoint.set(endpoint)

    def onEnablePanel(self):
        if self._enable.get():
            pub.sendMessage('start_photometer_req', role=self._role, alone=self._own_zp.get())
        else:
            pub.sendMessage('stop_photometer_req', role=self._role)

    def startCalibration(self):
        self._enable.set(True)
        self._own_zp.set(False)

    def stopCalibration(self):
        self._enable.set(False)
        self.clear()


# ============================================================================
#                        CALIBRATION PANEL WIDGETS
# ============================================================================


class CalibrationSettingsPanel(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Settings"), **kwargs)
        self._author = tk.StringVar()
        self._rounds = tk.IntVar()
        self._zp_offset = tk.DoubleVar()
        self._zp_fict = tk.DoubleVar()
        self._update_db = tk.BooleanVar()
        self._update_phot = tk.BooleanVar()
        self._dry_run = tk.BooleanVar()
        self.build()

    def start(self):
        pub.sendMessage('load_calib_config_req')

    def invalid_zp_off(self):
        self._zp_offset.set(0)

    def invalid_zp_fict(self):
        self._zp_fict.set(20.50)

    def build(self):
        widget = ttk.Label(self, text= _("Author"))
        widget.grid(row=0, column=0, padx=10, pady=4, sticky=tk.W)
        widget = ttk.Entry(self, width=16, textvariable=self._author)
        widget.grid(row=0, column=1, padx=4, pady=4, sticky=tk.W)

        widget = ttk.Label(self, text= _("Rounds"))
        widget.grid(row=1, column=0, padx=10, pady=4, sticky=tk.W)
        widget = ttk.Spinbox(self, textvariable=self._rounds, width=3, justify=tk.RIGHT, from_= 1, to=10)
        widget.grid(row=1, column=1, padx=4, pady=4, sticky=tk.W)
        ToolTip(widget, _("Number for calibration rounds"))

        vcmd = (self.register(float_validator), '%P')
        ivcmd = (self.register(self.invalid_zp_off),)
        widget = ttk.Label(self, text= _("ZP Offset"))
        widget.grid(row=2, column=0, padx=10, pady=4, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._zp_offset, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=2, column=1, padx=4, pady=4, sticky=tk.W)
        ToolTip(widget, _("Additiona Zero Point offset to compensate for mechanical deficiencies in the integration sphere"))

        ivcmd = (self.register(self.invalid_zp_fict),)
        widget = ttk.Label(self, text= _("Ficticious ZP"))
        widget.grid(row=3, column=0, padx=10, pady=4, sticky=tk.W)
        widget = ttk.Entry(self, width=6, textvariable=self._zp_fict, justify=tk.RIGHT, validate='focusout', validatecommand=vcmd, invalidcommand=ivcmd)
        widget.grid(row=3, column=1, padx=4, pady=4, sticky=tk.W)
        ToolTip(widget, _("Ficticious, common zero point when performing calibrations"))

        widget = ttk.Checkbutton(self, text= _("Update\nDatabase"), variable=self._update_db, command=self.onUpdateDatabase)
        widget.grid(row=0, column=2, padx=2, pady=4, sticky=tk.W)
        widget = ttk.Checkbutton(self, text= _("Update\nPhotometer"), variable=self._update_phot, command=self.onUpdatePhotometer)
        widget.grid(row=1, column=2, padx=2, pady=4, sticky=tk.EW)
       
        widget = ttk.Button(self, text=_("Save"), command=self.onClickButton)
        widget.grid(row=4, column=0, columnspan=3, padx=2, pady=4)

    def onUpdatePhotometer(self):
        pub.sendMessage('update_photometer_req', flag=self._update_phot.get())

    def onUpdateDatabase(self):
        pub.sendMessage('update_database_req', flag=self._update_db.get())

    def onClickButton(self):
        config = {
            'author': self._author.get(),
            'rounds': self._rounds.get(),
            'offset': self._zp_offset.get(),
            'zp_fict': self._zp_fict.get(),
        }
        pub.sendMessage('save_calib_config_req', config=config)

    def set(self, config):
        self._author.set(config['author'])
        self._rounds.set(config['rounds'])
        self._zp_offset.set(config['offset'])
        self._zp_fict.set(config['zp_fict'])

# ----------------------------------------------------------------------------

class CalibrationStatePanel(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("State"), **kwargs)
        self._round = tk.IntVar()
        self._magdif = tk.DoubleVar()
        self._zp = tk.DoubleVar()
        self._best_freq = tk.DoubleVar()
        self._best_zp = tk.DoubleVar()
        self._best_mag = tk.DoubleVar()
        self._zp_fict = tk.StringVar()
        self._freq_method = tk.StringVar()
        self._zp_method = tk.StringVar()
        self._progress = tk.IntVar()
        self._nrounds  = 0
        self.build()

    def start(self):
        pass

    def build(self):
        widget = ttk.Progressbar(self, 
            variable = self._progress,
            maximum  = 100,  # Express in percentage
            length   = 100, 
            mode     = 'determinate', 
            orient   = tk.HORIZONTAL, 
            value    = 0,
        )
        widget.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=2, pady=5, ipadx=0, ipady=0)
        self._progress_widget = widget

        left_frame = ttk.LabelFrame(self,text= _("Round"))
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=2, pady=2, ipadx=0, ipady=0)

        widget = ttk.Label(left_frame, width=8, text= _("Round #"))
        widget.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(left_frame, width=8, textvariable=self._round, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(left_frame, width=8, text= _("\u0394 Mag."))
        widget.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(left_frame, width=8, textvariable=self._magdif, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(left_frame, width=8, text= _("ZP "))
        widget.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(left_frame, width=8, textvariable=self._zp,  anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=2, pady=2, sticky=tk.W)

        right_frame = ttk.LabelFrame(self,text= _("Summary"))
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=2, pady=2, ipadx=0, ipady=0)

        widget = ttk.Label(right_frame, width=8, text= _("Best freq."))
        widget.grid(row=0, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._best_freq, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=1, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._freq_method, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=0, column=2, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(right_frame, width=8, text= _("Best ZP"))
        widget.grid(row=1, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._best_zp, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=1, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._zp_method, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=1, column=2, padx=2, pady=2, sticky=tk.W)

        widget = ttk.Label(right_frame, width=8, text= _("Best mag."))
        widget.grid(row=2, column=0, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._best_mag, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=1, padx=2, pady=2, sticky=tk.W)
        widget = ttk.Label(right_frame, width=8, textvariable=self._zp_fict, anchor=tk.E, borderwidth=1, relief=tk.SUNKEN)
        widget.grid(row=2, column=2, padx=2, pady=2, sticky=tk.W)

    def set(self, config):
        self._nrounds = int(config['rounds'])


    def updateCalibration(self, count, stats_info):
        self._round.set(count)
        self._magdif.set(round(stats_info['mag_diff'],3))
        self._zp.set(stats_info['zero_point'])
        self._progress.set(count * 100 / self._nrounds)

    def updateSummary(self, summary_info):
        self._best_freq.set(summary_info['freq'])
        self._best_zp.set(summary_info['zero_point'])
        self._best_mag.set(round(summary_info['mag'],2))
        self._freq_method .set(summary_info['freq_method'])
        self._zp_method.set(summary_info['zero_point_method'])
        self._zp_fict.set(f"@ {summary_info['zp_fict']}")

    def clear(self):
        self._round.set(0)
        self._magdif.set(0)
        self._zp.set(0)
        self._best_freq.set(0)
        self._best_zp.set(0)
        self._best_mag.set(0)
        self._zp_fict.set('')
        self._freq_method.set('')
        self._zp_method.set('')
        self._progress.set(0)
       
# ----------------------------------------------------------------------------

class CalibrationPanel(ttk.LabelFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text="Fix me", borderwidth=4, **kwargs)
        self._enable = tk.BooleanVar()
        self._text   = tk.StringVar()
        self.build()

    def start(self):
        self.settings.start()

    def build(self):
        self.settings = CalibrationSettingsPanel(self)
        self.settings.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        self.state = CalibrationStatePanel(self)
        self.state.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)        
        widget = ttk.Checkbutton(self, text= _("Calibration"), variable=self._enable, command=self.onEnablePanel)
        self.configure(labelwidget=widget)


    def onEnablePanel(self):
        if self._enable.get():
            self.state.clear()
            pub.sendMessage('start_calibration_req')
        else:
            pub.sendMessage('stop_calibration_req')

    def updateCalibration(self, count, stats_info):
        self.state.updateCalibration(count, stats_info)

    def updateSummary(self, summary_info):
        self.state.updateSummary(summary_info)

    def stopCalibration(self):
        self._enable.set(False)

# ============================================================================
#                      BATCH MANAGEMENT PANEL WIDGETS
# ============================================================================

class BatchManagemetPanel(ttk.LabelFrame):

    EVENTS = {'open': "open_batch_req", 'close': "close_batch_req", 'purge': "purge_batch_req", 'export': "export_batch_req"}

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, text=_("Batch Management"), borderwidth=4, **kwargs)
        self._command  = tk.StringVar()
        self._email    = tk.BooleanVar()
        self._updated  = tk.BooleanVar()
        self._base_dir = tk.StringVar()
        self._email.set(True)
        self._updated.set(True)
        self._base_dir.set("/tmp/zptess")
        self.build()

    def start(self):
        pass

    def build(self):

        upper_panel = ttk.Frame(self)
        upper_panel.pack(side=tk.TOP,  padx=0, pady=0)
        lower_panel = ttk.Frame(self)
        lower_panel.pack(side=tk.TOP,  padx=0, pady=0)

        cmd_panel    = ttk.LabelFrame(upper_panel, text=_("Actions"))
        cmd_panel.pack(side=tk.LEFT,  padx=3, pady=3)
        export_panel = ttk.LabelFrame(upper_panel, text=_("Export options"))
        export_panel.pack(side=tk.LEFT,  padx=3, pady=3)

        # Commands
        widget = ttk.Radiobutton(cmd_panel, text=_("Open Batch"), variable=self._command, value="open")
        widget.pack(side=tk.TOP, anchor=tk.W, padx=2, pady=2)
        widget = ttk.Radiobutton(cmd_panel, text=_("Close Batch"), variable=self._command, value="close")
        widget.pack(side=tk.TOP, anchor=tk.W, padx=2, pady=2)
        widget = ttk.Radiobutton(cmd_panel, text=_("Purge Batch"), variable=self._command, value="purge")
        widget.pack(side=tk.TOP, anchor=tk.W, padx=2, pady=2)
        widget = ttk.Radiobutton(cmd_panel, text=_("Export Batch"), variable=self._command, value="export")
        widget.pack(side=tk.TOP, anchor=tk.W, padx=2, pady=2)

        # Export options
        widget = ttk.Checkbutton(export_panel, text= _("Email after export"),  variable=self._email)
        widget.pack(side=tk.TOP,  fill=tk.X,padx=6, pady=2)
        widget = ttk.Checkbutton(export_panel, text= _("Only ZP flashed to devices"),  variable=self._updated)
        widget.pack(side=tk.TOP,  fill=tk.X, padx=6, pady=2)
        widget = ttk.Button(export_panel, text=_("Choose folder"), command=self.onChooseFolder)
        widget.pack(side=tk.TOP,   anchor=tk.W, padx=6, pady=2)
        widget = ttk.Entry(export_panel, width=32, textvariable=self._base_dir)
        widget.pack(side=tk.TOP,  fill=tk.X, padx=6, pady=2)

        # Lower panel
        widget = ttk.Button(lower_panel, text=_("Execute"), command=self.onClickButton)
        widget.pack(side=tk.TOP,  padx=5, pady=5)

    def onChooseFolder(self):
        base_dir = tk.filedialog.askdirectory()
        self._base_dir.set(base_dir) 
      

    def onClickButton(self):
        cmd = self._command.get()
        args = {'base_dir': self._base_dir.get(), 'email_flag': self._email.get(), 'update': self._updated.get()}
        if cmd:
            pub.sendMessage(self.EVENTS[cmd], args=args)

       

