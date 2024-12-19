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

# Access SQL scripts withing the package
from pkg_resources import resource_filename

# ---------------
# Twisted imports
# ---------------

from twisted  import __version__ as __twisted_version__

#--------------
# local imports
# -------------

from ._version import __version__ as __version__

# ----------------
# Module constants
# ----------------
TEST = 'TEST'
REF  = 'REF.'

MEDIAN = "median"
MEAN   = "mean"
MODE   = 'mode'

# Photometer models
TESSW = "TESS-W"
TESSP = "TESS-P"
TAS   = "TAS"

SERIAL_PORT_PREFIX = "/dev/ttyUSB"

# TESS-W data

TEST_IP    = '192.168.4.1'
TEST_TCP_PORT = 23
TEST_UDP_PORT = 2255
TEST_SERIAL_PORT = 0
TEST_BAUD = 9600

# Timestamp format
TSTAMP_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'

# Condensed timestamp
TSTAMP_SESSION_FMT = '%Y-%m-%dT%H:%M:%S'


# DATABASE RESOURCES
SQL_SCHEMA           = resource_filename(__name__, os.path.join('dbase', 'sql', 'schema.sql'))
SQL_INITIAL_DATA_DIR = resource_filename(__name__, os.path.join('dbase', 'sql', 'initial' ))
SQL_UPDATES_DATA_DIR = resource_filename(__name__, os.path.join('dbase', 'sql', 'updates' ))

# ------------------------
# Module Utility Functions
# ------------------------

def get_status_code():
    return _exit_status_code


def set_status_code(code):
    global _exit_status_code
    _exit_status_code = code

# -----------------------
# Module global variables
# -----------------------

# Assume bad result unless we set it to ok
_exit_status_code = 1

name = os.path.split(os.path.dirname(sys.argv[0]))[-1]

FULL_VERSION_STRING = "{4} {0} on Twisted {1}, Python {2}.{3}".format(
		__version__, 
		__twisted_version__, 
		sys.version_info.major, 
		sys.version_info.minor,
		name)
