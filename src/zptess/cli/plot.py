# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import logging
from collections import Counter
from argparse import Namespace, ArgumentParser

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
from .util import parser as prs
from ..dao import engine
from ..controller.dbsamples import Controller as Sampler
from ..mpl import plot

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


async def cli_plot_session(args: Namespace) -> None:
    session = args.session
    sampler = Sampler()
    ref_tstamps, ref_freqs = await sampler.samples(session, Role.REF)
    tst_tstamps, tst_freqs = await sampler.samples(session, Role.TEST)
    ref_histo = Counter(ref_freqs)
    test_histo=Counter(tst_freqs)
    if args.samples:
        plot.plot_samples(
            session=session,
            ref_tstamps=ref_tstamps,
            ref_freqs=ref_freqs,
            test_tstamps=tst_tstamps,
            test_freqs=tst_freqs,
        )
    elif args.histo:
        plot.plot_histograms(
            disttributions=(ref_histo, test_histo),
        )
    else:
        plot.plot_samples(
            session=session,
            ref_tstamps=ref_tstamps,
            ref_freqs=ref_freqs,
            test_tstamps=tst_tstamps,
            test_freqs=tst_freqs,
        )
        plot.plot_histograms(
            distributions=(ref_histo, test_histo),
        )

    return


def add_args(parser: ArgumentParser):
    subparser = parser.add_subparsers(dest="command", required=True)
    p = subparser.add_parser(
        "session",
        parents=[prs.sess(), prs.ploto()],
        help="Plot calibration session samples",
    )
    p.set_defaults(func=cli_plot_session)


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
        description="Plotting tools",
    )
