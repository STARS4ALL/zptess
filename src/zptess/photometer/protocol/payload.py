# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import re
import json

# ---------------
# Twisted imports
# ---------------

from zope.interface               import implementer

#--------------
# local imports
# -------------

from zptess.photometer.protocol.interface import IPayloadDecoder

# ----------------
# Module constants
# ----------------


# -----------------------
# Module global variables
# -----------------------


# ----------------
# Module functions
# ----------------

# ----------
# Exceptions
# ----------


# -------
# Classes
# -------


@implementer(IPayloadDecoder)
class OldPayload:
    """
    Decodes Old Style TESS payload:
    <fH 04606><tA +2987><tO +2481><mZ -0000>
    """

    UNSOLICITED_RESPONSES = (
        {
            'name'    : 'Hz reading',
            'pattern' : r'^<fH([ +]\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
        },
        {
            'name'    : 'mHz reading',
            'pattern' : r'^<fm([ +]\d{5})><tA ([+-]\d{4})><tO ([+-]\d{4})><mZ ([+-]\d{4})>',       
        },
    )
    UNSOLICITED_PATTERNS = [ re.compile(ur['pattern']) for ur in UNSOLICITED_RESPONSES ]

    def __init__(self, label, log, log_msg):
        '''Sets the delimiter to the closihg parenthesis'''
        # LineOnlyReceiver.delimiter = b'\n'
        self.log   = log_msg
        self.label = label
        log.info("{label:6s} Using {who} decoder", label=self.label, who=self.__class__.__name__)
     
    # ----------------------------
    # Incoming Data reception API
    # ---------------------------

    def onDataReceived(self, data, tstamp):
        self.log.info("<== {label:6s} [{l:02d}] {line}", l=len(data), label=self.label, line=data)
        return self._handleUnsolicitedResponse(data, tstamp)
    
    # --------------
    # Helper methods
    # --------------

    def _match_unsolicited(self, line):
        '''Returns matched command descriptor or None'''
        for i, regexp in enumerate(self.UNSOLICITED_PATTERNS, 0):
            matchobj = regexp.search(line)
            if matchobj:
                self.log.debug("matched {pattern}", pattern=self.UNSOLICITED_RESPONSES[i]['name'])
                return self.UNSOLICITED_RESPONSES[i], matchobj
        return None, None


    def _handleUnsolicitedResponse(self, line, tstamp):
        '''
        Handle unsolicited responses from zptess.
        Returns True if handled, False otherwise
        '''
        ur, matchobj = self._match_unsolicited(line)
        if not ur:
            return False, None
        reading = {}
        reading['tbox']   = float(matchobj.group(2))/100.0
        reading['tsky']   = float(matchobj.group(3))/100.0
        reading['zp']     = float(matchobj.group(4))/100.0
        reading['tstamp'] = tstamp
        if ur['name'] == 'Hz reading':
            reading['freq']   = float(matchobj.group(1))/1.0
            self.log.debug("Matched {name}", name=ur['name'])
        elif ur['name'] == 'mHz reading':
            reading['freq'] = float(matchobj.group(1))/1000.0
            self.log.debug("Matched {name}", name=ur['name'])
        else:
            return False, None
        return True, reading



@implementer(IPayloadDecoder)
class JSONPayload:
    """
    Decodes new JSON style TESS payload:
    <fH 04606><tA +2987><tO +2481><mZ -0000>
    """

    def __init__(self, label, log, log_msg):
        self.label = label
        self.log = log_msg
        log.info("{label:6s} Using {who} decoder", label=self.label, who=self.__class__.__name__)

    # ----------------------------
    # Incoming Data reception API
    # ---------------------------

    def onDataReceived(self, data, tstamp):
        self.log.info("<== {label:6s} [{l:02d}] {line}", l=len(data), label=self.label, line=data)
        try:
            reading = json.loads(data)
        except Exception as e:
            return False, None
        else:
            if type(reading) == dict:
                reading['tstamp'] = tstamp
                return True, reading
            else:
                return False, None


#---------------------------------------------------------------------
# --------------------------------------------------------------------
# --------------------------------------------------------------------



__all__ = [
    "JSONPayload",
    "OldPayload",
]
