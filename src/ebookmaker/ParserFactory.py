#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

ParserFactory.py

Copyright 2009-14 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""


import os.path
import re

from six.moves import urllib
import six

from pkg_resources import resource_listdir, resource_stream # pylint: disable=E0611
import requests

from libgutenberg.Logger import critical, debug, error, info
from libgutenberg import MediaTypes
from ebookmaker.CommonCode import Options
from ebookmaker.Version import VERSION
from ebookmaker import parsers

options = Options()
parser_modules = {}

def load_parsers():
    """ See what types we can parse. """

    for fn in resource_listdir('ebookmaker.parsers', ''):
        modulename, ext = os.path.splitext(fn)
        if ext == '.py':
            if modulename.endswith('Parser'):
                module = __import__('ebookmaker.parsers.' + modulename, fromlist=[modulename])
                debug("Loading parser from module: %s for mediatypes: %s" % (
                    modulename, ', '.join(module.mediatypes)))
                for mediatype in module.mediatypes:
                    parser_modules[mediatype] = module

    return parser_modules.keys()


def unload_parsers():
    """ Unload parser modules. """
    for k in parser_modules.keys():
        del parser_modules[k]


class ParserFactory(object):
    """ A factory and a cache for parsers.

    So we don't reparse the same file twice.

    """

    parsers = {} # cache: parsers[url] = parser

    @staticmethod
    def get(attribs):
        """ Get the right kind of parser. """

        try:
            mediatype = attribs.orig_mediatype.value
            if mediatype == 'text/plain' and attribs.referrer:
                # don't use GutenbergTextParser, it's a linked text file
                return parsers.TxtParser(attribs)
            return parser_modules[mediatype].Parser(attribs)
        except (AttributeError, KeyError):
            return parser_modules['*/*'].Parser(attribs)


    @classmethod
    def create(cls, url, attribs=None):
        """ Create an appropriate parser. """
        url = parsers.webify_url(url)
        if attribs is None:
            attribs = parsers.ParserAttributes()

        # debug("Need parser for %s" % url)

        if url in cls.parsers:
            # debug("... reusing parser for %s" % url)
            # reuse same parser, maybe already filled with data
            parser = cls.parsers[url]
            parser.reset()
            parser.attribs.update(attribs)
            # debug(str(parser.attribs))
            return parser

        scheme = urllib.parse.urlsplit(url).scheme
        if scheme == 'resource':
            fp = cls.open_resource(url, attribs)
        elif scheme in ('http', 'https'):
            fp = cls.open_url(url, attribs)
        else:
            fp = cls.open_file(url, attribs)
        if fp is None:
            return
        if attribs.url in cls.parsers:
            # reuse parser because parsing may be expensive, eg. reST docs
            # debug("... reusing parser for %s" % attribs.url)
            parser = cls.parsers[attribs.url]
            parser.attribs.update(attribs)
            return parser

        # ok. so we have to create a new parser
        debug("... creating new parser for %s" % url)

        if options.mediatype_from_extension:
            attribs.orig_mediatype = attribs.HeaderElement(MediaTypes.guess_type(url))
            debug("... set mediatype %s from extension" % attribs.orig_mediatype.value)

        attribs.orig_url = url
        parser = cls.get(attribs)
        parser.fp = fp

        cls.parsers[url] = parser

        return parser


    @classmethod
    def open_url(cls, url, attribs):
        """ Open url for parsing. """

        fp = requests.get(
            url,
            stream=True,
            headers={
                'User-Agent': "EbookMaker/%s (+http://pypi.python.org/ebookmaker)" % VERSION
            },
            proxies=options.config.PROXIES
        )
        attribs.orig_mediatype = attribs.HeaderElement.from_str(
            fp.headers.get('Content-Type', 'application/octet-stream'))
        debug("... got mediatype %s from server" % str(attribs.orig_mediatype))
        attribs.orig_url = url
        attribs.url = fp.url
        return six.BytesIO(fp.content)


    @classmethod
    def open_file(cls, url, attribs):
        """ Open a local file for parsing. """
        def open_file_from_path(path):
            try:
                return open(url, 'rb')
            except FileNotFoundError:
                critical('Missing file: %s' % url)
            except IsADirectoryError:
                critical('Missing file is a directory: %s' % url)
            return None
            
        if re.search(r'^([a-zA-z]:|/)', url):
            fp = open_file_from_path(url)
        else:
            try:
                # handles all the flavors of file: urls, including on windows
                fp = urllib.request.urlopen(url)
            except urllib.error.URLError as what:
                fp = None
                critical('Missing file: %s' % what.reason)
                return None
            except ValueError:  # just a relative path?
                fp = open_file_from_path(url)
            
        attribs.orig_mediatype = attribs.HeaderElement(MediaTypes.guess_type(url))

        debug("... got mediatype %s from guess_type" % str(attribs.orig_mediatype))
        attribs.orig_url = attribs.url = url
        return fp


    @classmethod
    def open_resource(cls, orig_url, attribs):
        """ Open a python package resource file for parsing. """

        # resource://python.package/filename.ext

        o = urllib.parse.urlsplit(orig_url)
        package = o.hostname
        filename = o.path[1:]
        fp = resource_stream(package, filename)
        attribs.orig_mediatype = attribs.HeaderElement(MediaTypes.guess_type(filename))

        debug("... got mediatype %s from guess_type" % str(attribs.orig_mediatype))
        attribs.orig_url = orig_url
        attribs.url = orig_url
        return fp


    @classmethod
    def clear_parser_cache(cls):
        """ Clear parser cache to free memory. """

        # debug: kill refs
        for dummy_url, parser in cls.parsers.items():
            del parser

        cls.parsers = {}
