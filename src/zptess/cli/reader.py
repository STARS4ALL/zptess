# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import logging
import asyncio
from argparse import Namespace, ArgumentParser
from datetime import datetime, timezone

# -------------------
# Third party imports
# -------------------

from lica.sqlalchemy import sqa_logging
from lica.asyncio.cli import execute
from lica.asyncio.photometer import Role

# --------------
# local imports
# -------------

from .. import __version__
from ..controller.photometer import Reader
from .util import parser as prs
from .util.misc import log_phot_info, log_messages
from ..dao import engine
from ..mpl import plot

# ----------------
# Module constants
# ----------------

DESCRIPTION = "TESS-W Reader tool"

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


# -------------------
# Auxiliary functions
# -------------------


async def cli_read_ref(args: Namespace) -> None:
    global controller
    session = datetime.now(timezone.utc)
    ref_params = {
        "model": args.ref_model,
        "sensor": args.ref_sensor,
        "endpoint": args.ref_endpoint,
        "old_proto": args.ref_old_proto,
        "log_level": logging.DEBUG if args.ref_raw_message else logging.INFO,
        "strict": args.ref_strict,
    }
    controller = Reader(
        ref_params=ref_params,
    )
    await controller.init()
    await log_phot_info(controller, Role.REF)
    if not args.info:
        messages = await log_messages(controller, Role.REF, args.num_messages)
        if args.plot_histo:
            freqs = [msg["freq"] for msg in messages]
            tstamps = [msg["tstamp"] for msg in messages]
            name = messages[0].get("name", "stars3")
            plot.histograms(
                session=session,
                roles=[Role.REF],
                freqs=[freqs],
                tstamps=[tstamps],
                names=[name],
                decimals=[3]
        )


async def cli_read_test(args: Namespace) -> None:
    global controller
    session = datetime.now(timezone.utc)
    test_params = {
        "model": args.test_model,
        "sensor": args.test_sensor,
        "endpoint": args.test_endpoint,
        "old_proto": args.test_old_proto,
        "log_level": logging.DEBUG if args.test_raw_message else logging.INFO,
        "strict": args.test_strict,
    }
    controller = Reader(
        test_params=test_params,
    )
    await controller.init()
    await log_phot_info(controller, Role.TEST)
    if not args.info:
        messages = await log_messages(controller, Role.TEST, args.num_messages)
        if args.plot_histo:
            freqs = [msg["freq"] for msg in messages]
            tstamps = [msg["tstamp"] for msg in messages]
            name = messages[0]["name"]
            plot.histograms(
                session=session,
                roles=[Role.REF],
                freqs=[freqs],
                tstamps=[tstamps],
                names=[name],
                decimals=[2]
        )


async def cli_read_both(args: Namespace) -> None:
    global controller
    session = datetime.now(timezone.utc)
    ref_params = {
        "model": args.ref_model,
        "sensor": args.ref_sensor,
        "endpoint": args.ref_endpoint,
        "old_proto": args.ref_old_proto,
        "log_level": logging.DEBUG if args.ref_raw_message else logging.INFO,
        "strict": args.ref_strict,
    }
    test_params = {
        "model": args.test_model,
        "sensor": args.test_sensor,
        "endpoint": args.test_endpoint,
        "old_proto": args.test_old_proto,
        "log_level": logging.DEBUG if args.test_raw_message else logging.INFO,
        "strict": args.test_strict,
    }
    controller = Reader(
        ref_params=ref_params,
        test_params=test_params,
    )
    try:
        await controller.init()
        async with asyncio.TaskGroup() as tg:
            tg.create_task(log_phot_info(controller, Role.REF))
            tg.create_task(log_phot_info(controller, Role.TEST))
        if args.info:
            return
        async with asyncio.TaskGroup() as tg:
            task_ref = tg.create_task(log_messages(controller, Role.REF, args.num_messages))
            task_tst = tg.create_task(log_messages(controller, Role.TEST, args.num_messages))
        if args.plot_histo:
            ref_freqs = [msg["freq"] for msg in task_ref.result()]
            ref_tstamps = [msg["tstamp"] for msg in task_ref.result()]
            tst_freqs = [msg["freq"] for msg in task_tst.result()]
            tst_tstamps = [msg["tstamp"] for msg in task_tst.result()]
            ref_name = task_ref.result()[0].get("name", "stars3")
            tst_name = task_tst.result()[0]["name"]
            plot.histograms(
                session=session,
                roles=[Role.REF, Role.TEST],
                freqs=[ref_freqs, tst_freqs],
                tstamps=[ref_tstamps, tst_tstamps],
                names=[ref_name, tst_name],
                decimals=[3,2]
        )
    except* Exception as eg:
        for e in eg.exceptions:
            if args.trace:
                log.exception(e)
            else:
                log.error(e)
        raise RuntimeError("Could't continue execution, check errors above")


# -----------------
# CLI API functions
# -----------------


def add_args(parser: ArgumentParser):
    subparser = parser.add_subparsers(dest="command", required=True)
    p = subparser.add_parser(
        "ref",
        parents=[prs.info(), prs.nmsg(), prs.ref(), prs.ploto()],
        help="Read reference photometer",
    )
    p.set_defaults(func=cli_read_ref)
    p = subparser.add_parser(
        "test",
        parents=[prs.info(), prs.nmsg(), prs.test(), prs.ploto()],
        help="Read test photometer",
    )
    p.set_defaults(func=cli_read_test)
    p = subparser.add_parser(
        "both",
        parents=[prs.info(), prs.nmsg(), prs.ref(), prs.test(), prs.ploto()],
        help="read both photometers",
    )
    p.set_defaults(func=cli_read_both)


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
