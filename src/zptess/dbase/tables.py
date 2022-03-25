# ----------------------------------------------------------------------
# Copyright (c) 2022
#
# See the LICENSE file for details
# see the AUTHORS file for authors
# ----------------------------------------------------------------------

#--------------------
# System wide imports
# -------------------

import sqlite3
import datetime

# ---------------
# Twisted imports
# ---------------

from twisted.logger import Logger
from twisted.enterprise import adbapi

#--------------
# local imports
# -------------

from zptess.logger import setLogLevel

# ----------------
# Module constants
# ----------------

NAMESPACE = 'DBASE'

# Insert variations
QUERY_INSERT_OR_REPLACE = 1
INSERT_OR_REPLACE = 2
INSERT = 3

# -----------------------
# Module global variables
# -----------------------

log = Logger(NAMESPACE)

class Table:

    def __init__(self, pool, table, id_column, 
        natural_key_columns, other_columns,
        insert_mode=QUERY_INSERT_OR_REPLACE, log_level='info'):
        self.log = Logger(namespace=table)
        self._pool = pool
        self._table = table
        self._id_column = id_column
        self._natural_key_columns = natural_key_columns
        self._other_columns = other_columns
        self._insert_mode =  insert_mode
        setLogLevel(namespace=table, levelStr=log_level)

    # ----------
    # Public API
    # ----------

    def lookup(self, nk_dict):
        '''
        Read a row returning a dictionary with the column_id value
        nk_dict is a dictionary containing at least the values for the natural key columns
        Returns a Deferred
        '''
        return self._pool.runInteraction( self._readId, nk_dict)


    def load(self, nk_dict):
        '''
        Read a row returning a dictionary with both the natural key columns and other columns
        nk_dict is a dictionary containing at least the values for the natural key columns
        Returns a Deferred
        '''
        return self._pool.runInteraction(self._readEntry, nk_dict)

    def loadById(self, id_dict):
        '''
        Read a row returning a dictionary with both the natural key columns and other columns
        id_dict is a dictionary containing at least the value for the column_id
        Returns a Deferred
        '''
        return self._pool.runInteraction(self._readEntryById, id_dict)


    def loadAll(self):
        ''' 
        Read all rows in the table returning a dictionary with both the natural key columns and other columns
        Returns a Deferred
        '''
        return self._pool.runInteraction(self._readEntries)


    def loadAllNK(self):
        '''
        Read all rows in the table returning a dictionary with the natural key columns
        Returns a Deferred
        '''
        return self._pool.runInteraction(self._readNaturalKeys)


    def save(self, all_dict):
        '''
        Insert or replace a row in the table where data_dict contains the values for both 
        the natural key columns and other columns
        Returns a Deferred
        '''
        mode = self._insert_mode
        if mode == QUERY_INSERT_OR_REPLACE:
            return self._pool.runInteraction( self._insert_qior, all_dict)
        elif mode == INSERT_OR_REPLACE:
            return self._pool.runInteraction( self._insert_ior, all_dict)
        else:
            return self._pool.runInteraction( self._insert_i, all_dict)

    def savemany(self, all_seq_of_dict):
        '''
        Insert or replace a row in the table where data_dict contains the values for both 
        the natural key columns and other columns
        Returns a Deferred
        '''
        mode = self._insert_mode
        if mode == QUERY_INSERT_OR_REPLACE:
            raise NotImplementedError("savemany() not avaliable for query and insert-or-replace mode")
        elif mode == INSERT_OR_REPLACE:
            return self._pool.runInteraction( self._insert_ior, all_seq_of_dict, many=True)
        else:
            return self._pool.runInteraction( self._insert_i, all_seq_of_dict, many=True)

    def delete(self, nk_dict):
        '''
        Delete a row in the table where nk_dict contains the values for the natural key columns.
        Return count with the rows deleted.
        Returns a Deferred
        '''
        return self._pool.runInteraction( self._delete, nk_dict)


    # ----------------------
    # Private helper methods
    # ----------------------

   # ------------------------------------------------------------------------------------------------

    def _sqlReadId(self):
        table = self._table
        id_column = self._id_column
        natural_keys = self._natural_key_columns
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in natural_keys])
        sql = f"SELECT {id_column} FROM {table} WHERE {unique_conditions};"
        return sql


    def _readId(self, txn, nk_dict):
        query_sql = self._sqlReadId()
        self.log.debug("{sql} {data}", sql=query_sql, data=nk_dict)
        txn.execute(query_sql, nk_dict)
        result = txn.fetchone()
        if result:
            result = dict(zip((self._id_column,), result))
        return result

    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntry(self):
        table = self._table
        natural_keys = self._natural_key_columns
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in natural_keys])
        sql = f"SELECT {all_columns} FROM {table} WHERE {unique_conditions};"
        return sql


    def _readEntry(self, txn, nk_dict):
        query_sql = self._sqlReadEntry()
        all_columns = self._natural_key_columns + self._other_columns
        self.log.debug("{sql} {data}", sql=query_sql, data=nk_dict)
        txn.execute(query_sql, nk_dict)
        result = txn.fetchone()
        if result:
            result = dict(zip(all_columns,result))
        return result

    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntryById(self):
        table = self._table 
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        id_column = self._id_column
        sql = f"SELECT {all_columns} FROM {table} WHERE {id_column} = :{id_column};"
        return sql


    def _readEntryById(self, txn, id_dict):
        query_sql = self._sqlReadEntryById()
        all_columns = self._natural_key_columns + self._other_columns
        self.log.debug("{sql} {data}", sql=query_sql, data=id_dict)
        txn.execute(query_sql, id_dict)
        result = txn.fetchone()
        if result:
            result = dict(zip(all_columns,result))
        return result

    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntries(self):
        table = self._table 
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        order_by  = " ASC,".join(self._natural_key_columns)
        sql = f"SELECT {all_columns} FROM {table};"
        return sql


    def _readEntries(self, txn):
        query_sql = self._sqlReadEntries()
        all_columns = self._natural_key_columns + self._other_columns
        self.log.debug("{sql}", sql=query_sql)
        txn.execute(query_sql)
        result = txn.fetchall()
        if result:
            result = [dict(zip(all_columns, row)) for row in result]
        return result


    # ------------------------------------------------------------------------------------------------

    def _sqlNaturalKeys(self):
        table = self._table 
        natural_keys =  ",".join(self._natural_key_columns)
        order_by = " ASC,".join(self._natural_key_columns)
        sql = f"SELECT {natural_keys} FROM {table};"
        return sql


    def _readNaturalKeys(self, txn):
        query_sql = self._sqlNaturalKeys()
        all_columns = self._natural_key_columns
        self.log.debug("{sql}", sql=query_sql)
        txn.execute(query_sql)
        result = txn.fetchall()
        if result:
            result = [dict(zip(all_columns, row)) for row in result]
        return result

    # ------------------------------------------------------------------------------------------------


    def _sqlPrevQuery(self):
        '''For direct insert operation'''
        table = self._table
        natural_key_columns = self._natural_key_columns
        other_columns = ",".join(self._other_columns)
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in natural_key_columns])
        sql = f"SELECT {other_columns} FROM {table} WHERE {unique_conditions};"
        return sql


    def _sqlInsert(self):
        table = self._table 
        column_list = self._natural_key_columns + self._other_columns
        all_values = ",".join([f":{column}" for column in column_list])
        all_columns = ",".join(column_list)
        sql = f"INSERT INTO {table} ({all_columns}) VALUES ({all_values});"
        return sql

    def _sqlInsertOrReplace(self):
        table = self._table 
        column_list = self._natural_key_columns + self._other_columns
        all_values = ",".join([f":{column}" for column in column_list])
        all_columns = ",".join(column_list)
        sql = f"INSERT OR REPLACE INTO {table} ({all_columns}) VALUES ({all_values});"
        return sql


    def _sqlReplace(self):
        table = self._table 
        natural_key_columns = self._natural_key_columns
        other_columns = self._other_columns
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in natural_key_columns])
        assignments_other = ", ".join([f"{column} = :{column}" for column in other_columns])
        sql = f"UPDATE {table} SET {assignments_other} WHERE {unique_conditions};"
        return sql

    def _insert_ior(self, txn, data, many=False):
        table = self._table
        natural_key_columns = self._natural_key_columns
        other_columns = self._other_columns
        insert_sql = self._sqlInsertOrReplace()
        if many:
            self.log.debug("{sql}", sql=insert_sql)
            txn.executemany(insert_sql, data)
        else:
            self.log.debug("{sql} {data}", sql=insert_sql, data=data)
            txn.execute(insert_sql, data)


    def _insert_i(self, txn, data, many=False):
        table = self._table
        natural_key_columns = self._natural_key_columns
        other_columns = self._other_columns
        insert_sql = self._sqlInsert()
        if many:
            self.log.debug("{sql}", sql=insert_sql)
            txn.executemany(insert_sql, data)
        else:
            self.log.debug("{sql} {data}", sql=insert_sql, data=data)
            txn.execute(insert_sql, data)


    def _insert_qior(self, txn, data):
        # using INSERT OR REPLACE changes the internal id, which is 
        # something undesireable or referential integrity
        self.log.debug("Data to insert/replace: {data}",data=data)
        table = self._table
        natural_key_columns = self._natural_key_columns
        other_columns = self._other_columns
        query_sql = self._sqlPrevQuery()
        replace_sql = self._sqlReplace()
        insert_sql = self._sqlInsert()
        self.log.debug("{sql}", sql=query_sql)
        txn.execute(query_sql, data)
        result = txn.fetchone()
        if not result:
            self.log.debug("{sql} {data}", sql=insert_sql, data=data)
            txn.execute(insert_sql, data)
        else:
            self.log.debug("{sql} {data}", sql=replace_sql, data=data)
            txn.execute(replace_sql, data)

    # ------------------------------------------------------------------------------------------------

    def _sqlCountDelete(self):
        table = self._table 
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"SELECT COUNT(*) FROM {table} WHERE {unique_conditions};"
        self.log.debug("{sql}", sql=sql)
        return sql

    def _sqlDelete(self):
        table = self._table 
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"DELETE FROM {table} WHERE {unique_conditions};"
        self.log.debug("{sql}", sql=sql)
        return sql

    def _delete(self, txn, nk_dict):
        count_sql = self._sqlCountDelete()
        delete_sql = self._sqlDelete()
        self.log.debug("{sql}", sql=count_sql)
        txn.execute(count_sql, nk_dict)
        count = txn.fetchone()
        if count:
            count = count[0]
            if count:
                self.log.debug("{sql} {data}", sql=delete_sql, data=nk_dict)
                txn.execute(delete_sql, nk_dict)
        else:
            count = 0
        return count
        



