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
import re
import csv
import datetime
import os.path

# -------------
# Other modules
# -------------

import requests

# ---------------
# Twisted imports
# ---------------

from twisted                   import __version__ as __twisted_version__
from twisted.logger            import Logger, LogLevel
from twisted.internet          import task, reactor, defer
from twisted.internet.defer    import Deferred, inlineCallbacks, returnValue
from twisted.internet.threads  import deferToThread
#from twisted.internet.protocol import Protocol
#from twisted.web.client        import Agent
#from twisted.web.http_headers  import Headers

#--------------
# local imports
# -------------

from zptess import __version__
from zptess.config import VERSION_STRING, loadCfgFile
from zptess.logger import setLogLevel

from zptess.service.reloadable import MultiService
from zptess.config   import cmdline
from zptess.protocol import TESSProtocolFactory
from zptess.serial   import SerialService
from zptess.tcp      import MyTCPService
from zptess.stats    import StatsService    



# ----------------
# Module constants
# ----------------

TSTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

REGEXP = {
    # These apply to the /config page
    'name'  : re.compile(r".+(stars\d+)"),       
    'mac'   : re.compile(r".+MAC: ([0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2}:[0-9A-Fa-f]{1,2})"),       
    'zp'    : re.compile(r".+ZP: (\d{1,2}\.\d{1,2})"),  
    # This applies to the /setconst?cons=nn.nn page
    'flash' : re.compile(r"New Zero Point (\d{1,2}\.\d{1,2})")     
}



# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace='zptess')

# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------    
# -----------------------------------------------------------------------------  


