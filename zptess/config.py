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

try:
    # Python 2
    import ConfigParser
except:
    import configparser as ConfigParser


# ---------------
# Twisted imports
# ---------------

from twisted.logger import LogLevel

#--------------
# local imports
# -------------

from zptess import CSV_FILE, CONFIG_FILE, VERSION_STRING, TESSW, TESSP, TAS

import zptess.utils

# ----------------
# Module constants
# ----------------





# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------


def mkendpoint(value):
    return zptess.utils.mkendpoint(value,"192.168.4.1", 23, 0, 9600)


def cmdline():
    '''
    Create and parse the command line for the tess package.
    Minimal options are passed in the command line.
    The rest goes into the config file.
    '''
    name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
    parser = argparse.ArgumentParser(prog=name)
    parser.add_argument('--version', action='version', version='{0} {1}'.format(name, VERSION_STRING))
    parser.add_argument('-k' , '--console', action='store_true', help='log to console')
    parser.add_argument('-a' , '--author',  type=str, required=True, help='person performing the calibration process')
    group0 = parser.add_mutually_exclusive_group()
    group0.add_argument('-d' , '--dry-run', action='store_true', default=False, help='connect to TEST photometer, display info and exit')
    group0.add_argument('-u' , '--update',  action='store_true', default=False, help='calibrate and update TEST photometer ZP')
    group0.add_argument('-z' , '--zero-point', action='store',  default=None, type=float, help='connect to TEST photometer, write ZP  and exit')
    
    parser.add_argument('--port',      type=mkendpoint, default="tcp",     metavar='<test endpoint>', help='Test photometer endpoint')
    parser.add_argument('--model',     type=str, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()], required=True, help='Test photometer model')
    parser.add_argument('--ref-port',  type=mkendpoint, default="serial:0", metavar='<ref endpoint>', help='Reference photometer port')
    parser.add_argument('--ref-model', type=str, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()], default=TESSW.lower(), help='Reference photometer port')
 
    parser.add_argument('-i', '--iterations',  type=int, help='process iterations')
    parser.add_argument('-n', '--number',      type=int, help='# samples in each iteration')

    parser.add_argument('-m', '--messages', type=str, choices=["none","ref","test","both"], default="none", help='display protocol messages.')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-v', '--verbose',  action='store_true', help='verbose output')
    group2.add_argument('-q', '--quiet',    action='store_true', help='quiet output')
    

    parser.add_argument('--config',   type=str, default=CONFIG_FILE, action='store', metavar='<config file>', help='detailed configuration file')
    parser.add_argument('--log-file', type=str, default=None,    action='store', metavar='<log file>', help='log file path')
    parser.add_argument('--csv-file', type=str, default=CSV_FILE,action='store', metavar='<csv file>', help='calibration file path')
    parser.add_argument('--zp-fict', type=float, action='store', metavar='<Zero Point>', help='override ficticious zero point in the config value with given value')
    parser.add_argument('--zp-abs',  type=float, action='store', metavar='<Zero Point>', help='override absolute zero point in the config value with given value')

    return parser.parse_args()

def select_log_level_for(who,gen_level,msg_level):

   
    ref = {
        'verbose': {'none': 'warn', 'ref': 'debug', 'test': 'warn', 'both': 'debug'},
        'normal' : {'none': 'warn', 'ref': 'info',  'test': 'warn', 'both': 'info'},
        'quiet'  : {'none': 'warn', 'ref': 'warn',  'test': 'warn', 'both': 'warn'},
    }
    test = {
        'verbose': {'none': 'warn', 'ref': 'warn',  'test': 'debug', 'both': 'debug'},    
        'normal' : {'none': 'warn', 'ref': 'warn',  'test': 'info',  'both': 'info'},
        'quiet'  : {'none': 'warn', 'ref': 'warn',  'test': 'warn',  'both': 'warn'},
    }
    general = {
        'verbose': {'none': 'debug', 'ref': 'debug', 'test': 'debug', 'both': 'debug'},    
        'normal' : {'none': 'info',  'ref': 'info',  'test': 'info',  'both': 'info'},
        'quiet'  : {'none': 'warn',  'ref': 'warn',  'test': 'warn',  'both': 'warn'},
    }

    table = {'general': general, 'ref': ref, 'test': test}

    return table[who][gen_level][msg_level]


def loadCmdLine(cmdline_options):
    '''
    Load options from the command line object formed
    Returns a dictionary
    '''

    options = {}

    if cmdline_options.verbose:
        gen_level = "verbose"
    elif cmdline_options.quiet:
        gen_level = "quiet"
    else:
        gen_level = "normal"
    
    msg_level = cmdline_options.messages


    options['reference'] = {}
    options['reference']['model']        = cmdline_options.ref_model.upper()
    options['reference']['endpoint']     = cmdline_options.ref_port
    options['reference']['log_level']    = select_log_level_for("general",gen_level, msg_level)
    options['reference']['log_messages'] = select_log_level_for("ref",gen_level, msg_level)
  
    options['test'] = {}
    options['test']['model']          = cmdline_options.model.upper()
    options['test']['endpoint']       = cmdline_options.port
    options['test']['dry_run']        = cmdline_options.dry_run
    options['test']['zero_point']     = cmdline_options.zero_point
    options['test']['log_level']      = select_log_level_for("general",gen_level, msg_level)
    options['test']['log_messages']   = select_log_level_for("test",gen_level, msg_level)

    options['stats'] = {}
    if cmdline_options.number is not None:
        options['stats']['size']      = cmdline_options.number
    if cmdline_options.iterations is not None:
        options['stats']['rounds']    = cmdline_options.iterations
    if cmdline_options.zp_fict is not None:
        options['stats']['zp_fict']   = cmdline_options.zp_fict
    if cmdline_options.zp_abs is not None:
        options['stats']['zp_abs']    = cmdline_options.zp_abs
    options['stats']['log_level']     = select_log_level_for("general",gen_level, msg_level)
    options['stats']['author']        = cmdline_options.author
    options['stats']['update']        = cmdline_options.update
    options['stats']['csv_file']      = cmdline_options.csv_file
    
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
    options['stats']['zp_abs']        = parser.getfloat("stats","zp_abs")
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
    cmdline_opts = loadCmdLine(cmdline_obj)
    config_file  =  cmdline_obj.config
    if config_file:
       file_opts  = loadCfgFile(config_file)
       for key in file_opts.keys():
            options[key] = zptess.utils.merge_two_dicts(file_opts[key], cmdline_opts[key])
    else:
       file_opts = {}
       options = cmdline_opts
    return options, cmdline_obj

__all__ = ["VERSION_STRING", "read_options"]
