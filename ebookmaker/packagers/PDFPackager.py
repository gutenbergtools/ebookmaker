#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
PDFPackager.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Package a PDF file for PG.

"""

from ebookmaker.packagers import OneFileZipPackager

TYPE = 'ww'
FORMATS = ''.split ()

class Packager (OneFileZipPackager):
    """ WW packager for PDF files. """
    pass
