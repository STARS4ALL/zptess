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
import sys
import csv
import datetime
import gettext

# ---------------
# Twisted imports
# ---------------

from twisted.logger   import Logger
from twisted.internet import  reactor, defer
from twisted.internet.defer import inlineCallbacks, maybeDeferred
from twisted.internet.threads import deferToThread

# -------------------
# Third party imports
# -------------------

from pubsub import pub

#--------------
# local imports
# -------------

from zptess import __version__, TSTAMP_SESSION_FMT
from zptess.logger  import startLogging, setLogLevel


# ----------------
# Module constants
# ----------------

# Support for internationalization
_ = gettext.gettext

NAMESPACE = 'ctrl'


EXPORT_CSV_HEADERS = [ "Model","Name","Timestamp","Magnitud TESS.","Frecuencia","Magnitud Referencia",
                    "Frec Ref","MagDiff vs stars3","ZP (raw)", "Extra offset", "Final ZP", "Station MAC","OLD ZP",
                    "Author","Firmware","Updated"]
EXPORT_CSV_ADD_HEADERS = ["# Rounds", "ZP Sel. Method", "Freq Method", "Ref Freq Method"]


# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------

def get_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)

def summary_export(self, extended, csv_path, updated=None, begin_tstamp=None, end_tstamp=None):
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


# --------------
# Module Classes
# --------------

