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

from twisted.application.service import Application, IServiceCollection

#--------------
# local imports
# -------------

from zptess            import STATS_SERVICE, TEST_PHOTOMETER_SERVICE, REF_PHOTOMETER_SERVICE
from zptess.logger     import startLogging
from zptess.config     import read_options
from zptess.stats      import StatsService
from zptess.photometer import PhotometerService

# ====
# Main
# ====

options, cmdline_opts = read_options()
startLogging(console=cmdline_opts.console, filepath=cmdline_opts.log_file)

# ------------------------------------------------
# Assemble application from its service components
# ------------------------------------------------

application = Application("zptess")
serviceCollection = IServiceCollection(application)

if cmdline_opts.dry_run or cmdline_opts.zero_point is not None:
    testService = PhotometerService(options['test'],False)
    testService.setName(TEST_PHOTOMETER_SERVICE)
    testService.setServiceParent(serviceCollection)
else:
    referenceService = PhotometerService(options['reference'],True)
    referenceService.setName(REF_PHOTOMETER_SERVICE)
    referenceService.setServiceParent(serviceCollection)
    testService = PhotometerService(options['test'],False)
    testService.setName(TEST_PHOTOMETER_SERVICE)
    testService.setServiceParent(serviceCollection)
    statsService = StatsService(options['stats'])
    statsService.setName(STATS_SERVICE)
    statsService.setServiceParent(serviceCollection)


__all__ = [ "application" ]