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

from twisted.internet import task, reactor

#--------------
# local imports
# -------------

from zptess.service.reloadable import Service, MultiService, Application
from zptess.logger import sysLogInfo,  startLogging
from zptess.config import VERSION_STRING, cmdline, loadCfgFile


from zptess.tess      import TESSService
from zptess.serial    import SerialService 
from zptess.tcp       import MyTCPService 
from zptess.stats     import StatsService    



# Read the command line arguments and config file options
cmdline_opts = cmdline()
config_file = cmdline_opts.config
if config_file:
   options  = loadCfgFile(config_file)
else:
   options = None

# Start the logging subsystem

# Default config file path
if os.name == "nt":
    LOG_FILE=os.path.join("C:\\", "zptess", "zptess.log")
else:
    LOG_FILE=os.path.join("/", "var", "log", "zptess.log")

startLogging(console=cmdline_opts.console, filepath=LOG_FILE)

# ------------------------------------------------
# Assemble application from its service components
# ------------------------------------------------

application = Application("zptess")

tessService  = TESSService(options['tess'],config_file)
tessService.setName(TESSService.NAME)
tessService.setServiceParent(application)

serialService = SerialService(options['serial'])
serialService.setName(SerialService.NAME)
serialService.setServiceParent(tessService)

tcpService = MyTCPService(options['tcp'])
tcpService.setName(MyTCPService.NAME)
tcpService.setServiceParent(tessService)

statsService = StatsService(options['stats'])
statsService.setName(StatsService.NAME)
statsService.setServiceParent(tessService)

# --------------------------------------------------------
# Store direct links to subservices in our manager service
# --------------------------------------------------------


__all__ = [ "application" ]