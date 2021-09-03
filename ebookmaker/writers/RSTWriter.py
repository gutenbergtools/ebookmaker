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

        info ("Creating RST file: %s" % filename)

        parser = ParserFactory.ParserFactory.create (job.url)

        if not hasattr (parser, 'rst2nroff'):
            error ('RSTWriter can only work on a RSTParser.')
            raise SkipOutputFormat

        data = parser.preprocess ('utf-8').encode ('utf-8')

        self.write_with_crlf (filename, data)

        info ("Done RST file: %s" % filename)
