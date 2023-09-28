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

import sys
import argparse
import os.path
import logging
#import logging.handlers
import traceback
import importlib
import sqlite3

# -------------------------
# Other thrid party imports
# -------------------------

import decouple

# -------------
# Local imports
# -------------

from zptool import  __version__
from zptool.utils import mkdate, mkbool

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")

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


def setup(options):
	python2_warning()
	
def open_database(dbase_path):
    if not os.path.exists(dbase_path):
    	raise IOError(f"Database file not found '{dbase_path}'")
    log.info(f"Opened database file {dbase_path}")
    return sqlite3.connect(dbase_path)

# =================== #
# THE ARGUMENT PARSER #
# =================== #

def createParser():
	# create the top-level parser
	name = os.path.split(os.path.dirname(sys.argv[0]))[-1]
	parser = argparse.ArgumentParser(prog=name, description="ZERO POINT TOOL")

	# Global options
	parser.add_argument('--version', action='version', version='{0} {1}'.format(name, __version__))
	group = parser.add_mutually_exclusive_group()
	group.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
	group.add_argument('-q', '--quiet',   action='store_true', help='Quiet output.')
	parser.add_argument('-nk','--no-console', action='store_true', help='Do not log to console.')
	parser.add_argument('-l', '--log-file', type=str, default=None, help='Optional log file')

	
	# --------------------------
	# Create first level parsers
	# --------------------------

	subparser = parser.add_subparsers(dest='command')

	parser_summary  = subparser.add_parser('summary', help='summary command')
	parser_samples  = subparser.add_parser('samples', help='samples command')
	parser_rounds   = subparser.add_parser('rounds', help='rounds command')
	parser_batch    = subparser.add_parser('batch', help='batch command')
	parser_reference = subparser.add_parser('reference', help='reference command')
	parser_email    = subparser.add_parser('emailer', help='email command')


	# ---------------------------------------
	# Create second level parsers for 'email'
	# ---------------------------------------

	subparser = parser_email.add_subparsers(dest='subcommand')
	emvi = subparser.add_parser('view',  help="View email section")

	emup = subparser.add_parser('update',  help="Update email section attributes")
	emup.add_argument('--host',      type=str, default=None, help='SMTP host')
	emup.add_argument('--port',      type=str, default=None, help='SMTP port')
	emup.add_argument('--sender',    type=str, default=None, help='sender email address')
	emup.add_argument('--password',  type=str, default=None, help='sender password')
	emup.add_argument('--receivers', type=str, nargs='+', default=None, help='comma-separated list of email addresses')
	
	# -------------------------------------------
	# Create second level parsers for 'reference'
	# -------------------------------------------

	subparser = parser_reference.add_subparsers(dest='subcommand')
	revi = subparser.add_parser('view',  help="View reference section")

	reup = subparser.add_parser('update',  help="Update reference section attributes")
	reup.add_argument('--model',    type=str, choices=("TESS-W","TAS","TESS-P"), default=None, help='Ref. photometer model')
	reup.add_argument('--name',     type=str, default=None, help='Ref. photometer name')
	reup.add_argument('--mac',      type=str, default=None, help='Ref. photometer MAC address')
	reup.add_argument('--firmware', type=str, default=None, help='Ref. photometer firmware revision')
	reup.add_argument('--zp',       type=str, default=None, help='Ref. photometer absolute Zero Point (calibrated against SQM)')

	# -----------------------------------------
	# Create second level parsers for 'summary'
	# -----------------------------------------

	subparser = parser_summary.add_subparsers(dest='subcommand')

	smexp = subparser.add_parser('export',  help="Export summary data to CSV file")
	smexp.add_argument('-f', '--csv-file',  type=str, required=True, help='CSV file to export (required)')
	smexp.add_argument('-x', '--extended',  action='store_true', help='extended data export')
	smexp.add_argument('-u', '--updated',   action='store_true', help='export only when ZP was actually written to TESS-W')

	smdf = subparser.add_parser('differences',  help="Show mismatches respect to rounds information")

	smvw = subparser.add_parser('view',  help="View calibration summary")
	smvw.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	smvwex = smvw.add_mutually_exclusive_group(required=True)
	smvwex.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	smvwex.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	smvwex.add_argument('-A', '--all',   action='store_true', help='all calibration sessions')
	smvw.add_argument('-a', '--also-ref',   action='store_true', help='Also show reference photometer data')


	# ----------------------------------------
	# Create second level parsers for 'rounds'
	# ----------------------------------------

	subparser = parser_rounds.add_subparsers(dest='subcommand')

	rold = subparser.add_parser('load',  help="Import rounds data from log file")
	rold.add_argument('-f', '--input-file',  type=str, required=True, help='input LOG file to analyze (required)')

	rovw = subparser.add_parser('view',  help="View calibration rounds")
	rovw.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	rovwex = rovw.add_mutually_exclusive_group(required=True)
	rovwex.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	rovwex.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	rovw.add_argument('-a', '--also-ref',   action='store_true', help='Also show reference photometer data')
	rovw.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	# -----------------------------------------
	# Create second level parsers for 'samples'
	# -----------------------------------------

	subparser = parser_samples.add_subparsers(dest='subcommand')

	savw = subparser.add_parser('view',  help="View individual samples")
	savw.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	savwex1 = savw.add_mutually_exclusive_group(required=True)
	savwex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	savwex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	savwex2 = savw.add_mutually_exclusive_group(required=True)
	savwex2.add_argument('-r', '--round',  type=int, default=None, help='individual round')
	savwex2.add_argument('-A', '--all',   action='store_true', help='all rounds')
	savw.add_argument('-a', '--also-ref',   action='store_true', help='Also show reference photometer data')
	savw.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	saexp = subparser.add_parser('export',  help="Export individual data to a CSV file")
	saexp.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	saexp.add_argument('-f', '--csv-file',  type=str, required=True, help='CSV file to export (required)')
	saexpex1 = saexp.add_mutually_exclusive_group(required=True)
	saexpex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	saexpex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	saexpex2 = saexp.add_mutually_exclusive_group(required=True)
	saexpex2.add_argument('-r', '--round',  type=int, default=None, metavar='<n>', help='from individual round')
	saexpex2.add_argument('-A', '--all',   action='store_true', help='all rounds')
	saexp.add_argument('-a', '--also-ref', action='store_true', help='Also show reference photometer data')
	saexp.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	sast = subparser.add_parser('stats',  help="Central statistics a round of individual samples")
	sast.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	sastex1 = sast.add_mutually_exclusive_group(required=True)
	sastex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	sastex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	sastex2 = sast.add_mutually_exclusive_group(required=True)
	sastex2.add_argument('-r', '--round',  type=int, default=None, help='individual round')
	sastex2.add_argument('-A', '--all',   action='store_true', help='all rounds')
	sast.add_argument('-a', '--also-ref',   action='store_true', help='Include reference photometer stats')
	sast.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	sahi = subparser.add_parser('hist',  help="Histogram (top rows only)")
	sahi.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	sahiex1 = sahi.add_mutually_exclusive_group(required=True)
	sahiex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	sahiex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	sahi.add_argument('-r', '--round',  type=int, required=True, help='individual round')
	sahi.add_argument('-a', '--also-ref',   action='store_true', help='Include reference photometer histo')
	sahi.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	sazp = subparser.add_parser('zero',  help="Compute zero point from a round of individual samples")
	sazp.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	sazpex1 = sazp.add_mutually_exclusive_group(required=True)
	sazpex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	sazpex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	sazpex2 = sazp.add_mutually_exclusive_group(required=True)
	sazpex2.add_argument('-r', '--round',  type=int, default=None, help='individual round')
	sazpex2.add_argument('-A', '--all',   action='store_true', help='all rounds')
	sazp.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	sazp = subparser.add_parser('magdif',  help="Compute Magnitude differences from a round of individual samples")
	sazp.add_argument('-n', '--name',  type=str,  required=True, help='TESS name (required)')
	sazpex1 = sazp.add_mutually_exclusive_group(required=True)
	sazpex1.add_argument('-s', '--session',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by session')
	sazpex1.add_argument('-l', '--latest',   action='store_true', help='latest calibration session')
	sazpex2 = sazp.add_mutually_exclusive_group(required=True)
	sazpex2.add_argument('-r', '--round',  type=int, default=None, help='individual round')
	sazpex2.add_argument('-A', '--all',   action='store_true', help='all rounds')
	sazp.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	# ---------------------------------------
	# Create second level parsers for 'batch'
	# --------------------------------------

	subparser = parser_batch.add_subparsers(dest='subcommand')

	babe = subparser.add_parser('begin', help="begin calibration batch")
	babe.add_argument('-c', '--comment',  type=str, nargs='+', default=[], help='Optional batch comment')

	
	baen = subparser.add_parser('end',  help="end calibration batch")
	
	bavi = subparser.add_parser('view', help="view calibration batches")
	
	bavi = subparser.add_parser('purge', help="purge batches with no callibrations")

	baex = subparser.add_parser('export', help="Export calibrations in a batch")
	baexex1 = baex.add_mutually_exclusive_group(required=True)
	baexex1.add_argument('-b', '--begin-date',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by begin')
	baexex1.add_argument('-l', '--latest',   action='store_true', help='latest closed batch')
	baexex1.add_argument('-a', '--all',   action='store_true', help='all closed batches')
	baex.add_argument('-d', '--base-dir',  type=str, default="/tmp/zptool", help='Base dir for the export')
	baex.add_argument('-e', '--email',   action='store_true', help='send results by email')
	baex.add_argument('-u', '--updated', type=mkbool, choices=(True, False), default=None, help='do action only when ZP updated flag is True|False')

	bast = subparser.add_parser('stats', help="generate ZP statistics per batch")
	bastex = bast.add_mutually_exclusive_group(required=True)
	bastex.add_argument('-b', '--begin-date',  type=mkdate, metavar='<YYYY-MM-DDTHH:MM:SS>', default=None, help='by begin')
	bastex.add_argument('-l', '--latest',   action='store_true', help='latest closed batch')
	bastex.add_argument('-a', '--all',   action='store_true', help='all closed batches')
	bast.add_argument('-f', '--csv-file',  type=str, required=True, help='CSV file to export (required)')
	bast.add_argument('-v', '--view',  action='store_true', help='View as console table as well')


	return parser

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
		database_url = decouple.config('DATABASE_URL')
		connection = open_database(database_url)
		package = f"{name}"
		command  = f"{options.command}"
		subcommand = f"{options.subcommand}"
		try: 
			command = importlib.import_module(command, package=package)
		except ModuleNotFoundError:	# when debugging module in git source tree ...
			command  = f".{options.command}"
			command = importlib.import_module(command, package=package)
		getattr(command, subcommand)(connection, options)
	except KeyboardInterrupt as e:
		log.critical("[%s] Interrupted by user ", __name__)
	except Exception as e:
		log.critical("[%s] Fatal error => %s", __name__, str(e) )
		traceback.print_exc()
	finally:
		pass

main()
