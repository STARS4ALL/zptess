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

cmdline_opts, file_opts = read_options()
startLogging(console=cmdline_opts.console, filepath=cmdline_opts.log_file)

# ------------------------------------------------
# Assemble application from its service components
# ------------------------------------------------

application = Application("zptess")

statsService = StatsService(file_opts['stats'], cmdline_opts)
statsService.setName(StatsService.NAME)
statsService.setServiceParent(application)

referenceService = PhotometerService(file_opts['reference'],cmdline_opts,True)
referenceService.setName('reference')
referenceService.setServiceParent(application)

testService = PhotometerService(file_opts['test'],cmdline_opts,False)
testService.setName('test')
testService.setServiceParent(application)

# tessService  = TESSService(options['tess'],config_file)
# tessService.setName(TESSService.NAME)
# tessService.setServiceParent(application)

# serialService = SerialService(options['serial'])
# serialService.setName(SerialService.NAME)
# serialService.setServiceParent(tessService)

# tcpService = MyTCPService(options['tcp'])
# tcpService.setName(MyTCPService.NAME)
# tcpService.setServiceParent(tessService)

# statsService = StatsService(options['stats'])
# statsService.setName(StatsService.NAME)
# statsService.setServiceParent(tessService)

# --------------------------------------------------------
# Store direct links to subservices in our manager service
# --------------------------------------------------------


__all__ = [ "application" ]