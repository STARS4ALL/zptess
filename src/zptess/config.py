# ----------------------------------------------------------------------
# Copyright (c) 2020
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

import os
import os.path
import sys
import datetime
import argparse


#--------------
# local imports
# -------------

import zptess.utils 
from zptess import VERSION_STRING, TEST_IP, TESSW, TESSP, TAS, TSTAMP_SESSION_FMT

# ----------------
# Module constants
# ----------------

DBASE    = "zptess.db"

REF_PORT = 'serial:0'
REF_NAME = "stars3"
REF_MAC  = "18:FE:34:CF:E9:A3"

TEST_PORT  = 'tcp'

TEST_TELNET_PORT = 23
TEST_SERIAL_PORT = 0
TEST_BAUD = 9600


ITERATIONS = 5
SAMPLES    = 125

# Ficticious ZP to establish comparisons
# We keep it as 20.50 to calculate magnitudes in the same way as 
# Cristobal's TESS Windows program
ZP_FICT = 20.50

# Calibrated Reference ZP to establish comparisons
# as measured by LICA for stars3 reference photometer
REF_ZP_ABS  = 20.44

MEDIAN  = "median"
AVERAGE = "mean"
MODE    = 'mode'

SECS = 5


# -----------------------
# Module global variables
# -----------------------

# ------------------------
# Module Utility Functions
# ------------------------


def mkendpoint(value):
    return zptess.utils.mkendpoint(value, TEST_IP, TEST_TELNET_PORT, TEST_SERIAL_PORT, TEST_BAUD)


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
    parser.add_argument('-a' , '--author',  type=str, nargs='+', required=True, help='person performing the calibration process')
    parser.add_argument('-t' , '--test',   action='store_true', default=False, help='run calibration but do not update the database')
    parser.add_argument('-o' , '--offset',  type=float, required=True, help='Additional offset to add to final ZP')

    group0 = parser.add_mutually_exclusive_group()
    group0.add_argument('-c' , '--create', action='store_true', default=False, help='Create the database and exit')
    group0.add_argument('-d' , '--dry-run', action='store_true', default=False, help='connect to TEST photometer, display info and exit')
    group0.add_argument('-u' , '--update',  action='store_true', default=False, help='calibrate and update TEST photometer ZP')
    group0.add_argument('-w' , '--write-zero-point', action='store',  default=None, type=float, help='connect to TEST photometer, write ZP and exit')
    
    parser.add_argument('--port',      type=mkendpoint, default=TEST_PORT, metavar='<test endpoint>', help='Test photometer endpoint')
    parser.add_argument('--model',     type=str, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()], default=TESSW.lower(), help='Test photometer model')
    parser.add_argument('--old-protocol',  action='store_true', default=False, help='Use very old protocol instead of JSON')

    parser.add_argument('--ref-port',  type=mkendpoint, default=REF_PORT, metavar='<ref endpoint>', help='Reference photometer port')
    parser.add_argument('--ref-model', type=str, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()], default=TESSW.lower(), help='Ref. photometer model')
    parser.add_argument('--ref-old-protocol',  action='store_true', default=False, help='Use very old protocol instead of JSON')
 
    parser.add_argument('--execute',  type=str, choices=["none","ref","test","both"], default="both", help='execute photometer readings')
    parser.add_argument('-m', '--messages', type=str, choices=["none","ref","test","both"], default="none", help='display protocol messages.')
    group2 = parser.add_mutually_exclusive_group()
    group2.add_argument('-v', '--verbose',  action='store_true', help='verbose output')
    group2.add_argument('-q', '--quiet',    action='store_true', help='quiet output')
    
    parser.add_argument('--activate', type=str, choices=["none","ref","test","both"], default="both", help='activate photometer readings')
    parser.add_argument('--dbase',    type=str, default=DBASE, action='store', metavar='<SQLite database>', help='SQLite database to operate upon')
    parser.add_argument('--log-file', type=str, default=None,    action='store', metavar='<log file>', help='log file path')
   
    parser.add_argument('--central', type=str,  default=MEDIAN, choices=[MEDIAN,AVERAGE,MODE], metavar='<estimator>', help='central tendency estimator')
    parser.add_argument('--seconds',  type=float, default=SECS, action='store', metavar='<secs.>', help='How long do we wait between measurements')
    parser.add_argument('-r', '--rounds',  type=int, default=ITERATIONS, help='how many rounds')
    parser.add_argument('-s', '--samples', type=int, default=SAMPLES,    help='# samples in each round')

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



def read_options():
    '''
    Load options from the command line object formed
    Returns a dictionary
    '''
    # strip microseconds in sessions
    session = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)
    cmdline_options  = cmdline()
    options = {}

    if cmdline_options.verbose:
        gen_level = "verbose"
    elif cmdline_options.quiet:
        gen_level = "quiet"
    else:
        gen_level = "normal"
    
    msg_level = cmdline_options.messages

    options['global'] = {}
    options['global']['console']  = cmdline_options.console
    options['global']['log_file'] = cmdline_options.log_file
    options['global']['activate'] = cmdline_options.activate

    if cmdline_options.dry_run or cmdline_options.write_zero_point: 
        options['global']['activate'] = 'test'
    
    options['dbase'] = {}
    options['dbase']['path']     = cmdline_options.dbase
    options['dbase']['session']  = session
    options['dbase']['test']     = cmdline_options.test
    options['dbase']['author']   = ' '.join(cmdline_options.author)
    options['dbase']['create']   = cmdline_options.create

    options['reference'] = {}
    options['reference']['session']      = session
    options['reference']['endpoint']     = cmdline_options.ref_port
    options['reference']['model']        = cmdline_options.ref_model.upper()
    options['reference']['log_level']    = select_log_level_for("general",gen_level, msg_level)
    options['reference']['log_messages'] = select_log_level_for("ref",gen_level, msg_level)
    options['reference']['size']         = cmdline_options.samples # yes, this is not a mistake
    options['reference']['old_protocol'] = cmdline_options.ref_old_protocol
    
    options['test'] = {}
    options['test']['session']        = session
    options['test']['endpoint']       = cmdline_options.port
    options['test']['model']          = cmdline_options.model.upper()
    options['test']['log_level']      = select_log_level_for("general",gen_level, msg_level)
    options['test']['log_messages']   = select_log_level_for("test",gen_level, msg_level)
    options['test']['size']           = cmdline_options.samples # yes, this is not a mistake
    options['test']['old_protocol']   = cmdline_options.old_protocol
    options['test']['dry_run']        = cmdline_options.dry_run
    options['test']['write_zero_point'] = cmdline_options.write_zero_point
   

    options['stats'] = {}
    options['stats']['size']      = cmdline_options.samples # yes, this is not a mistake
    options['stats']['rounds']    = cmdline_options.rounds
    options['stats']['session']   = session
    options['stats']['log_level'] = select_log_level_for("general",gen_level, msg_level)
    options['stats']['update']    = cmdline_options.update
    options['stats']['central']   = cmdline_options.central
    options['stats']['size']      = cmdline_options.samples
    options['stats']['rounds']    = cmdline_options.rounds
    options['stats']['period']    = cmdline_options.seconds
    options['stats']['offset']    = cmdline_options.offset
        
    return options




__all__ = ["VERSION_STRING", "read_options"]
