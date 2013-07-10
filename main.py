#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals
import sys
import datetime
import hashlib
import requests
import requests_cache
import scraperwiki
import tempfile
from cStringIO import StringIO
import os

from send_email import send_email

TABLE_URLS = '_urls'
TABLE_CHANGES = 'changes'
EMAIL_VAR_NAME = 'notify_email'


def add_watch_url(url):
    scraperwiki.sql.save(
        unique_keys=['url'],
        data={'url': url,
              'checksum': False},
        table_name=TABLE_URLS)


def main():
    install_cache()
    for (url, old_checksum) in get_urls_to_check():
        new_checksum = make_checksum(download_url(url))
        if old_checksum == new_checksum:
            continue
        print("{} old: {}  new: {}".format(url, old_checksum, new_checksum))
        store_checksum(url, new_checksum)
        report_change(url)
     

def install_cache():
    requests_cache.install_cache(
        expire_after=12 * 60 * 60)


def get_urls_to_check():
    results = scraperwiki.sql.select('url,checksum FROM {}'.format(TABLE_URLS))
    return [(row['url'], row['checksum']) for row in results]


def download_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return StringIO(response.content)


def html_to_text(html):
    (_, html_tmpfile) = tempfile.mkstemp()
    (_, text_tmpfile) = tempfile.mkstemp()
    
    with open(html_tmpfile, 'w') as f:
        f.write(html)
    command = 'html2text -style compact -o {outfile} {infile}'.format(
        outfile=text_tmpfile, infile=html_tmpfile)
    retval = os.system(command)
    if retval != 0:
        raise RuntimeError("Command failed: {}".format(command))
    
    with open(text_tmpfile, 'r') as f:
        text = f.read()

    os.unlink(html_tmpfile)
    os.unlink(text_tmpfile)
    return text


def make_checksum(html_fobj):
    text = html_to_text(html_fobj.read())
    m = hashlib.md5()
    m.update(text)
    return m.hexdigest()


def store_checksum(url, checksum):
    scraperwiki.sql.save(
        unique_keys=['url'],
        data={'url': url,
              'checksum': checksum},
        table_name=TABLE_URLS)


def report_change(url):
    print("{} : has changed".format(url))
    notify_email = scraperwiki.sql.get_var(EMAIL_VAR_NAME, None)
    if notify_email:
        send_email(notify_email, "[Watch A Web Page] Web page has changed", url)
    else:
        print("No {} variable, can't send email.".format(EMAIL_VAR_NAME))
    
    scraperwiki.sql.save(
        unique_keys=[],
        data={'url': url,
              'datetime': datetime.datetime.now()},
        table_name=TABLE_CHANGES)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.exit(main())

    if sys.argv[1] == 'email':
        scraperwiki.sql.save_var(EMAIL_VAR_NAME, sys.argv[2])
    else:
        for url in sys.argv[1:]:
            add_watch_url(url)
