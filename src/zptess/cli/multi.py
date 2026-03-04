# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import json
import logging
import asyncio
import statistics

from dataclasses import dataclass
from collections import defaultdict
from logging import Logger
from argparse import Namespace, ArgumentParser
from datetime import datetime, timezone
from typing import Tuple

# -------------------
# Third party imports
# -------------------


from lica.sqlalchemy import sqa_logging
from lica.asyncio.cli import execute

# --------------
# local imports
# -------------

from .. import __version__
from .util import parser as prs
from ..dao import engine

# ----------------
# Module constants
# ----------------

DESCRIPTION = "TESS-W Multi photometer reader tool"

# -----------------------
# Module global variables
# -----------------------

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])
controller = None

# ------------------
# Auxiliar functions
# ------------------

# -----------------
# Auxiliary classes
# -----------------


class UdpProtocol(asyncio.DatagramProtocol):
    def __init__(
        self,
        logger: Logger,
        local_host: str = "0.0.0.0",
        local_port: int = 2255,
        loop: asyncio.AbstractEventLoop | None = None,
        encoding: str = "utf-8",
        newline: bytes = b"\r\n",
    ):
        self.loop = loop or asyncio.get_event_loop()
        self.log = logger
        self.encoding = encoding
        self.newline = newline
        self.local_host = local_host
        self.local_port = local_port
        # Futures for external awaiters
        self.on_data_received: asyncio.Future | None = None
        self.on_conn_lost: asyncio.Future = self.loop.create_future()
        self.log.info("Using %s", self.__class__.__name__)

    async def open(self) -> None:
        self.log.debug("Opening UDP endpoint on (%s, %s)", self.local_host, self.local_port)
        transport, self.protocol = await self.loop.create_datagram_endpoint(
            lambda: self, local_addr=(self.local_host, self.local_port)
        )

    def close(self) -> None:
        self.log.debug("Closing %s transport", self.transport.__class__.__name__)
        self.transport.close()

    # ---------------------------------------
    # The asyncio Protocol callback interface
    # ---------------------------------------

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.log.debug("UDP socket listening to (%s, %s)", self.local_host, self.local_port)
        self.transport = transport

    def connection_lost(self, exc: Exception | None) -> None:
        self.log.debug("Closed UDP endpoint on (%s, %s)", self.local_host, self.local_port)
        if not self.on_conn_lost.cancelled() and not self.on_conn_lost.done():
            self.on_conn_lost.set_result(True)
        if (
            self.on_data_received is not None
            and not self.on_data_received.done()
            and not self.on_data_received.cancelled()
        ):
            self.on_data_received.set_exception(
                ConnectionError("UDP socket closed before incoming message was complete")
            )
        self.transport.close()

    def datagram_received(self, payload: bytes, addr: str):
        now = datetime.now(timezone.utc)
        message = payload.decode(self.encoding, errors="replace")
        try:
            message = json.loads(message)
        except Exception as e:
            self.log.exception(e)
        else:
            if isinstance(message, dict):
                message["seq"] = message["udp"]
                del message["udp"]
                if (
                    self.on_data_received is not None
                    and not self.on_data_received.cancelled()
                    and not self.on_data_received.done()
                ):
                    self.on_data_received.set_result((now, message))

    # ----------------------
    # The iterator interface
    # ----------------------

    def __aiter__(self) -> "UdpProtocol":
        # The iterator is its own async iterator.
        return self

    async def __anext__(self) -> Tuple[datetime, str]:
        if self.on_data_received is not None and not self.on_data_received.done():
            self.on_data_received.cancel()
        self.on_data_received = self.loop.create_future()
        return await self.on_data_received


@dataclass
class Stats:
    mean: float
    median: float
    stdev: float
    mode: float

    def __repr__(self) -> str:
        return f"mean={self.mean:.2f}, \u03c3={self.stdev:.3f}, median={self.median:.2f}, mode={self.mode:.2f}"


# -------------------
# Auxiliary functions
# -------------------


def stats_by_name(hashable) -> dict[str, Stats]:
    stats = dict()
    for name, messages in hashable.items():
        values = [msg["mag"] for msg in messages]
        mean = statistics.fmean(values)
        median = statistics.median_low(values)
        stdev = statistics.stdev(values, xbar=mean)
        modes = statistics.multimode(values)
        stats[name] = Stats(mean=mean, median=median, stdev=stdev, mode=modes[0])
    return stats


async def cli_multi(args: Namespace) -> None:
    meas_session = datetime.now(timezone.utc)
    log.info("Session de medidas %s", meas_session.strftime("%Y-%m-%dT%H:%M:%S"))
    proto = UdpProtocol(log)
    N = args.num_messages
    messages = defaultdict(list)
    await proto.open()
    for i in range(N):
        tstamp, msg = await anext(proto)
        log.info("%s %s",tstamp.strftime("%H:%M:%S.%f"), msg)
        msg["tstamp"] = tstamp
        messages[msg["name"]].append(msg)
    stats = stats_by_name(messages)
    for name, stat in stats.items():
        log.info("%8s => %s", name, stat)


# -----------------
# CLI API functions
# -----------------


def add_args(parser: ArgumentParser):
    subparser = parser.add_subparsers(dest="command", required=True)
    p = subparser.add_parser(
        "test",
        parents=[prs.nmsg()],
        help="Read several test photometers",
    )
    p.set_defaults(func=cli_multi)


async def cli_main(args: Namespace) -> None:
    sqa_logging(args)
    await args.func(args)
    await engine.dispose()


def main():
    """The main entry point specified by pyproject.toml"""
    execute(
        main_func=cli_main,
        add_args_func=add_args,
        name=__name__,
        version=__version__,
        description=DESCRIPTION,
    )


if __name__ == "__main__":
    main()
