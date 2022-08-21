#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

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
no_kindlegen_langs = ['ceb', 'eo', 'fur', 'ia', 'ilo', 'iu', 'mi',
                      'myn', 'nah', 'nap', 'oc', 'oji', 'tl', 'bo']

class Writer(BaseWriter):
    """ Class for writing kindle files. """


    def build(self, job):
        """ Build kindle file from epub using amazon kindlegen or calibre. """

        if job.maintype == 'kindle':
            if job.dc.languages:
                if job.dc.languages[0].id in no_kindlegen_langs:
                    mobimaker = options.config.MOBILANG
                else:
                    mobimaker = options.config.MOBIGEN
        else:
            mobimaker = options.config.MOBIKF8
        if not mobimaker:
            info('no mobimaker available')
            return

        # kindlegen needs localized paths
        outputdir = os.path.abspath(job.outputdir)

        info("Creating Kindle file: %s" % os.path.join(outputdir, job.outputfile))
        info("            ... from: %s" % job.url)

        try:
            cwd = os.getcwd()
            os.chdir(outputdir)
            if 'ebook-convert' in mobimaker:
                kindlegen = subprocess.run(
                    [
                        mobimaker,
                        job.url,
                        os.path.basename(job.outputfile),
                        '--personal-doc="[EBOK]"',
                        '--mobi-file-type=' + ('new' if job.maintype == 'kf8' else 'old')
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            else:
                kindlegen = subprocess.run(
                    [
                        mobimaker,
                        '-o', os.path.basename(job.outputfile),
                        job.url
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

        except OSError as what:
            os.chdir(cwd)
            error("KindleWriter: %s %s" % (mobimaker, what))
            raise SkipOutputFormat

        os.chdir(cwd)

        if kindlegen.returncode > 0:
            regex = re.compile(r'^(\w+)\(prcgen\):')

            # pylint: disable=E1103
            msg = kindlegen.stderr.rstrip()
            if msg:
                msg = msg.decode(sys.stderr.encoding)
                error(msg)
            msg = kindlegen.stdout.rstrip()
            msg = msg.decode(sys.stdout.encoding)
            for line in msg.splitlines():
                match = regex.match(line)
                if match:
                    sline = regex.sub("", line)
                    g = match.group(1).lower()
                    if g == 'info':
                        if sline == 'MOBI File generated with WARNINGS!':
                            # we knew that already
                            continue
                        # info("kindlegen: %s" % sline)
                    elif g == 'warning':
                        if sline.startswith('Cover is too small'):
                            continue
                        if sline == 'Cover not specified':
                            continue
                        warning("kindlegen: %s" % sline)
                    elif g == 'error':
                        error("kindlegen: %s" % sline)
                    else:
                        error(line)

        info("Done Kindle file: %s" % os.path.join(outputdir, job.outputfile))
