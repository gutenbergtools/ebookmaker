#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

CSSParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Open an url and return raw data.

"""

import logging
import re
from six.moves import urllib

import cssutils

from libgutenberg.Logger import debug
from libgutenberg.MediaTypes import mediatypes as mt

from ebookmaker import parsers
from ebookmaker.parsers import ParserBase

RE_ELEMENT = re.compile(r'\[[^\]]*\]|((?:^|\s|\+|>|~|,)[a-z0-9]+)', re.I)

mediatypes = (mt.css, )
PG_CSS_PROFILE = (
    'Added Properties for Project Gutenberg',
    {
        'display': 'flex|initial',
        'justify-content': 'center',
        'speak': r'auto|never|always',
        'speak-as': 'normal|spell-out|digits|literal-punctuation|no-punctuation',
        'all': 'initial|inherit|unset',

        # added to update css fonts level 3
        'font-variant-numeric': r'normal|{font-variant-attrs}(\s+{font-variant-attrs})*',

        # (partial) update to CSS Cascading and Inheritance Level 3
        'font-family': 'initial',
        'font-size': 'initial',
        'font-style': 'initial',
        'font-variant': 'initial',
        'font-weight': 'initial',
        'font': 'initial',
        'margin-right': 'initial',
        'margin-left': 'initial',
        'margin-top': 'initial',
        'margin-bottom': 'initial',
        'margin': 'initial',
        'padding-top': 'initial',
        'padding-right': 'initial',
        'padding-bottom': 'initial',
        'padding-left': 'initial',
        'padding': 'initial',
        'text-align': 'initial',
        'text-decoration': 'initial',
        'text-indent': 'initial',
        'text-transform': 'initial',
        
        # updated for  https://www.w3.org/TR/css-writing-modes-3/
        # direction and unicode-bidi  are not supported based on the standard's recommendation
        'writing-mode': 'vertical-lr|vertical-rl|horizontal-tb',
        'text-orientation': 'mixed|upright|sideways',
        'text-combine-upright': 'none | all',      
    },
    {
        'numeric-figure-values': 'lining-nums|oldstyle-nums',
        'numeric-spacing-values': 'proportional-nums|tabular-nums',
        'numeric-fraction-values': 'diagonal-fractions|stacked-fractions',
        'font-variant-attrs': '{numeric-figure-values}|{numeric-spacing-values}|{numeric-fraction-values}|ordinal|slashed-zero',
    }
)

cssutils.profile.addProfiles([PG_CSS_PROFILE])

class Parser(ParserBase):
    """ Parse an external CSS file. """

    def __init__(self, attribs=None):
        cssutils.log.setLog(logging.getLogger('cssutils'))
        # logging.DEBUG is way too verbose
        cssutils.log.setLevel(max(cssutils.log.getEffectiveLevel(), logging.INFO))
        ParserBase.__init__(self, attribs)
        self.sheet = None

    def pre_parse(self):
        """ Parse the CSS file. """

        if self.sheet is not None:
            return

        parser = cssutils.CSSParser()
        if self.fp:
            self.sheet = parser.parseString(self.unicode_content())
        else:
            try:
                self.sheet = parser.parseUrl(self.attribs.url)
            except ValueError:
                logging.error('Missing file: %s', self.attribs.url)
                return

        self.attribs.mediatype = 'text/css'
        self.lowercase_selectors(self.sheet)
        self.make_links_absolute()


    def parse_string(self, s):
        """ Parse the CSS in string. """

        if self.sheet is not None:
            return

        parser = cssutils.CSSParser()
        self.sheet = parser.parseString(s)

        self.attribs.mediatype = 'text/css'
        self.lowercase_selectors(self.sheet)


    @staticmethod
    def iter_properties(sheet):
        """ Iterate on properties in css. """
        for rule in sheet:
            if rule.type == rule.STYLE_RULE:
                for prop in rule.style:
                    yield prop


    @staticmethod
    def lowercase_selectors(sheet):
        """ make element names in selectors lowercase to match xhtml tags """
        for rule in sheet:
            if rule.type == rule.STYLE_RULE:
                for sel in rule.selectorList:
                    sel.selectorText = RE_ELEMENT.sub(
                        lambda m: m.group(1).lower() if m.group(1) else m.group(0),
                        sel.selectorText)

    def make_links_absolute(self):
        """ make links absolute """
        def abs_url(url):
            return urllib.parse.urljoin(self.attribs.url, url)
        cssutils.replaceUrls(self.sheet, abs_url)


    def rewrite_links(self, f):
        """ Rewrite all links using the function f. """
        cssutils.replaceUrls(self.sheet, f)


    def iterlinks(self):
        """ Return the urls of all images in document."""

        for url in cssutils.getUrls(self.sheet):
            yield urllib.parse.urljoin(self.attribs.url, url), parsers.em.style()

    def strip_images(self):
        """ remove all rules with url() in them """
        to_delete = []
        for rule in self.sheet:
            if rule.type == rule.STYLE_RULE and rule.cssText and 'url(' in rule.cssText:
                to_delete.append(rule)
        for rule in to_delete:
            self.sheet.deleteRule(rule)


    def get_aux_urls(self):
        """ Return the urls of all auxiliary files in document.

        Auxiliary files are non-document files you need to correctly
        display the document file, eg. CSS files.

        """

        aux = []

        for rule in self.sheet:
            if rule.type == rule.IMPORT_RULE:
                aux.append(urllib.parse.urljoin(self.attribs.url, rule.href))

        return  aux


    def serialize(self):
        """ Serialize CSS. """

        return self.sheet.cssText
