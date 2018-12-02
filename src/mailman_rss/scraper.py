# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from mailman_rss.mailman import MailmanArchive
from collections import namedtuple
from contextlib import closing
from logging import getLogger
import os
from datetime import datetime
import time

logger = getLogger(__file__)

try:
    import sqlite3
except ImportError as e:
    logger.error(e)


class HeaderScraper(object):
    """ Mailman archive header scraper with cache storage. """

    def __init__(self, archive_url, db_path):
        self.archive_url = archive_url
        self.db_path = db_path
        self._connect()

    def __del__(self):
        if self._conn:
            self._conn.close()

    def _connect(self):
        self._conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES
            )
        sqlite3.dbapi2.converters['DATETIME'] = (
            sqlite3.dbapi2.converters['TIMESTAMP'])
        self._conn.row_factory = sqlite3.Row
        with self._conn as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS headers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author VARCHAR(64) NOT NULL,
                    subject VARCHAR(256) NOT NULL,
                    url VARCHAR(128) UNIQUE,
                    fetched_at DATETIME NOT NULL,
                    read_at DATETIME DEFAULT NULL
                )""")

    def fetch(self, max_items=10):
        """ Fetch new posts from archive. """
        archive = MailmanArchive(self.archive_url)
        with self._conn as conn:
            c = conn.cursor()
            for index, header in enumerate(archive.iter_headers()):
                if index >= max_items:
                    logger.info("Max fetches reached: {}".format(index))
                    break

                c.execute("SELECT COUNT(*) as c FROM headers WHERE url = ?",
                          (header.url,))
                if int(c.fetchone()[0]):
                    # Record already fetched.
                    logger.info("Last fetched URL: {}".format(header.url))
                    break
                c.execute("INSERT INTO headers "
                          "(author, subject, url, fetched_at) "
                          "VALUES (?, ?, ?, ?)",
                          (header.author, header.subject, header.url,
                          datetime.now()))

    def iter_unread(self, mark_unread=False):
        """ Iterate over unread message headers. """
        with self._conn as conn:
            c = conn.cursor()
            c.execute("""
                SELECT * FROM headers
                WHERE read_at IS NULL
                ORDER BY fetched_at DESC
                """)
            for row in c.fetchall():
                yield row
                if mark_unread:
                    c.execute(
                        "UPDATE headers SET read_at = ? WHERE id = ?",
                        (datetime.now(), row[0]))

    def iter_all(self, mark_unread=False):
        """ Iterate over all headers. """
        with self._conn as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM headers")
            for row in c.fetchall():
                yield row

    def count(self, unread=False):
        """ Count the number of fetched headers. """
        with self._conn as conn:
            c = conn.cursor()
            if unread:
                c.execute(
                    "SELECT COUNT(*) as c FROM headers WHERE read_at IS NULL")
            else:
                c.execute("SELECT COUNT(*) FROM headers")
            return int(c.fetchone()[0])
