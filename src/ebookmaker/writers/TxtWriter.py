#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
TxtWriter.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Build an UTF-8-encoded PG plain text file. This is just the plain text
version recoded into UTF-8.

"""

from __future__ import unicode_literals

import os
import subprocess
import sys

from libgutenberg.Logger import debug, info, warning, error
from libgutenberg.GutenbergGlobals import SkipOutputFormat, mkdir_for_filename

from ebookmaker import ParserFactory
from ebookmaker import writers
from ebookmaker.CommonCode import Options
from ebookmaker.parsers.boilerplate import strip_headers_from_txt

from .HtmlTemplates import pgheader, pgfooter

options = Options()

# map some not-widely-supported characters to more common ones
u2u = {
    0x2010: '-',  # unicode HYPHEN to HYPHEN-MINUS. Many Windows fonts lack this.
    }


def insert_boilerplate(job, text):
    text, header, footer = strip_headers_from_txt(text)
    pg_header = pgheader(job.dc).text_content()
    pg_footer = pgfooter(job.dc).text_content()
    return pg_header + text + pg_footer


class Writer(writers.BaseWriter):
    """ Class to write PG plain text. """

    def build(self, job):
        """ Build TXT file. """

        filename = os.path.join(job.outputdir, job.outputfile)

        encoding = job.subtype.strip('.')

        mkdir_for_filename(filename)

        debug("Creating plain text file: %s from %s", filename, job.url)

        parser = ParserFactory.ParserFactory.create(job.url)

        # don't make txt file unless the source is txt of some encoding
        has_txt_source = 'text/plain' in str(parser.attribs.orig_mediatype)
        is_html_source = not has_txt_source and \
                         hasattr(parser, 'xhtml') and \
                         parser.xhtml is not None

        if is_html_source:
            info("Plain text file %s aborted due to html input" % filename)
            return
        else:
            data = parser.unicode_content()

        data = insert_boilerplate(job, data)

        data = data.encode('utf_8_sig' if encoding == 'utf-8' else encoding, 'unitame')

        self.write_with_crlf(filename, data)

        debug("Done plain text file: %s" % filename)
