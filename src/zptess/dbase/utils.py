# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import os
import os.path
import glob
import sqlite3

# -------------------
# Third party imports
# -------------------

#--------------
# local imports
# -------------

# ----------------
# Module constants
# ----------------

VERSION_QUERY = "SELECT value from config_t WHERE section ='database' AND property = 'version'"

# -----------------------
# Module global variables
# -----------------------

# ------------------------
# Module Utility Functions
# ------------------------

def _filter_factory(connection):
    cursor = connection.cursor()
    cursor.execute(VERSION_QUERY)
    result = cursor.fetchone()
    if not result:
        raise NotImplementedError(VERSION_QUERY)
    version = int(result[0])
    return lambda path: int(os.path.basename(path)[:2]) > version


# -------------------------
# Module exported functions
# -------------------------


def create_database(dbase_path):
    '''Creates a Database file if not exists and returns a connection'''
    new_database = False
    output_dir = os.path.dirname(dbase_path)
    if not output_dir:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    if not os.path.exists(dbase_path):
        with open(dbase_path, 'w') as f:
            pass
        new_database = True
    return sqlite3.connect(dbase_path), new_database


def create_schema(connection, schema_path, initial_data_dir_path, updates_data_dir, query=VERSION_QUERY):
    created = True
    cursor = connection.cursor()
    try:
        cursor.execute(query)
    except Exception:
        created = False
    if not created:
        with open(schema_path) as f: 
            lines = f.readlines() 
        script = ''.join(lines)
        connection.executescript(script)
        #log.info("Created data model from {0}".format(os.path.basename(schema_path)))
        file_list = glob.glob(os.path.join(initial_data_dir_path, '*.sql'))
        for sql_file in file_list:
            #log.info("Populating data model from {0}".format(os.path.basename(sql_file)))
            with open(sql_file) as f: 
                lines = f.readlines() 
            script = ''.join(lines)
            connection.executescript(script)
    else:
        filter_func = _filter_factory(connection)
        file_list = sorted(glob.glob(os.path.join(updates_data_dir, '*.sql')))
        file_list = list(filter(filter_func,file_list))
        for sql_file in file_list:
            print("Applying updates to data model from {0}".format(os.path.basename(sql_file)))
            with open(sql_file) as f: 
                lines = f.readlines() 
            script = ''.join(lines)
            connection.executescript(script)
    connection.commit()
    return not created, file_list

  
__all__ = [
    "create_database",
    "create_schema",
]
