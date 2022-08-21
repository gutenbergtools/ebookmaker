#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

epub2.py

Copyright 2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

A writer that writes XHTML 1 files suited for conversion into EPUB2.

"""

import re

# from libgutenberg.Logger import info, debug, warning, error

from ebookmaker.mydocutils.writers.xhtml1 import Writer as WriterBase
from ebookmaker.mydocutils.writers.xhtml1 import Translator as TranslatorBase


class Writer (WriterBase):
    """ EPUB2 writer. """

    def __init__ (self):
        WriterBase.__init__ (self)
        self.translator_class = Translator


class Translator (TranslatorBase):
    """ HTML Translator with EPUB2 tweaks. """

    def init_css (self):
        for css_file in ('rst2all.css', 'rst2epub.css'):
            self.head.append ('<style type="text/css">\n%s</style>\n' %
                              self.encode (self.read_css (css_file)))


    def calc_centering_style (self, node):
        """
        Rationale: The EPUB standard allows user agents to replace
        `margin: auto` with `margin: 0`. Thus we cannot use `margin: auto`
        to center images, we have to calculate the left margin value.

        Also we must use 'width' on the html element, not css style,
        or Adobe ADE will not scale the image properly (ie. only
        horizontally).

        :align: is supposed to work on blocks. It floats or centers
        a block.

        :align: center has not the same semantics as :class: center.
        Former centers the block, eg. the whole table, latter centers
        the text, eg, the text in every table cell.

            `:align: center`
                Used on image: centers image
                Used on figure: centers image and caption
                Used on table: centers table and caption

        """

        width = node.get ('width')
        if width is None:
            return []

        style = ['width: %s' % width]

        m = re.match (r'(\d+)\s*%', width)
        if m:
            width = max (min (int (m.group (1)), 100), 0)
            margin = 100 - width

            align = node.get ('align', 'center')
            if align == 'center':
                style.append ('margin-left: %d%%' % (margin / 2))
            if align == 'right':
                style.append ('margin-left: %d%%' % margin)

        node['styles'].extend (style)
