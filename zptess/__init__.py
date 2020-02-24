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

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

STATS_SERVICE           = 'Statistics Service'
TEST_PHOTOMETER_SERVICE = 'Test Photometer'
REF_PHOTOMETER_SERVICE  = 'Reference Photometer'
TSTAMP_FORMAT           = "%Y-%m-%dT%H:%M:%SZ"

# -----------------------
# Module global variables
# -----------------------

__version__ = get_versions()['version']
del get_versions