class VersionedTable(Table):
    '''
    This class handles all versioning of the 'other columns'
    The version control columns are always 'valid_since', 'valid_until' and 'valid_state'
    '''

    END_OF_TIMES = "2999-12-31 23:59:59"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._insert_mode = QUERY_INSERT_OR_REPLACE

    # ----------
    # Public API
    # ----------

    def deleteVersions(self, nk_dict):
        '''
        Delete 'Expired' versions of a row in the table 
        where nk_dict contains the values for the natural key columns
        Return count with the rows deleted.
        Returns a Deferred
        '''
        return self._pool.runInteraction(self._deleteVersions, nk_dict)


    # --------------------------------
    # Private overriden helper methods
    # --------------------------------

    # ------------------------------------------------------------------------------------------------

    def _sqlReadId(self):
        table = self._table
        id_column = self._id_column
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"SELECT {id_column} FROM {table} WHERE valid_state = 'Current' AND {unique_conditions};"
        return sql
        
    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntry(self):
        table = self._table 
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"SELECT {all_columns} FROM {table} WHERE valid_state = 'Current' AND {unique_conditions};"
        return sql

    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntryById(self):
        table = self._table 
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        id_column = self._id_column
        sql = f"SELECT {all_columns} FROM {table} WHERE {id_column} = :{id_column};"
        return sql

    # ------------------------------------------------------------------------------------------------

    def _sqlReadEntries(self):
        table = self._table 
        all_columns = ",".join(self._natural_key_columns + self._other_columns)
        order_by  = " ASC,".join(self._natural_key_columns)
        sql = f"SELECT {all_columns} FROM {table} WHERE valid_state = 'Current';"
        return sql

    # ------------------------------------------------------------------------------------------------

    def _sqlNaturalKeys(self):
        table = self._table 
        natural_keys =  ",".join(self._natural_key_columns)
        order_by  = " ASC,".join(self._natural_key_columns)
        sql = f"SELECT {natural_keys} FROM {table} WHERE valid_state = 'Current';"
        return sql

    # ------------------------------------------------------------------------------------------------

    def _sqlVersionedQuery(self):
        '''For versioned insert operation'''
        versioned = ",".join(self._other_columns)
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"SELECT {versioned},valid_since,valid_until FROM {self._table} WHERE valid_state = 'Current' AND {unique_conditions};"
        return sql


    def _sqlVersionedInsert(self):
        table = self._table 
        column_list = self._natural_key_columns + self._other_columns + ("valid_since","valid_until","valid_state")
        all_values = ",".join([f":{column}" for column in column_list])
        all_columns = ",".join(column_list)
        sql = f"INSERT INTO {table} ({all_columns}) VALUES ({all_values});"
        return sql


    def _sqlVersionedReplace(self):
        table = self._table 
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"UPDATE {table} SET valid_until = :valid_until, valid_state = 'Expired' \
                    WHERE valid_state = 'Current' AND {unique_conditions};"
        return sql


    def _insert_qior(self, txn, data):
        # Cache internal data
        table = self._table
        natural_key_columns = self._natural_key_columns
        other_columns = self._other_columns
        query_sql = self._sqlVersionedQuery()
        replace_sql = self._sqlVersionedReplace()
        insert_sql = self._sqlVersionedInsert()
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        self.log.debug("{sql} {data}", sql=query_sql, data=data)
        txn.execute(query_sql, data)
        result = txn.fetchone()
        if not result:
            self.log.debug("Insert a brand new row in table {table}",table=table)
            data['valid_state'] = 'Current'
            data['valid_until'] = self.END_OF_TIMES
            data['valid_since'] = now
            self.log.debug("{sql} {data}", sql=insert_sql, data=data)
            txn.execute(insert_sql, data)
        else:
            old_values = set(zip(other_columns, result[:-2]))    # Strip dates for comparison
            new_row = data.copy()
            [new_row.pop(key) for key in natural_key_columns]
            new_values = set(new_row.items())
            if new_values == old_values:
                self.log.debug("table {table}, same old and new versioned attributes, do nothing", table=table)
            else:
                self.log.debug("table {table}, set a new version of versioned attributes", table=table)
                data['valid_until'] = now
                self.log.debug("{sql} {data}", sql=replace_sql, data=data)
                txn.execute(replace_sql, data)
                data['valid_state'] = 'Current'
                data['valid_until'] = self.END_OF_TIMES
                data['valid_since'] = now
                self.log.debug("{sql} {data}", sql=insert_sql, data=data)
                txn.execute(insert_sql, data)

    # ------------------------------------------------------------------------------------------------


    def _sqlCountDeleteVersions(self):
        table = self._table 
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"SELECT COUNT(*) FROM {table} WHERE valid_state = 'Expired' AND {unique_conditions};"
        return sql

    def _sqlDeleteVersions(self):
        table = self._table 
        unique_conditions = " AND ".join([f"{column} = :{column}" for column in self._natural_key_columns])
        sql = f"DELETE FROM {table} WHERE valid_state = 'Expired' AND {unique_conditions};"
        return sql   

    def _deleteVersions(self, txn, nk_dict):
        count_sql  = self._sqlCountDeleteVersions()
        delete_sql = self._sqlDeleteVersions()
        self.log.debug("{sql} {data}", sql=count_sql, data=nk_dict)
        txn.execute(count_sql, nk_dict)
        count = txn.fetchone()
        if count:
            count = count[0]
            if count:
                self.log.debug("{sql} {data}", sql=delete_sql, data=nk_dict)
                txn.execute(delete_sql, nk_dict)
        else:
            count = 0
        return count




