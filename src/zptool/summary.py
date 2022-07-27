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
from zptool.utils import paging


EXPORT_CSV_HEADERS = [ "Model","Name","Timestamp","Magnitud TESS.","Frecuencia","Magnitud Referencia",
					"Frec Ref","MagDiff vs stars3","ZP (raw)", "Extra offset", "Final ZP", "Station MAC","OLD ZP",
					"Author","Firmware","Updated"]
EXPORT_CSV_ADD_HEADERS = ["# Rounds", "ZP Sel. Method", "Freq Method", "Ref Freq Method"]

EXPORT_HEADERS = ("model","name","session", "test_mag", "test_freq", "ref_mag", "ref_freq", 
					"mag_diff", "raw_zero_point", "offset", "zero_point", "mac", "prev_zp", "author", "firmware", "upd_flag")
EXPORT_ADD_HEADERS = ("offset","nrounds","zero_point_method","test_freq_method","ref_freq_method" )
       		
NAMES_MAP = {
    "Model" : "model", 
    "Name" : "name",
    "Timestamp": "session",
    "Magnitud TESS" : "test_mag",
    "Frecuencia" : "test_freq",
    "Magnitud Referencia" : "ref_mag",
    "Frec Ref" : "ref_freq",
    "Offset vs stars3" : "mag_diff",
    "ZP": "zero_point",
    "Station MAC": "mac",
    "OLD ZP": "prev_zp"
}


# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")


def dyn_sql(columns, updated, begin_tstamp):
    all_columns = ",".join(columns)
    if begin_tstamp is None and updated is None:
        sql = f"SELECT {all_columns} FROM summary_v ORDER BY session ASC"
    elif begin_tstamp is None and updated is not None:
        sql = f"SELECT {all_columns} FROM summary_v WHERE upd_flag = :updated ORDER BY session ASC"
    elif begin_tstamp is not None and updated is None:
        sql = f"SELECT {all_columns} FROM summary_v WHERE session BETWEEN :begin_tstamp AND :end_tstamp ORDER BY session ASC"
    else:
        sql = f"SELECT {all_columns} FROM summary_v WHERE upd_flag = :updated AND session BETWEEN :begin_tstamp AND :end_tstamp ORDER BY session ASC"
    return sql


def export_iterable(connection, extended, updated, begin_tstamp, end_tstamp):
    cursor = connection.cursor()
    headers = EXPORT_HEADERS + EXPORT_ADD_HEADERS if extended else EXPORT_HEADERS
    row = {'updated': updated, 'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp}
    sql = dyn_sql(headers, updated, begin_tstamp)
    cursor.execute(sql, row)
    return cursor


def remap_2_summary_rows(item):
    test = {
        'session'          : item['Timestamp'][:-1],
        'role'             : 'test',
        'model'            : item['Model'],
        'name'             : item['Name'],
        'mac'              : item['Station MAC'],
        'firmware'         : item['Firmware'],
        'prev_zp'          : item['OLD ZP'],
        'author'           : item['Author'],
        'nrounds'          : None, # For the time being
        'offset'           : 0.0, # Foir the time being, we have the new boxes ....
        'upd_flag'         : 1 if item['Updated'] == 'True' else 0,
        'zero_point'       : float(item['ZP']),
        'freq'             : float(item['Frecuencia']),
        'mag'              : float(item['Magnitud TESS.']),
        'zero_point_method': None, # for the time being
        'freq_method'      : None, # for the time being
    }
    ref  = {
        'session'          : item['Timestamp'][:-1],
        'role'             : 'ref',
        'model'            : "TESS-W",
        'name'             : "stars3",
        'mac'              : "18:FE:34:CF:E9:A3",
        'firmware'         : '',
        'prev_zp'          : 20.50,
        'author'           : item['Author'],
        'nrounds'          : None, # For the time being
        'offset'           : 0.0, 
        'upd_flag'         : 0,
        'zero_point'       : 20.50,
        'freq'             : float(item['Frec Ref']),
        'mag'              : float(item['Magnitud Referencia']),
        'zero_point_method': None, # Always
        'freq_method'      : None, # for the time being
    }

    return ref, test

def fix_frequency(row):
    if (row['freq'] > 1000):
        fix = row['freq']/1000
        log.warning(f"{row['name']} has wrong frequency {row['freq']} => {fix:.3f}")
        row['freq'] = fix

def write_to_summary_table(connection, rows):
    cursor = connection.cursor()
    cursor.executemany(
        '''
        INSERT OR IGNORE INTO summary_t (
            session,
            role, 
            model, 
            name,
            mac,  
            firmware,
            prev_zp,
            author,
            nrounds,
            offset,
            upd_flag,
            zero_point,
            zero_point_method,
            freq,
            freq_method,
            mag
        )
        VALUES (
            :session,
            :role, 
            :model, 
            :name,
            :mac,  
            :firmware,
            :prev_zp,
            :author,
            :nrounds,
            :offset,
            :upd_flag,
            :zero_point,
            :zero_point_method,
            :freq,
            :freq_method,
            :mag
        )
        ''',
        rows,
    )
    connection.commit()

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

def summary_export(connection, extended, csv_path, updated=None, begin_tstamp=None, end_tstamp=None):
    '''Exports all the database to a single file'''
    fieldnames = EXPORT_CSV_HEADERS
    if extended:
        fieldnames.extend(EXPORT_CSV_ADD_HEADERS)
    with open(csv_path, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(fieldnames)
        iterable = export_iterable(connection, extended, updated, begin_tstamp, end_tstamp)
        for row in iterable:
            row = list(row)
            row[13] = bool(row[13]) 
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

def load(connection, options):
    '''Exports all the database to a single file'''
    rows=list()
    with open(options.csv_file, newline='') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=';')
        for row in reader:
            ref, test = remap_2_summary_rows(row)
            fix_frequency(test)
            fix_frequency(ref)
            rows.append(ref)
            rows.append(test)
        log.info(f"Processed {len(rows)//2} items")
    write_to_summary_table(connection, rows)


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