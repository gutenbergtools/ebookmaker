#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

PicsDirWriter.py

Copyright 2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Copies pics into local directory. Needed for HTML and Xetex.

"""


import os.path

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.Logger import info, debug, error

from ebookmaker.parsers import webify_url
from ebookmaker import writers


class Writer(writers.BaseWriter):
    """ Writes Pics directory. """

    def copy_aux_files(self, job, dest_dir):
        """ Copy image files to dest_dir. Use image data cached in parsers. """

        for p in job.spider.parsers:
            if hasattr(p, 'resize_image') or hasattr(p, 'auxparser'):
                src_uri = p.attribs.url
                if src_uri.startswith(webify_url(dest_dir)):
                    debug('Not copying %s to %s: already there' % (src_uri, dest_dir))
                    continue

                fn_dest = gg.make_url_relative(webify_url(job.base_url), src_uri)
                fn_dest = os.path.join(dest_dir, fn_dest)

                # debug('base_url =  %s, src_uri = %s' % (job.base_url, src_uri))

                if gg.is_same_path(src_uri, fn_dest):
                    debug('Not copying %s to %s: same file' % (src_uri, fn_dest))
                    continue
                debug('Copying %s to %s' % (src_uri, fn_dest))

                fn_dest = gg.normalize_path(fn_dest)
                gg.mkdir_for_filename(fn_dest)
                try:
                    with open(fn_dest, 'wb') as fp_dest:
                        fp_dest.write(p.serialize())
                except IOError as what:
                    error('Cannot copy %s to %s: %s' % (src_uri, fn_dest, what))



    def build(self, job):
        """ Build Pics file. """

        dest_dir = os.path.abspath(job.outputdir)

        info("Creating Pics directory in: %s" % dest_dir)

        self.copy_aux_files(job, dest_dir)

        info("Done Pics directory in: %s" % dest_dir)
