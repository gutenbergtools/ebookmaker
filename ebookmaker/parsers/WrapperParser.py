#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

WrapperParser.py

Copyright 2020 by Eric Hellman

Distributable under the GNU General Public License Version 3 or newer.

"""
from xml.sax.saxutils import escape, quoteattr

import lxml

from copy import copy
from ebookmaker.parsers import HTMLParserBase, IMAGE_WRAPPER

mediatypes = ()

class Parser(HTMLParserBase):

    def __init__(self, attribs):
        HTMLParserBase.__init__(self, copy(attribs))
        self.attribs.orig_mediatype = self.attribs.mediatype
        self.src = self.attribs.url
        self.attribs.url = self.wrapper_url(self.attribs.url)
        self.attribs.orig_url = self.attribs.url
        self.attribs.nonlinear = True
        if not self.attribs.title:
            self.attribs.title = 'linked image'
        self.xhtml = lxml.etree.fromstring(
            self.unicode_content(),
            lxml.html.XHTMLParser(),
            base_url=self.attribs.url
        )
        self.fp = True  # so writers won't skip it

        # mark the image for treatment as a linked image
        attribs.rel.add('linked_image')
        # set the referrer for the image to this wrapper
        attribs.referrer = self.attribs.url


    def unicode_content(self):
        """ wrapper page content """
        frag = ('#%s' % self.attribs.id) if self.attribs.id else ''
        backlink = '<br /><a href="%s%s" title="back" >back</a>' % (
            escape(self.attribs.referrer), frag)
        return IMAGE_WRAPPER.format(
            src=escape(self.src),
            title=quoteattr(self.attribs.title),
            backlink=backlink)


    def wrapper_url(self, img_url):
        """ make the wrapper url. """
        if self.attribs.id:
            return '%s.%s.wrap.html' % (img_url, self.attribs.id)
        return img_url + '.wrap.html'


    def make_toc(self, xhtml):
        return []


    def iterlinks(self):
        """ only return the image """
        for iterlink in super(Parser, self).iterlinks():
            if iterlink[1].tag == 'img':
                yield iterlink