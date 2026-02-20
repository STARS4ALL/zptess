# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import math
import logging
import asyncio
import contextlib
import statistics
from typing import Any

# -------------------
# Third party imports
# -------------------

from lica.asyncio.photometer import Role

# --------------
# local imports
# -------------

from ...controller.photometer import Controller


def mag(zp: float, freq_offset: float, freq: float):
    """Single sample magnitude calculation that takes into account zero frequencies"""
    f = freq - freq_offset
    return (float(zp) - 2.5 * math.log10(f)) if f > 0.0 else math.inf


def log_msgs_stats(msgs: list[dict[str, Any], ...], controller: Controller, role: Role, name: str) -> None:
    freqs = [msg["freq"] for msg in msgs]
    mean = statistics.fmean(freqs)
    median = statistics.median_low(freqs)
    stddev_mean = statistics.stdev(freqs, xbar=mean)
    stddev_median = statistics.stdev(freqs, xbar=median)
    multimode = statistics.multimode(freqs)
    zp = controller.phot_info[role]["zp"]
    fo = controller.phot_info[role]["freq_offset"]
    log = logging.getLogger(role.tag())
    log.info(
        "%-9s stats => mean freq = %.03f Hz, median = %.03f Hz, \u03c3(mean) = %.03f, \u03c3(median) = %.03f, local maxima = %s",
        name,
        mean,
        median,
        stddev_mean,
        stddev_median,
        multimode,
    )
    log.info(
        "%-9s stats => mean mag = %.03f @ %.02f",
        name,
        mag(zp, fo, mean),
        zp,
    )



async def log_phot_info(controller: Controller, role: Role) -> None:
    log = logging.getLogger(role.tag())
    phot_info = await controller.info(role)
    log.info("-" * 40)
    for key, value in sorted(phot_info.items()):
        log.info("%-12s: %s", key.upper(), value)
    log.info("-" * 40)


async def log_messages(controller: Controller, role: Role, num: int | None = None) -> None:
    log = logging.getLogger(role.tag())
    name = controller.phot_info[role]["name"]
    zp = controller.phot_info[role]["zp"]
    fo = controller.phot_info[role]["freq_offset"]
    # Although in this case, it doesn't matter, in general
    # async generatores may not close as expected,
    # hence the use of closing() context manager
    messages = list()
    async with contextlib.aclosing(controller.readings(role, num)) as generator:
        async for role, msg in generator:
            messages.append(msg)
            log.info(
                "%-9s [%d] T=%s, f=%s Hz, mag=%0.2f @ %s, tbox=%s, tsky=%s",
                name,
                msg.get("seq"),
                msg.get("tstamp"),
                msg["freq"],
                msg.get("mag", mag(zp, fo, msg["freq"])),
                zp,
                msg["tamb"],
                msg["tsky"],
            )
    log_msgs_stats(messages, controller, role, name)


async def update_zp(controller: Controller, zero_point: float) -> None:
    log = logging.getLogger(Role.TEST.tag())
    zero_point = round(zero_point, 2)
    log.info("Updating ZP : %0.2f", zero_point)
    name = controller.phot_info[Role.TEST]["name"]
    try:
        stored_zp = await controller.write_zp(zero_point)
    except asyncio.exceptions.TimeoutError:
        log.error("[%s] Failed contacting %s photometer", name, Role.TEST.tag())
    except Exception as e:
        log.exception(e)
    else:
        if stored_zp is None:
            log.error(
                "ZP Write verification failed: ZP to Write (%0.3f) "
                "doesn't match ZP subsequently read (%s). \u0394 = ?",
                zero_point,
                stored_zp,
            )
        elif stored_zp is None or zero_point != stored_zp:
            log.error(
                "ZP Write verification failed: ZP to Write (%0.3f) "
                "doesn't match ZP subsequently read (%0.3f). \u0394 = %0.16f",
                zero_point,
                stored_zp,
                zero_point - stored_zp,
            )
        else:
            log.info("[%s] ZP Write (%0.2f) verification Ok.", name, zero_point)
