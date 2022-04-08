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

# -----------------------
# Module global variables
# -----------------------

log = Logger(namespace=NAMESPACE)

# ------------------------
# Module Utility Functions
# ------------------------

def get_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime(TSTAMP_SESSION_FMT)

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
    def onOpenBatchReq(self):
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
    def onCloseBatchReq(self):
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
    def onPurgeBatchReq(self):
        try:
            log.info("onPurgeBatchReq()")
            yield  self.model.batch.purge()
            latest = yield self.model.batch.latest()
            self.view.statusBar.set(latest)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)

    @inlineCallbacks
    def onExportBatchReq(self):
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

        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)


    # --------------
    # Helper methods
    # --------------


    def _export(self, batch, base_dir, updated, send_email):
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



