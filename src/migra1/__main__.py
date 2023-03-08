# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------
# Copyright (c) 2021
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import re 
import os
import sys
import csv
import datetime
import argparse
import logging
import traceback
import jinja2

# -------------
# Local imports
# -------------

from zptool import  __version__
from zptool.utils import mkdate, mkbool

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")

EXCLUDED_NAMES = ('stars3','stars700','stars701','stars702','stars703','stars704','stars705','stars706','stars707','stars708','stars709','stars710',)

UNWANTED_WORDS = ('Sí', 'Sí **')
WRONG_MAC_REGEXP = re.compile(r"^([A-F0-9]{2})-([A-F0-9]{2})-([A-F0-9]{2})-([A-F0-9]{2})-([A-F0-9]{2})-([A-F0-9]{2})$")

TSTAMP_SESSION_FMT = "'%Y-%m-%dT%H:%M:%S'"

currentTimestamp = datetime.datetime(year=1000,month=1,day=1,hour=0,minute=1,second=0)
ONE_MINUTE = datetime.timedelta(minutes=1)

# -----------------------
# Module global functions
# -----------------------

def configureLogging(options):
    if options.verbose:
        level = logging.DEBUG
    elif options.quiet:
        level = logging.WARN
    else:
        level = logging.INFO
    
    log.setLevel(level)
    # Log formatter
    #fmt = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] %(message)s')
    fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    # create console handler and set level to debug
    if not options.no_console:
        ch = logging.StreamHandler()
        ch.setFormatter(fmt)
        ch.setLevel(level)
        log.addHandler(ch)
    # Create a file handler
    if options.log_file:
        #fh = logging.handlers.WatchedFileHandler(options.log_file)
        fh = logging.FileHandler(options.log_file)
        fh.setFormatter(fmt)
        fh.setLevel(level)
        log.addHandler(fh)


def python2_warning():
    if sys.version_info[0] < 3:
        log.warning("This software des not run under Python 2 !")
        sys.exit(1)


def setup(options):
    python2_warning()
    
def open_database(dbase_path):
    if not os.path.exists(dbase_path):
        raise IOError(f"Database file not found '{dbase_path}'")
    log.info(f"Opened database file {dbase_path}")
    return sqlite3.connect(dbase_path)

def mkfile(filestr):
    result = None
    if os.path.isfile(filestr):
        result = filestr
    else:
        raise FileNotFoundError(filestr)
    return result

def render(template_path, context):
    if not os.path.exists(template_path):
        raise IOError("No Jinja2 template file found at {0}. Exiting ...".format(template_path))
    path, filename = os.path.split(template_path)
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(path or './')
    ).get_template(filename).render(context)


# =================== #
# THE ARGUMENT PARSER #
# =================== #

def createParser():
    # create the top-level parser
    name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
    parser = argparse.ArgumentParser(prog=name, description="MIGRATION FROM GSHEET TO DATABASE TOOL")

    # Global options
    parser.add_argument('--version', action='version', version='{0} {1}'.format(name, __version__))
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
    group.add_argument('-q', '--quiet',   action='store_true', help='Quiet output.')
    parser.add_argument('-nk','--no-console', action='store_true', help='Do not log to console.')
    parser.add_argument('-l', '--log-file', type=str, default=None, help='Optional log file')
    parser.add_argument('-i', '--input-csv', type=mkfile, default='Fotometros TESS-W - Construccion y Calibracion.csv', help='Input CSV file')
    parser.add_argument('-o', '--output-sql', type=str, required=True, help='Output SQL file')
    parser.add_argument('-t', '--template', type=mkfile, required=True, help='Jinja2 template file')

    return parser

def slurpInputFile(filepath):
    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        return tuple(row for row in reader)

def quoteOrNull(string):
    return "'" +  string + "'" if string != '' else 'NULL'

def floatOrNull(string, ndecimals):
    try:
        result = round(float(string),ndecimals)
    except Exception:
        result= 'NULL'
    return result

def filterNotCalibrated(row):
    return row['Calibration date'] == '';

def excludeNames(row):
    return row['Name'] not in EXCLUDED_NAMES;

def replaceCollector(collector):
    if collector in UNWANTED_WORDS:
        collector = 'NULL'
    else:
        collector = quoteOrNull(collector)
    return collector 

def mapNames(row):
    '''This must be separate to exclude names later'''
    row['Name'] = row['Name'][0:5] + str(int(row['Name'][5:]))
    return row

def formatMAC(mac):
    mac = mac.upper()
    matchobj = WRONG_MAC_REGEXP.search(mac)
    if matchobj:
        mac = f"{matchobj.group(1)}:{matchobj.group(2)}:{matchobj.group(3)}:{matchobj.group(4)}:{matchobj.group(5)}:{matchobj.group(6)}"
    return mac

    return mac
def mapAll(row):
    global currentTimestamp
    row['Firmware'] = quoteOrNull(row['Firmware'])
    row['Model'] = quoteOrNull(row['Model'])
    row['Name'] = quoteOrNull(row['Name'])
    row['MAC'] = quoteOrNull(formatMAC(row['MAC']))
    row['Calibration date'] = currentTimestamp.strftime(TSTAMP_SESSION_FMT)
    row['Test Freq.'] = floatOrNull(row['Test Freq.'],3)
    row['Ref. Freq.'] = floatOrNull(row['Ref. Freq.'],3)
    row['Test Mag.'] = floatOrNull(row['Test Mag.'],2)
    row['Ref. Mag.'] = floatOrNull(row['Ref. Mag.'],2)
    row['Ref-Test Mag. Diff.'] = floatOrNull(row['Ref-Test Mag. Diff.'],3)
    row['Raw ZP'] = floatOrNull(row['Raw ZP'],2)
    row['ZP Offset'] = floatOrNull(row['ZP Offset'],2)
    row['Filter'] = 'UV/IR-740' if row['Filter'] == 'UV/IR-cut' else row['Filter']
    row['Filter'] = quoteOrNull(row['Filter'])
    row['Plug'] = 'USB-A' if row['Plug'] == 'USB' else row['Plug']
    row['Plug'] = quoteOrNull(row['Plug'])
    row['Box'] = quoteOrNull(row['Box'])
    row['Collector'] = replaceCollector(row['Collector'])
    row['Comment'] = quoteOrNull(row['Comment'])

    currentTimestamp += ONE_MINUTE
    return row


def doTheDammThing(options):
    rows = slurpInputFile(options.input_csv)
    g = filter(filterNotCalibrated, rows)
    g = map(mapNames,g)
    g = filter(excludeNames,g)
    g = map(mapAll,g)
    context = {'rows': tuple(g)}
    with open(options.output_sql, 'w') as outfile:
        rendered = render(options.template, context)
        outfile.write(rendered)
          

# ================ #
# MAIN ENTRY POINT #
# ================ #

def main():
    '''
    Utility entry point
    '''
    try:
        options = createParser().parse_args(sys.argv[1:])
        configureLogging(options)
        setup(options)
        name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
        log.info(f"============== {name} {__version__} ==============")
        doTheDammThing(options)
    except KeyboardInterrupt as e:
        log.critical("[%s] Interrupted by user ", __name__)
    except Exception as e:
        log.critical("[%s] Fatal error => %s", __name__, str(e) )
        traceback.print_exc()
    finally:
        pass

main()
