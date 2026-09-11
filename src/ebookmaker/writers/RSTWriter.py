#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""
RSTWriter.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Build an RST file. This is just the master RST with the PG license mixed in.

"""


import os

from libgutenberg.Logger import debug, info, error
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from ebookmaker import ParserFactory
from ebookmaker import writers

class Writer (writers.BaseWriter):
    """ Class to write a reStructuredText. """

    def build (self, job):
        """ Build RST file. """

        filename = os.path.join (os.path.abspath(job.outputdir), job.outputfile)

        debug ("Creating RST file: %s" % filename)

        parser = ParserFactory.ParserFactory.create (job.url)
        
        has_txt_source = 'text/plain' in str(parser.attribs.orig_mediatype)
        if not has_txt_source:
            raise SkipOutputFormat('f"needs plain text file for conversion: {filename} from {job.url}"')

        data = parser.preprocess ('utf-8').encode ('utf-8')

        self.write_with_crlf (filename, data)

        debug ("Done RST file: %s" % filename)
