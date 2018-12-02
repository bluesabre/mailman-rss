# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
from email.utils import formatdate
from html import escape
from datetime import datetime
import dateutil
from logging import getLogger
import xml.dom.minidom


logger = getLogger(__file__)


class RSSWriter(object):
    """  """
    def __init__(self, max_items=25, language=None):
        self.max_items = max_items
        self.language = language
        logger.debug("{}: {} max items".format(
            self.__class__.__name__, max_items))

    def write(self, fp, archive, pretty=True):
        self.doc = xml.dom.minidom.Document()
        rss = self._add_element(self.doc, "rss", version="2.0")
        channel = self._add_element(rss, "channel")
        self._write_header(channel, archive)
        for index, message in enumerate(archive.iter_messages()):
            self._write_item(channel, message)
            if index + 1 >= self.max_items:
                break

        kwargs = dict(addindent="  ", newl="\n") if pretty else dict()
        if hasattr(fp, "write"):
            self.doc.writexml(fp, encoding="utf-8", **kwargs)
        else:
            logger.debug("Writing to %s" % fp)
            with open(fp, "wb" if str == bytes else "w") as f:
                self.doc.writexml(f, encoding="utf-8", **kwargs)

    def _add_element(self, parent, name, content="", **kwargs):
        elem = parent.appendChild(self.doc.createElement(name))
        if content:
            elem.appendChild(self.doc.createTextNode(escape(content)))
        for key in kwargs:
            elem.attributes[key] = escape(kwargs[key])
        return elem

    def _write_header(self, channel, archive):
        if self.language:
            self._add_element(channel, "language", self.language)
        title = archive.title
        if title:
            self._add_element(channel, "title", str(title.string))
            self._add_element(channel, "description", str(title.string))
        self._add_element(channel, "link", archive.archive_url)
        dt = datetime.now(tz=dateutil.tz.tzlocal())
        self._add_element(channel, "pubDate", self._format_date(dt))

    def _write_item(self, channel, message):
        item = self._add_element(channel, "item")
        self._add_element(item, "author", message.author)
        self._add_element(item, "title", message.subject)
        if message.date is not None:
            self._add_element(item, "pubDate", self._format_date(message.date))
        self._add_element(item, "guid", message.message_id,
                          isPermaLink="false")
        self._add_element(item, "description", message.body)
        self._add_element(item, "link", message.url)
        for attachment in message.attachments():
            self._add_element(item, "enclosure",
                              url=attachment[0],
                              length=attachment[1],
                              type=attachment[2])

    def _format_date(self, dt):
        if hasattr(dt, "timestamp"):
            return formatdate(dt.timestamp(), localtime=True)
        else:
            import time
            return formatdate(time.mktime(dt.timetuple()), localtime=True)
