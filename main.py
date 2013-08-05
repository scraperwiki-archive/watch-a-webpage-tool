#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals
import sys
import codecs
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
from bs4 import BeautifulSoup  # for prettify
from collections import OrderedDict

TABLE_CHANGES = 'changes'
DEFAULT_URL = 'http://blog.scraperwiki.com'
DEFAULT_CHECKSUM = ''
DEFAULT_HTML = ''


def main():
    args = parse_command_line()
    create_table()

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
        update_status()


def parse_command_line():
    parser = argparse.ArgumentParser(description="Watch a Web Page (URL)")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument(
        '--set-url', dest="url", type=str, metavar='URL',
        help='Set the url to watch and check for changes')

    group.add_argument('--get-url', action='store_true', dest='get',
                       help='Print the url to watch')

    group.add_argument('--run', action='store_true',
                       help='Check for changes to the web page.')

    return parser.parse_args()


def create_table():
    scraperwiki.sql.execute(
        'CREATE TABLE IF NOT EXISTS `changes` (`url` text, `datetime` date);')
    scraperwiki.sql.commit()


def check_for_changes():
    url = get_url()

    old_checksum = get_checksum()
    old_html = get_current_html()

    current_html = prettify_html(download_url(url).read())
    current_checksum = make_checksum(current_html)

    if old_checksum != current_checksum:

        set_checksum(current_checksum)
        set_current_html(current_html)

        if old_checksum != DEFAULT_CHECKSUM:
            current_text = html_to_text(current_html)
            old_text = html_to_text(current_html)

            html_diff = diff_content(old_html, current_html)
            text_diff = diff_content(
                old_text,
                current_text)
            save_change(url, current_html, html_diff, current_text, old_text,
                        text_diff)


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
        f.write(html.encode('utf-8'))
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
    """
    Generate a checksum from the *text* of the HTML page, not the HTML itself.
    It's quite common that HTML pages change each request. The visible text
    content is less likely to change.
    """
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


def save_change(url, current_html, html_diff, text_current, text_old,
                text_diff):
    scraperwiki.sql.save(
        unique_keys=[],
        data=OrderedDict([
            ('url', url),
            ('datetime', datetime.datetime.now()),
            ('text_current', text_current),
            ('text_old', text_old),
            ('text_diff', text_diff),
            ('html', current_html),
            ('html_diff', html_diff),
        ]),
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
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
    sys.exit(main())
