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

import os.path
import logging
import csv 

# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT
from zptess.dbase.summary import EXPORT_HEADERS, EXPORT_ADD_HEADERS, dyn_sql
from zptool.utils import paging

# Beware: The source list for CSV exports is zptess.dbase.summary.EXPORT_HEADERS
NAMES_MAP = {
    'model'             : "Model", 
    'name'              : "Name",
    'mac'               : "MAC",
    'firmware'          : "Firmware",
    'sensor'            : "Sensor",
    'session'           : "Calibration date",
    'calibration'       : "Calibration",
    'calversion'        : "Cal. Sw. Version",
    'ref_mag'           : "Ref. Mag.",
    'ref_freq'          : "Ref. Freq." ,
    'test_mag'          : "Test Mag.",
    'test_freq'         : "Test Freq.",
    'raw_zero_point'    : "Raw ZP",
    'mag_diff'          : "Ref-Test Mag. Diff.",
    'offset'            : "ZP Offset",
    'zero_point'        : "Final ZP",
    'prev_zp'           : "Prev. ZP",
    'filter'            : "Filter",
    'plug'              : "Plug",
    'box'               : "Box",
    'collector'         : "Collector" ,
    'author'            : "Author",
    'comment'           : "Comment",
    'nrounds'           : "# Rounds",
    'zero_point_method' : "ZP Sel. Method",
    'test_freq_method'  : "Freq Method",
    'ref_freq_method'   : "Ref Freq Method",
}

EXPORT_CSV_HEADERS = tuple(NAMES_MAP[key] for key in EXPORT_HEADERS)
EXPORT_CSV_ADD_HEADERS = tuple(NAMES_MAP[key] for key in EXPORT_ADD_HEADERS)

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")


