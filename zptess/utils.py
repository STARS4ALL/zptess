# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import sys
import datetime
import argparse
import re

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

from zptess import PORT_PREFIX

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------

# setSystemTime function variable
setSystemTime = None

# ------------------------
# Module Utility Functions
# ------------------------

def merge_two_dicts(d1, d2):
    '''Valid for Python 2 & Python 3'''
    merged = d1.copy()   # start with d1 keys and values
    merged.update(d2)    # modifies merged with d2 keys and values & returns None
    return merged

def valid_ip_address(ip):
    '''Validate an IPv4 address returning True or False'''
    return [ 0 <= int(x) < 256 for x in re.split(r'\.', re.match(r'^\d+\.\d+\.\d+\.\d+$',ip).group(0))].count(True) == 4
    

def mkendpoint(value, default_ip, default_port , default_serial, default_baud):
    '''
    Utility to convert command line values to serial or tcp endpoints
    tcp
    tcp::<port>
    tcp:<ip>
    tcp:<ip>:<port>
    serial
    serial::<baud>
    serial:<serial_port>
    serial:<serial_port>:<baud>

    '''
    parts = [ elem.strip() for elem in value.split(':') ]
    length = len(parts)
    if length < 1 or length > 3:
        raise argparse.ArgumentTypeError("Invalid endpoint format {0}".format(value))
    proto = parts[0]
    if proto == "tcp":
        if length == 1:
            ip   = str(default_ip)
            port = "23"
        elif length == 2:
            ip   = parts[1]
            port = str(default_port)
        elif valid_ip_address(parts[1]):
            ip   = parts[1]
            port = parts[2]
        else:
            ip   = str(default_ip)
            port = parts[2]
        result = proto + ':' + ip + ':' + port
    elif proto == "serial":
        if length == 1:
            serial = PORT_PREFIX + str(default_serial)
            baud   = str(default_baud)
        elif length == 2:
            serial = PORT_PREFIX + str(parts[1])
            baud   = str(default_baud)
        elif parts[1] != '':
            serial = PORT_PREFIX + str(parts[1])
            baud   = parts[2]
        else:
            serial = PORT_PREFIX + str(default_serial)
            baud   = parts[2]
        result = proto + ':' + serial + ':' + baud
    else:
        raise argparse.ArgumentTypeError("Invalid endpoint prefix {0}".format(parts[0]))
    return result

def chop(value, sep=None):
    '''Chop a list of strings, separated by sep and 
    strips individual string items from leading and trailing blanks'''
    chopped = [ elem.strip() for elem in value.split(sep) ]
    if len(chopped) == 1 and chopped[0] == '':
        chopped = []
    return chopped


def _win_set_time(dati):
    '''
    dati is a datetime.datetime object
    '''
    
    # http://timgolden.me.uk/pywin32-docs/win32api__SetSystemTime_meth.html
    # pywin32.SetSystemTime(year, month , dayOfWeek , day , hour , minute , second , millseconds )
    ##dayOfWeek = datetime.datetime(time_tuple).isocalendar()[2]
    ##pywin32.SetSystemTime( time_tuple[:2] + (dayOfWeek,) + time_tuple[2:])
    time_tuple = dati.timetuple()
    dayOfWeek = dati.isocalendar()[2]
    pywin32.SetSystemTime( time_tuple[:2] + (dayOfWeek,) + time_tuple[2:])


def _linux_set_time(dati):
    '''
    dati is a datetime.datetime object
    '''
    # /usr/include/linux/time.h:
    #
    # define CLOCK_REALTIME                     0
    CLOCK_REALTIME = 0

    # /usr/include/time.h
    #
    # struct timespec
    #  {
    #    __time_t tv_sec;            /* Seconds.  */
    #    long int tv_nsec;           /* Nanoseconds.  */
    #  };
    class timespec(ctypes.Structure):
        _fields_ = [("tv_sec", ctypes.c_long),
                    ("tv_nsec", ctypes.c_long)]

    librt = ctypes.CDLL(ctypes.util.find_library("rt"))

    ts = timespec()
    time_tuple = dati.timetuple()
    ts.tv_sec = int( time.mktime( dati )) 
    ts.tv_nsec = time_tuple[6] * 1000000 # Millisecond to nanosecond

    # http://linux.die.net/man/3/clock_settime
    librt.clock_settime(CLOCK_REALTIME, ctypes.byref(ts))



if sys.platform=='linux2':
    import ctypes
    import ctypes.util
    import time
    setSystemTime =  _linux_set_time
elif sys.platform=='win32':
    import win32api
    setSystemTime = _win_set_time


__all__ = [
    "chop", 
    "setSystemTime", 
    "valid_ip_address",
    "mkendpoint",
    "merge_two_dicts"
]
