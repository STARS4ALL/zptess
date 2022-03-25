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
import sys
import argparse

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.application import service

#--------------
# local imports
# -------------

from zptess import __version__, get_status_code
from zptess import MEAN, MEDIAN, MODE, TESSP, TAS, TESSW

import zptess.utils
from zptess.logger        import startLogging
from zptess.dbase.service import DatabaseService

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
    return zptess.utils.mkendpoint(value)

def createParser():
    global name
    name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
    parser    = argparse.ArgumentParser(prog=name, description='AZOTEA GUI')

    # Global options
    parser.add_argument('--version', action='version', version='{0} {1}'.format(name, __version__))
    parser.add_argument('-d', '--dbase',    type=str, required=True, action='store', metavar='<file path>', help='SQLite database to operate upon')
    parser.add_argument('-c', '--console',  action='store_true',  help='log to console.')
    parser.add_argument('-l', '--log-file', type=str, default=None, action='store', metavar='<file path>', help='log to file')
   
    # --------------------------
    # Create first level parsers
    # --------------------------

    subparser = parser.add_subparsers(dest='command')
    parser_gui  = subparser.add_parser('gui', help='graphical user interface options')
    parser_cli  = subparser.add_parser('cli', help='command line interface options')

    # -----------------------------------------------------------------------------------
    # Arguments for 'gui' command are not needed since they are handled by the GUI itself
    # -----------------------------------------------------------------------------------

    parser_gui.add_argument('-m','--messages', type=str, choices=["ref","test","both"], default=None, help='log photometer messages')

    # -----------------------------
    # Arguments for 'batch' command
    # -----------------------------

    # Calibration related options
    parser_cli.add_argument('-a', '--author',  type=str, nargs='+', required=True, help='person performing the calibration process')
    parser_cli.add_argument('-o', '--offset',  type=float, required=True, help='Additional offset to add to final ZP')
    parser_cli.add_argument('-n', '--rounds',  type=int, default=5, help='how many rounds')
    
    # Statistics related options
    parser_cli.add_argument('-S', '--samples', type=int,   default=None, help='# samples in each round')
    parser_cli.add_argument('-C', '--central', type=str,   default=None, choices=[MEDIAN,MEAN,MODE], metavar='<estimator>', help='central tendency estimator')
    parser_cli.add_argument('-P', '--period',  type=float, default=None, action='store', metavar='<float>', help='Wait period between statistics')

    # generic options
    parser_cli.add_argument('-m','--messages', type=str, choices=["ref","test","both"], default=None, help='log photometer messages')
    
    group0 = parser_cli.add_mutually_exclusive_group()
    group0.add_argument('-d', '--dry-run', action='store_true', default=False, help='Connect to TEST photometer, display info and exit')
    group0.add_argument('-u', '--update',  action='store_true', default=False, help='Calibrate and update TEST photometer ZP')
    group0.add_argument('-w', '--write-zero-point', action='store',  default=None, metavar="<float>", type=float, help='connect to TEST photometer, write ZP and exit')
    group0.add_argument('-t', '--test',    action='store_true',  default=False, help="Calibrate but don't update database")
    group0.add_argument('-r', '--read',    type=str, choices=["ref","test","both"], default=None, help="Don't calibrate, read photometers only")

    # test-device related options
    parser_cli.add_argument('-tE', '--test-endpoint',  type=mkendpoint, default=None, metavar='<test endpoint>', help='Test photometer endpoint')
    parser_cli.add_argument('-tM', '--test-model',     type=str, default=None, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()],  help='Test photometer model')
    parser_cli.add_argument('-tO', '--test-old-proto', action='store_true', default=None, help='Use very old protocol instead of JSON')

    # ref.device related options
    parser_cli.add_argument('-rE', '--ref-endpoint',  type=mkendpoint, default=None, metavar='<ref endpoint>', help='Reference photometer endpoint')
    parser_cli.add_argument('-rM', '--ref-model',     type=str, default=None, choices=[TESSW.lower(), TESSP.lower(), TAS.lower()],  help='Ref. photometer model')
    parser_cli.add_argument('-rO', '--ref-old-proto', action='store_true', default=None, help='Use very old protocol instead of JSON')
 
    return parser

# -------------------
# Booting application
# -------------------

options = createParser().parse_args(sys.argv[1:])

startLogging(
    console  = options.console,
    filepath = options.log_file
)

# --------------------
# Application assembly
# --------------------

application = service.Application("zptess")
dbaseService = DatabaseService(
    path        = options.dbase,
)
dbaseService.setName(DatabaseService.NAME)
dbaseService.setServiceParent(application)


if options.command == 'gui':
    from zptess.gui.service import GraphicalService
    guiService = GraphicalService()
    guiService.setName(GraphicalService.NAME)
    guiService.setServiceParent(application)
elif options.command == 'cli':
    from zptess.cli.service      import CommandLineService
    batchService = CommandLineService(
        options = options,
    )
    batchService.setName(CommandLineService.NAME)
    batchService.setServiceParent(application)

# Start the ball rolling
service.IService(application).startService()
reactor.run()
sys.exit(get_status_code())
