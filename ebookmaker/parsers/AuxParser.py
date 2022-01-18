#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

AuxParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Open an url and return raw data.

"""


from ebookmaker.parsers import ParserBase

mediatypes = ('*/*', )

class Parser (ParserBase):
    """ Parse an auxiliary file. """
    auxparser = True
    def __init__ (self, attribs = None):
        ParserBase.__init__ (self, attribs)
        self.data = None


    def pre_parse (self):
        """ Parse the file. """
        self.data = self.bytes_content ()


    def serialize (self):
        """ Serialize file to string. """
        return self.data
