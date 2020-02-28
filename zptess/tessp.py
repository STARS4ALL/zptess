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


__all__ = [
    "TESSProtocol",
    "TESSProtocolFactory",
]