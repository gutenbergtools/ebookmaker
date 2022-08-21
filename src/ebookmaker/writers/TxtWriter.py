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

options = Options()

# map some not-widely-supported characters to more common ones
u2u = {
    0x2010: '-',  # unicode HYPHEN to HYPHEN-MINUS. Many Windows fonts lack this.
    }

class Writer(writers.BaseWriter):
    """ Class to write PG plain text. """

    def groff(self, job, nroff, encoding='utf-8'):
        """ Process thru groff.

        Takes and returns unicode strings!

        """

        device = {'utf-8': 'utf8',
                  'iso-8859-1': 'latin1',
                  'us-ascii': 'ascii'}[encoding]

        nroff = nroff.encode(encoding)
        nrofffilename = os.path.join(
            os.path.abspath(job.outputdir),
            os.path.splitext(job.outputfile)[0] + '.nroff')

        # write nroff file for debugging
        if options.verbose >= 2:
            with open(nrofffilename, 'wb') as fp:
                fp.write(nroff)
        else:
            try:
                # remove debug files from previous runs
                os.remove(nrofffilename)
            except OSError:
                pass

        # call groff
        try:
            _groff = subprocess.Popen([options.config.GROFF,
                                       "-t",             # preprocess with tbl
                                       "-K", device,     # input encoding
                                       "-T", device],    # output device
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE)
        except OSError:
            error("TxtWriter: executable not found: %s" % options.config.GROFF)
            raise SkipOutputFormat

        (txt, stderr) = _groff.communicate(nroff)

        # pylint: disable=E1103
        for line in stderr.splitlines():
            line = line.decode(sys.stderr.encoding)
            line = line.strip()
            if 'error' in line:
                error("groff: %s" % line)
            elif 'warn' in line:
                if options.verbose >= 1:
                    warning("groff: %s" % line)

        txt = txt.decode(encoding)
        return txt.translate(u2u) # fix nroff idiosyncracies


    def build(self, job):
        """ Build TXT file. """

        filename = os.path.join(job.outputdir, job.outputfile)

        encoding = job.subtype.strip('.')

        mkdir_for_filename(filename)

        info("Creating plain text file: %s from %s", filename, job.url)

        parser = ParserFactory.ParserFactory.create(job.url)

        # don't make txt file unless the source is txt of some encoding
        has_txt_source = 'text/plain' in str(parser.attribs.orig_mediatype)
        is_html_source = not has_txt_source and \
                         hasattr(parser, 'xhtml') and \
                         parser.xhtml is not None

        if hasattr(parser, 'rst2nroff'):
            data = self.groff(job, parser.rst2nroff(job, encoding), encoding)
        elif is_html_source:
            info("Plain text file %s aborted due to html input" % filename)
            return
        else:
            data = parser.unicode_content()

        data = data.encode('utf_8_sig' if encoding == 'utf-8' else encoding, 'unitame')

        self.write_with_crlf(filename, data)

        info("Done plain text file: %s" % filename)
