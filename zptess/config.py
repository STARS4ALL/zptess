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
else:
    CONFIG_FILE=os.path.join("/", "etc", "zptess", "config.ini")

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

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
    parser.add_argument('-c' , '--config',  type=str,  default=CONFIG_FILE, action='store', metavar='<config file>', help='detailed configuration file')
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

    options['tess'] = {}
    options['tess']['log_level']  = parser.get("tess","log_level")
    options['tess']['state_url']  = parser.get("tess","state_url")
    options['tess']['save_url']   = parser.get("tess","save_url")
    options['tess']['csv_file']   = parser.get("tess","csv_file")
    
    # options['tess']['host_rtc']   = parser.getboolean("tess","host_rtc")
    # options['tess']['nretries']   = parser.getint("tess","nretries")
    # options['tess']['period']     = parser.getint("tess","period")
    # options['tess']['overlap']    = parser.getint("tess","overlap")
    # options['tess']['shutdown']   = parser.getboolean("tess","shutdown")

    options['serial'] = {}
    options['serial']['endpoint']      = parser.get("serial","endpoint")
    options['serial']['log_level']     = parser.get("serial","log_level")
 
    options['serial']['log_messages']  = parser.getboolean("serial","log_messages")
  
    options['tcp'] = {}
    options['tcp']['endpoint']      = parser.get("tcp","endpoint")
    options['tcp']['log_level']     = parser.get("tcp","log_level")
    options['tcp']['log_messages']  = parser.getboolean("tcp","log_messages")

    options['stats'] = {}
    options['stats']['refname']       = parser.get("stats","refname")
    options['stats']['zp_fict']       = parser.getfloat("stats","zp_fict")
    options['stats']['zp_calib']      = parser.getfloat("stats","zp_calib")
    options['stats']['central']       = parser.get("stats","central")
    options['stats']['size']          = parser.getint("stats","size")
    options['stats']['rounds']        = parser.getint("stats","rounds")
    options['stats']['period']        = parser.getint("stats","period")
    options['stats']['log_level']     = parser.get("stats","log_level")
   
    return options


__all__ = ["VERSION_STRING", "loadCfgFile", "cmdline"]
