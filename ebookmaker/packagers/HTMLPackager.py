#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
HTMLPackager.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Package a HTML file for PG.

"""

from ebookmaker.packagers import HTMLishPackager

TYPE = 'ww'
FORMATS = 'html.images'.split ()

class Packager (HTMLishPackager):
    """ Package a HTML file with its images. """
    pass
