# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------


# ---------------------
# Third party libraries
# ---------------------

from lica.misc import chop
from lica.asyncio.photometer import Role, Model
from lica.asyncio.photometer.protocol import UdpProtocol, TcpProtocol, SerialProtocol
from lica.asyncio.photometer.payload import JsonPayload, OldPayload
from lica.asyncio.photometer.photinfo import HTMLInfo, DBaseInfo
from lica.asyncio.photometer.photometer import Photometer


class PhotometerBuilder:
    def __init__(self, engine=None):
        self._engine = engine

    def build(
        self, model: Model, role: Role, endpoint: str | None = None, strict: bool = False
    ) -> Photometer:
        url = role.endpoint() if endpoint is None else endpoint
        transport, name, number = chop(url, sep=":")
        number = int(number) if number else 80
        photometer = Photometer(role)

        if role == Role.REF:
            assert model is Model.TESSW, "Reference photometer model should be TESS-W"
            assert transport == "serial", "Reference photometer should use a serial transport"
            assert self._engine is not None, "Database engine is needed for the REF photometer"
            info_obj = DBaseInfo(logger=photometer.log, engine=self._engine)
            transport_obj = SerialProtocol(logger=photometer.log, port=name, baudrate=number)
            decoder_obj = OldPayload(logger=photometer.log, strict=strict)
        else:
            if transport == "serial":
                # Although we are able to get readings from serial port,
                # there is no PhotInfo object available
                # The DBaseInfo is only available for the reference photometer.
                raise NotImplementedError(
                    "Test Photometer calibration not possible using a serial port"
                )
            elif transport == "tcp":
                assert model is Model.TESSW, "Test photometer using TCP should be a TESS-W model"
                info_obj = HTMLInfo(logger=photometer.log, addr=name)
                transport_obj = TcpProtocol(logger=photometer.log, host=name, port=number)
                decoder_obj = OldPayload(log=photometer.log, strict=strict)
            elif transport == "udp":
                assert model is Model.TESSW, "Test photometer using UDP should be a TESS-W model"
                info_obj = HTMLInfo(logger=photometer.log, addr=name)
                transport_obj = UdpProtocol(logger=photometer.log, local_port=number)
                decoder_obj = JsonPayload(logger=photometer.log, strict=strict)
            else:
                raise ValueError(f"Transport {transport} not known")
        photometer.attach(transport_obj, info_obj, decoder_obj)
        return photometer