class BatchController:

    NAME = NAMESPACE

    def __init__(self, parent, view, model):
        self.parent = parent
        self.model = model
        self.view = view
        setLogLevel(namespace=NAMESPACE, levelStr='info')
        self.start()

    def start(self):
        # events coming from GUI
        pub.subscribe(self.onOpenBatchReq, 'open_batch_req')
        pub.subscribe(self.onCloseBatchReq, 'close_batch_req')
        pub.subscribe(self.onPurgeBatchReq, 'purge_batch_req')
        pub.subscribe(self.onExportBatchReq, 'export_batch_req')

    @inlineCallbacks
    def onOpenBatchReq(self, args):
        try:
            log.info("onOpenBatchReq()")
            isOpen = yield self.model.batch.isOpen()
            if isOpen:
                self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("Batch already open")
                )
            else:
                tstamp = get_timestamp()
                yield self.model.batch.open(tstamp)
                result = yield self.model.batch.latest()
                self.view.statusBar.set(result)   
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)
    
    @inlineCallbacks
    def onCloseBatchReq(self, args):
        try:
            log.info("onCloseBatchReq()")
            isOpen = yield self.model.batch.isOpen()
            if not isOpen:
                self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("No open batch to close")
                )
            else:
                result = yield self.model.batch.latest()
                begin_tstamp = result['begin_tstamp']
                end_tstamp = get_timestamp()
                N = yield self.model.summary.numSessions(begin_tstamp, end_tstamp)
                yield self.model.batch.close(end_tstamp, N)
                result = yield self.model.batch.latest()
                self.view.statusBar.set(result)   
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    @inlineCallbacks
    def onPurgeBatchReq(self, args):
        try:
            log.info("onPurgeBatchReq()")
            yield  self.model.batch.purge()
            latest = yield self.model.batch.latest()
            self.view.statusBar.set(latest)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    @inlineCallbacks
    def onExportBatchReq(self, args):
        try:
            log.info("onExportBatchReq()")
            isOpen = yield self.model.batch.isOpen()
            if isOpen:
                self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("Must close batch first!")
                )
                return
            latest = yield self.model.batch.latest()
            base_dir = args['base_dir']
            send_email = args['email_flag']
            updated = args['update']
            yield self._export(latest, base_dir, updated, send_email)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)


    # --------------
    # Helper methods
    # --------------

    def _summary_write(self, summary, csv_path, extended):
        fieldnames = EXPORT_CSV_HEADERS
        if extended:
            fieldnames.extend(EXPORT_CSV_ADD_HEADERS)
        with open(csv_path, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(fieldnames)
            for row in summary:
                row = list(row) # row was a tuple thus we could not modifi it
                row[13] = bool(row[13]) 
                writer.writerow(row)
        log.info(f"Saved summary calibration data to CSV file: '{os.path.basename(csv_path)}'")


    def _rounds_write(self, test_rounds, ref_rounds, csv_path):
        header = ("Model", "Name", "MAC", "Session (UTC)", "Role", "Round", "Freq (Hz)", "\u03C3 (Hz)", "Mag", "ZP", "# Samples","\u0394 T (s.)")
        with open(csv_path, 'w') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(header)
            for row in test_rounds:
                writer.writerow(row)
            for row in ref_rounds:
                writer.writerow(row)
        log.info(f"Saved rounds calibration data to CSV file: '{os.path.basename(csv_path)}'")


    def _samples_write(self, test_samples, ref_samples, csv_path):
        HEADERS = ("Model", "Name", "MAC", "Session (UTC)", "Role", "Round", "Timestamp", "Frequency", "Box Temperature", "Sequence #")
        created = os.path.isfile(csv_path)
        with open(csv_path, 'a') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            if not created:
                writer.writerow(HEADERS)
            for sample in test_samples:
                writer.writerow(sample)
            for sample in ref_samples:
                writer.writerow(sample)
        log.info(f"Saved samples calibration data to CSV file: '{os.path.basename(csv_path)}'")


    @inlineCallbacks
    def _summary_export(self, updated, export_dir, begin_tstamp, end_tstamp):
        suffix1 = f"from_{begin_tstamp}_to_{end_tstamp}".replace('-','').replace(':','')
        csv_path = os.path.join(export_dir, f"summary_{suffix1}.csv")
        summary = yield self.model.summary.export(
            extended     = False,
            updated      = updated,
            begin_tstamp = begin_tstamp,
            end_tstamp   = end_tstamp
        )
        yield deferToThread(self._summary_write, summary, csv_path, False)


    @inlineCallbacks
    def _rounds_export(self, session, updated, csv_path):
        test_rounds = yield self.model.rounds.export(session, 'test', updated)
        ref_rounds  = yield self.model.rounds.export(session, 'ref', None)
        yield deferToThread(self._rounds_write, test_rounds, ref_rounds, csv_path)
           

    @inlineCallbacks
    def _samples_export(self, session, roun, also_ref, csv_path):
        test_model, test_name, nrounds = yield self.model.summary.getDeviceInfo(session,'test')
        ref_model,  ref_name, _        = yield self.model.summary.getDeviceInfo(session,'ref')
        if roun is None:   # round None is a marker for all rounds
            for r in range(1, nrounds+1):
                test_samples = yield self.model.samples.export(session, 'test', r)
                if also_ref:
                    ref_samples = yield self.model.samples.export(session, 'ref', r)
                else:
                    ref_samples = tuple()
                yield deferToThread(self._samples_write, test_samples, ref_samples, csv_path)
        else:
            test_samples = yield self.model.samples.export(session, 'test', roun)
            if also_ref:
                ref_samples = yield self.model.samples.export(session, 'ref', roun)
            else:
                ref_samples = tuple()
            yield deferToThread(self._samples_write, test_samples, ref_samples, csv_path)



    @inlineCallbacks
    def _export(self, batch, base_dir, updated, send_email):
        begin_tstamp = batch['begin_tstamp']
        end_tstamp = batch['end_tstamp']
        email_sent = batch['email_sent']
        calibrations = batch['calibrations']
        log.info("(begin_tstamp, end_tstamp)= ({bts}, {ets}, up to {cal} calibrations)",bts=begin_tstamp, ets=end_tstamp,cal=calibrations)
        os.makedirs(base_dir, exist_ok=True)
        yield self._summary_export(
            updated      = updated,   # This should be true when sendimg email to people
            export_dir   = base_dir,
            begin_tstamp = begin_tstamp, 
            end_tstamp   = end_tstamp, 
        )
        sessions = yield self.model.summary.sessions(updated, begin_tstamp, end_tstamp)
        for i, (session,) in enumerate(sessions):
            log.info(f"Calibration {session} [{i+1}/{calibrations}] (updated = {bool(updated)})")
            _, name, _ = yield self.model.summary.getDeviceInfo(session,'test')
            rounds_name  = f"{name}_rounds_{session}.csv".replace('-','').replace(':','')
            samples_name = f"{name}_samples_{session}.csv".replace('-','').replace(':','')
            yield self._rounds_export(
                session = session, 
                updated = updated, 
                csv_path = os.path.join(base_dir, rounds_name)
            )
            yield self._samples_export(
                session      = session,
                also_ref     = True, # Include reference photometer samples
                roun         = None, # None is a marker for all rounds,
                csv_path     = os.path.join(base_dir, samples_name),
            )

        # ------------------------------
        # DE MOMENTO PROBAMOS HASTA AQUI
        # ------------------------------
        return 
            
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



