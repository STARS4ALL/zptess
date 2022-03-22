# ----------------------------------------------------------------------
# Copyright (c) 2014 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# ---------------
# Twisted imports
# ---------------

from zope.interface import Interface

class IPhotometerControl(Interface):
    """
    Interface for all TESS photometer models.
    All photometers should have a way to get its info as a dictionary
    and also a way to set the new zero point.
    """

    def getPhotometerInfo(timeout):
        """
        Gets a photometer information as a dictionary whose keys should be.
        - 'name' - photometer's name like stars3
        - 'model' - photomerter model (TESS-W, TAS, TESS-P)
        - 'mac' - photometer MAC address (or unique identifier if not a mac address)
        - 'firmware' - firmware revision.
        - 'zp' - current zero point
        - ' freq_offset' - dark current frequency

        It can take a while, so it returns a Deferred.
        If the response does not arrive in a certain niumber of seconds
        it triggers an errback.
        @rtype: L{Deferred<defer.Deferred>}
        @return: a L{Deferred<defer.Deferred>} triggered when the implementation
        has the information (usually, C{None}).
        """

    def writeZeroPoint(zp, timeout):
        """
        Writes the new zerp point (a float) to the photometer.
        It can take a while, so it returns a Deferred.
        If the response does not arrive in a certain number of seconds
        it triggers an errback.
        @rtype: L{Deferred<defer.Deferred>}
        @return: a L{Deferred<defer.Deferred>}, triggered when the photometer
        has written the new ZP or when timeout expires C{None}).
        """

    def onPhotommeterInfoResponse(line, tstamp):
        """
        Handles response from a given traǹsport, returning True if handled
        and possibly trigering callbacks for the deferred operations above
        """


class IPayloadDecoder(Interface):
    """
    Interface to decode payloads for all TESS photometer models.
    """

    def onDataReceived(data, tstamp):
        """
        Receives a chunk of data (line from SerialPort or TCP connection and datagram for UDP).
        decodes it and retuns a tuple with two values (handled_flag, message)
        Message is a dictionary with all the different photometer items, including as minimum:
        - 'tstamp'
        - 'freq'
        - 'mag'
        - 'tamb'
        - 'tbox'
       
        """