#!/usr/bin/env python

import smtplib
from getpass import getuser
from socket import gethostname

def send_email(recipient, subject, body, attach=None):
    if attach is not None:
        raise NotImplementedError("Currently don't support attachments.")

    from_user = "{}@{}".format(getuser(), gethostname())
    headers = "\r\n".join([
        "From: " + from_user,
        "Subject: " + subject,
        "To: " + recipient,
        "MIME-Version: 1.0",
        "Content-Type: text/html"])

    server = smtplib.SMTP('localhost', 25)
    server.ehlo()
    server.sendmail(from_user, recipient, headers + "\r\n\r\n" + body)
    server.close()
