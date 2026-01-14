# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import asyncio
import logging
from datetime import datetime
from argparse import Namespace, ArgumentParser

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
from ..controller.exporter import Controller as Exporter


# ----------------
# Module constants
# ----------------

TSTAMP_FMT = "%Y-%m-%dT%H:%M:%S"

# -----------------------
# Module global variables
# -----------------------

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])


# -----------------
# Auxiliar function
# -----------------


def this_year(value: datetime | None) -> datetime:
    """Date & time validator for the command line interface"""
    return value or datetime.now().replace(
        month=1, day=1, hour=0, minute=0, second=0, microsecond=0
    )


def next_year(value: datetime | None) -> datetime:
    """Date & time validator for the command line interface"""
    return value or datetime.now().replace(
        month=12, day=31, hour=23, minute=59, second=59, microsecond=0
    )


# -----------------
# CLI API functions
# -----------------


async def cli_session_export(args: Namespace) -> None:
    log.info("exporting session %s", args.session)
    log.info("exporting to directory %s", args.base_dir)
    assert isinstance(args.session, datetime)
    exporter = Exporter(
        base_dir=args.base_dir,
        begin_tstamp=args.session,
        end_tstamp=args.session,
        filename_prefix="session",
    )
    N = await exporter.query_nsummaries()
    if N > 0:
        summaries = await exporter.query_summaries()
        await asyncio.to_thread(exporter.export_summaries, summaries)
        rounds = await exporter.query_rounds()
        await asyncio.to_thread(exporter.export_rounds, rounds)
        samples = await exporter.query_samples()
        await asyncio.to_thread(exporter.export_samples, samples)
        zip_file_path = await asyncio.to_thread(exporter.pack)
        log.info("zipped file in  %s", zip_file_path)
    else:
        log.warn("No calibration session found for %s", args.session)
    return


async def cli_session_count(args: Namespace) -> None:
    args.since = args.since or this_year(args.since)
    args.until = args.until or next_year(args.until)
    exporter = Exporter(
        base_dir=args.base_dir,
        begin_tstamp=args.since,
        end_tstamp=args.until,
        filename_prefix="count",
    )
    N = await exporter.query_nsummaries(mode=args.mode)
    log.info("%d calibrations made between %s and %s", N, args.since, args.until)
    if args.detailed:
        # Sort result by calibration date
        summaries = sorted(
            await exporter.query_summaries(args.mode), key=lambda x: x[5]
        )  # Sort by session (calibration date)
        await asyncio.to_thread(exporter.export_summaries, summaries)
    return


def add_args(parser: ArgumentParser):
    subparser = parser.add_subparsers(dest="command", required=True)
    p = subparser.add_parser(
        "single",
        parents=[prs.sess(), prs.bdir()],
        help="Export a single calibration session to CSV files",
    )
    p.set_defaults(func=cli_session_export)
    p = subparser.add_parser(
        "count",
        parents=[prs.trange(), prs.bdir(), prs.mode(), prs.detailed()],
        help="Count number of calibrations from a given time range",
    )
    p.set_defaults(func=cli_session_count)


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
        description="Additional tools",
    )
