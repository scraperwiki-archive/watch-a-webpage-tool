#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals
import sys
import datetime
import hashlib
import requests
import scraperwiki
import tempfile
from cStringIO import StringIO
import os
import argparse
import subprocess
import shlex
from bs4 import BeautifulSoup

TABLE_CHANGES = 'changes'
DEFAULT_URL = 'http://blog.scraperwiki.com'
DEFAULT_CHECKSUM = ''
DEFAULT_HTML = ''


def main():
    create_table()
    parser = argparse.ArgumentParser(description="Watch a Web Page (URL)")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '--set-url', dest="url", type=str, metavar='URL',
        help='Set the url to watch and check for changes')

    group.add_argument('--get-url', action='store_true', dest='get',
                       help='Print the url to watch')

    group.add_argument('--run', action='store_true',
                       help='Check for changes to the web page.')

    args = parser.parse_args()
    if args.url is not None:
        if args.url != get_url():  # has it changed?
            set_url(args.url)
            check_for_changes()
        return 0

    elif args.get:
        print(get_url())
        return 0

    elif args.run:
        check_for_changes()


def create_table():
    scraperwiki.sql.execute(
        'CREATE TABLE IF NOT EXISTS `changes` (`url` text, `datetime` date);')
    scraperwiki.sql.commit()


def check_for_changes():
    url = get_url()
    if not url:
        scraperwiki.status('error', 'No URL specified.')
        return

    old_checksum = get_checksum()
    current_html = download_url(url).read()

    new_checksum = make_checksum(current_html)
    if old_checksum != new_checksum:
        set_checksum(new_checksum)
        old_html = get_current_html()
        set_current_html(current_html)
        if old_checksum != DEFAULT_CHECKSUM:
            diff = diff_content(old_html, current_html)
            report_change(url, current_html, diff)
    update_status()


def download_url(url):
    response = requests.get(url)
    response.raise_for_status()
    return StringIO(response.content)


def update_status():
    status_text = 'Last changed: {}'.format(
        get_most_recent_record('changes', 'datetime'))
    scraperwiki.status('ok', status_text)


def get_most_recent_record(table, column):
    """
    Pass a table and column pointing to a date field . The most recent one
    will be returned.
    """
    result = scraperwiki.sql.select(
        "MAX({1}) AS most_recent FROM {0} LIMIT 1".format(table, column))
    return result[0]['most_recent']


def html_to_text(html):
    """
    >>> html_to_text('<html><body>Foo</body></html')
    'Foo\\n'
    """
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


def make_checksum(html):
    text = html_to_text(html)
    m = hashlib.md5()
    m.update(text)
    return m.hexdigest()


def diff_content(old_html, new_html):
    """
    >>> diff_content('<html>Foo</html>\\n', '<html>Bar</html>\\n').split('\\n')
    [u'1c1', u'< <html>Foo</html>', u'---', u'> <html>Bar</html>', u'']
    """
    (_, left_tmpfile) = tempfile.mkstemp()
    (_, right_tmpfile) = tempfile.mkstemp()

    with open(left_tmpfile, 'w') as f, open(right_tmpfile, 'w') as g:
        f.write(old_html)
        g.write(new_html)

    command = 'diff --ignore-all-space {left} {right}'.format(
        left=left_tmpfile, right=right_tmpfile)
    try:
        subprocess.check_output(shlex.split(command))
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:  # inputs differ
            return e.output
        else:  # error
            raise RuntimeError("Command failed with retcode {}: {}\n{}".format(
                e.returncode, e.command, e.output))
    finally:
        os.unlink(left_tmpfile)
        os.unlink(right_tmpfile)

    return ''  # zero return code means inputs are the same


def report_change(url, current_html, html_diff):
    scraperwiki.sql.save(
        unique_keys=[],
        data={'url': url,
              'datetime': datetime.datetime.now().strftime(
                  "%Y-%m-%d %H:%M:%S"),
              'html_diff': html_diff,
              'html': current_html},
        table_name=TABLE_CHANGES)


def prettify_html(html):
    return BeautifulSoup(html).prettify()


def set_url(url):
    scraperwiki.sql.save_var('url', url)
    set_checksum(DEFAULT_CHECKSUM)


def get_url():
    return scraperwiki.sql.get_var('url', DEFAULT_URL)


def get_checksum():
    return scraperwiki.sql.get_var('checksum', DEFAULT_CHECKSUM)


def set_checksum(checksum):
    return scraperwiki.sql.save_var('checksum', checksum)


def get_current_html():
    return scraperwiki.sql.get_var('current_html', DEFAULT_HTML)


def set_current_html(html):
    return scraperwiki.sql.save_var('current_html', html)


if __name__ == '__main__':
    sys.exit(main())
