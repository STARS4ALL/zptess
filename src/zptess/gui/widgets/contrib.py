# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import tkinter as tk
import tkinter.ttk as ttk

######################################
## GENERAL PURPOSE, RESUABLE WIDGETS #
######################################


# From https://stackoverflow.com/questions/3221956/how-do-i-display-tooltips-in-tkinter
# Answser by https://stackoverflow.com/users/3357935/stevoisiak

class ToolTip:
    '''
    create a tooltip for a given widget
    '''
    def __init__(self, widget, text='widget info'):
        self.waittime = 500     #miliseconds
        self.wraplength = 180   #pixels
        self.widget = widget
        self.text = text
        self.widget.bind('<Enter>', self.enter)
        self.widget.bind('<Leave>', self.leave)
        self.widget.bind('<ButtonPress>', self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox('insert')
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # creates a toplevel window
        self.hidetip()
        self.tw = tk.Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry('+%d+%d' % (x, y))
        label = tk.Label(self.tw, text=self.text, justify='left',
                       background='#ffffff', relief='solid', borderwidth=1,
                       wraplength = self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tw
        self.tw= None
        if tw:
            tw.destroy()


class LabelInput(tk.Frame):
    '''A widget containing a label and input together.'''
    def __init__(self, parent, label='', input_class=ttk.Entry,
        input_var=None, input_args=None, label_args=None, tip=None,
        **kwargs):
        super().__init__(parent, **kwargs)
        input_args = input_args or {}
        label_args = label_args or {}
        self._variable = input_var
        if input_class in (ttk.Checkbutton, ttk.Button, ttk.Radiobutton):
            input_args['text'] = label
            input_args['variable'] = input_var
        else:
            self.label = ttk.Label(self, text=label, **label_args)
            self.label.grid(row=0, column=0, sticky=(tk.W + tk.E))
            #self.label.pack(side=tk.TOP)
            input_args['textvariable'] = input_var
        self._input = input_class(self, **input_args)
        self._input.grid(row=1, column=0, sticky=(tk.W + tk.E))
        #self._input.pack(side=tk.TOP)
        self.columnconfigure(0, weight=1)
        if tip:
            ToolTip(self._input, tip)


    def grid(self, sticky=(tk.E + tk.W), **kwargs):
        super().grid(sticky=sticky, **kwargs)


    def pack(self, fill='both', **kwargs):
        super().pack(fill=fill, **kwargs)


    def state(self, state):
        self._input.configure(state=state)

    def get(self):
        try:
            if self._variable:
                return self._variable.get()
            elif type(self._input) == tk.Text:
                return self._input.get('1.0', tk.END)
            else:
                return self._input.get()
        except (TypeError, tk.TclError):
            # happens when numeric fields are empty.
            return ''


    def set(self, value, *args, **kwargs):
        if type(self._variable) == tk.BooleanVar:
            self._variable.set(bool(value))
        elif self._variable:
            self._variable.set(value, *args, **kwargs)
        elif type(self._input) in (ttk.Checkbutton,ttk.Radiobutton):
            if value:
                self._input.select()
            else:
                self._input.deselect()
        elif type(self._input) == tk.Text:
            self._input.delete('1.0', tk.END)
            self._input.insert('1.0', value)
        else: # input must be an Entry-type widget with no variable
            self._input.delete(0, tk.END)
            self._input.insert(0, value)

    def configure(self, **kwargs):
        self._input.configure(**kwargs)