class TESSService(MultiService):

    # Service name
    NAME = 'ZPTESS'
    # Queue names, by priority
    QNAMES = ['test','reference']
    # Queue sizes
    QSIZES = [ 15, 15, 10, 10*24*60, 10*24*60]


    def __init__(self, options, cfgFilePath):
        MultiService.__init__(self)
        setLogLevel(namespace='tess', levelStr=options['log_level'])
        self.cfgFilePath = cfgFilePath
        self.options     = options
        cmdline_options  = cmdline()
        self.update      = cmdline_options.update
        self.author      = cmdline_options.author
        self.serialService = None
        self.statsService  = None
        self.tcpService    = None
        self.tess_name     = None
        self.tess_mac      = None
        self.old_zp        = None
        self.factory       = TESSProtocolFactory()

    @inlineCallbacks
    def reloadService(self, options):
        '''
        Reload application parameters
        '''
        log.warn("{tess} config being reloaded", tess=VERSION_STRING)
        try:
            options  = yield deferToThread(loadCfgFile, self.cfgFilePath)
        except Exception as e:
            log.error("Error trying to reload: {excp!s}", excp=e)
        else:
            self.options                  = options['tess']
            MultiService.reloadService(self, options)
           

    def startService(self):
        '''
        Starts only two services (serial & probe) and see if we can continue.
        '''
        log.info('starting {name} {version} using Twisted {tw_version}', 
            name=self.name,
            version=__version__, 
            tw_version=__twisted_version__)
        self.serialService  = self.getServiceNamed(SerialService.NAME)
        self.serialService.setFactory(self.factory) 
        self.tcpService   = self.getServiceNamed(MyTCPService.NAME)
        self.tcpService.setFactory(self.factory) 
        self.statsService = self.getServiceNamed(StatsService.NAME)
        self._getTessInfo()
        self.statsService.testname = self.tess_name
        
        try:
            self.serialService.startService()
            self.statsService.startService()
            self.tcpService.startService()
        except Exception as e:
            log.failure("{excp!s}", excp=e)
            log.critical("Problems initializing {name}. Exiting gracefully", 
                name=self.serialService.name)
            reactor.callLater(0,reactor.stop)   # reactor is no yet running here ...

    @inlineCallbacks
    def stopService(self):
        log.info("Stopping other services")
        yield self.serialService.stopService()
        yield self.tcpService.stopService()
        reactor.stop()

    # ----------------------------------
    # Event Handlers from child services
    # ----------------------------------

    def onReading(self, reading, who):
        '''
        Adds last visual magnitude estimate
        and pass it upwards
        '''
        if who == self.serialService:
            self.statsService.queue['reference'].append(reading)
        elif who == self.tcpService:
            self.statsService.queue['test'].append(reading)
        else:
            log.error("Unknown queue")

    
    @inlineCallbacks
    def onStatsComplete(self, stats):
        yield self.statsService.stopService()
        if self.update:
            log.info("updating {tess} ZP to {zp}", tess=self.tess_name, zp=stats['zp'])
            # This should not be synchronous, but I could not make it work either with
            # the Twisted Agent or even deferring to thread
            self._flashZeroPoint(stats['zp'])   
        else:
            log.info("skipping updating of {tess} ZP",tess=self.tess_name)

        yield deferToThread(self._exportCSV, stats)
        yield self.stopService()
        

    # --------------------
    # Scheduler Activities
    # --------------------

    
    

    # ----------------------
    # Other Helper functions
    # ----------------------

    def _getTessInfo(self):
        '''Contact the TESS-W web server and get its name, MAC & current ZP'''
        try:
            log.debug("requesting URL {url}", url=self.options["state_url"])
            resp = requests.get(self.options["state_url"], timeout=(2,5))
            resp.raise_for_status()
            self.text  = resp.text
        except Exception as e:
            log.error("{e}",e=e)
            sys.exit(1)
        else:
            matchobj = REGEXP['name'].search(self.text)
            self.tess_name = matchobj.groups(1)[0]
            log.info("[TEST] TESS-W name: {name}", name=self.tess_name)
            matchobj = REGEXP['mac'].search(self.text)
            self.tess_mac = matchobj.groups(1)[0]
            log.info("[TEST] TESS-W MAC : {name}", name=self.tess_mac)
            matchobj = REGEXP['zp'].search(self.text)
            self.old_zp = float(matchobj.groups(1)[0])
            log.info("[TEST] TESS-W ZP  : {name} (old)", name=self.old_zp)


    def _exportCSV(self, stats):
        '''Exports summary statistics to a common CSV file'''
        log.debug("Appending to CSV file {file}",file=self.options['csv_file'])
        # Adding metadata to the estimation
        stats['mac']     = self.tess_mac    # Is it station or AP MAC ?????
        stats['tstamp']  = (datetime.datetime.utcnow() + datetime.timedelta(seconds=0.5)).strftime(TSTAMP_FORMAT)
        stats['author']  = self.author
        stats['tess']    = self.tess_name
        stats['updated'] = self.update
        stats['old_zp']  = self.old_zp
        # transform dictionary into readable header columns for CSV export
        oldkeys = ['tess', 'testMag', 'testFreq', 'refMag', 'refFreq', 'magDiff', 'zp', 'old_zp', 'mac', 'tstamp', 'author', 'updated']
        newkeys = ['Name', 'Magnitud TESS.', 'Frecuencia', 'Magnitud Referencia', 'Frec Ref', 'Offset vs stars3', 'ZP'.'OLD ZP', 'Station MAC', 'Timestamp', 'Author', 'Updated']
        for old,new in zip(oldkeys,newkeys):
            stats[new] = stats.pop(old)
        # CSV file generation
        writeheader = not os.path.exists(self.options['csv_file'])
        with open(self.options['csv_file'], mode='a+') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=newkeys, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            if writeheader:
                writer.writeheader()
            writer.writerow(stats)
        log.info("updated CSV file {file}",file=self.options['csv_file'])


    def _flashZeroPoint(self, zp):
        '''Flash new ZP. Synchronous request to be executed in a separate thread'''
        try:
            url = "{0:s}?cons={1:0.2f}".format(self.options['save_url'], zp)
            log.debug("requesting URL {url}", url=url)
            resp = requests.get(url, timeout=(2,5))
            resp.raise_for_status()
        except Exception as e:
            log.error("{e}",e=e)
        else:
            matchobj = REGEXP['flash'].search(self.text)
            if matchobj:
                flashed_zp = float(matchobj.groups(1)[0])
                log.info("Flashed ZP of {tess} is {fzp}", tess=self.tess_name, fzp=flashed_zp)

    @inlineCallbacks
    def _flash2ZeroPoint(self, zp):
        '''Flash new ZP. Twisted agent way'''
        try:
            agent = Agent(reactor)
            url = "{0:s}?cons={1:0.2f}".format(self.options['save_url'], zp)
            log.debug("requesting URL {url}", url=url)
            headers = Headers({'User-Agent': [userAgent]})
            userAgent = 'Twisted/%s' % (__twisted_version__,)
            response = yield agent.request(b'GET',url, headers, None)
            log.debug("response: {response.code}/{response.phrase}", response=response)
            text = yield readBody(response)
        except Exception as e:
            log.error("{e}",e=e)
        else:
            matchobj = REGEXP['flash'].search(text)
            if matchobj:
                flashed_zp = float(matchobj.groups(1)[0])
                log.info("Flashed ZP of {tess} is {fzp}", tess=self.tess_name, fzp=flashed_zp)
      
            


    

    




        

__all__ = [ "CalibService" ]