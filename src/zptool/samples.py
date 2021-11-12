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

import csv 
import math
import logging
import os.path
import statistics

# --------------------
# Third party packages
# --------------------


# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT
from zptool.utils import paging
from zptool.summary import summary_latest_session, summary_get_test_data, summary_get_ref_data, summary_get_info
from zptool.summary import summary_session_from_name

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")


def get_samples_from_round(connection, session, model, role, r):
    cursor = connection.cursor()
    row = {'round': r, 'session': session, 'role': role}
    cursor.execute('''
        SELECT u.model, u.name, u.mac, u.session, u.role, r.round, s.tstamp, s.freq, s.temp_box, s.seq
        FROM samples_t AS s
        JOIN rounds_t  AS r USING(role, session)
        JOIN summary_t AS u USING(role, session)
        WHERE s.tstamp BETWEEN r.begin_tstamp AND r.end_tstamp
        AND r.session = :session
        AND r.role    = :role
        AND r.round   = :round
        ORDER BY s.tstamp ASC, r.role DESC, r.round ASC
    ''', row)
    return cursor

def get_samples_count_from_round(connection, session, model, role, r):
    cursor = connection.cursor()
    row = {'round': r, 'session': session, 'role': role}
    cursor.execute('''
        SELECT nsamples
        FROM rounds_t 
        WHERE session = :session
        AND role    = :role
        AND round   = :round
    ''', row)
    return cursor.fetchone()[0]


def compute_stats(cursor, r):
    iterable = cursor.fetchall()
    # Extracte metadata from database rows and frequencies as well
    frequencies = list(map(lambda t: t[6], iterable))
    metadata    = list(map(lambda t: t[0:4], iterable))
    aver = statistics.mean(frequencies)
    median = statistics.median(frequencies)
    mode = statistics.mode(frequencies)
    row = list(metadata[0])
    row.append(r)
    row.append(round(aver,3))
    row.append(round(statistics.stdev(frequencies, aver), 3))
    row.append(median)
    row.append(round(statistics.stdev(frequencies, median), 3))
    row.append(mode)
    row.append(round(statistics.stdev(frequencies, mode), 3))        
    return row

def compute_magdif(test_stats_row, ref_stats_row):
    centrals = ( 
        (ref_stats_row[5], test_stats_row[5]),  # mean
        (ref_stats_row[7], test_stats_row[7]),  # median
        (ref_stats_row[9], test_stats_row[9]),  # mode
    )
    magdif_list = [-2.5*math.log10(ref/test) for ref, test in centrals]
    return test_stats_row[0:5] + magdif_list

def compute_zero_point(test_stats_row, ref_stats_row):
    ZP_ABS = 20.44
    md = compute_magdif(test_stats_row, ref_stats_row)
    for i in range(5,8):
        md[i] = round(md[i] + ZP_ABS, 2)
    return md

def compute_histo(cursor, r):
    iterable = cursor.fetchall()
    # Extracte metadata from database rows and frequencies as well
    frequencies = list(map(lambda t: t[6], iterable))
    metadata    = list(map(lambda t: t[0:4], iterable))
    histo = { f:0 for f in frequencies}
    for f in frequencies:
        histo[f] += 1
    N = len(frequencies)
    histo = [metadata[0] + (r,) + (key,value,100*value/N ) for key, value in histo.items()]
    histo = sorted(histo, key=lambda t: t[7], reverse=True)
    return histo


def samples_write(connection, writer, r, nrounds, session, model, name, role):
    log.debug(f"[{r}/{nrounds}]: {session}, {model}, {name}, {role}")
    iterable = get_samples_from_round(connection, session, model, role, r)
    for row in iterable:
        writer.writerow(row)

# -------------------------------------
# Useful functions to be used elsewhere
# -------------------------------------

