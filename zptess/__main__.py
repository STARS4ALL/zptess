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
import sys

# ---------------
# Twisted imports
# ---------------

#--------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


if os.name == "nt":
    import zptess.main_win
elif os.name == "posix":
    import zptess.main_posix
else:
    print("ERROR: unsupported OS {name}".format(name = os.name))
    sys.exit(1)