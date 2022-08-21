#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

Module parsers

Copyright 2010-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Customized Project Gutenberg directives for RST parser.

"""

from docutils import statemachine
from docutils.parsers.rst import Directive, directives

from ebookmaker.mydocutils import parsers

from ebookmaker.mydocutils.gutenberg import transforms as gutenberg_transforms

from libgutenberg.Logger import error, warning, info, debug

# pylint: disable=W0142, W0102


class PGHeaderFooter (Directive):
    """ Inserts PG header or footer. """

    required_arguments = 0
    optional_arguments = 0

    def run (self):
        settings = self.state.document.settings
        include_lines = statemachine.string2lines (
            settings.get_resource ('mydocutils.gutenberg.parsers', self.resource),
            settings.tab_width,
            convert_whitespace = 1)
        self.state_machine.insert_input (include_lines, '')
        return []


class PGHeader (PGHeaderFooter):
    """ Inserts PG header. """
    resource = 'pg-header.rst'


class PGFooter (PGHeaderFooter):
    """ Inserts PG footer. """
    resource = 'pg-footer.rst'


class Parser (parsers.Parser):
    """ Parser with PG custom directives. """

    def __init__ (self):
        parsers.Parser.__init__ (self)

        directives.register_directive ('pgheader',        PGHeader)
        directives.register_directive ('pgfooter',        PGFooter)


    def get_transforms (self):
        return parsers.Parser.get_transforms (self) + [
            gutenberg_transforms.VariablesTransform,
            gutenberg_transforms.SubRefToVarTransform]
