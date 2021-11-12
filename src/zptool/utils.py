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

import logging
import datetime
import itertools

#--------------------
# Third party imports
# -------------------

import tabulate

# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT

RECORD_START = r'(\[global#info] zptess|\[zptess#info] starting ZPTESS)'

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")

def paging(iterable, headers, size=None, page=10):
    '''
    Pages query output from database and displays in tabular format
    '''
    db_iterable = hasattr(iterable, 'fetchmany')
    while True:
        if db_iterable:
            result = iterable.fetchmany(page)
        else:
            result = list(itertools.islice(iterable, page))
        if len(result) == 0:
            break
        if size is not None:
            size -= page
            if size < 0:
                result = result[:size]  # trim the last rows up to size requested
                print(tabulate.tabulate(result, headers=headers, tablefmt='grid'))
                break
            elif size == 0:
                break
        print(tabulate.tabulate(result, headers=headers, tablefmt='grid'))
        if len(result) < page:
            break
        input("Press Enter to continue [Ctrl-C to abort] ...")
    

def mkbool(boolstr):
    result = None
    if boolstr == 'True':
        result = True
    elif boolstr == 'False':
        result = False
    return result

def mkdate(datestr):
    date = None
    for fmt in ['%Y-%m','%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%Y-%m-%dT%H:%M:%SZ']:
        try:
            date = datetime.datetime.strptime(datestr, fmt)
        except ValueError:
            pass
    return date

def read_property(connection, section, proper):
    cursor = connection.cursor()
    row = {'section': section, 'property': proper}
    cursor.execute("SELECT value FROM config_t WHERE section = :section AND property = :property", row)
    return cursor.fetchone()[0]

def update_property(connection, section, proper, value):
    cursor = connection.cursor()
    row = {'section': section, 'property': proper, 'value': value}
    cursor.execute("UPDATE config_t SET value = :value WHERE section = :section AND property = :property", row)
    connection.commit()

def section_display(iterable):
    headers = ("Section", "Propèrty", "Value")
    paging(iterable, headers)

def section_read(connection, section):
    row = {'section': section,}
    cursor = connection.cursor()
    cursor.execute('SELECT section, property, value FROM config_t WHERE section = :section', row)
    return cursor
