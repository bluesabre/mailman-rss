# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import unittest
from mailman_rss.mailman import MailmanArchive
from mailman_rss.rss import RSSWriter
from mailman_rss.scraper import HeaderScraper
import tempfile
from six import StringIO


ARCHIVE_URL = "https://mail.python.org/pipermail/mailman-developers/"


class TestMailmanArchive(unittest.TestCase):

    def test_rsswriter_stringio(self):
        archive = MailmanArchive(ARCHIVE_URL)
        with StringIO() as f:
            writer = RSSWriter(max_items=1)
            writer.write(f, archive)

    def test_rsswriter_filename(self):
        archive = MailmanArchive(ARCHIVE_URL)
        with tempfile.NamedTemporaryFile(suffix=".rss") as f:
            writer = RSSWriter(max_items=1)
            writer.write(f.name, archive)


class TestHeaderScraper(unittest.TestCase):

    def test_scraper(self):
        scraper = HeaderScraper(ARCHIVE_URL, ":memory:")
        scraper.fetch(max_items=3)
        assert len(list(scraper.iter_unread(False))) == 3
        assert scraper.count() == 3
        assert scraper.count(True) == 3
        for header in scraper.iter_unread(True):
            pass
        assert scraper.count() == 3
        assert scraper.count(True) == 0


if __name__ == "__main__":
    unittest.main()
