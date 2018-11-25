# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from future.standard_library import hooks
from base64 import b32encode
from bs4 import BeautifulSoup
from collections import namedtuple
from email.header import decode_header, make_header
from hashlib import sha1
from logging import getLogger
import dateutil.parser
import gzip
import html
import io
import mailbox
import requests
import os
import re
import tempfile
import itertools
try:
    from itertools import izip
except ImportError:
    izip = zip

with hooks():
    from urllib.parse import urlparse


logger = getLogger(__file__)


class MailmanArchive(object):
    """
    Mailman archive representation.
    """
    def __init__(self, archive_url, encoding=None):
        self.encoding = encoding
        self._load(archive_url)

    def _load(self, archive_url):
        self.archive_url = archive_url
        r = requests.get(archive_url)
        self._soup = BeautifulSoup(r.content, "html.parser")
        if not self.encoding:
            self._set_encoding()

    def _set_encoding(self):
        meta = self._soup.find_all("meta", {"http-equiv": "Content-Type"})
        if not meta:
            self.encoding = "utf-8"
        else:
            self.encoding = meta[0].get("content").split("charset=")[1]
            logger.info("Encoding set to {}".format(self.encoding))

    @property
    def title(self):
        return self._soup.html.head.title

    def iter_header_list(self):
        for a in self._soup.find_all("a", href=re.compile(r".*/date.html")):
            yield list(self._iter_month_headers(a.get("href")))

    def _iter_month_headers(self, date_url):
        base_url = os.path.join(self.archive_url, os.path.dirname(date_url))
        r = requests.get(os.path.join(self.archive_url, date_url))
        page = BeautifulSoup(r.content, "html.parser")
        for a in page.find_all("a", href=re.compile(r"\d+\.html")):
            author = a.find_next_sibling("i").text.strip()
            subject = a.text.strip()
            url = os.path.join(base_url, a.get("href"))
            yield MessageHeader(author, subject, url)

    def iter_mboxes(self):
        for a in self._soup.find_all("a", href=re.compile(r".*txt(.gz)?")):
            url = a.get("href")
            if not url.endswith(".gz"):
                url = url + ".gz"
            gzip_url = os.path.join(self.archive_url, url)
            try:
                yield self._get_month(gzip_url)
            except OSError as e:
                logger.error("{}".format(e))

    def _get_month(self, gzip_url):
        r = requests.get(gzip_url, stream=True)
        zipped_mbox = gzip.GzipFile(fileobj=io.BytesIO(r.raw.read())).read()
        with tempfile.NamedTemporaryFile() as f:
            f.write(zipped_mbox)
            f.flush()
            mbox = mailbox.mbox(f.name)
            return mbox

    def iter_headers(self, reverse=True):
        for headers in self.iter_header_list():
            if reverse:
                for header in reversed(headers):
                    yield header
            else:
                for header in headers:
                    yield header


    def iter_messages(self):
        for mbox, headers in izip(self.iter_mboxes(),
                                  self.iter_header_list()):
            length = min(len(mbox), len(headers))
            if len(mbox) != len(headers):
                logger.info(
                    "Unmatched header and mbox size: "
                    "mbox={} vs headers={}".format(len(mbox), len(headers)))
            for index in reversed(range(length)):
                if hasattr(mbox, "get_bytes"):
                    yield Message(
                        self,
                        headers[index].url,
                        mbox.get_bytes(index).decode(self.encoding))
                else:
                    yield Message(
                        self,
                        headers[index].url,
                        mbox.get_string(index))


class MessageHeader(namedtuple("_MessageHeader", "author subject url")):
    pass


class Attachment(namedtuple("_Attachment", "url mime_type size")):
    pass


class Message(mailbox.mboxMessage, object):
    """
    Mail message that wraps `mailbox.mboxMessage`.
    """

    def __init__(self, archive, url, *args):
        super(Message, self).__init__(*args)
        self._url = url
        self._archive = archive

    @property
    def author(self):
        """Message sender name"""
        value = self.get("from")
        return value if value else None

    @property
    def subject(self):
        """Message subject"""
        value = self.get("subject")
        return str(make_header(decode_header(value))) if value else None

    @property
    def date(self):
        """Message date in dateutil format"""
        value = self.get("date")
        return dateutil.parser.parse(value) if value else None

    @property
    def message_id(self):
        """Message ID"""
        return self.get("message-id")

    @property
    def url(self):
        """Message URL"""
        return self._url

    @property
    def body(self):
        """Message body"""
        return self.parts()[0]

    @property
    def stable_url(self):
        """
        Calculate stable URL. Not really supported in reality.
        See https://wiki.list.org/DEV/Stable%20URLs
        """
        archived_at = self.get("archived-at")
        if archived_at:
            return archived_at
        # Calculate stable URL
        message_id = re.sub(r"^<(.*)>$", r"\1", self.message_id).encode(
            "utf-8")
        encoded_id = b32encode(sha1(message_id).digest()).decode("utf-8")
        return os.path.join(self._archive.archive_url, encoded_id)

    def parts(self):
        if self.is_multipart():
            body = self.get_payload(0)
        else:
            body = self.get_payload()
        parts = re.split(re.compile("^-+\s+next part\s+-+$", re.MULTILINE),
                         body)
        return [part.strip() for part in parts]

    def attachments(self):
        """Returns a list of attachments"""
        attachments = []
        for part in self.parts()[1:]:
            if "A non-text attachment was scrubbed" not in part:
                continue
            mime_type = self._get_part_field(part, "type")
            size = self._get_part_field(part, "size")
            url = self._get_part_field(part, "url")
            if mime_type and size and url:
                if urlparse(url).netloc:
                    attachments.append(Attachment(url, mime_type, size))
        return attachments

    def _get_part_field(self, part, name):
        fp = io.StringIO(part)
        for line in fp.readlines():
            if line.lower().startswith(name):
                return line.split(":", 1)[1].strip()
