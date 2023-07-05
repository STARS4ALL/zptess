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
import os 
import os.path
import datetime
import logging
import zipfile
import traceback
import statistics

# --------------------
# Third party packages
# --------------------

import requests

# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT
from zptool.utils import paging, read_property
from zptool.summary import summary_number_of_sessions, summary_export, summary_sessions_iterable, summary_get_info, summary_get_zero_point
from zptool.rounds  import rounds_export
from zptool.samples import samples_export
from zptool.emailer import email_send

log = logging.getLogger("zptool")


# ----------------
# Helper functions
# ----------------

def get_paths(directory):
    '''Get all file paths in a list''' 
    file_paths = [] 
    # crawling through directory and subdirectories 
    for root, directories, files in os.walk(directory):
        root = os.path.basename(root) # Needs a change of cwd later on if we do this
        log.debug("Exploring directory '{0}'".format(root))
        for filename in files: 
            filepath = os.path.join(root, filename) 
            file_paths.append(filepath) 
    return file_paths         


def pack(base_dir, zip_file):
    '''Pack all files in the ZIP file given by options'''
    paths = get_paths(base_dir)
    log.info(f"Creating ZIP File: '{os.path.basename(zip_file)}'")
    with zipfile.ZipFile(zip_file, 'w') as myzip:
        for myfile in paths: 
            myzip.write(myfile) 


