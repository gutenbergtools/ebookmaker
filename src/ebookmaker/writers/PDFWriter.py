#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
PDFWriter.py

Copyright 2011 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Convert RST to PDF.

"""


import os
import subprocess

from libgutenberg.Logger import debug, info, warning, error
from libgutenberg.GutenbergGlobals import SkipOutputFormat

from ebookmaker import ParserFactory
from ebookmaker import writers
from ebookmaker.CommonCode import Options

options = Options()

class Writer (writers.BaseWriter):
    """ Class to write PDF. """

    def build (self, job):
        """ Build PDF file. """

        inputfilename  = job.url
        outputfilename = os.path.join (os.path.abspath(job.outputdir), job.outputfile)

        debug ("Inputfile: %s" % inputfilename)
        info ("Creating PDF file: %s" % outputfilename)

        parser = ParserFactory.ParserFactory.create (inputfilename)

        if not hasattr (parser, 'rst2xetex'):
            warning ('Skipping PDF Output because input mediatype is %s' % parser.mediatype())
            raise SkipOutputFormat

        # Brain-dead xetex doesn't understand unix pipes
        # so we have to write a temp file

        texfilename = os.path.splitext (outputfilename)[0] + '.tex'
        auxfilename = os.path.splitext (outputfilename)[0] + '.aux'
        logfilename = os.path.splitext (outputfilename)[0] + '.log'

        try:
            os.remove (auxfilename)
        except OSError:
            pass

        tex = parser.rst2xetex (job)
        with open (texfilename, 'wb') as fp:
            fp.write (tex)

        try:
            cwd = os.getcwd ()
            os.chdir (os.path.abspath(job.outputdir))

            _xetex = subprocess.Popen ([options.config.XELATEX,
                                        "-output-directory", job.outputdir,
                                        "-interaction", "nonstopmode",
                                        texfilename],
                                       stdin = subprocess.PIPE,
                                       stdout = subprocess.PIPE,
                                       stderr = subprocess.PIPE)
        except OSError as what:
            os.chdir (cwd)
            error ("PDFWriter: %s %s" % (options.config.XELATEX, what))
            raise SkipOutputFormat

        (dummy_stdout, dummy_stderr) = _xetex.communicate ()

        with open (logfilename, encoding='utf-8') as fp:
            for line in fp:
                line = line.strip ()
                if 'Error:' in line:
                    error ("xetex: %s" % line)
                if options.verbose >= 1:
                    if 'Warning:' in line:
                        warning ("xetex: %s" % line)

        if options.verbose < 2:
            try:
                os.remove (texfilename)
                os.remove (logfilename)
                os.remove (auxfilename)
            except OSError:
                pass

        os.chdir (cwd)

        info ("Done PDF file: %s" % outputfilename)
