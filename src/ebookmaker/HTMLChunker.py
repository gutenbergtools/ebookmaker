#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

HTMLChunker.py

Copyright 2009, 2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Splits a HTML file into chunks.

"""

from __future__ import unicode_literals


import os
import re
import copy

from lxml import etree
from six.moves import urllib

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS
from libgutenberg.Logger import debug, error, info

from ebookmaker.CommonCode import Options
options = Options()

MAX_CHUNK_SIZE = 100 * 1024  # bytes
MIN_CHUNK_SIZE = 1024  # bytes

SECTIONS = [
    ('div.section', 0.0),
    ('div.chapter', 0.0),
    ('section', 0.0),
    ('h1', 0.5),
    ('div', 0.5),
    ('h2', 0.7),
    ('h3', 0.75),
    ('p', 0.8),
    ('figure', 0.8),
]

NEVER_SPLIT = [NS.xhtml[tag] for tag in ['table', 'figure', 'dl', 'ol', 'ul']]

def xpath(node, path):
    """ xpath helper """
    return node.xpath(path, namespaces = gg.NSMAP)

def normalize_uri(uri):
    """ Normalize URI for idmap. """
    return urllib.parse.unquote(uri) # .decode('utf-8')


class HTMLChunker(object):
    """ Splits HTML tree into smaller chunks.

    Some epub viewers are limited in that they cannot display files
    larger than 300K.  If our HTML happens to be longer, we have to
    split it up.  Also smaller chunks do improve page flip times.


    """

    def __init__(self, version='epub2'):
        self.chunks = []
        self.idmap = {}
        self.chunk = None
        self.chunk_body = None
        self.chunk_size = 0
        self.next_id = 0
        self.version = version
        self.max_chunk_size = MAX_CHUNK_SIZE * (1 if version == 'epub2' else 3)
        self.nosplit = False

        self.tags = {}
        for tag, size in SECTIONS:
            self.tags[NS.xhtml[tag]] = max(MIN_CHUNK_SIZE, int(size * self.max_chunk_size))
        for tag in options.section_tags:
            self.tags[NS.xhtml[tag]] = MIN_CHUNK_SIZE


    def _make_name(self, url):
        """ Generate a name for the chunk. """
        u = list(urllib.parse.urlparse(url))
        root, ext = os.path.splitext(u[2])
        html_ext = 'html' if self.version == 'epub2' else 'xhtml'
        u[2] = f'{root}-{self.next_id}{ext}.{html_ext}'
        self.next_id += 1
        return urllib.parse.urlunparse(u)


    @staticmethod
    def make_template(tree):
        """ Make a copy with an empty html:body.

        This makes a template into which we can paste our chunks.

        """

        template = copy.deepcopy(tree)

        for c in xpath(template, '//xhtml:body'):

            # descend while elem has only one child
            while len(c) == 1:
                c = c[0]

            # clear children but save attributes
            attributes = c.attrib.items()
            c.clear()
            # was tentative fix for patological one-element-html case
            # for child in c:
            #     c.remove(child)
            for a in attributes:
                c.set(a[0], a[1])

        # debug(etree.tostring(template))

        return template


    def reset_chunk(self, template):
        """ start a new chunk """

        self.chunk = copy.deepcopy(template)
        self.chunk_size = 0
        self.chunk_body = xpath(self.chunk, "//xhtml:body")[0]
        while len(self.chunk_body) == 1:
            self.chunk_body = self.chunk_body[0]
        self.nosplit = False


    def shipout_chunk(self, attribs, chunk_id = None, comment = None):
        """ ready chunk to be shipped """

        attribs = copy.copy(attribs)

        if self.chunk_size > self.max_chunk_size and not self.nosplit:
            self.split(self.chunk, attribs)
            return

        url = normalize_uri(attribs.url)
        chunk_name = self._make_name(url)

        # the url of the whole page
        if url not in self.idmap:
            self.idmap[url] = chunk_name

        # fragments of the page
        for e in xpath(self.chunk, '//xhtml:*[@id]'):
            id_ = e.attrib['id']
            old_id = "%s#%s" % (url, id_)
            # key is unicode string,
            # value is uri-escaped byte string
            # if ids get cloned while chunking, map to the first one only
            if old_id not in self.idmap:
                self.idmap[old_id] = "%s#%s" % (
                    chunk_name,  urllib.parse.quote(id_))

        attribs.url = chunk_name
        attribs.id = chunk_id
        attribs.comment = comment
        self.chunks.append((self.chunk, attribs) )

        debug("Adding chunk %s (%d bytes) %s" % (chunk_name, self.chunk_size, chunk_id))


    def split(self, tree, attribs):
        """ Split whole html or split chunk.

        Find some arbitrary points to do it.

        """

        for body in xpath(tree, "//xhtml:body"):
            # we can't split a node that has only one child
            # descend while elem has only one child
            while len(body) == 1:
                body = body[0]

            debug("body tag is %s" % body.tag)

            template = self.make_template(tree)
            self.reset_chunk(template)

            # FIXME: is this ok ???
            # fixes patological one-element-body case
            self.chunk_body.text = body.text

            for child in body:
                if not isinstance(child, etree.ElementBase):
                    # comments, processing instructions etc.
                    continue

                # size measurement doesn't need to be exact
                try:
                    child_size = len(etree.tostring(child, encoding='utf-8'))
                except etree.SerialisationError:
                    child_size = len(etree.tostring(child, encoding='latin_1'))

                try:
                    tags = [child.tag + '.' + c for c in child.attrib['class'].split()]
                    tags.append(child.tag)
                except KeyError:
                    tags = [child.tag]

                for tag in tags:
                    if child.tag in NEVER_SPLIT:
                        self.nosplit = True
                        break
                    if ((self.chunk_size + child_size > self.max_chunk_size) or
                              (tag in self.tags and self.chunk_size > self.tags[tag])):

                        comment = ("Chunk: size=%d Split on %s"
                                   % (self.chunk_size, re.sub('^{.*}', '', tag)))
                        debug(comment)

                        # find a suitable id
                        chunk_id = None
                        for c in self.chunk_body:
                            if 'id' in c.attrib:
                                chunk_id = c.get('id')
                                break
                        debug("chunk id is: %s" % (chunk_id or ''))

                        self.shipout_chunk(attribs, chunk_id, comment)
                        self.reset_chunk(template)
                        break

                self.chunk_body.append(child)
                self.chunk_size = self.chunk_size + child_size

            # fixes patological one-element-body case
            self.chunk_body.tail = body.tail

            chunk_id = None
            if len(self.chunk_body):
                chunk_id = self.chunk_body[0].get('id')
            comment = "Chunk: size=%d" % self.chunk_size
            self.shipout_chunk(attribs, chunk_id, comment)
            self.reset_chunk(template)


    def rewrite_links(self, f):
        """ Rewrite all href and src using f(). """

        for chunk in self.chunks:
            # chunk['name'] = f(chunk['name'])

            for link in xpath(chunk[0], '//xhtml:*[@href]'):
                link.set('href', f(link.get('href')))

            for image in xpath(chunk[0], '//xhtml:*[@src]'):
                image.set('src', f(image.get('src')))

        for k, v in self.idmap.items():
            self.idmap[k] = f(v)


    def rewrite_internal_links(self):
        """ Rewrite links to point into right chunks.

        Because we split the HTML into chunks, all internal links need
        to be rewritten to become links into the right chunk.
        Rewrite all internal links in all chunks.

        """
        for chunk in self.chunks:
            for a in xpath(chunk[0], "//xhtml:*[@href]"):
                try:
                    uri = normalize_uri(a.get('href'))
                    a.set('href', self.idmap[uri])
                except KeyError:
                    ur, dummy_frag = urllib.parse.urldefrag(uri)
                    if ur in self.idmap:
                        error("HTMLChunker: Cannot rewrite internal link '%s'", uri)


    def rewrite_internal_links_toc(self, toc):
        """ Rewrite links to point into right chunks.

        Because we split the HTML into chunks, all internal links need
        to be rewritten to become links into the right chunk.
        Rewrite all links in the passed toc.

        """

        for entry in toc:
            try:
                entry[0] = self.idmap [normalize_uri(entry[0])]
            except KeyError:
                error("HTMLChunker: Cannot rewrite toc entry '%s'" % entry[0])
                error(repr(self.idmap))
                del entry
