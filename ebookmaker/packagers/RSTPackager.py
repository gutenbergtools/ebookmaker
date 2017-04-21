#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
RSTPackager.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Package a RST file for PG.

"""

from ebookmaker.packagers import HTMLishPackager

TYPE = 'ww'
FORMATS = 'rst.gen'.split ()

class Packager (HTMLishPackager):
    """ Package a RST file with its images. """
    pass