def samples_export(connection, session, roun, also_ref, csv_path):
    '''Exports individual samples froma photometer to a CSV file'''
    HEADERS = ("Model", "Name", "MAC", "Session (UTC)", "Role", "Round", "Timestamp", "Frequency", "Box Temperature", "Sequence #")
    test_model, test_name, nrounds = summary_get_info(connection, session, 'test')
    ref_model , ref_name, _       = summary_get_info(connection, session, 'ref')
    with open(csv_path, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(HEADERS)
        log.info(f"Writting samples for {test_name}, all rounds ({nrounds} rounds)")
        if roun is None:   # round None is a marker for all rounds
            for r in range(1, nrounds+1):
                samples_write(connection, writer, r, nrounds, session, test_model, test_name, 'test')
            if also_ref:
                for r in range(1, nrounds+1):       
                    samples_write(connection, writer, r, nrounds, session, ref_model, ref_name, 'ref')
        else:
            r = roun
            samples_write(connection, writer, r, nrounds, session, test_model, test_name, 'test')
            if also_ref:
                samples_write(connection, writer, r, nrounds, session, ref_model, ref_name, 'ref')
    log.info(f"Saved samples to CSV file: '{os.path.basename(csv_path)}'")
     

# ==================
# 'samples' commands
# ==================

def export(connection, options):
    '''Exports individual samples froma photometer to a CSV file'''
    if options.latest:
        session = summary_session_from_name(connection, options.name,'test', options.updated)
    else:
        session  = options.session
    if session is None:
         log.error(f"No photometer summary data for {options.name}")
    else:
        session, = session
        roun     = None if options.all else options.round 
        also_ref = options.also_ref
        csv_file = options.csv_file
        samples_export(connection, session, roun, also_ref, csv_file)


def view(connection, options):
    '''Show individual samples for a given photometer'''
    HEADERS = ("Model", "Name", "MAC", "Session (UTC)", "Role", "Round", "Timestamp", "Freq (Hz)", "Box Temp", "# Seq")
    try:
        session, model, name, role, nrounds = summary_get_test_data(connection, options.name, options.latest, options.session, options.updated)
        _, ref_model, ref_name, ref_role, _ = summary_get_ref_data(connection, session)
    except TypeError:
        log.error(f"No photometer summary data for {options.name}")
    else:
        if options.all:
            for r in range(1, nrounds+1):
                size = get_samples_count_from_round(connection, session, model, role, r)
                cursor = get_samples_from_round(connection, session, model, role, r)
                paging(cursor, HEADERS)
                input("Press Enter to continue [Ctrl-C to abort] ...")
                if options.also_ref:
                    size = get_samples_count_from_round(connection, session, ref_model, ref_role, r)
                    cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                    paging(cursor, HEADERS)
                    input("Press Enter to continue [Ctrl-C to abort] ...")
        else:

            r = options.round
            size = get_samples_count_from_round(connection, session, model, role, r)
            cursor = get_samples_from_round(connection, session, model, role, r)
            paging(cursor, HEADERS)
            if options.also_ref:
                size = get_samples_count_from_round(connection, session, ref_model, ref_role, r)
                cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                paging(cursor, HEADERS)


def stats(connection, options):
    HEADERS = ("Model", "Name", "Session (UTC)", "Role", "Round","Mean (Hz)", "\u03C3 (Hz)", "Median (Hz)", "\u03C3 (Hz)", "Mode (Hz)", "\u03C3 (Hz)")
    try:
        session, model, name, role, nrounds = summary_get_test_data(connection, options.name, options.latest, options.session, options.updated)
        _, ref_model, ref_name, ref_role, _ = summary_get_ref_data(connection, session)
    except TypeError:
        log.error(f"No photometer summary data for {options.name}")
    else:
        if options.all:
            result = list()
            for r in range(1, nrounds+1):
                cursor = get_samples_from_round(connection, session, model, role, r)
                result.append(compute_stats(cursor, r))
                if options.also_ref:
                    cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                    result.append(compute_stats(cursor, r))
            paging(result, HEADERS)
        else:
            r = options.round
            cursor = get_samples_from_round(connection, session, model, role, r)
            result = list()
            result.append(compute_stats(cursor, r))
            if options.also_ref:
                cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                result.append(compute_stats(cursor, r))
            paging(result, HEADERS)


def hist(connection, options):
    HEADERS = ("Model", "Name", "Session (UTC)", "Role", "Round","Freq (Hz)", "Count", "%")
    try:
        session, model, name, role, nrounds = summary_get_test_data(connection, options.name, options.latest, options.session, options.updated)
        _, ref_model, ref_name, ref_role, _ = summary_get_ref_data(connection, session)
    except TypeError:
        log.error(f"No photometer summary data for {options.name}")
    else:
        r = options.round
        result = list()
        cursor = get_samples_from_round(connection, session, model, role, r)
        histo = compute_histo(cursor, r)
        if options.also_ref:
            cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
            histo.extend(compute_histo(cursor, r))
        paging(result, HEADERS) 


def zero(connection, options):
    HEADERS = ("Model", "Name", "Session (UTC)", "Role", "Round","ZP Mean", "ZP Median",  "ZP Mode")
    try:
        session, model, name, role, nrounds = summary_get_test_data(connection, options.name, options.latest, options.session, options.updated)
        _, ref_model, ref_name, ref_role, _ = summary_get_ref_data(connection, session)
    except TypeError:
        log.error(f"No photometer summary data for {options.name}")
    else:
        if options.all:
            result = list()
            for r in range(1, nrounds+1):
                cursor = get_samples_from_round(connection, session, model,role, r)
                test_stats_row = compute_stats(cursor, r)
                cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                ref_stats_row = compute_stats(cursor, r)
                row = compute_zero_point(test_stats_row, ref_stats_row)
                result.append(row)     
            paging(result, HEADERS)
        else:
            r = options.round
            cursor = get_samples_from_round(connection, session, model, role, r)
            test_stats_row = compute_stats(cursor, r)
            cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
            ref_stats_row = compute_stats(cursor, r)
            row = compute_zero_point(test_stats_row, ref_stats_row)
            result = list()
            result.append(row)
            paging(result, HEADERS)


def magdif(connection, options):
    HEADERS = ("Model", "Name", "Session (UTC)", "Role", "Round","\u0394 Mag Mean", "\u0394 Mag Median", "\u0394 Mag Mode")
    try:
        session, model, name, role, nrounds = summary_get_test_data(connection, options.name, options.latest, options.session, options.updated)
        _, ref_model, ref_name, ref_role, _ = summary_get_ref_data(connection, session)
    except TypeError:
        log.error(f"No photometer summary data for {options.name}")
    else:
        if options.all:
            result = list()
            for r in range(1, nrounds+1):
                cursor = get_samples_from_round(connection, session, model, role, r)
                test_stats_row = compute_stats(cursor, r)
                cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
                ref_stats_row = compute_stats(cursor, r)
                row = compute_magdif(test_stats_row, ref_stats_row)
                result.append(row)
            paging(result, HEADERS)

        else:
            r = options.round
            cursor = get_samples_from_round(connection, session, model, role, r)
            test_stats_row = compute_stats(cursor, r)
            cursor = get_samples_from_round(connection, session, ref_model, ref_role, r)
            ref_stats_row = compute_stats(cursor, r)
            row = compute_magdif(test_stats_row, ref_stats_row)
            result = list()
            result.append(row)
            paging(result, HEADERS)

# ###########################################
