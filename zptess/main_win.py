# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

# ---------------
# Twisted imports
# ---------------

from twisted.internet import reactor
from twisted.application.service import IService

#--------------
# local imports
# -------------

from zptess             import VERSION_STRING
from zptess.application import application

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='global')

# ------------------------
# Module Utility Functions
# ------------------------

# ====
# Main
# ====

serv = IService(application)

log.info('{program} {version}', program=serv.name, version=VERSION_STRING) 
print("Starting {0} {1} Windows program".format(serv.name, VERSION_STRING ))
serv.startService()
reactor.run()
print("{0} {1} Windows program stopped".format(serv.name, VERSION_STRING ))
