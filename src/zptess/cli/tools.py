# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import os
import asyncio
import logging
from datetime import datetime
from argparse import Namespace, ArgumentParser

# -------------------
# Third party imports
# -------------------

from lica.sqlalchemy import sqa_logging
from lica.asyncio.cli import execute
from lica.tabulate import paging

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
    summaries = await exporter.query_summaries()
    await asyncio.to_thread(exporter.export_summaries, summaries)
    rounds = await exporter.query_rounds()
    await asyncio.to_thread(exporter.export_rounds, rounds)
    samples = await exporter.query_rounds()
    await asyncio.to_thread(exporter.export_samples, samples)
    zip_file_path = await asyncio.to_thread(exporter.pack)
    log.info("zipped file in  %s", zip_file_path)
    return


def add_args(parser: ArgumentParser):
    subparser = parser.add_subparsers(dest="command", required=True)
    p = subparser.add_parser(
        "export",
        parents=[prs.sess()],
        help="Export a single calibration session to CSV files",
    )
    p.set_defaults(func=cli_session_export)


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
