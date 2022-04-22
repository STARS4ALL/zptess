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
import sys
import csv
import zipfile
import datetime
import gettext
import ssl
import smtplib
import email
import shutil

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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

import requests
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


def pack(base_dir, zip_file):
    '''Pack all files in the ZIP file given by options'''
    paths = os.listdir(base_dir)
    log.info(f"Creating ZIP File: '{os.path.basename(zip_file)}'")
    with zipfile.ZipFile(zip_file, 'w') as myzip:
        for myfile in paths: 
            myzip.write(myfile) 

# Adapted From https://realpython.com/python-send-email/
def email_send(subject, body, sender, receivers, attachment, host, port, password, confidential=False):
    msg_receivers = receivers
    receivers = receivers.split(sep=',')
    message = MIMEMultipart()
    message["Subject"] = subject
    # Create a multipart message and set headers
    if confidential:
        message["From"] = sender
        message["To"]   = sender
        message["Bcc"]  = msg_receivers
    else:
        message["From"] = sender
        message["To"]   = msg_receivers

    # Add body to email
    message.attach(MIMEText(body, "plain"))

    # Open file in binary mode
    with open(attachment, "rb") as fd:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(fd.read())

    # Encode file in ASCII characters to send by email    
    encoders.encode_base64(part)

    # Add header as key/value pair to attachment part
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {os.path.basename(attachment)}",
    )
    # Add attachment to message and convert message to string
    message.attach(part)
    # Log in to server using secure context and send email
    context = ssl.create_default_context()
    with smtplib.SMTP(host, port) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(sender, password)
        server.sendmail(sender, receivers, message.as_string())


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
                yield self.view.messageBoxWarn(
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
                yield self.view.messageBoxWarn(
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
                yield self.view.messageBoxWarn(
                    title = _("Batch Management"),
                    message = _("Must close batch first!")
                )
                return
            latest = yield self.model.batch.latest()
            begin_tstamp = latest['begin_tstamp']
            base_dir = args['base_dir']
            send_email = args['email_flag']
            updated = args['update']
            email_sent = yield self._export(latest, base_dir, updated, send_email)
        except (requests.ConnectionError, requests.Timeout) as exception:
            yield self.view.messageBoxError(
                title = _("Batch Management"),
                message = _("No Internet connection!")
            )
            email_sent = False
        except smtplib.SMTPSenderRefused:
            yield self.view.messageBoxError(
                title = _("Batch Management"),
                message = _("Error sending email.\nCheck logfile for details")
            )
            email_sent = False
            yield self.model.batch.emailed(begin_tstamp, 0)
        except Exception as e:
            log.failure('{e}',e=e)
            pub.sendMessage('quit', exit_code = 1)
            email_sent = False
        latest = yield self.model.batch.latest()
        self.view.statusBar.set(latest)
        if email_sent:
            yield self.view.messageBoxInfo(
                title = _("Batch Management"),
                message = _("Batch exported & email sent.")
            )
        else:
            yield self.view.messageBoxInfo(
                title = _("Batch Management"),
                message = _("ZIP File available at folder\n{0}.").format(os.path.dirname(base_dir))
            )



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
                log.info(f"Saved samples calibration data to CSV file: '{os.path.basename(csv_path)}'")
            for sample in test_samples:
                writer.writerow(sample)
            for sample in ref_samples:
                writer.writerow(sample)


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


    def _archive(self, base_dir, begin_tstamp, end_tstamp):
        suffix1 = f"from_{begin_tstamp}_to_{end_tstamp}".replace('-','').replace(':','')
        prev_workdir = os.getcwd()
        zip_file = os.path.join(os.path.dirname(base_dir), suffix1 + '.zip' )
        os.chdir(base_dir)
        paths = os.listdir(base_dir)
        log.info(f"Creating ZIP File: '{os.path.basename(zip_file)}'")
        with zipfile.ZipFile(zip_file, 'w') as myzip:
            for myfile in paths: 
                myzip.write(myfile) 
        os.chdir(prev_workdir)
        return zip_file


    @inlineCallbacks
    def _email(self, begin_tstamp, end_tstamp, email_sent, zip_file):
        config = yield self.model.config.loadSection('smtp')
        if email_sent is None:
            log.info("Never tried to send an email for this batch")
        elif email_sent == 0:
            log.info("Tried to send email for this batch previously but failed")
        else:
            log.info("Already sent an email for this batch")
            return False
        request = yield deferToThread(requests.head, "http://www.google.com", timeout=5)
        log.info("Connected to Internet")
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
        log.info("Email sent")
        return True
    

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
        zip_file = yield deferToThread(self._archive, base_dir, begin_tstamp, end_tstamp)
        shutil.rmtree(base_dir)
        if not send_email:
            return False
        emailed = yield self._email(begin_tstamp, end_tstamp, email_sent, zip_file)
        yield self.model.batch.emailed(begin_tstamp, 1)
        return emailed

    