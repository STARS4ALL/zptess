# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

from __future__ import division, absolute_import
import re

# ---------------
# Twisted imports
# ---------------

from twisted.logger               import Logger
from twisted.internet.protocol    import ClientFactory

#--------------
# local imports
# -------------

from zptess.tessbase   import TESSBaseProtocol, TESSBaseProtocolFactory

# -------
# Classes
# -------


class TESSProtocolFactory(TESSBaseProtocolFactory):

    def buildProtocol(self, addr):
        self.log.debug('Factory: Connected.')
        return TESSProtocol(self.namespace)


class TESSProtocol(TESSBaseProtocol):
    label = "TESS-P"

    def __init__(self, namespace):
        super().__init__(namespace)
        self.SOLICITED_RESPONSES.append({
            'name'    : 'name',
            'pattern' : r'^TSP SN: (TSP\w{3})',       
        })
        self.SOLICITED_PATTERNS = [ re.compile(sr['pattern']) for sr in self.SOLICITED_RESPONSES ]


__all__ = [
    "TESSProtocol",
    "TESSProtocolFactory",
]