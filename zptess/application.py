# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import

import os.path

# ---------------
# Twisted imports
# ---------------

from zope.interface    import implementer, Interface
from twisted.internet  import task, reactor, defer
from twisted.persisted import sob
from twisted.python    import components
from twisted.application.service import IService, Service, MultiService, Process

#--------------
# local imports
# -------------

from . import STATS_SERVICE, TEST_PHOTOMETER_SERVICE, REF_PHOTOMETER_SERVICE

from zptess.logger     import sysLogInfo,  startLogging
from zptess.config     import VERSION_STRING, read_options
from zptess.stats      import StatsService
from zptess.photometer import PhotometerService

def Application(name, uid=None, gid=None):
    """
    Return a compound class.
    Return an object supporting the L{IService}, L{IReloadable}, L{IServiceCollection},
    L{IProcess} and L{sob.IPersistable} interfaces, with the given
    parameters. Always access the return value by explicit casting to
    one of the interfaces.
    """
    ret = components.Componentized()
    availableComponents = [MultiService(), Process(uid, gid),
                           sob.Persistent(ret, name)]
    for comp in availableComponents:
        ret.addComponent(comp, ignoreClass=1)
    IService(ret).setName(name)
    return ret  

# ====
# Main
# ====

options, cmdline_opts = read_options()
startLogging(console=cmdline_opts.console, filepath=cmdline_opts.log_file)

# ------------------------------------------------
# Assemble application from its service components
# ------------------------------------------------

application = Application("zptess")

statsService = StatsService(options['stats'])
statsService.setName(STATS_SERVICE)
statsService.setServiceParent(application)

referenceService = PhotometerService(options['reference'],True)
referenceService.setName(REF_PHOTOMETER_SERVICE)
referenceService.setServiceParent(application)

testService = PhotometerService(options['test'],False)
testService.setName(TEST_PHOTOMETER_SERVICE)
testService.setServiceParent(application)


__all__ = [ "application" ]