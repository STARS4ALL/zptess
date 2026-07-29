# ----------------------------------------------------------------------
# Copyright (c) 2024 Rafael Gonzalez.
#
# See the LICENSE file for details
# ----------------------------------------------------------------------

# --------------------
# System wide imports
# -------------------


from argparse import Namespace, ArgumentParser
import logging
import csv
import re
from pathlib import Path


# -------------------
# Third party imports
# -------------------

from lica.cli import execute
from lica.validators import vfile

# --------------
# local imports
# -------------

from .. import __version__

# ----------------
# Module constants
# ----------------

DESCRIPTION = "Extract aggregate values from individual log file runs"

# Expresión regular para las líneas de log de interés
LOG_LINE_REGEX = re.compile(
    r"""
    ^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d{3})      # timestamp
    \s+\[INFO\s*\]\s+\[REF.\]\s+
    \[(?P<wavelength>\d+)\]\s+                                      # [350]
    (?P<name>stars\d{1,4})\s+                                       # starsNNNN
    stats\s+=>\s+
    mean\s+freq\s*=\s*(?P<mean_freq>[-+]?\d+\.\d+e[+-]\d+)\s*Hz,\s*  # mean freq
    median\s*=\s*(?P<median_freq>[-+]?\d+\.\d+e[+-]\d+)\s*Hz,\s*     # median
    σ\(mean\)\s*=\s*(?P<sigma_mean>[-+]?\d+\.\d+e[+-]\d+),\s*        # σ(mean)
    σ\(median\)\s*=\s*(?P<sigma_median>[-+]?\d+\.\d+e[+-]\d+)        # σ(median)
    """,
    re.VERBOSE,
)


# -----------------------
# Module global variables
# -----------------------

# get the module logger
log = logging.getLogger(__name__.split(".")[-1])
controller = None



def cli_parse_log(args: Namespace) -> None:

    input_path = Path(args.input)
    output_path = Path(args.output)

    # Cabecera del CSV
    fieldnames = [
        "name",
        "timestamp",
        "wavelength",
        "mean freq",
        "sigma freq",
        "median freq",
        "sigma median",
    ]

    with input_path.open("r", encoding="utf-8") as fin, \
            output_path.open("w", newline="", encoding="utf-8") as fout:

        log.info("processing input file %s", input_path);
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for line in fin:
            m = LOG_LINE_REGEX.search(line)
            if not m:
                continue

            row = {
                "name": m.group("name"),
                "timestamp": m.group("timestamp").replace(",","."),
                "wavelength": int(m.group("wavelength")),
                "mean freq": m.group("mean_freq"),
                "sigma freq": m.group("sigma_mean"),
                "median freq": m.group("median_freq"),
                "sigma median": m.group("sigma_median"),
            }
            writer.writerow(row)
        log.info("written onto output file %s", output_path);


def add_args(parser: ArgumentParser):
    parser.add_argument(
        "-i", "--input",
        required=True,
        type=vfile,
        help="Input log file.",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output csv file.",
    )
    parser.set_defaults(func=cli_parse_log)



def cli_main(args: Namespace) -> None:
    args.func(args)


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
