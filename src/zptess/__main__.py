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

from zptess.dbase.service      import DatabaseService
from zptess.photometer.service import PhotometerService
from zptess.stats              import StatsService
from zptess.config             import read_options
from zptess.logger             import startLogging

# ----------------
# Module constants
# ----------------

# -----------------------
# Module global variables
# -----------------------


# ------------------------
# Module Utility Functions
# ------------------------

# -------------------
# Applcation assembly
# -------------------

options = read_options()
startLogging(
    console  = options['global']['console'], 
    filepath = options['global']['log_file'],
)

application = service.Application("zptess")

dbaseService = DatabaseService(options['dbase'])
dbaseService.setName(DatabaseService.NAME)
dbaseService.setServiceParent(application)

dry_run = options['test']['dry_run']
write_zero_point = options['test']['write_zero_point']
create_dbase = options['dbase']['create']

if not (dry_run or write_zero_point or create_dbase) :
    statsService = StatsService(options['stats'])
    statsService.setName(StatsService.NAME)
    statsService.setServiceParent(application)

activate = options['global']['activate']
if not create_dbase and activate == 'test':
    testService = PhotometerService(options['test'], False) # REVISAR options (test photometer)
    testService.setName(testService.NAME)
    testService.setServiceParent(application)
elif not create_dbase and activate == 'ref':
    referenceService = PhotometerService(options['reference'], True) # REVISAR options (ref photometer)
    referenceService.setName(referenceService.NAME)
    referenceService.setServiceParent(application)
elif not create_dbase and activate == 'both':
    referenceService = PhotometerService(options['reference'], True) # REVISAR options (ref photometer)
    referenceService.setName(referenceService.NAME)
    referenceService.setServiceParent(application)
    testService = PhotometerService(options['test'], False)  # REVISAR options (test photometer)
    testService.setName(testService.NAME)
    testService.setServiceParent(application)


# Start the ball rolling
service.IService(application).startService()
reactor.run()