def batch_view_iterable(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT begin_tstamp, end_tstamp, calibrations, email_sent, comment FROM batch_t ORDER BY begin_tstamp DESC")
    return cursor

def check_open_batch(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT count(*) FROM batch_t WHERE begin_tstamp IS NOT NULL AND end_tstamp IS NULL")
    n = cursor.fetchone()[0]
    if n > 0:
        result = True
    else:
        result = False
    return result

def get_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)

def get_open_batch(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT begin_tstamp FROM batch_t WHERE end_tstamp IS NULL")
    return cursor.fetchone()[0]

def update_email_state(connection, tstamp, flag):
    cursor = connection.cursor()
    row = {'tstamp': tstamp, 'flag': flag}
    cursor.execute("UPDATE batch_t SET email_sent = :flag WHERE begin_tstamp = :tstamp", row)
    connection.commit()

def insert_begin(connection, tstamp, comment):
    cursor = connection.cursor()
    row = {'tstamp': tstamp, 'comment': comment}
    cursor.execute("INSERT INTO batch_t(begin_tstamp, end_tstamp, comment) VALUES(:tstamp, NULL, :comment)", row)

def insert_end(connection, begin_tstamp, end_tstamp, N):
    cursor = connection.cursor()
    row = {'end_tstamp': end_tstamp, 'N': N}
    cursor.execute('''
        UPDATE batch_t
        SET end_tstamp = :end_tstamp, calibrations = :N
        WHERE begin_tstamp = (SELECT begin_tstamp WHERE end_tstamp IS NULL)
        ''', row)

def batch_iterable(connection):
    cursor = connection.cursor()
    cursor.execute('''
        SELECT begin_tstamp, end_tstamp, email_sent, calibrations 
        FROM batch_t 
        WHERE end_tstamp IS NOT NULL
        ORDER BY begin_tstamp DESC
    ''')
    return cursor.fetchall()

def batch_latest(connection):
    cursor = connection.cursor()
    cursor.execute('''
        SELECT begin_tstamp, end_tstamp, email_sent, calibrations 
        FROM batch_t 
        WHERE end_tstamp IS NOT NULL
        AND begin_tstamp = (SELECT MAX(begin_tstamp) FROM batch_t)
        ORDER BY begin_tstamp DESC
    ''')
    return cursor.fetchone()

def batch_specific(connection, tstamp):
    cursor = connection.cursor()
    row = {'begin_tstamp': tstamp}
    cursor.execute('''
        SELECT begin_tstamp, end_tstamp, email_sent, calibrations 
        FROM batch_t
        WHERE begin_tstamp =: begin_tstamp
        WHERE end_tstamp IS NOT NULL
        ORDER BY begin_tstamp DESC
    ''', row)
    return cursor.fetchone()

def batch_delete(connection, rows):
    cursor = connection.cursor()
    cursor.executemany('''
        DELETE FROM batch_t 
        WHERE begin_tstamp = :begin_tstamp 
         AND end_tstamp    = :end_tstamp
    ''', rows)


def batch_export(connection, batch, base_dir, updated, send_email):
    begin_tstamp, end_tstamp, email_sent, calibrations = batch
    log.info(f"(begin_tstamp, end_tstamp)= ({begin_tstamp}, {end_tstamp}, up to {calibrations} calibrations)")
    suffix1 = f"from_{begin_tstamp}_to_{end_tstamp}".replace('-','').replace(':','')
    export_dir = os.path.join(base_dir, suffix1)
    os.makedirs(export_dir, exist_ok=True)
    csv_path = os.path.join(export_dir, f"summary_{suffix1}.csv")
    summary_export(
        connection   = connection,
        extended     = False, 
        updated      = updated,   # This should be true when sendimg email to people
        csv_path     = csv_path,
        begin_tstamp = begin_tstamp, 
        end_tstamp   = end_tstamp, 
    )
    iterable = summary_sessions_iterable(connection, updated, begin_tstamp, end_tstamp)
    for i, (session,) in enumerate(iterable):
        log.info(f"Calibration {session} [{i+1}/{calibrations}] (updated = {bool(updated)})")
        _, name, _ = summary_get_info(connection, session, 'test')
        rounds_name = f"{name}_rounds_{session}.csv".replace('-','').replace(':','')
        samples_name = f"{name}_samples_{session}.csv".replace('-','').replace(':','')
        rounds_export(
            connection   = connection,
            updated      = updated, # This should be true when sendimg email to people
            csv_path     = os.path.join(export_dir, rounds_name),
            session      = session, 
        )
        samples_export(
            connection   = connection,
            session      = session,
            roun         = None, # None is a marker for all rounds,
            also_ref     = True, # Include reference photometer samples
            csv_path     = os.path.join(export_dir, samples_name),
        )
        
    # Prepare a ZIP File
    try:
        prev_workdir = os.getcwd()
        zip_file = os.path.join(base_dir, suffix1 + '.zip' )
        os.chdir(base_dir)
        pack(export_dir, zip_file)
    except Exception as e:
        log.error(f"excepcion {e}")
    finally:
        os.chdir(prev_workdir)

    if not send_email:
        return
    if email_sent is None:
        log.info("Never tried to send an email for this batch")
    elif email_sent == 0:
        log.info("Tried to send email for this batch previously but failed")
    else:
        log.info("Already sent an email for this batch")
    # Test internet connectivity
    try:
        request = requests.get("http://www.google.com", timeout=5)
        log.info("Connected to Internet")
    except (requests.ConnectionError, requests.Timeout) as exception:
        log.warning("No connection to internet. Stopping here")
        return

    # Check email configuration
    config = dict()
    missing = list()
    smtp_keys   = ("host", "port", "sender", "password", "receivers")
    for key in smtp_keys:
        try:
            config[key] = read_property(connection, "smtp", key)
        except Exception as e:
            missing.append(key)
            continue
    if len(config) != len(smtp_keys):
        log.error(f"Missing configuration: {missing}")
        return   

    # Email ZIP File
    try:
        email_sent = 1
        receivers = read_property(connection, "smtp","receivers")
        email_send(
            subject    = f"[STARS4ALL] TESS calibration data from {begin_tstamp} to {end_tstamp}", 
            body       = "Find attached hereafter the summary, rounds and samples from this calibration batch", 
            sender     = config["sender"],
            receivers  = config["receivers"], 
            attachment = zip_file, 
            host       = config["host"], 
            port       = int(config["port"]),
            password   = config["password"],
        )
    except Exception as e:
        # Mark fail in database
        email_sent = 0
        log.error(f"Exception while sending email: {e}")
        print(traceback.format_exc())
    else:
        # Mark success in database
        log.info(f"Mail succesfully sent.")
    finally:
        update_email_state(connection, begin_tstamp, email_sent)


# ================
# 'batch' commands
# ================

def begin(connection, options):
    '''Exports all the database to a single file'''
    if check_open_batch(connection):
        log.error("A batch is already open")
        return
    comment =  " ".join(options.comment)
    insert_begin(connection, get_timestamp(), comment)
    connection.commit()
    log.info("A new batch has been opened")


def end(connection, options):
    '''Exports all the database to a single file'''
    if not check_open_batch(connection):
        log.error("There is no open batch to close")
        return
    begin_tstamp = get_open_batch(connection)
    end_tstamp   = get_timestamp()
    N = summary_number_of_sessions(connection, begin_tstamp, end_tstamp)
    insert_end(connection, begin_tstamp, end_tstamp, N)
    connection.commit()
    log.info("Current open batch has been closed")


def view(connection, options):
    '''Exports all the database to a single file'''
    HEADERS = ("Begin (UTC)","End (UTC)","# Sessions","Emailed?","Comment")
    cursor =  batch_view_iterable(connection)
    paging(cursor, HEADERS, size=100)


def purge(connection, options):
    '''Exports all the database to a single file'''
    batches = list()
    for begin_tstamp, end_tstamp, _, _ in batch_iterable(connection):
        n = summary_number_of_sessions(connection, begin_tstamp, end_tstamp)
        if n == 0:
            batches.append({'begin_tstamp': begin_tstamp, 'end_tstamp': end_tstamp})
    log.info(f"purging {len(batches)} batches with unreferenced calibration sessions")
    batch_delete(connection, batches)
    connection.commit()


def export(connection, options):
    if options.latest:
        if check_open_batch(connection):
            log.error("A batch is already open, close it first to export")
            return
        batch = batch_latest(connection)
        if not batch:
            log.error("No batches registered")
            return
        batch_export(connection, batch, options.base_dir, options.updated, options.email)
    elif options.begin_date:
        batch = batch_specific(connection, options.begin_date)
        if not batch:
            log.error(f"No batches registered with staring date {options.begin_date}")
            return
        batch_export(connection, batch, options.base_dir, options.updated, options.email)
    else:
        for begin_tstamp, end_tstamp in batch_iterable(connection):
            batch_export(connection, batch, options.base_dir, options.updated, options.email)
            

def stats(connection, options):
    HEADER = ("from","to","N","mean","stdev")
    if options.latest:
        log.info(f"calculating mean zero point for latest batch")
        begin_tstamp, end_tstamp, _, N = batch_latest(connection)
        do_zero_point_stats(connection, begin_tstamp, end_tstamp, N, options.csv_file)

    elif options.begin_date:
        log.info(f"calculating mean zero point for specific batch {options.begin_date}")
        begin_tstamp, end_tstamp, _, N = batch_specific(connection, options.begin_date)
        do_zero_point_stats(connection, begin_tstamp, end_tstamp, N, options.csv_file)

    else:
        log.info(f"calculating mean zero point for all batches")
        stats = list()
        for begin_tstamp, end_tstamp, _, N in batch_iterable(connection):
            zero_points = summary_get_zero_point(connection, None, begin_tstamp, end_tstamp)
            try:
                mean = round(statistics.mean(zero_points),2)
                stdev = round(statistics.stdev(zero_points),3)
            except Exception as e:
                log.warn(f"Excluding batch {begin_tstamp} from the list due to: {e}")
            else:
                stats.append((begin_tstamp, end_tstamp, N, mean, stdev))

        log.info(f"Generating CSV file with {len(stats)} entries + header")
        with open(options.csv_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(HEADER)
            for row in stats:
                writer.writerow(row)
        if options.view:
            paging(stats, HEADER,size=len(stats))
           


         