class ConfigTable:

    def __init__(self, pool, log_level='info'):
        self._pool = pool
        self.log = Logger(namespace='config_t')
        setLogLevel(namespace='config_t', levelStr=log_level)

    def load(self, section, property):
        '''Returns a Deferred'''
        row = {'section': section, 'property': property}
        return self._pool.runInteraction(self._read, row)

    def loadSection(self, section):
        '''Returns a Deferred'''
        row= {'section': section}
        return self._pool.runInteraction(self._readSection, row)

    def save(self, section, property, value):
        '''Returns a Deferred'''
        rows = [{'section': section, 'property': property, 'value': value}]
        return self._pool.runInteraction(self._write, rows)

    def saveSection(self, section, prop_dict):
        '''Returns a Deferred'''
        rows = [{'section': section, 'property': key, 'value': value} for key,value in prop_dict.items()]
        return self._pool.runInteraction(self._write, rows)

    def delete(self, section, property):
        '''Returns a Deferred'''
        rows = [{'section': section, 'property': property, 'value': value}]
        return self._pool.runInteraction(self._delete, rows)

    def deleteSection(self, section, prop_dict):
        '''Returns a Deferred'''
        rows = [{'section': section, 'property': key} for key,value in prop_dict.items()]
        return self._pool.runInteraction(self._delete, rows)

    def _read(self, txn, row):
        sql = "SELECT property, value FROM config_t WHERE section = :section AND property = :property;"
        self.log.debug("{sql} {data}", sql=sql, data=row)
        txn.execute(sql,row)
        result = txn.fetchall()
        if result:
            result = dict(result)
        return result

    def _readSection(self, txn, row):
        sql = "SELECT property, value FROM config_t WHERE section = :section"
        self.log.debug("{sql} {data}", sql=sql, data=row)
        txn.execute(sql,row)
        result = txn.fetchall()
        if result:
            result = dict(result)
        return result

    def _write(self, txn, rows):
        sql = '''
        INSERT OR REPLACE INTO config_t(section, property, value)
        VALUES(:section, :property, :value)
        '''
        self.log.debug("{sql} {data}", sql=sql, data=rows)
        txn.executemany(sql,rows)

    def _delete(self, txn, rows):
        '''Deletes the values, not the row in the database'''
        sql = '''
        UPDATE config_t SET value = NULL WHERE section = :section AND property = :property;
        '''
        self.log.debug("{sql} {data}", sql=sql, data=rows)
        txn.executemany(sql,rows)
