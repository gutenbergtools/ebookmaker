#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

KindleWriter.py

Copyright 2009-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

import re
import os
import subprocess
import sys

from libgutenberg.Logger import info, debug, warning, error
from libgutenberg.GutenbergGlobals import SkipOutputFormat
from ebookmaker.writers import BaseWriter
from ebookmaker.CommonCode import Options

options = Options()

class Writer (BaseWriter):
    """ Class for writing kindle files. """


    def build (self, job):
        """ Build kindle file from epub using amazon kindlegen. """

        info ("Creating Kindle file: %s" % os.path.join (job.outputdir, job.outputfile))
        info ("            ... from: %s" % job.url)

        try:
            cwd = os.getcwd ()
            os.chdir (job.outputdir)

            kindlegen = subprocess.Popen (
                [
                    options.config.MOBIGEN,
                    '-o', os.path.basename (job.outputfile),
                    job.url
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

        except OSError as what:
            os.chdir (cwd)
            error ("KindleWriter: %s %s" % (options.config.MOBIGEN, what))
            raise SkipOutputFormat

        (stdout, stderr) = kindlegen.communicate ()

        os.chdir (cwd)

        if kindlegen.returncode > 0:
            regex = re.compile (r'^(\w+)\(prcgen\):')

            # pylint: disable=E1103
            msg = stderr.rstrip ()
            if msg:
                msg = msg.decode (sys.stderr.encoding)
                error (msg)
            msg = stdout.rstrip ()
            msg = msg.decode (sys.stdout.encoding)
            for line in msg.splitlines ():
                match = regex.match (line)
                if match:
                    sline = regex.sub ("", line)
                    g = match.group (1).lower ()
                    if g == 'info':
                        if sline == 'MOBI File generated with WARNINGS!':
                            # we knew that already
                            continue
                        # info ("kindlegen: %s" % sline)
                    elif g == 'warning':
                        if sline.startswith ('Cover is too small'):
                            continue
                        if sline == 'Cover not specified':
                            continue
                        warning ("kindlegen: %s" % sline)
                    elif g == 'error':
                        error ("kindlegen: %s" % sline)
                    else:
                        error (line)

        info ("Done Kindle file: %s" % os.path.join (
            job.outputdir, job.outputfile))
