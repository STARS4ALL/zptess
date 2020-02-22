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

def read_options():
    # Read the command line arguments and config file options
    cmdline_opts = cmdline()
    config_file = cmdline_opts.config
    if config_file:
       file_options  = loadCfgFile(config_file)
    else:
       file_options = None
    return cmdline_opts, file_options


def loglevel(cmdline_options):
    if cmdline_options.verbose:
        level = "debug"
    elif cmdline_options.quiet:
        level = "warn"
    else:
        level = "info"
    return level

def cmdline():
    '''
    Create and parse the command line for the tess package.
    Minimal options are passed in the command line.
    The rest goes into the config file.
    '''
    parser = argparse.ArgumentParser(prog='zptess')
    parser.add_argument('--version',        action='version', version='{0}'.format(VERSION_STRING))
    parser.add_argument('-k' , '--console', action='store_true', help='log to console')
    parser.add_argument('-d' , '--dry-run', action='store_true', help='connect to TEST TESS-W, display info and exit')
    parser.add_argument('-u' , '--update',  action='store_true', help='automatically update TESS-W with new calibrated ZP')
    parser.add_argument('-a' , '--author',  type=str, required=True, help='person performing the calibration process')
    parser.add_argument('--config',   type=str, default=CONFIG_FILE, action='store', metavar='<config file>', help='detailed configuration file')
    parser.add_argument('--log-file', type=str, default=LOG_FILE,    action='store', metavar='<log file>', help='log file path')
    
    group1 = parser.add_mutually_exclusive_group(required=True)
    group1.add_argument('--tess-w',  action='store_true', help='Calibrate a TESS-W')
    group1.add_argument('--tess-p',  action='store_true', help='Calibrate a TESS-P')
    group1.add_argument('--tass',    action='store_true', help='Calibrate a TAS')

    group2 = parser.add_mutually_exclusive_group(required=True)
    group2.add_argument('--serial',  action='store_true', help='Calibrate photometer using a serial port')
    group2.add_argument('--tcp',     action='store_true', help='Calibrate photometer using a TCP port')

    group3 = parser.add_mutually_exclusive_group()
    group3.add_argument('-v', '--verbose',  action='store_true', help='verbose output')
    group3.add_argument('-q', '--quiet',    action='store_true', help='quiet output')
 
    return parser.parse_args()


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


__all__ = ["VERSION_STRING", "loadCfgFile", "cmdline"]