def export_iterable(connection, extended, updated, begin_tstamp, end_tstamp):
    cursor = connection.cursor()
    headers = EXPORT_HEADERS + EXPORT_ADD_HEADERS if extended else EXPORT_HEADERS
    row = {'updated': updated, 'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp}
    sql = dyn_sql(headers, updated, begin_tstamp)
    cursor.execute(sql, row)
    return cursor

# -------------------------------------
# Useful functions to be used elsewhere
# -------------------------------------

def summary_update(connection, rows):
    cursor = connection.cursor()
    cursor.executemany(
        '''
        UPDATE summary_t
        SET
            nrounds           = :nrounds,
            zero_point_method = :zero_point_method,
            freq_method       = :freq_method
        WHERE session = :session AND role = :role
        ''',
        rows
    )
    log.info(f"Updated {cursor.rowcount} rows in summary_t")


def summary_get_test_data(connection, name, latest, session, updated=None):
    cursor = connection.cursor()
    if latest:
        session = summary_latest_session(connection, name, updated)
    else:
        session = session.strftime(TSTAMP_SESSION_FMT)
    row = {'name': name, 'session': session}
    cursor.execute('''
            SELECT session, model, name, role, nrounds
            FROM summary_t
            WHERE session = :session
            AND name = :name
            ''',row)
    return cursor.fetchone()

def summary_get_ref_data(connection, session):
    cursor = connection.cursor()
    row = {'session': session, 'role': 'ref'}
    cursor.execute('''
        SELECT session, model, name, role, nrounds
        FROM summary_t
        WHERE session = :session
        AND role = :role;
    ''', row)
    return cursor.fetchone()


def summary_latest_session(connection, name, updated):
    row = {'name': name}
    if updated is None:
        sql = f"SELECT MAX(session) FROM summary_t  WHERE name = :name"
    else:
        row['updated'] = 1 if updated else 0
        sql = f"SELECT MAX(session) FROM summary_t  WHERE name = :name AND upd_flag = :updated"
    cursor = connection.cursor()
    cursor.execute(sql, row)
    result = cursor.fetchone()
    return result[0] if result else None

def summary_number_of_sessions(connection, begin_tstamp, end_tstamp, updated=None):
    row = {'begin_tstamp': begin_tstamp + 'Z', 'end_tstamp': end_tstamp + 'Z','updated': updated}
    cursor = connection.cursor()
    if updated is not None:
        cursor.execute('''
            SELECT count(*) 
            FROM summary_v 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
            AND upd_flag = :updated
        ''', row)
    else:
        cursor.execute('''
            SELECT count(*) 
            FROM summary_v 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
        ''', row)
    return cursor.fetchone()[0]


def summary_sessions_iterable(connection, updated, begin_tstamp, end_tstamp):
    row = {'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp, 'updated': updated}
    cursor = connection.cursor()
    if updated is not None:
        cursor.execute('''
            SELECT DISTINCT session 
            FROM summary_t 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
            AND upd_flag = :updated
        ''', row)
    else:
        cursor.execute('''
            SELECT DISTINCT session 
            FROM summary_t 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
        ''', row)
    return cursor

def summary_get_info(connection, session, role):
    row = {'session': session, 'role': role}
    cursor = connection.cursor()
    cursor.execute("SELECT model, name, nrounds FROM summary_t WHERE session = :session AND role = :role",row)
    return cursor.fetchone()

def summary_session_from_name(connection, name, role='test', updated=False):
    row = {'name': name, 'role': role, 'updated': updated}
    log.info(f"row = {row}, updated = {updated}")
    cursor = connection.cursor()
    if updated is not None:
        cursor.execute('''
            SELECT MAX(session) FROM summary_t 
            WHERE name   = :name
            AND role     = :role
            AND upd_flag = :updated
            ''',row)
    else:
        cursor.execute('''
            SELECT MAX(session) FROM summary_t 
            WHERE name = :name
            AND role   = :role
            ''',row)
    return cursor.fetchone()


def summary_export(connection, extended, csv_path, updated, begin_tstamp=None, end_tstamp=None):
    '''Exports all the database summary to a single file'''
    fieldnames = EXPORT_CSV_HEADERS
    if extended:
        fieldnames.extend(EXPORT_CSV_ADD_HEADERS)
    with open(csv_path, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(fieldnames)
        iterable = export_iterable(connection, extended, updated, begin_tstamp, end_tstamp)
        for row in iterable:
            row = list(row)
            row[1] = f"{row[1][0:5]}{int(row[1][5:]):04d}" # reformat starsXXXXX 
            row[5] = row[5] + 'Z' # reformat session timestamp 
            writer.writerow(row)
    log.info(f"Saved summary calibration data to CSV file: '{os.path.basename(csv_path)}'")


def summary_view_sql(connection, latest, also_ref, view_all):
    
    if latest and not also_ref and not view_all:
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE session = (SELECT MAX(session) FROM summary_v WHERE name = :name)
        ORDER BY session ASC
        '''
    elif latest and also_ref and not view_all:
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Ref. Freq (Hz)", "Ref. Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, ref_freq, ref_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE session = (SELECT MAX(session) FROM summary_v WHERE name = :name)
        ORDER BY session ASC
        '''
    elif not latest and not also_ref and not view_all: 
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE session = :session
        ORDER BY session ASC
        '''
    elif not latest and also_ref and not view_all:
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Ref. Freq (Hz)", "Ref. Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, ref_freq, ref_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE session = :session
        ORDER BY session ASC
        '''
    elif view_all and not also_ref:
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE name = :name
        ORDER BY session ASC
        '''
    elif view_all and also_ref:
        headers = ("Session (UTC)", "Name", "ZP", "Freq (Hz)", "Mag", "Ref. Freq (Hz)", "Ref. Mag", "Prev ZP", "Updated?")
        sql = '''
        SELECT session, name, zero_point, test_freq, test_mag, ref_freq, ref_mag, prev_zp, upd_flag
        FROM summary_v
        WHERE name = :name
        ORDER BY session ASC
        '''
    else:
        sql = None
        headers = tuple()
    return sql, headers


def summary_get_zero_point(connection, updated, begin_tstamp, end_tstamp):
    row = {'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp, 'updated': updated}
    cursor = connection.cursor()
    if updated is not None:
        cursor.execute('''
            SELECT zero_point 
            FROM summary_t 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
            AND role = 'test'
            AND upd_flag = :updated
        ''', row)
    else:
        cursor.execute('''
            SELECT zero_point 
            FROM summary_t 
            WHERE session BETWEEN :begin_tstamp AND :end_tstamp
            AND role = 'test'
        ''', row)

    result = list(map(lambda x: x[0], cursor))
    return result
   

# ==================
# 'summary' commands
# ==================

def export(connection, options):
    '''Exports all the database to a single file'''
    summary_export(connection, options.extended, options.csv_file, options.updated)


# Differences may come from old log file parsing
def differences(connection, options):
    '''Show summary mismatches from rounds information'''
    cursor = connection.cursor()
    cursor.execute(
        '''
        SELECT session, model, name, zero_point, test_freq
        FROM summary_v
        WHERE session NOT IN (SELECT DISTINCT session || 'Z' from rounds_t)
        ORDER BY session ASC
        ''')
    paging(cursor,["Session (UTC)","Model","Name", "ZP", "Frequency (Hz)"])


def view(connection, options):
    '''Show summary data for a given photometer'''
    row = {'name': options.name}
    if options.session:
        row['session'] = options.session.strftime(TSTAMP_SESSION_FMT) + 'Z'
    sql, headers = summary_view_sql(connection, options.latest, options.also_ref, options.all)
    cursor = connection.cursor()
    cursor.execute(sql, row)
    paging(cursor, headers)