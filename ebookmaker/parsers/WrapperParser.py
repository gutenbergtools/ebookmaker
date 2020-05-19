#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

WrapperParser.py

Copyright 2020 by Eric Hellman

Distributable under the GNU General Public License Version 3 or newer.

"""
import lxml

from ebookmaker.parsers import HTMLParserBase, IMAGE_WRAPPER

mediatypes = ()

class Parser(HTMLParserBase):

    def __init__(self, attribs):
        HTMLParserBase.__init__(self)

        self.attribs.update(attribs)
        attribs.rel.add('linked_image')
        self.src = self.attribs.url
        self.attribs.referrer = attribs.referrer
        self.attribs.url = self.wrapper_url(self.attribs.url)
        self.attribs.orig_url = self.attribs.url
        if not self.attribs.title:
            self.attribs.title = 'linked image'
        self.xhtml = lxml.etree.fromstring(
            self.unicode_content(),
            lxml.html.XHTMLParser(),
            base_url=self.attribs.url
        )


    def bytes_content(self):
        return bytes(self.unicode_content(self), 'utf-8')


    def unicode_content(self):
        """ wrapper page content """
        return IMAGE_WRAPPER.format(src=self.src, title=self.attribs.title)


    def wrapper_url(self, img_url):
        """ make the wrapper url. """
        return img_url + '.wrap.html'


    def make_toc(self, xhtml):
        return []