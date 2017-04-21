#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
GzipPackager.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Gzip a file.

"""

from ebookmaker.packagers import OneFileGzipPackager

TYPE = 'gzip'
FORMATS = 'rst html.noimages html.images txt.us-ascii txt.iso-8859-1 txt.utf-8'.split ()

class Packager (OneFileGzipPackager):
    """ Gzip packager. """
    pass
