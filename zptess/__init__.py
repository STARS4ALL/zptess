# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------


#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import os
import os.path
import sys

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

from ._version import get_versions

# ----------------
# Module constants
# ----------------

__version__ = get_versions()['version']

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

VERSION_STRING = "{0} on Python {1}.{2}".format(__version__, sys.version_info.major, sys.version_info.minor)

STATS_SERVICE           = 'Statistics Service'
TEST_PHOTOMETER_SERVICE = 'Test Photometer'
REF_PHOTOMETER_SERVICE  = 'Reference Photometer'
TSTAMP_FORMAT           = "%Y-%m-%dT%H:%M:%SZ"


# Default config file path
if os.name == "nt":
    CONFIG_FILE = os.path.join("C:\\", "zptess",  "config.ini")
    LOG_FILE    = os.path.join("C:\\", "zptess", "zptess.log")
    CSV_FILE    = os.path.join("C:\\", "zptess", "zptess.csv")
else:
    CONFIG_FILE = os.path.join("/", "etc", "zptess", "config.ini")
    LOG_FILE    = os.path.join("/", "var", "log", "zptess.log")
    CSV_FILE    = os.path.join("/", "var", "zptess", "zptess.csv")

# -----------------------
# Module global variables
# -----------------------

del get_versions
