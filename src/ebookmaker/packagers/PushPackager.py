#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
PushPackager.py

Copyright 2011 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Package a zip containing everything, that can be pushed to ibiblio.

"""


import os.path
import re

from libgutenberg.Logger import info, error
import libgutenberg.GutenbergGlobals as gg

from ebookmaker.CommonCode import Options
from ebookmaker.packagers import ZipPackager

options = Options()
TYPE = 'ww'
FORMATS = ['push']

class Packager (ZipPackager):
    """ Package one big zip for push.

    Zip contains one directory named after ebook_no.
    This dir mirrors structure on ibiblio::

      12345/12345.txt
      12345/12345.zip
      12345/12345-h/12345-h.html
      12345/12345-h/images/cover.jpg
      12345/12345-h.zip

    """

    def package (self, job):
        self.setup (job)
        zipfilename = job.outputfile # filename is zipfile

        m = re.match (r'\d+', zipfilename)
        if m:
            ebook_no = m.group (0)
        else:
            error ('Invalid filename %s for push packager.' % zipfilename)
            return

        zip_ = self.create (zipfilename)

        for suffix in '.txt -8.txt -0.txt .zip -8.zip -0.zip -rst.zip -h.zip'.split ():
            filename = '%s%s' % (ebook_no, suffix)
            memberfilename = '%s/%s' % (ebook_no, filename)
            self.add (zip_, filename, memberfilename)

        for suffix, ext in (('-h', 'html'), ('-rst', 'rst')):
            filename = '%s%s.%s' % (ebook_no, suffix, ext)
            memberfilename = '%s/%s%s/%s' % (ebook_no, ebook_no, suffix, filename)
            self.add (zip_, filename, memberfilename)

            # image files
            for url in options.html_images_list:
                rel_url = gg.make_url_relative (job.base_url, url)
                filename = os.path.join (self.path, rel_url)
                memberfilename = '%s/%s%s/%s' % (ebook_no, ebook_no, suffix, rel_url)
                self.add (zip_, filename, memberfilename)

        zip_.close ()
        info ('Done Zip file: %s' % zipfilename)
