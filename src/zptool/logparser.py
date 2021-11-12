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
import datetime
import logging

# -------------
# Local imports
# -------------

from zptess import TSTAMP_SESSION_FMT

# -----------------------
# Module global variables
# -----------------------

log = logging.getLogger("zptool")


class LogRecord:

    RECORD_START = r'(\[global#info] zptess|\[zptess#info] starting ZPTESS)'

    dry_run_exp     = re.compile(r'Dry run\.')
    aborted_run_exp = re.compile(r'Received SIGINT, shutting down')
    crash_run_exp   = re.compile(r'Traceback \(most recent call last\)')
    update_zp_exp   = re.compile(r'(updating )|(skipping updating of )')
    best_zp_exp     = re.compile(r'Best ZP        list is \[(.+)\]')
    ref_freq_exp    = re.compile(r'Best (REF.|Ref ) Freq list is \[(.+)\]')
    test_freq_exp   = re.compile(r'Best (TEST|Test) Freq list is \[(.+)\]')
    nsamples_exp    = re.compile(r'Window Size= (\d+) samples, T = \d+ secs, Rounds = (\d+)')
    session_exp     = re.compile(r'^(.{24}).+ updated CSV file')
    # original version
    ref_exp         = re.compile(r'\[REF\.\] (\w+)\s{1,8}\(.+\)\[(.+)s\]\[.+\] & ZP (\d+\.\d+) .+ (\d+\.\d+), .+ (\d+\.\d+) Hz, .+ (\d+\.\d+) Hz')
    test_exp        = re.compile(r'\[TEST\] (\w+)\s{1,8}\(.+\)\[(.+)s\]\[.+\] & ZP (\d+\.\d+) .+ (\d+\.\d+), .+ (\d+\.\d+) Hz, .+ (\d+\.\d+) Hz')
    # first modified version before database was introduced
    ref_exp2        = re.compile(r'\[REF\.\] (\w+)\s{1,8}\(.+\)\[(.+)s\] => Median = (\d+\.\d+) Hz, StDev = (\d+\.\d+e[+-]\d+) Hz')
    test_exp2       = re.compile(r'\[TEST\] (\w+)\s{1,8}\(.+\)\[(.+)s\] => Median = (\d+\.\d+) Hz, StDev = (\d+\.\d+e[+-]\d+) Hz')
    # second modified version  before database was introduced
    ref_exp3        = re.compile(r'\[REF\.\] (\w+)\s{1,8}\((\S{8})-(\S{8})\) => Median = (\d+\.\d+) Hz, StDev = (\d+\.\d+e[+-]\d+) Hz')
    test_exp3       = re.compile(r'\[TEST\] (\w+)\s{1,8}\((\S{8})-(\S{8})\) => Median = (\d+\.\d+) Hz, StDev = (\d+\.\d+e[+-]\d+) Hz')
    rounds_exp      = re.compile(r'\[stats#info\] ROUND \d+: REF. Mag = (\d+\.\d+). TEST Mag = (\d+\.\d+)')
    method_exp      = re.compile(r'Error choosing best (zp|Test Freq.|Ref. Freq.) using mode, selecting median instead')
    
    def __init__(self, i, connection):
        # Internal management
        self.start_line = i
        self.connection = connection
        self.tstamp    = None # Proxy for session
        
        # Info to collect for summary_t table
        self.nrounds           = None 
        self.zero_point_method = 'mode'
        self.ref_freq_method   = 'mode'
        self.test_freq_method  = 'mode'
        
        # Info to collect for rounds_t table
        self.session       = None
        self.nsamples      = None
        self.zp_fict       = None
        self.central       = None # central type of measurement: either 'mean' or 'median'
        self.ref_freq      = list()
        self.ref_mag       = list()
        self.ref_stddev    = list()
        self.ref_duration  = list()
        self.test_freq     = list()
        self.zero_point    = list()
        self.test_mag      = list()
        self.test_stddev   = list()
        self.test_duration = list()
        self.ref_name = None
        self.test_name = None
         # additional info not going anywhere
        self.upd_flag  = None
       

    def __repr__(self):
        return f"R({self.start_line}, {self.end_line})"

    def __lt__(self, other):
        return self.start_line < other.start_line

    def update(self, lines, end_line):
        self.end_line = end_line
        self.len   = end_line - self.start_line
        self.lines = lines[self.start_line : self.end_line]


    def selectSession(self, tstamp, delta_T=3):
        cursor = self.connection.cursor()
        row = {'tstamp': tstamp, 'delta': delta_T}
        cursor.execute(
            '''
            SELECT session
            FROM summary_t
            WHERE ABS(strftime('%s',session) - strftime('%s',:tstamp)) < :delta
            ''',
            row
        )
        result = cursor.fetchall()
        log.debug(f"result = {result}")
        if not result:
            log.warning(f"No hay session cerca de la fecha {tstamp}")
            result = None
        elif len(result) != 2:
            log.warning(f"Pasa algo raro con la fecha {tstamp}, salen {len(result)} sessones")
            result = None
        else:
            result = result[0][0]
        return result

    def _handleSession(self, matchobj):
        t1 = matchobj.group(1)
        t1 = datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S%z')
        self.tstamp = (t1 - t1.tzinfo.utcoffset(t1)).replace(tzinfo=None).strftime(TSTAMP_SESSION_FMT)
        self.session = self.selectSession(self.tstamp)

    def _handleUpdated(self, matchobj):
        self.upd_flag = 1 if matchobj.group(1) else 0

    def _handleNSamples(self, matchobj):
        self.nsamples = int(matchobj.group(1))
        self.nrounds  = int(matchobj.group(2))

    def _handleRefFreqList(self, matchobj):
        self.ref_freq = [float(freq) for freq in matchobj.group(2).split(sep=',')]

    def _handleTestFreqList(self, matchobj):
        self.test_freq = [float(freq) for freq in matchobj.group(2).split(sep=',')]

    def _handleZPList(self, matchobj):
        self.zero_point = [float(zp) for zp in matchobj.group(1).split(sep=', ')]

    def _handleRefReadings(self, matchobj):        
        self.ref_name     = matchobj.group(1)
        self.ref_duration.append(float(matchobj.group(2)))
        self.zp_fict      = float(matchobj.group(3))
        self.ref_mag.append(float(matchobj.group(4)))
        freq              = matchobj.group(5) # Not used
        self.ref_stddev.append(float(matchobj.group(6)))
        

    def _handleTestReadings(self, matchobj):
        self.test_name    = matchobj.group(1)
        self.test_duration.append(float(matchobj.group(2)))
        self.zp_fict      = float(matchobj.group(3))
        self.test_mag.append(float(matchobj.group(4)))
        freq              = matchobj.group(5) # Not used
        self.test_stddev.append(float(matchobj.group(6)))

    def _handleRefReadings2(self, matchobj):        
        self.ref_name     = matchobj.group(1)
        self.ref_duration.append(float(matchobj.group(2)))
        self.zp_fict      = 20.50
        freq              = matchobj.group(3) # Not used
        self.ref_stddev.append(float(matchobj.group(4)))
        
    def _handleTestReadings2(self, matchobj):
        self.test_name    = matchobj.group(1)
        self.test_duration.append(float(matchobj.group(2)))
        self.zp_fict      = 20.50
        freq              = matchobj.group(3) # Not used
        self.test_stddev.append(float(matchobj.group(4)))

    def _handleRefReadings3(self, matchobj):       
        self.ref_name     = matchobj.group(1)
        start_time = datetime.datetime.strptime(matchobj.group(2),"%H:%M:%S")
        end_time = datetime.datetime.strptime(matchobj.group(3),"%H:%M:%S")
        self.ref_duration.append(float((end_time - start_time).total_seconds()))
        self.zp_fict      = 20.50
        freq              = matchobj.group(4) # Not used
        self.ref_stddev.append(float(matchobj.group(5)))
        
    def _handleTestReadings3(self, matchobj):
        self.test_name     = matchobj.group(1)
        start_time = datetime.datetime.strptime(matchobj.group(2),"%H:%M:%S")
        end_time = datetime.datetime.strptime(matchobj.group(3),"%H:%M:%S")
        self.test_duration.append(float((end_time - start_time).total_seconds()))
        self.zp_fict      = 20.50
        freq              = matchobj.group(4) # Not used
        self.test_stddev.append(float(matchobj.group(5)))

    def _handleRoundsLine(self, matchobj):
        self.ref_mag.append(float(matchobj.group(1)))
        self.test_mag.append(float(matchobj.group(2)))

    def _handleMethods(self, matchobj):
        method = matchobj.group(1)
        if method == 'zp':
            self.zero_point_method = 'median'
        elif method == 'Test Freq.':
            self.test_freq_method = 'median'
        elif method == 'Ref. Freq.':
            self.ref_freq_method = 'median'
        else:
            pass


    def trimLists(self):
        if self.ref_name:
            log.debug("-"*72)
            log.debug(f"{self.ref_name:8} Total Ref  Before: Mag {len(self.ref_mag)}, Dur {len(self.ref_duration)}, SD {len(self.ref_stddev)}")
            self.ref_mag      = self.ref_mag[-self.nrounds:]
            self.ref_duration = self.ref_duration[-self.nrounds:]
            self.ref_stddev   = self.ref_stddev[-self.nrounds:]
           
        if self.test_name:
            log.debug(f"{self.test_name:8} Total Test Before: Mag {len(self.test_mag)}, Dur {len(self.test_duration)}, SD {len(self.test_stddev)}")
            self.test_mag      = self.test_mag[-self.nrounds:]
            self.test_duration = self.test_duration[-self.nrounds:]
            self.test_stddev   = self.test_stddev[-self.nrounds:]
           


    def parse(self):
        for line in self.lines:
            matchobj = self.session_exp.search(line)
            if matchobj:
                self._handleSession(matchobj)
                continue
            matchobj = self.update_zp_exp.search(line)
            if matchobj:
                self._handleUpdated(matchobj)
                continue
            matchobj = self.nsamples_exp.search(line)
            if matchobj:
                self._handleNSamples(matchobj)
                continue
            matchobj = self.ref_exp.search(line)
            if matchobj:
                self._handleRefReadings(matchobj)
                continue
            matchobj = self.ref_exp2.search(line)
            if matchobj:
                self._handleRefReadings2(matchobj)
                continue
            matchobj = self.ref_exp3.search(line)
            if matchobj:
                self._handleRefReadings3(matchobj)
                continue
            matchobj = self.test_exp.search(line)
            if matchobj:
                self._handleTestReadings(matchobj)
                continue
            matchobj = self.test_exp2.search(line)
            if matchobj:
                self._handleTestReadings2(matchobj)
                continue
            matchobj = self.test_exp3.search(line)
            if matchobj:
                self._handleTestReadings3(matchobj)
                continue
            matchobj = self.best_zp_exp.search(line)
            if matchobj:
                self._handleZPList(matchobj)
                continue
            matchobj = self.ref_freq_exp.search(line)
            if matchobj:
                self._handleRefFreqList(matchobj)
                continue
            matchobj = self.test_freq_exp.search(line)
            if matchobj:
                self._handleTestFreqList(matchobj)
                continue
            matchobj = self.rounds_exp.search(line)
            if matchobj:
                self._handleRoundsLine(matchobj)
                continue
            matchobj = self.method_exp.search(line)
            if matchobj:
                self._handleMethods(matchobj)
                continue
        self.trimLists()


    def check(self):
        error = False
        if self.ref_name is None:
            log.error(f"{self}:  No reference name")
            error = True
        if self.test_name is None:
            log.error(f"{self}:  No test name")
            error = True
        if len(self.ref_freq) != self.nrounds:
            log.error(f"{self}: inconsistent ref_freq list {self.ref_freq} ({len(self.ref_freq)}) with nrounds {self.nrounds}")
            error = True
        if len(self.ref_mag) != self.nrounds:
            log.error(f"{self}: inconsistent ref_mag list {self.ref_mag} ({len(self.ref_mag)}) with nrounds {self.nrounds}")     
            error = True
        if len(self.ref_stddev) != self.nrounds:
            log.error(f"{self}: inconsistent ref_stddev list {self.ref_stddev} ({len(self.ref_stddev)}) with nrounds {self.nrounds}")   
            error = True
        if len(self.ref_duration)  != self.nrounds:
            log.error(f"{self}: inconsistent ref_duration list {self.ref_duration} ({len(self.ref_duration)}) with nrounds {self.nrounds}")
            error = True
        if len(self.test_freq) != self.nrounds: 
            log.error(f"{self}: inconsistent test_freq list {self.test_freq} ({len(self.test_freq)}) with nrounds {self.nrounds}")   
            error = True
        if len(self.zero_point) !=self.nrounds:
            log.error(f"{self}: inconsistent zero_point list {self.zero_point} ({len(self.zero_point)}) with nrounds {self.nrounds}")   
            error = True
        if len(self.test_mag)!= self.nrounds:
            log.error(f"{self}: inconsistent test_mag list {self.test_mag} ({len(self.test_mag)}) with nrounds {self.nrounds}")     
            error = True
        if len(self.test_stddev) != self.nrounds:
            log.error(f"{self}: inconsistent test_stddev list {self.test_stddev} ({len(self.test_stddev)}) with nrounds {self.nrounds}")  
            error = True
        if len(self.test_duration) != self.nrounds:
            log.error(f"{self}: inconsistent test_duration list {self.test_duration} ({len(self.test_duration)}) with nrounds {self.nrounds}")
            error = True
        return error

    def summary(self):
        return [
            {   
                'nrounds'           : self.nrounds,
                'session'           : self.session,
                'role'              : 'ref',
                'zero_point_method' : None,
                'freq_method'       : self.ref_freq_method,
            },
            {
                'nrounds'           : self.nrounds,
                'session'           : self.session,
                'role'              : 'test',
                'zero_point_method' : self.zero_point_method,
                'freq_method'       : self.test_freq_method,
            }
        ]


    def rounds(self):
        rows = list()
        for i in range(self.nrounds):
            ref = {
                'session'    : self.session,
                'round'      : i+1,
                'role'       : 'ref',
                'name'       : self.ref_name,
                'central'    : 'median',
                'freq'       : self.ref_freq[i],
                'stddev'     : self.ref_stddev[i],
                'mag'        : self.ref_mag[i],
                'zp_fict'    : self.zp_fict,
                'zero_point' : None,
                'nsamples'   : self.nsamples,
                'duration'   : self.ref_duration[i],
            }
            rows.append(ref)
            test = {
                'session'    : self.session,
                'round'      : i+1,
                'role'       : 'test',
                'name'       : self.test_name,
                'central'    : 'median',
                'freq'       : self.test_freq[i],
                'stddev'     : self.test_stddev[i],
                'mag'        : self.test_mag[i],
                'zp_fict'    : self.zp_fict,
                'zero_point' : self.zero_point[i],
                'nsamples'   : self.nsamples,
                'duration'   : self.ref_duration[i],
            }
            rows.append(test)
        return rows

