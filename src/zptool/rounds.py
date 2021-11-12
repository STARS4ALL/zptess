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
import csv
import os.path
import datetime
import logging

# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT
from zptool.utils import paging
from zptool.summary import summary_latest_session, summary_update
from zptool.logparser import LogRecord

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")


def rounds_update(connection, rows):
    cursor = connection.cursor()
    cursor.executemany( 
        '''
        INSERT OR IGNORE INTO rounds_t (
                session,  
                round,    
                role, 
                central,       
                freq,       
                stddev,       
                mag,       
                zp_fict,       
                zero_point,       
                nsamples,    
                duration       
        ) VALUES (
                :session,  
                :round,    
                :role, 
                :central,       
                :freq,       
                :stddev,       
                :mag,       
                :zp_fict,       
                :zero_point,       
                :nsamples,    
                :duration
        )
        ''',
        rows
    )
    log.info(f"Inserted {cursor.rowcount} rows in rounds_t")


def rounds_export_iterable(connection, session, role, updated):
    '''Show rounds data for a given photometer'''
    row = {'session': session, 'role':role, 'updated': updated}

    if updated is None:
        sql = '''SELECT model, name, mac, session, role, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        AND role = :role
        ORDER BY round ASC
        '''
    else:
        sql = '''SELECT model, name, mac, session, role, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        AND role = :role
        AND upd_flag = :updated
        ORDER BY round ASC
        '''
    cursor = connection.cursor()
    cursor.execute(sql, row)
    return cursor

# -------------------------------------
# Useful functions to be used elsewhere
# -------------------------------------

def rounds_export(connection, session, updated, csv_path):
    headers = ("Model", "Name", "MAC", "Session (UTC)", "Role", "Round", "Freq (Hz)", "\u03C3 (Hz)", "Mag", "ZP", "# Samples","\u0394 T (s.)")
    with open(csv_path, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(headers)
        iterable = rounds_export_iterable(connection, session, 'test', updated)
        for row in iterable:
            writer.writerow(row)
        iterable = rounds_export_iterable(connection, session, 'ref', None)
        for row in iterable:
            writer.writerow(row)
    log.info(f"Saved rounds calibration data to CSV file: '{os.path.basename(csv_path)}'")   
   
# ==================
# 'rounds' commands
# ==================


def load(connection, options):
    '''Exports all the database to a single file'''
    records = list()
    regexp = re.compile(LogRecord.RECORD_START)
    with open(options.input_file, newline='') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        matchobj = regexp.search(line)
        if matchobj:
            records.append(LogRecord(i,connection))
            if len(records) > 1:
                records[-2].update(lines,i)
    if len(records) == 0:
        log.error("No se ha parseado bien el fichero")
    records[-1].update(lines,i)
    log.info(f"Initally detected {len(records)} records")
    records = sorted(records)
    for r in records:
        r.parse()
    records = list(filter(lambda r: r.session is not None, records))
    log.info(f"Left {len(records)} records for further analysis after excluding those without a session")
    error_records = list(filter(lambda r: r.check(), records))
    records = sorted(set(records) - set(error_records))
    log.info(f"Left {len(records)} after a thorough error check")
    summary = list()
    rounds  = list()
    for r in records:
        summary.extend(r.summary())
        rounds.extend(r.rounds())
    summary_update(connection, summary)
    rounds_update(connection, rounds)
    connection.commit()


def view(connection, options):
    '''Show rounds data for a given photometer'''
    row = {'name': options.name}
    headers = ("Session (UTC)", "Name", "MAC", "Round", "Freq (Hz)", "\u03C3 (Hz)", "Mag", "ZP", "# Samples","\u0394 T (s.)")
    if options.latest and not options.also_ref:
        session = summary_latest_session(connection, options.name, options.updated)
        log.info(f"Session (UTC) = {session}")
        row['session'] = session
        sql = '''
        SELECT session, name, mac, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        AND role = 'test'
        ORDER BY session ASC
        '''
    elif options.latest and options.also_ref:
        session = summary_latest_session(connection, options.name, options.updated)
        row['session'] = session
        sql = '''
        SELECT session, name, mac, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        ORDER BY session,round ASC
        '''
    elif not options.latest and not options.also_ref:
        row['session'] = options.session.strftime(TSTAMP_SESSION_FMT)
        sql = '''
        SELECT session, name, mac, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        AND role = 'test'
        ORDER BY session,round ASC
        '''
    else:
        row['session'] = options.session.strftime(TSTAMP_SESSION_FMT)
        sql = '''
        SELECT session, name, mac, round, freq, stddev, mag, zero_point, nsamples, duration
        FROM rounds_v
        WHERE session = :session
        ORDER BY session ASC
        '''
    cursor = connection.cursor()
    cursor.execute(sql, row)
    paging(cursor, headers)
   
