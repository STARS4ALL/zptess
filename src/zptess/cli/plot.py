# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------

import logging
import statistics
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
    ref_freqs, ref_tstamps, ref_name = await sampler.samples(session, Role.REF)
    tst_freqs, tst_tstamps, tst_name = await sampler.samples(session, Role.TEST)
    ref_name, tst_name = ref_name[0], tst_name[0]
    decimals = 2 if statistics.mean(ref_freqs) > 3 else 3
    if args.plot_samples:
        plot.samples(
            session=session,
            roles=[Role.REF, Role.TEST],
            freqs=[ref_freqs, tst_freqs],
            tstamps=[ref_tstamps, tst_tstamps],
            names=[ref_name, tst_name],
            use_median=args.median,
        )
    elif args.plot_histo:
        plot.histograms(
            session=session,
            roles=[Role.REF, Role.TEST],
            freqs=[ref_freqs, tst_freqs],
            tstamps=[ref_tstamps, tst_tstamps],
            names=[ref_name, tst_name],
            use_median=args.median,
            decimals=[decimals, 2],
        )
    elif args.plot_both:
        plot.samples(
            session=session,
            roles=[Role.REF, Role.TEST],
            freqs=[ref_freqs, tst_freqs],
            tstamps=[ref_tstamps, tst_tstamps],
            names=[ref_name, tst_name],
            use_median=args.median,
        )

        plot.histograms(
            session=session,
            roles=[Role.REF, Role.TEST],
            freqs=[ref_freqs, tst_freqs],
            tstamps=[ref_tstamps, tst_tstamps],
            names=[ref_name, tst_name],
            use_median=args.median,
            decimals=[decimals, 2],
        )
    else:
        pass

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
