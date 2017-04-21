#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

Spider.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Rudimentary Web Spider

"""


import fnmatch

from six.moves import urllib

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS
from libgutenberg.Logger import debug
from libgutenberg import MediaTypes as mt

from ebookmaker import parsers
from ebookmaker import ParserFactory


class Spider (object):
    """ A very rudimentary web spider. """

    def __init__ (self):
        self.parsed_urls = set ()
        self.parsers = []
        self.redirection_map = {}

        self.include_urls = []
        self.exclude_urls = []
        self.include_mediatypes = []
        self.exclude_mediatypes = []
        self.max_depth = 1


    def recursive_parse (self, root_attribs):
        """ Do a recursive parse starting from url.

        Do a breadth-first traversal. Assuming the first page contains
        a linked TOC, this will get us a more natural ordering of the
        pages than a depth-first traversal.

        """

        queue = []

        debug ("Start of retrieval")

        # enqueue root url

        self.enqueue (queue, 0, root_attribs, True)

        while queue:
            depth, attribs = queue.pop (0)

            url = self.redirect (attribs.url)
            if url in self.parsed_urls:
                continue

            parser = ParserFactory.ParserFactory.create (url, attribs)

            # Maybe the url was redirected to something we already have?
            url = parser.attribs.url
            if url in self.parsed_urls:
                continue
            self.parsed_urls.add (url)

            self.add_redirection (parser.attribs.orig_url, url)
            parser.pre_parse ()
            self.parsers.append (parser)

            # look for more documents to add to the queue
            debug ("Requesting iterlinks for: %s ..." % url)
            for url, link_attr in parser.iterlinks ():

                new_attribs = parsers.ParserAttributes ()
                new_attribs.url = urllib.parse.urldefrag (url)[0]
                new_attribs.referrer = parser.attribs.url

                for k, v in link_attr.items ():
                    if k in ('tag', 'id', 'title'):
                        setattr (new_attribs, k, v)
                    elif k == 'type':
                        new_attribs.orig_mediatype = new_attribs.HeaderElement.from_str (v)
                    elif k == 'rel':
                        new_attribs.rel.update (v.lower ().split ())

                tag = link_attr.get ('tag')
                if tag == NS.xhtml.a:
                    self.enqueue (queue, depth + 1, new_attribs, True)
                elif tag == NS.xhtml.img:
                    self.enqueue (queue, depth, new_attribs, False)
                elif tag == NS.xhtml.link:
                    if new_attribs.rel.intersection ( ('stylesheet', 'coverpage') ):
                        self.enqueue (queue, depth, new_attribs, False)
                    else:
                        self.enqueue (queue, depth + 1, new_attribs, True)
                elif tag == NS.xhtml.object:
                    self.enqueue (queue, depth, new_attribs, False)

        debug ("End of retrieval")

        # rewrite redirected urls
        if self.redirection_map:
            for parser in self.parsers:
                parser.remap_links (self.redirection_map)

        self.topological_sort ()


    def enqueue (self, queue, depth, attribs, is_doc):
        """ Enque url for parsing. """

        if is_doc:
            if depth >= self.max_depth:
                return
            if not self.is_included_url (attribs):
                return
        if not self.is_included_mediatype (attribs) and not self.is_included_relation (attribs):
            return

        queue.append ((depth, attribs))


    def is_included_url (self, attribs):
        """ Return True if this document is eligible. """

        url = attribs.url

        included = any ([fnmatch.fnmatchcase (url, x) for x in self.include_urls])
        excluded = any ([fnmatch.fnmatchcase (url, x) for x in self.exclude_urls])

        if included and not excluded:
            return True

        if excluded:
            debug ("Dropping excluded %s" % url)
        if not included:
            debug ("Dropping not included %s" % url)
        return False


    def is_included_mediatype (self, attribs):
        """ Return True if this document is eligible. """

        if attribs.orig_mediatype is None:
            mediatype = mt.guess_type (attribs.url)
            if mediatype:
                attribs.orig_mediatype = attribs.HeaderElement (mediatype)
            else:
                return True # always include if mediatype unknown

        mediatype = attribs.orig_mediatype.value

        included = any ([fnmatch.fnmatch (mediatype, pattern)
                         for pattern in self.include_mediatypes])
        excluded = any ([fnmatch.fnmatch (mediatype, pattern)
                         for pattern in self.exclude_mediatypes])

        if included and not excluded:
            return True

        if excluded:
            debug ("Dropping excluded mediatype %s" % mediatype)
        if not included:
            debug ("Dropping not included mediatype %s" % mediatype)

        return False


    def is_included_relation (self, attribs):
        """ Return True if this document is eligible. """

        return attribs.rel.intersection ( ('coverpage', 'important') )


    def topological_sort (self):
        """ Do a topological sort of documents using <link rel='next'> """

        relnext = [(p.attribs.referrer, p.attribs.url)
                   for p in self.parsers if 'next' in p.attribs.rel]
        if relnext:
            try:
                d = {}
                for order, url in enumerate (gg.topological_sort (relnext)):
                    d[url] = order
                    debug ("%s order %d" % (url, order))
                for parser in self.parsers:
                    parser.order = d.get (parser.attribs.url, 999999)
                self.parsers.sort (key = lambda p: p.order)

            except Exception:
                pass


    def add_redirection (self, from_url, to_url):
        """ Remember this redirection. """

        if from_url != to_url:
            self.redirection_map[from_url] = to_url
            debug ("Adding redirection from %s to %s" % (from_url, to_url))


    def redirect (self, url):
        """
        Redirect url.

        Parsers are cached under the 200 url. This is an offline redirect
        to find the 200 url.

        """
        return self.redirection_map.get (url, url)


    def dict_urls_mediatypes (self):
        """ Return a dict of all parsed urls and mediatypes. """
        return dict ([(p.attribs.url, p.mediatype ()) for p in self.parsers])


    def get_aux_file_list (self):
        """ Iterate over image files. Return absolute urls. """

        for p in self.parsers:
            if hasattr (p, 'resize_image'):
                yield p.attribs.url
