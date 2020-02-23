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
import os
import os.path
import argparse
import errno
import copy

# Only Python 2
import ConfigParser

# ---------------
# Twisted imports
# ---------------

from twisted.logger import LogLevel

#--------------
# local imports
# -------------

from zptess.utils import chop
from zptess import __version__

# ----------------
# Module constants
# ----------------


VERSION_STRING = "zptess/{0}/Python {1}.{2}".format(__version__, sys.version_info.major, sys.version_info.minor)

# Default config file path
if os.name == "nt":
    CONFIG_FILE=os.path.join("C:\\", "zptess",  "config.ini")
    LOG_FILE=os.path.join("C:\\", "zptess", "zptess.log")
else:
    CONFIG_FILE=os.path.join("/", "etc", "zptess", "config.ini")
    LOG_FILE=os.path.join("/", "var", "log", "zptess.log")


# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

def merge_two_dicts(d1, d2):
    '''Valid for Python 2 & Python 3'''
    merged = d1.copy()   # start with d1 keys and values
    merged.update(d2)    # modifies merged with d2 keys and values & returns None
    return merged


def toEndpointString(port):
    '''Helps forming and endpoint string from cmd line options'''
    if port == "tcp":
        result = "tcp:192.168.4.1:23"
    else:
        result = "serial:" + port + ":9600"
    return result



def cmdline():
    '''
    Create and parse the command line for the tess package.
    Minimal options are passed in the command line.
    The rest goes into the config file.
    '''
    parser = argparse.ArgumentParser(prog='zptess')
    parser.add_argument('--version',        action='version', version='{0}'.format(VERSION_STRING))
    parser.add_argument('-k' , '--console', action='store_true', help='log to console')
    parser.add_argument('-d' , '--dry-run', action='store_true', help='connect to TEST photometer, display info and exit')
    parser.add_argument('-u' , '--update',  action='store_true', help='automatically update photometer with new calibrated ZP')
    parser.add_argument('-a' , '--author',  type=str, required=True, help='person performing the calibration process')
    
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument('--tess-w', type=str, default="tcp",          action='store', metavar='<optional serial port device>', help='Calibrate a TESS-W')
    group1.add_argument('--tess-p', type=str, default="/dev/ttyUSB1", action='store', metavar='<serial port device>', help='Calibrate a TESS-P using specified serial port')
    group1.add_argument('--tas',    type=str, default="/dev/ttyUSB1", action='store', metavar='<serial port device>', help='Calibrate a TAS using specified serial port')
  
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-v', '--verbose',  action='store_true', help='verbose output')
    group2.add_argument('-m', '--messages', action='store_true', help='verbose output with serial port messages shown')
    group2.add_argument('-q', '--quiet',    action='store_true', help='quiet output')
 
    parser.add_argument('--ref-port', type=str, default="/dev/ttyUSB0", action='store', metavar='<serial port device>', help='Reference photometer serial port')
    parser.add_argument('--config',   type=str, default=CONFIG_FILE, action='store', metavar='<config file>', help='detailed configuration file')
    parser.add_argument('--log-file', type=str, default=LOG_FILE,    action='store', metavar='<log file>', help='log file path')

    return parser.parse_args()

def loadCmdLine(cmdline_options):
    '''
    Load options from the command line object formed
    Returns a dictionary
    '''

    options = {}
    
    if cmdline_options.verbose:
        log_level     = "debug"
        log_messages = False
    elif cmdline_options.messages:
        log_level    = "debug"
        log_messages = True
    elif cmdline_options.quiet:
        log_level    = "warn"
        log_messages = False
    else:
        log_level    = "info"
        log_messages = False

    if cmdline_options.tess_w:
        endpoint = toEndpointString(cmdline_options.tess_w)
        model = "TESS-W"
    elif cmdline_options.tess_p:
        endpoint = toEndpointString(cmdline_options.tess_p)
        model = "TESS-P"
    else:
        endpoint = toEndpointString(cmdline_options.tas)
        model = "TAS"

    options['reference'] = {}
    options['reference']['model']        = "TESS-W"
    options['reference']['endpoint']     = toEndpointString(cmdline_options.ref_port)
    options['reference']['log_level']    = log_level
    options['reference']['log_messages'] = log_messages
  
    options['test'] = {}
    options['test']['model']          = model
    options['test']['endpoint']       = endpoint
    options['test']['log_level']      = log_level
    options['test']['log_messages']   = log_messages

    options['stats'] = {}
    options['stats']['log_level']     = log_level
   
    return options

def loadCfgFile(path):
    '''
    Load options from configuration file whose path is given
    Returns a dictionary
    '''

    if path is None or not (os.path.exists(path)):
        raise IOError(errno.ENOENT,"No such file or directory", path)

    options = {}
    parser  = ConfigParser.RawConfigParser()
    # str is for case sensitive options
    #parser.optionxform = str
    parser.read(path)

    options['reference'] = {}
    options['reference']['endpoint']      = parser.get("reference","endpoint")
    options['reference']['log_messages']  = parser.getboolean("reference","log_messages")
  
    options['test'] = {}
    options['test']['endpoint']       = parser.get("test","endpoint")
    options['test']['log_messages']   = parser.getboolean("test","log_messages")

    options['stats'] = {}
    options['stats']['refname']       = parser.get("stats","refname")
    options['stats']['zp_fict']       = parser.getfloat("stats","zp_fict")
    options['stats']['zp_calib']      = parser.getfloat("stats","zp_calib")
    options['stats']['central']       = parser.get("stats","central")
    options['stats']['size']          = parser.getint("stats","size")
    options['stats']['rounds']        = parser.getint("stats","rounds")
    options['stats']['period']        = parser.getint("stats","period")
    options['stats']['state_url']     = parser.get("stats","state_url")
    options['stats']['save_url']      = parser.get("stats","save_url")
    options['stats']['csv_file']      = parser.get("stats","csv_file")
   
    return options


def read_options():
    # Read the command line arguments and config file options
    options = {}
    cmdline_obj  = cmdline()
    config_file  =  cmdline_obj.config
    cmdline_opts = loadCmdLine(cmdline_obj)
    if config_file:
       file_opts  = loadCfgFile(config_file)
       for key in file_opts.keys():
            options[key] = merge_two_dicts(file_opts[key], cmdline_opts[key])
    else:
       file_opts = {}
       options = cmdline_opts

    return options, cmdline_obj

__all__ = ["VERSION_STRING", "read_options"]
