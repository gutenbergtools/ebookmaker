#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
PushPackager.py

Copyright 2011 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Package a zip containing everything, that can be pushed to ibiblio.

"""


import os
import zipfile
import re

from libgutenberg.Logger import info, error
import libgutenberg.GutenbergGlobals as gg

from ebookmaker.packagers import BasePackager

TYPE = 'ww'
FORMATS = ['push']

class Packager (BasePackager):
    """ Package one big zip for push.

    Zip contains one directory named after ebook_no.
    This dir mirrors structure on ibiblio::

      12345/12345.txt
      12345/12345.zip
      12345/12345-h/12345-h.html
      12345/12345-h/images/cover.jpg
      12345/12345-h.zip

    """

    @staticmethod
    def add (zip_, filename, memberfilename):
        """ Add one file to the zip. """

        try:
            os.stat (filename)
            dummy_name, ext = os.path.splitext (filename)
            info ('  Adding file: %s as %s' % (filename, memberfilename))
            zip_.write (filename, memberfilename,
                        zipfile.ZIP_STORED if ext in ['.zip', '.png']
                        else zipfile.ZIP_DEFLATED)
        except OSError:
            # warning ('PushPackager: Cannot find file %s', filename)
            return


    def package (self, job, aux_file_list = None):
        self.setup (job)
        zipfilename = job.outputfile # filename is zipfile

        if aux_file_list is None:
            aux_file_list = []

        m = re.match (r'\d+', zipfilename)
        if m:
            ebook_no = m.group (0)
        else:
            error ('Invalid filename %s for push packager.' % zipfilename)
            return

        info ('Creating Zip file: %s' % zipfilename)

        zip_ = zipfile.ZipFile (zipfilename, 'w', zipfile.ZIP_DEFLATED)

        for suffix in '.txt -8.txt -0.txt .zip -8.zip -0.zip -rst.zip -h.zip'.split ():
            filename = '%s%s' % (ebook_no, suffix)
            memberfilename = '%s/%s' % (ebook_no, filename)
            self.add (zip_, filename, memberfilename)

        for suffix, ext in (('-h', 'html'), ('-rst', 'rst')):
            filename = '%s%s.%s' % (ebook_no, suffix, ext)
            memberfilename = '%s/%s%s/%s' % (ebook_no, ebook_no, suffix, filename)
            self.add (zip_, filename, memberfilename)

            # image files
            for url in aux_file_list:
                rel_url = gg.make_url_relative (job.base_url, url)
                filename = os.path.join (self.path, rel_url)
                memberfilename = '%s/%s%s/%s' % (ebook_no, ebook_no, suffix, rel_url)
                self.add (zip_, filename, memberfilename)

        zip_.close ()

        info ('Done Zip file: %s' % zipfilename)
