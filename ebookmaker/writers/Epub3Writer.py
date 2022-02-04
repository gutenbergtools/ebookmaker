#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

EpubWriter.py

Copyright 2009-2022 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Writes an EPUB3 file.

"""

import re
import datetime
import zipfile
import time
import os
import copy
import subprocess
from xml.sax.saxutils import quoteattr

from six.moves import urllib
from lxml import etree
from lxml.builder import ElementMaker
from pkg_resources import resource_string # pylint: disable=E0611

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS, xpath
from libgutenberg.Logger import info, debug, warning, error, exception
from libgutenberg.MediaTypes import mediatypes as mt
from ebookmaker import parsers
from ebookmaker import ParserFactory
from ebookmaker import HTMLChunker
# from ebookmaker import Spider
from ebookmaker import writers
from ebookmaker.CommonCode import Options
from ebookmaker.Version import VERSION, GENERATOR
from .EpubWriter import (
    MAX_CHUNK_SIZE,
    MAX_IMAGE_SIZE,
    MAX_COVER_DIMEN,
    MAX_IMAGE_DIMEN,
    LINKED_IMAGE_SIZE,
    LINKED_IMAGE_DIMEN,
    TOC_HEADERS,
    DP_PAGENUMBER_CLASSES,
    STRIP_CLASSES,
    PRIVATE_CSS,
    OPS_TEXT_MEDIATYPES,
    OPS_IMAGE_MEDIATYPES,
    OPS_CORE_MEDIATYPES,
    OPS_CONTENT_DOCUMENTS,
    OPS_FONT_TYPES
)
from . import HTMLWriter

EPUB_TYPE = '{%s}type' % NS.epub

options = Options()


match_link_url = re.compile(r'^https?://', re.I)
match_non_link = re.compile(r'[a-zA-Z0-9_\-\.]*(#.*)?$')

class OEBPSContainer(zipfile.ZipFile):
    """ Class representing an OEBPS Container. """

    def __init__(self, filename, oebps_path=None):
        """ Create the zip file.

        And populate it with mimetype and container.xml files.

        """

        self.zipfilename = filename
        self.oebps_path = oebps_path if oebps_path else 'OEBPS/'
        info('Creating Epub file: %s' % filename)

        # open zipfile
        zipfile.ZipFile.__init__(self, filename, 'w', zipfile.ZIP_DEFLATED)

        # write mimetype
        # the OCF spec says mimetype must be first and uncompressed
        i = self.zi()
        i.compress_type = zipfile.ZIP_STORED
        i.filename = 'mimetype'
        self.writestr(i, 'application/epub+zip')

        self.add_container_xml('content.opf')

        self.wrappers = 0 # to generate unique filenames for wrappers


    def commit(self):
        """ Close OCF Container. """
        info("Done Epub file: %s" % self.zipfilename)
        self.close()


    def rollback(self):
        """ Remove OCF Container. """
        debug("Removing Epub file: %s" % self.zipfilename)
        os.remove(self.zipfilename)


    def add_unicode(self, name, u):
        """ Add file to zip from unicode string. """
        i = self.zi(name)
        self.writestr(i, u.encode('utf-8'))


    def add_bytes(self, name, bytes_, mediatype=None):
        """ Add file to zip from bytes string. """

        i = self.zi(name)
        if mediatype and mediatype in parsers.ImageParser.mediatypes:
            i.compress_type = zipfile.ZIP_STORED
        self.writestr(i, bytes_)


    def add_file(self, name, url, mediatype=None):
        """ Add file to zip from bytes string. """

        with open(url) as fp:
            self.add_bytes(name, fp.read(), mediatype)


    def zi(self, filename=None):
        """ Make a ZipInfo. """
        z = zipfile.ZipInfo()
        z.date_time = time.gmtime()
        z.compress_type = zipfile.ZIP_DEFLATED
        z.external_attr = 0x81a40000
        if filename:
            z.filename = os.path.join(self.oebps_path, filename)
        return z


    def add_container_xml(self, rootfilename):
        """ Write container.xml

        <?xml version='1.0' encoding='UTF-8'?>

        <container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'
                   version='1.0'>
          <rootfiles>
            <rootfile full-path='$path'
                      media-type='application/oebps-package+xml' />
          </rootfiles>
        </container>

        """

        rootfilename = os.path.join(self.oebps_path, rootfilename)

        ns_oasis = 'urn:oasis:names:tc:opendocument:xmlns:container'

        ocf = ElementMaker(namespace=ns_oasis,
                           nsmap={None: ns_oasis})

        container = ocf.container(
            ocf.rootfiles(
                ocf.rootfile(**{
                    'full-path': rootfilename,
                    'media-type': 'application/oebps-package+xml'})),
            version='1.0')

        i = self.zi()
        i.filename = 'META-INF/container.xml'#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

EpubWriter.py

Copyright 2009-2022 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Writes an EPUB3 file.

"""

import re
import datetime
import zipfile
import time
import os
import copy
import subprocess
from xml.sax.saxutils import quoteattr

from six.moves import urllib
from lxml import etree
from lxml.builder import ElementMaker
from pkg_resources import resource_string # pylint: disable=E0611

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS, xpath
from libgutenberg.Logger import info, debug, warning, error, exception
from libgutenberg.MediaTypes import mediatypes as mt
from ebookmaker import parsers
from ebookmaker import ParserFactory
from ebookmaker import HTMLChunker
# from ebookmaker import Spider
from ebookmaker import writers
from ebookmaker.CommonCode import Options
from ebookmaker.Version import VERSION, GENERATOR
from .EpubWriter import (
    MAX_CHUNK_SIZE,
    MAX_IMAGE_SIZE,
    MAX_COVER_DIMEN,
    MAX_IMAGE_DIMEN,
    LINKED_IMAGE_SIZE,
    LINKED_IMAGE_DIMEN,
    TOC_HEADERS,
    DP_PAGENUMBER_CLASSES,
    STRIP_CLASSES,
    PRIVATE_CSS,
    OPS_TEXT_MEDIATYPES,
    OPS_IMAGE_MEDIATYPES,
    OPS_CORE_MEDIATYPES,
    OPS_CONTENT_DOCUMENTS,
    OPS_FONT_TYPES
)
from . import HTMLWriter

EPUB_TYPE = '{%s}type' % NS.epub

options = Options()


match_link_url = re.compile(r'^https?://', re.I)
match_non_link = re.compile(r'[a-zA-Z0-9_\-\.]*(#.*)?$')

class OEBPSContainer(zipfile.ZipFile):
    """ Class representing an OEBPS Container. """

    def __init__(self, filename, oebps_path=None):
        """ Create the zip file.

        And populate it with mimetype and container.xml files.

        """

        self.zipfilename = filename
        self.oebps_path = oebps_path if oebps_path else 'OEBPS/'
        info('Creating Epub file: %s' % filename)

        # open zipfile
        zipfile.ZipFile.__init__(self, filename, 'w', zipfile.ZIP_DEFLATED)

        # write mimetype
        # the OCF spec says mimetype must be first and uncompressed
        i = self.zi()
        i.compress_type = zipfile.ZIP_STORED
        i.filename = 'mimetype'
        self.writestr(i, 'application/epub+zip')

        self.add_container_xml('content.opf')

        self.wrappers = 0 # to generate unique filenames for wrappers


    def commit(self):
        """ Close OCF Container. """
        info("Done Epub file: %s" % self.zipfilename)
        self.close()


    def rollback(self):
        """ Remove OCF Container. """
        debug("Removing Epub file: %s" % self.zipfilename)
        os.remove(self.zipfilename)


    def add_unicode(self, name, u):
        """ Add file to zip from unicode string. """
        i = self.zi(name)
        self.writestr(i, u.encode('utf-8'))


    def add_bytes(self, name, bytes_, mediatype=None):
        """ Add file to zip from bytes string. """

        i = self.zi(name)
        if mediatype and mediatype in parsers.ImageParser.mediatypes:
            i.compress_type = zipfile.ZIP_STORED
        self.writestr(i, bytes_)


    def add_file(self, name, url, mediatype=None):
        """ Add file to zip from bytes string. """

        with open(url) as fp:
            self.add_bytes(name, fp.read(), mediatype)


    def zi(self, filename=None):
        """ Make a ZipInfo. """
        z = zipfile.ZipInfo()
        z.date_time = time.gmtime()
        z.compress_type = zipfile.ZIP_DEFLATED
        z.external_attr = 0x81a40000
        if filename:
            z.filename = os.path.join(self.oebps_path, filename)
        return z


    def add_container_xml(self, rootfilename):
        """ Write container.xml

        <?xml version='1.0' encoding='UTF-8'?>

        <container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'
                   version='1.0'>
          <rootfiles>
            <rootfile full-path='$path'
                      media-type='application/oebps-package+xml' />
          </rootfiles>
        </container>

        """

        rootfilename = os.path.join(self.oebps_path, rootfilename)

        ns_oasis = 'urn:oasis:names:tc:opendocument:xmlns:container'

        ocf = ElementMaker(namespace=ns_oasis,
                           nsmap={None: ns_oasis})

        container = ocf.container(
            ocf.rootfiles(
                ocf.rootfile(**{
                    'full-path': rootfilename,
                    'media-type': 'application/oebps-package+xml'})),
            version='1.0')

        i = self.zi()
        i.filename = 'META-INF/container.xml'
        self.writestr(i, etree.tostring(
            container, encoding='utf-8', xml_declaration=True, pretty_print=True))


    def add_image_wrapper(self, img_url, img_title):
        """ Add a HTML file wrapping img_url. """
        img_title = quoteattr(img_title)
        filename = 'wrap%04d.xhtml' % self.wrappers
        self.wrappers += 1
        self.add_bytes(filename,
                       parsers.IMAGE_WRAPPER.format(src=img_url,
                                                    title=img_title,
                                                    backlink="",
                                                    doctype=gg.HTML5_DOCTYPE),
                       mt.xhtml)
        return filename



class OutlineFixer(object):
    """ Class that fixes outline levels. """

    def __init__(self):
        self.stack = [(0, 0),]
        self.last = 0

    def level(self, in_level):
        if in_level < 1:
            return in_level
        (promotion, from_level) = self.stack[-1]
        if in_level > self.last + 1:
            # needs promotion
            more_promotion = in_level - self.last - 1
            new_promotion = promotion + more_promotion
            self.last = in_level
            self.stack.append((new_promotion, in_level))
            return in_level - new_promotion

        if in_level < from_level:
            # close out promotion
            self.last = from_level - promotion - 1
            self.stack.pop()
            return self.level(in_level)

        self.last = in_level
        return in_level - promotion


class Toc(object):
    """ Class that builds toc.xhtml. derived from EpubWriter.TocNCX"""

    def __init__(self, dc):
        self.toc = []
        self.dc = dc
        self.seen_urls = {}
        self.elementmaker = ElementMaker(namespace=str(NS.xhtml),
                                nsmap={None: str(NS.xhtml)})


    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        """ Serialize toc.em as unicode string. """
        em = self.elementmaker
        tocdepth = 1

        if self.toc:
            # normalize toc so that it starts with an h1 and doesn't jump down more than one
            # level at a time
            fixer = OutlineFixer()
            for t in self.toc:
                t[2] = fixer.level(t[2])

            # flatten toc if it contains only one top-level entry
            top_level_entries = sum(t[2] == 1 for t in self.toc)
            if top_level_entries < 2:
                for t in self.toc:
                    if t[2] != -1:
                        t[2] = max(1, t[2] - 1)

            tocdepth = max(t[2] for t in self.toc)

        doc_title = em.title(self.dc.title)
        head = em.head(
            doc_title,
            em.meta(name='dtb:uid', content=self.dc.opf_identifier),
            em.meta(name='dtb:depth', content=str(tocdepth)),
            em.meta(name='dtb:generator', content=GENERATOR % VERSION),
            em.meta(name='dtb:totalPageCount', content='0'),
            em.meta(name='dtb:maxPageNumber', content='0'))

        body = em.body(**{EPUB_TYPE: 'frontmatter'})

        self.seen_urls = {}
        has_pages = False
        for url, dummy_title, depth in self.toc:
            # navPoints and pageTargets referencing the same element
            # must have the same playOrder
            if url not in self.seen_urls:
                self.seen_urls[url] = str(len(self.seen_urls) + 1)
            if depth == -1:
                has_pages = True

        params = {NS.xml.lang: self.dc.languages[0].id} if self.dc.languages else {}

        body.append(self._make_navmap(self.toc))
        ncx = em.html(
            head,
            body,
            **params
        )

        if has_pages:
            ncx.append(self._make_pagelist(self.toc))

        # Ugly workaround for error: "Serialisation to unicode must not
        # request an XML declaration"

        toc_ncx = "%s\n\n%s" % (gg.XML_DECLARATION,
            etree.tostring(ncx, doctype=None, encoding=str, pretty_print=True)
        )

        if options.verbose >= 3:
            debug(toc_ncx)
        return toc_ncx


    def rewrite_links(self, f):
        """ Rewrite all links f(). """
        for entry in self.toc:
            entry[0] = f(entry[0])


    def _make_navmap(self, toc):
        """ Build the toc. """
        em = self.elementmaker

        root = em.nav(**{EPUB_TYPE: 'toc'})
        toctop = em.ol()
        root.append(toctop)

        count = 0
        prev_depth = 0
        current_ol = toctop
        for url, title, depth in toc:
            if depth < 0:
                continue
            count += 1
            toc_item = em.a(title, **{'href': url, 'id': "np-%d" % count})
            if depth > prev_depth:
                while depth > prev_depth:
                    new_ol = em.ol()
                    li = em.li(new_ol)
                    prev_depth += 1
                    current_ol.append(li)
                    current_ol = new_ol
            else:
                while depth < prev_depth:
                    current_ol = current_ol.getparent().getparent()
                    prev_depth -= 1
            li = em.li(toc_item)
            current_ol.append(li)
                               
        return root


    def _make_pagelist(self, toc):
        """ Build the page list. """
        em = self.elementmaker
        root = em.nav(**{EPUB_TYPE: 'landmarks'})
        pagelist_top = em.ol(**{'id': 'pages', 'class': 'pagelist'})
        root.append(pagelist_top)

        for url, pagename, depth in toc:
            if depth == -1:
                toc_item = em.a(pagename, **{
                    'href': url, 
                    'id': "pt-%d" % len(pagelist_top),
                    'value': str(len(pagelist_top)), 
                    EPUB_TYPE: 'normal' if re.search('[0-9]', pagename) else 'frontmatter',
                })
                pagelist_top.append(em.li(toc_item))

        return root


class ContentOPF(object):
    """ Class that builds content.opf metadata. """

    def __init__(self):
        self.nsmap = gg.build_nsmap('opf dc dcterms xsi')

        # FIXME: remove this when lxml is fixed
        # workaround for lxml fat-fingering the default attribute namespaces
        self.nsmap[None] = str(NS.opf) + 'lxml-bug-workaround'

        self.opf = ElementMaker(namespace=self.nsmap[None], nsmap=self.nsmap)

        self.metadata = self.opf.metadata()
        self.manifest = self.opf.manifest()
        self.spine = self.opf.spine()
        self.item_id = 0


    def __str__(self):
        return self.__unicode__()


    def __unicode__(self):
        """ Serialize content.opf as unicode string. """

        assert len(self.manifest) > 0, 'No manifest item in content.opf.'
        assert len(self.spine) > 0, 'No spine item in content.opf.'

        package = self.opf.package(
            **{'version': '3.0', 'unique-identifier': 'id'}) # FIXME add version to instance
        package.append(self.metadata)
        package.append(self.manifest)
        package.append(self.spine)

        content_opf = "%s\n\n%s" % (gg.XML_DECLARATION,
                                    etree.tostring(package,
                                                   encoding=str,
                                                   pretty_print=True))

        # FIXME: remove this when lxml is fixed
        # now merge xmlns:opf and xmlns:
        content_opf = content_opf.replace('lxml-bug-workaround', '')

        if options.verbose >= 3:
            debug(content_opf)
        return content_opf


    def rewrite_links(self, f):
        """ Rewrite all links through f(). """
        for item in self.manifest:
            if item.get('href'):
                item.set('href', f(item.get('href')))


    def meta_item(self, name, content):
        """ Add item to metadata. """
        self.metadata.append(self.opf.meta(name=name, content=content))


    def manifest_item(self, url, mediatype, id_=None, prop=None):
        """ Add item to manifest. """
        def add_prop(prop, newprop):
            if prop:
                vals = prop.split()
            else:
                vals = []
            vals.append(newprop)
            prop = ' '.join(vals)

        if id_ is None or xpath(self.manifest, "//*[@id = '%s']" % id_):
            self.item_id += 1
            id_ = 'item%d' % self.item_id
        
        if prop == 'cover':
            self.add_coverpage(url, _id_)
        manifest_atts = {'href': url, 'id': id_, 'media-type': mediatype}
        if mediatype == 'image/svg+xml':
            prop = add_prop(prop, 'svg')
        if prop:
            manifest_atts['properties'] = prop
        self.manifest.append(
            self.opf.item(**manifest_atts))

        return id_


    def spine_item(self, url, mediatype, id_=None, first=False):
        """ Add item to spine and manifest. """

        if id_ and id_.startswith('pgepubid'):
            # this is an auto-generated header id, not human-readable and probably duplicated
            # make a new one
            id_ = None
        
        id_ = self.manifest_item(url, mediatype, id_)

        # HACK: ADE needs cover flow as first element
        # but we don't know if we have a native coverpage until the manifest is complete
        if first:
            self.spine.insert(
                0, self.opf.itemref(idref=id_))
        else:
            self.spine.append(
                self.opf.itemref(idref=id_))


    def manifest_item_from_parser(self, p):
        """ Add item to manifest from parser. """
        if hasattr(p.attribs, 'comment'):
            self.manifest.append(etree.Comment(p.attribs.comment))
        cover = 'cover-image' if 'icon' in p.attribs.rel else None
        return self.manifest_item(p.attribs.url, p.mediatype(), id_=p.attribs.id, prop=cover)


    def spine_item_from_parser(self, p):
        """ Add item to spine and manifest from parser. """
        if hasattr(p.attribs, 'comment'):
            self.manifest.append(etree.Comment(p.attribs.comment))
        return self.spine_item(p.attribs.url, p.mediatype(), p.attribs.id)


    def toc_item(self, url):
        """ Add TOC to manifest and spine. """
        self.manifest_item(url, mt.xhtml, id_='ncx', prop='nav')


    def pagemap_item(self, url):
        """ Add page-map to manifest and spine. """
        self.manifest_item(url, 'application/oebps-page-map+xml', 'map')
        self.spine.attrib['page-map'] = 'map'


    def metadata_item(self, dc):
        """ Build metadata from DublinCore struct.

        Example of metadata:

  <metadata xmlns:dcterms='http://purl.org/dc/terms/'
            xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
            xmlns:opf='http://www.idpf.org/2007/opf'>

    <dc:identifier id='id'>http://www.gutenberg.org/ebooks/29000</dc:identifier>
    <dc:creator id="author_0">Anthony Trollope</dc:creator>
    <meta property="file-as" refines="#author_0">Trollope, Anthony</meta>
    <meta property="role" refines="#author_0" scheme="marc:relators">aut</meta>
    <dc:title>The Macdermots of Ballycloran</dc:title>
    <dc:language>en</dc:language>
    <dc:subject>Domestic fiction</dc:subject>
    <dc:subject>Ireland -- Fiction</dc:subject>
    <dc:created>1890</dc:created>
    <dc:publisher>Project Gutenberg</dc:publisher>
    <dc:date opf:event='publication'>2009-05-31</dc:date>
    <dc:date opf:event='conversion'>2009-08-26T21:11:14Z</dc:date>
    <dc:rights>Public domain</dc:rights>
    <dc:source>29000-h.htm</dc:source>

    <meta name='cover' content='item0' />
  </metadata>
    """

        # OPF 2.0 v1.0 specifies to use the
        # Dublin Core Metadata Element Set, Version 1.1
        # http://dublincore.org/documents/2004/12/20/dces/

        dcterms = ElementMaker(nsmap=self.nsmap, namespace=str(NS.dc))

        if dc.publisher:
            self.metadata.append(dcterms.publisher(dc.publisher))
        if dc.rights:
            self.metadata.append(dcterms.rights(dc.rights))

        self.metadata.append(dcterms.identifier(dc.opf_identifier, {'id': 'id'})) 

        for count, author in enumerate(dc.authors):
            pretty_name = dc.make_pretty_name(author.name)
            if author.marcrel in {'aut', 'cre'}:
                self.metadata.append(dcterms.creator(pretty_name, {'id': f'author_{count}' }))
            else:
                self.metadata.append(dcterms.contributor(pretty_name, {'id': f'author_{count}' }))
            self.metadata.append(self.opf.meta(author.name,
                                 {'property':'file-as', 'refines': f'#author_{count}'}))
            self.metadata.append(self.opf.meta(author.marcrel,
                                 {'property':'role',
                                  'refines': f'#author_{count}',
                                  'scheme': 'marc:relators'}))


        # replace newlines with /
        title = re.sub(r'\s*[\r\n]+\s*', ' / ', dc.title)
        self.metadata.append(dcterms.title(title))

        for language in dc.languages:
            self.metadata.append(dcterms.language(language.id))

        for subject in dc.subjects:
            self.metadata.append(dcterms.subject(subject.subject))

        if dc.release_date != datetime.date.min:
            self.metadata.append(dcterms.date(
                dc.release_date.isoformat()))

        self.metadata.append(self.opf.meta(
            datetime.datetime.now(gg.UTC()).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            {'property': 'dcterms:modified'}))

        source = dc.source
        if hasattr(options.config, 'FILESDIR'):
            if source.startswith(options.config.FILESDIR):
                source = source[len(options.config.FILESDIR):]
                source = urllib.parse.urljoin(options.config.PGURL, source)

        self.metadata.append(dcterms.source(source))


    def add_coverpage(self, url, id_):
        """ Add a coverpage for ADE and Kindle.        """

        debug("Adding coverpage id: %s url: %s" % (id_, url))

        # register mobipocket style
        self.meta_item('cover', id_)



class Writer(writers.HTMLishWriter):
    """ Class that writes epub files. """


    @staticmethod
    def strip_pagenumbers(xhtml, strip_classes):
        """ Strip dp page numbers.

        Rationale: DP implements page numbers either with float or
        with absolute positioning. Float is not supported by Kindle.
        Absolute positioning is not allowed in epub.

        If we'd leave these in, they would show up as numbers in the
        middle of the text.

        To still keep links working, we replace all page number
        contraptions we can find with empty <a>'s.

        """

        # look for elements with a class that is in strip_classes

        for class_ in strip_classes:
            xp = "//xhtml:*[@class and contains(concat(' ', normalize-space(@class), ' '), ' %s ')]" % class_

            count = 0
            for elem in xpath(xhtml, xp):

                # save textual content
                text = gg.normalize(etree.tostring(elem,
                                                   method="text",
                                                   encoding=str,
                                                   with_tail=False))
                if len(text) > 10:
                    # safeguard against removing things that are not pagenumbers
                    continue

                if not text:
                    text = elem.get('title')

                # look for id anywhere inside element
                id_ = elem.xpath(".//@id")

                # transmogrify element into empty <a>
                tail = elem.tail
                elem.clear()
                elem.tag = NS.xhtml.a
                if id_:
                    # some blockheaded PPers include more than
                    # one page number in one span. take the last id
                    # because the others represent empty pages.
                    elem.set('id', id_[-1])

                if class_ in DP_PAGENUMBER_CLASSES:
                    # mark element as rewritten pagenumber. we
                    # actually don't use this class for styling
                    # because it is on an empty element
                    elem.set('class', 'x-ebookmaker-pageno')

                if text:
                    elem.set('title', text)
                elem.tail = tail
                count += 1

                # The OPS Spec 2.0 is very clear: "Reading Systems
                # must be XML processors as defined in XML 1.1."
                # Nevertheless many browser-plugin ebook readers use
                # the HTML parsers of the browser.  But HTML parsers
                # don't grok the minimized form of empty elements.
                #
                # This will force lxml to output the non-minimized form
                # of the element.
                elem.text = ''

            if count:
                warning("%d elements having class %s have been rewritten." %
                        (count, class_))


    @staticmethod
    def insert_root_div(xhtml):
        """ Insert a div immediately below body and move body contents
        into it.

        Rationale: We routinely turn page numbers into <a> elements.
        <a> elements are illegal as children of body, but are legal as
        children of <div>. See: `strip_page_numbers ()`

        """
        em = ElementMaker(namespace=str(NS.xhtml),
                          nsmap={None: str(NS.xhtml)})

        for body in xpath(xhtml, "/xhtml:body"):
            div = em.div
            div.set('id', 'pgepub-root-div')
            for child in body:
                div.append(child)
            body.append(div)


    # characters that are not widely supported
    translate_map = {
        0x2012: 0x2013,    # U+2012 FIGURE-DASH    -> U+2013 EN-DASH (ADE lacks this)
        0x2015: 0x2014,    # U+2015 HORIZONTAL BAR -> U+2014 EM-DASH (ADE lacks this)
    }


    @staticmethod
    def fix_incompatible_css(sheet):
        """ Strip CSS properties and values that are not EPUB compatible.
            Unpack "media handheld" rules
        """

        cssclass = re.compile(r'\.(-?[_a-zA-Z]+[_a-zA-Z0-9-]*)')
        html5tag = re.compile(r'(^|[ ,~>+])(figure|figcaption|footer|header|section)')

        for rule in sheet:
            if rule.type == rule.MEDIA_RULE:
                if rule.media.mediaText.find('handheld') > -1:
                    debug("Unpacking CSS @media handheld rule.")
                    rule.media.mediaText = 'all'
                    info("replacing  @media handheld rule with @media all")

            if rule.type == rule.STYLE_RULE:
                #change html5 tags to classes with the same name
                newrule = html5tag.sub(r'\1div.\2', rule.selectorList.selectorText)
                rule.selectorList.selectorText = newrule

                ruleclasses = list(cssclass.findall(rule.selectorList.selectorText))
                for p in list(rule.style):
                    if p.name == 'float' and "x-ebookmaker" not in ruleclasses:
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty('float')
                        rule.style.removeProperty('width')
                        rule.style.removeProperty('height')
                    elif p.name == 'position':
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty('position')
                        rule.style.removeProperty('left')
                        rule.style.removeProperty('right')
                        rule.style.removeProperty('top')
                        rule.style.removeProperty('bottom')
                    elif p.name in ('background-image', 'background-position',
                                    'background-attachment', 'background-repeat'):
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty(p.name)
                    elif 'border' not in p.name and 'px' in p.value:
                        debug("Dropping property with px value %s" % p.name)
                        rule.style.removeProperty(p.name)

        # debug("exit fix_incompatible_css")


    @staticmethod
    def get_classes_that_float(xhtml):
        """ Get a list of all classes that use float or position. """

        classes = set()
        regex = re.compile(r"\.(\w+)", re.ASCII)

        for style in xpath(xhtml, "//xhtml:style"):
            p = parsers.CSSParser.Parser()
            if style.text: # try to fix os-dependent empty style bug
                p.parse_string(style.text)

                for rule in p.sheet:
                    if rule.type == rule.STYLE_RULE:
                        for p in rule.style:
                            if p.name in ('float', 'position'):
                                classes.update(regex.findall(rule.selectorList.selectorText))
                                break

        return classes


    @staticmethod
    def strip_links(xhtml, manifest):
        """
        Strip all links to local resources that aren't in manifest or are images.

        This does not strip inline images, only standalone images that
        are targets of links. EPUB does not allow that.

        """

        for link in xpath(xhtml, '//xhtml:a[@href]'):
            href = urllib.parse.urldefrag(link.get('href'))[0]
            if href in manifest and not manifest[href].startswith('image'):
                continue
            if not href.startswith('file:'):
                continue
            debug("strip_links: Deleting <a> to file not in manifest: %s" % href)
            del link.attrib['href']


    @staticmethod
    def strip_ins(xhtml):
        """
        Strip all <ins> tags.

        There's a bug in the epub validator that trips on class and
        title attributes in <ins> elements.

        """
        for ins in xpath(xhtml, '//xhtml:ins'):
            ins.drop_tag()


    @staticmethod
    def strip_noepub(xhtml):
        """ Strip all <* class='x-ebookmaker-drop'> tags.

        As a way to tailor your html towards epub.

        """

        for e in xpath(xhtml, "//xhtml:*[contains (@class, 'x-ebookmaker-drop')]"):
            e.drop_tree()


    @staticmethod
    def single_child(e):
        """ Resturn true if node contains a single child element and nothing else. """
        p = e.getparent()
        return (len(p) == 1 and
                (p.text is None or p.text.isspace()) and
                (e.tail is None or e.tail.isspace()))


    @staticmethod
    def url2filename(url):
        """ Generate a filename for this url.
            - preserve original filename and fragment
            - map directory path to a cross platform filename string

        """
        if match_link_url.match(url):
            return url
        if url.startswith('file://'):
            url = url[7:]

        url_match = match_non_link.search(url)
        prefix = url[0:-len(url_match.group(0))]
        if prefix:
            prefix = abs(hash(prefix))
            return f'{prefix}_{url_match.group(0)}'
        return url


    @staticmethod
    def rescale_into(dimen, max_dimen):
        """ Scale down dimen to fit into max_dimen. """
        scale = 1.0
        if dimen[0]:
            scale = min(scale, max_dimen[0] / float(dimen[0]))
        if dimen[1]:
            scale = min(scale, max_dimen[1] / float(dimen[1]))

        if scale < 1.0:
            dimen = (int(dimen[0] * scale) if dimen[0] else None,
                     int(dimen[1] * scale) if dimen[1] else None)

        return dimen


    @staticmethod
    def fix_html_image_dimensions(xhtml):
        """
        Remove all width and height that is not specified in '%'.
        """

        for img in xpath(xhtml, '//xhtml:img'):
            a = img.attrib

            if '%' in a.get('width', '%') and '%' in a.get('height', '%'):
                continue

            if 'width' in a:
                del a['width']
            if 'height' in a:
                del a['height']


    def remove_coverpage(self, xhtml, url):
        """ Remove coverpage from flow.

        EPUB readers will display the coverpage from the manifest and
        if we don't remove it from flow it will be displayed twice.

        """
        for img in xpath(xhtml, "//xhtml:img[@src = $url and not(contains(@class, 'x-ebookmaker-important'))]", url=url):
            debug("remove_coverpage: dropping <img> %s from flow" % url)
            img.drop_tree()
            return # only the first one though


    def shipout(self, job, parserlist, ncx):
        """ Build the zip file. """

        try:
            ocf = OEBPSContainer(
                os.path.join(os.path.abspath(job.outputdir), job.outputfile),
                ('%d/' % options.ebook if options.ebook else None))

            opf = ContentOPF()

            opf.metadata_item(job.dc)

            # write out parserlist

            for p in parserlist:
                try:
                    ocf.add_bytes(self.url2filename(p.attribs.url), p.serialize(),
                                  p.mediatype())
                    if p.mediatype() == mt.xhtml:
                        opf.spine_item_from_parser(p)
                    else:
                        opf.manifest_item_from_parser(p)
                except Exception as what:
                    error("Could not process file %s: %s" % (p.attribs.url, what))

            # toc


            opf.toc_item('toc.xhtml')
            ocf.add_unicode('toc.xhtml', str(ncx))

            for p in parserlist:
                if 'icon' in p.attribs.rel:
                    cover_url = p.attribs.url
                    break
            else:
                # no items cover items. should not happen
                critical('no cover image available. turn on --generate_cover option')
                cover_url

            #register an ADE cover
            href = ocf.add_image_wrapper(Writer.url2filename(cover_url), 'Cover')
            opf.spine_item(href, mt.xhtml, id_='coverpage-wrapper', first=True)

            opf.rewrite_links(self.url2filename)
            ocf.add_unicode('content.opf', str(opf))

            ocf.commit()

        except Exception as what:
            exception("Error building Epub: %s" % what)
            ocf.rollback()
            raise


    def validate(self, job):
        """ Validate generated epub using external tools. """

        debug("Validating %s ..." % job.outputfile)

        filename = os.path.join(os.path.abspath(job.outputdir), job.outputfile)

        if hasattr(options.config,'EPUB_VALIDATOR'):
            validator = options.config.EPUB_VALIDATOR 
            info('validating...')
            params = validator.split() + [filename]
            checker = subprocess.Popen(params,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            (dummy_stdout, stderr) = checker.communicate()
            if stderr:
                error(stderr)
                return 1

        info("%s validates ok." % job.outputfile)
        return 0

    def build(self, job):
        """ Build epub """

        ncx = Toc(job.dc)
        parserlist = []
        css_count = 0

        # add CSS parser
        self.add_external_css(job.spider, None, PRIVATE_CSS, 'pgepub.css')

        try:
            chunker = HTMLChunker.HTMLChunker(version='epub3')
            coverpage_url = None

            # do images early as we need the new dimensions later
            for p in job.spider.parsers:
                if hasattr(p, 'resize_image'):
                    if 'icon' in p.attribs.rel:
                        np = p.resize_image(MAX_IMAGE_SIZE, MAX_COVER_DIMEN)
                        np.id = p.attribs.get('id', 'coverpage')
                        coverpage_url = p.attribs.url
                    elif 'linked_image' in p.attribs.rel:
                        np = p.resize_image(LINKED_IMAGE_SIZE, LINKED_IMAGE_DIMEN)
                        np.id = p.attribs.get('id')
                    else:
                        np = p.resize_image(MAX_IMAGE_SIZE, MAX_IMAGE_DIMEN)
                        np.id = p.attribs.get('id')
                    parserlist.append(np)

            for p in job.spider.parsers:
                if p.mediatype() in OPS_CONTENT_DOCUMENTS:
                    debug("URL: %s" % p.attribs.url)

                    if hasattr(p, 'rst2epub2'):
                        xhtml = p.rst2epub2(job)

                        if options.verbose >= 2:
                            # write html to disk for debugging
                            debugfilename = os.path.join(os.path.abspath(job.outputdir),
                                                         job.outputfile)
                            debugfilename = os.path.splitext(debugfilename)[0] + '.' + \
                                job.maintype + '.debug.html'
                            with open(debugfilename, 'wb') as fp:
                                fp.write(etree.tostring(xhtml, encoding='utf-8'))

                    else:
                        # make a copy so we can mess around
                        p.parse()
                        xhtml = copy.deepcopy(p.xhtml) if hasattr(p, 'xhtml') else None
                    if xhtml is not None:
                        
                        HTMLWriter.Writer.xhtml_to_html(xhtml)

                        # build up TOC
                        # has side effects on xhtml
                        ncx.toc += p.make_toc(xhtml)

                        # allows authors to customize css for epub
                        self.add_body_class(xhtml, 'x-ebookmaker')

                        self.insert_root_div(xhtml)

                        # strip all links to items not in manifest
                        p.strip_links(xhtml, job.spider.dict_urls_mediatypes())
                        self.strip_links(xhtml, job.spider.dict_urls_mediatypes())

                        self.strip_noepub(xhtml)

                        self.fix_html_image_dimensions(xhtml)
                        if coverpage_url and not hasattr(p.attribs, 'nonlinear'):
                            self.remove_coverpage(xhtml, coverpage_url)

                        # externalize and fix CSS
                        for style in xpath(xhtml, '//xhtml:style'):
                            self.add_external_css(
                                job.spider, xhtml, style.text, "%d.css" % css_count)
                            css_count += 1
                            style.drop_tree()

                        self.add_external_css(job.spider, xhtml, None, 'pgepub.css')

                        self.add_meta_generator(xhtml)

                        debug("Splitting %s ..." % p.attribs.url)
                        chunker.next_id = 0
                        chunker.split(xhtml, p.attribs)
                    else:
                        # parsing xml worked, but it isn't xhtml. so we need to reset mediatype
                        # to something that isn't recognized as content
                        p.attribs.mediatype = parsers.ParserAttributes.HeaderElement('text/xml')
            for p in job.spider.parsers:
                if str(p.attribs.mediatype) == 'text/css':
                    p.parse()
                if hasattr(p, 'sheet') and p.sheet:
                    self.fix_incompatible_css(p.sheet)
                    if job.subtype == '.noimages':
                        p.strip_images()
                    p.rewrite_links(self.url2filename)
                    parserlist.append(p)
                if str(p.attribs.mediatype) in OPS_FONT_TYPES:
                    warning('font file embedded: %s ;  check its license!', p.attribs.url)
                    parserlist.append(p)

            # after splitting html into chunks we have to rewrite all
            # internal links in HTML
            chunker.rewrite_internal_links()
            # also in the TOC
            if not ncx.toc:
                ncx.toc.append([job.spider.parsers[0].attribs.url, 'Start', 1])
            chunker.rewrite_internal_links_toc(ncx.toc)

            # make absolute links zip-filename-compatible
            chunker.rewrite_links(self.url2filename)
            ncx.rewrite_links(self.url2filename)

            # Do away with the chunker and copy all chunks into new parsers.
            # These are fake parsers that never actually parsed anything,
            # we just use them to just hold our data.
            for chunk, attribs in chunker.chunks:
                p = ParserFactory.ParserFactory.get(attribs)
                p.xhtml = chunk
                parserlist.append(p)

            self.shipout(job, parserlist, ncx)

        except Exception as what:
            exception("Error building Epub: %s" % what)
            raise

        self.writestr(i, etree.tostring(
            container, encoding='utf-8', xml_declaration=True, pretty_print=True))


    def add_image_wrapper(self, img_url, img_title):
        """ Add a HTML file wrapping img_url. """
        img_title = quoteattr(img_title)
        filename = 'wrap%04d.xhtml' % self.wrappers
        self.wrappers += 1
        self.add_bytes(filename,
                       parsers.IMAGE_WRAPPER.format(src=img_url,
                                                    title=img_title,
                                                    backlink="",
                                                    doctype=gg.HTML5_DOCTYPE),
                       mt.xhtml)
        return filename



class OutlineFixer(object):
    """ Class that fixes outline levels. """

    def __init__(self):
        self.stack = [(0, 0),]
        self.last = 0

    def level(self, in_level):
        if in_level < 1:
            return in_level
        (promotion, from_level) = self.stack[-1]
        if in_level > self.last + 1:
            # needs promotion
            more_promotion = in_level - self.last - 1
            new_promotion = promotion + more_promotion
            self.last = in_level
            self.stack.append((new_promotion, in_level))
            return in_level - new_promotion

        if in_level < from_level:
            # close out promotion
            self.last = from_level - promotion - 1
            self.stack.pop()
            return self.level(in_level)

        self.last = in_level
        return in_level - promotion


class Toc(object):
    """ Class that builds toc.xhtml. derived from EpubWriter.TocNCX"""

    def __init__(self, dc):
        self.toc = []
        self.dc = dc
        self.seen_urls = {}
        self.elementmaker = ElementMaker(namespace=str(NS.xhtml),
                                nsmap={None: str(NS.xhtml)})


    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        """ Serialize toc.em as unicode string. """
        em = self.elementmaker
        tocdepth = 1

        if self.toc:
            # normalize toc so that it starts with an h1 and doesn't jump down more than one
            # level at a time
            fixer = OutlineFixer()
            for t in self.toc:
                t[2] = fixer.level(t[2])

            # flatten toc if it contains only one top-level entry
            top_level_entries = sum(t[2] == 1 for t in self.toc)
            if top_level_entries < 2:
                for t in self.toc:
                    if t[2] != -1:
                        t[2] = max(1, t[2] - 1)

            tocdepth = max(t[2] for t in self.toc)

        doc_title = em.title(self.dc.title)
        head = em.head(
            doc_title,
            em.meta(name='dtb:uid', content=self.dc.opf_identifier),
            em.meta(name='dtb:depth', content=str(tocdepth)),
            em.meta(name='dtb:generator', content=GENERATOR % VERSION),
            em.meta(name='dtb:totalPageCount', content='0'),
            em.meta(name='dtb:maxPageNumber', content='0'))

        body = em.body(**{EPUB_TYPE: 'frontmatter'})

        self.seen_urls = {}
        has_pages = False
        for url, dummy_title, depth in self.toc:
            # navPoints and pageTargets referencing the same element
            # must have the same playOrder
            if url not in self.seen_urls:
                self.seen_urls[url] = str(len(self.seen_urls) + 1)
            if depth == -1:
                has_pages = True

        params = {NS.xml.lang: self.dc.languages[0].id} if self.dc.languages else {}

        body.append(self._make_navmap(self.toc))
        ncx = em.html(
            head,
            body,
            **params
        )

        if has_pages:
            ncx.append(self._make_pagelist(self.toc))

        # Ugly workaround for error: "Serialisation to unicode must not
        # request an XML declaration"

        toc_ncx = "%s\n\n%s" % (gg.XML_DECLARATION,
            etree.tostring(ncx, doctype=None, encoding=str, pretty_print=True)
        )

        if options.verbose >= 3:
            debug(toc_ncx)
        return toc_ncx


    def rewrite_links(self, f):
        """ Rewrite all links f(). """
        for entry in self.toc:
            entry[0] = f(entry[0])


    def _make_navmap(self, toc):
        """ Build the toc. """
        em = self.elementmaker

        root = em.nav(**{EPUB_TYPE: 'toc'})
        toctop = em.ol()
        root.append(toctop)

        count = 0
        prev_depth = 1
        current_ol = toctop
        for url, title, depth in toc:
            if depth < 0:
                continue
            count += 1
            toc_item = em.a(title, **{'href': url, 'id': "np-%d" % count})
            if depth > prev_depth:
                while depth > prev_depth:
                    for el in reversed(current_ol):
                        li = el
                        break
                    else:
                        li = em.li()
                    new_ol = em.ol()
                    li.append(new_ol)
                    prev_depth += 1
                    current_ol.append(li)
                    current_ol = new_ol
            else:
                while depth < prev_depth:
                    current_ol = current_ol.getparent().getparent()
                    prev_depth -= 1
            li = em.li(toc_item)
            current_ol.append(li)
                               
        return root


    def _make_pagelist(self, toc):
        """ Build the page list. """
        em = self.elementmaker
        root = em.nav(**{EPUB_TYPE: 'landmarks'})
        pagelist_top = em.ol(**{'id': 'pages', 'class': 'pagelist'})
        root.append(pagelist_top)

        for url, pagename, depth in toc:
            if depth == -1:
                toc_item = em.a(pagename, **{
                    'href': url, 
                    'id': "pt-%d" % len(pagelist_top),
                    'value': str(len(pagelist_top)), 
                    EPUB_TYPE: 'normal' if re.search('[0-9]', pagename) else 'frontmatter',
                })
                pagelist_top.append(em.li(toc_item))

        return root


class ContentOPF(object):
    """ Class that builds content.opf metadata. """

    def __init__(self):
        self.nsmap = gg.build_nsmap('opf dc dcterms xsi')

        # FIXME: remove this when lxml is fixed
        # workaround for lxml fat-fingering the default attribute namespaces
        self.nsmap[None] = str(NS.opf) + 'lxml-bug-workaround'

        self.opf = ElementMaker(namespace=self.nsmap[None], nsmap=self.nsmap)

        self.metadata = self.opf.metadata()
        self.manifest = self.opf.manifest()
        self.spine = self.opf.spine()
        self.item_id = 0


    def __str__(self):
        return self.__unicode__()


    def __unicode__(self):
        """ Serialize content.opf as unicode string. """

        assert len(self.manifest) > 0, 'No manifest item in content.opf.'
        assert len(self.spine) > 0, 'No spine item in content.opf.'

        package = self.opf.package(
            **{'version': '3.0', 'unique-identifier': 'id'}) # FIXME add version to instance
        package.append(self.metadata)
        package.append(self.manifest)
        package.append(self.spine)

        content_opf = "%s\n\n%s" % (gg.XML_DECLARATION,
                                    etree.tostring(package,
                                                   encoding=str,
                                                   pretty_print=True))

        # FIXME: remove this when lxml is fixed
        # now merge xmlns:opf and xmlns:
        content_opf = content_opf.replace('lxml-bug-workaround', '')

        if options.verbose >= 3:
            debug(content_opf)
        return content_opf


    def rewrite_links(self, f):
        """ Rewrite all links through f(). """
        for item in self.manifest:
            if item.get('href'):
                item.set('href', f(item.get('href')))


    def meta_item(self, name, content):
        """ Add item to metadata. """
        self.metadata.append(self.opf.meta(name=name, content=content))


    def manifest_item(self, url, mediatype, id_=None, prop=None):
        """ Add item to manifest. """
        def add_prop(prop, newprop):
            if prop:
                vals = prop.split()
            else:
                vals = []
            vals.append(newprop)
            prop = ' '.join(vals)

        if id_ is None or xpath(self.manifest, "//*[@id = '%s']" % id_):
            self.item_id += 1
            id_ = 'item%d' % self.item_id
        
        if prop == 'cover':
            self.add_coverpage(url, _id_)
        manifest_atts = {'href': url, 'id': id_, 'media-type': mediatype}
        if mediatype == 'image/svg+xml':
            prop = add_prop(prop, 'svg')
        if prop:
            manifest_atts['properties'] = prop
        self.manifest.append(
            self.opf.item(**manifest_atts))

        return id_


    def spine_item(self, url, mediatype, id_=None, first=False):
        """ Add item to spine and manifest. """

        if id_ and id_.startswith('pgepubid'):
            # this is an auto-generated header id, not human-readable and probably duplicated
            # make a new one
            id_ = None
        
        id_ = self.manifest_item(url, mediatype, id_)

        # HACK: ADE needs cover flow as first element
        # but we don't know if we have a native coverpage until the manifest is complete
        if first:
            self.spine.insert(
                0, self.opf.itemref(idref=id_))
        else:
            self.spine.append(
                self.opf.itemref(idref=id_))


    def manifest_item_from_parser(self, p):
        """ Add item to manifest from parser. """
        if hasattr(p.attribs, 'comment'):
            self.manifest.append(etree.Comment(p.attribs.comment))
        cover = 'cover-image' if 'icon' in p.attribs.rel else None
        return self.manifest_item(p.attribs.url, p.mediatype(), id_=p.attribs.id, prop=cover)


    def spine_item_from_parser(self, p):
        """ Add item to spine and manifest from parser. """
        if hasattr(p.attribs, 'comment'):
            self.manifest.append(etree.Comment(p.attribs.comment))
        return self.spine_item(p.attribs.url, p.mediatype(), p.attribs.id)


    def toc_item(self, url):
        """ Add TOC to manifest and spine. """
        self.manifest_item(url, mt.xhtml, id_='ncx', prop='nav')


    def pagemap_item(self, url):
        """ Add page-map to manifest and spine. """
        self.manifest_item(url, 'application/oebps-page-map+xml', 'map')
        self.spine.attrib['page-map'] = 'map'


    def metadata_item(self, dc):
        """ Build metadata from DublinCore struct.

        Example of metadata:

  <metadata xmlns:dcterms='http://purl.org/dc/terms/'
            xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
            xmlns:opf='http://www.idpf.org/2007/opf'>

    <dc:identifier id='id'>http://www.gutenberg.org/ebooks/29000</dc:identifier>
    <dc:creator id="author_0">Anthony Trollope</dc:creator>
    <meta property="file-as" refines="#author_0">Trollope, Anthony</meta>
    <meta property="role" refines="#author_0" scheme="marc:relators">aut</meta>
    <dc:title>The Macdermots of Ballycloran</dc:title>
    <dc:language>en</dc:language>
    <dc:subject>Domestic fiction</dc:subject>
    <dc:subject>Ireland -- Fiction</dc:subject>
    <dc:created>1890</dc:created>
    <dc:publisher>Project Gutenberg</dc:publisher>
    <dc:date opf:event='publication'>2009-05-31</dc:date>
    <dc:date opf:event='conversion'>2009-08-26T21:11:14Z</dc:date>
    <dc:rights>Public domain</dc:rights>
    <dc:source>29000-h.htm</dc:source>

    <meta name='cover' content='item0' />
  </metadata>
    """

        # OPF 2.0 v1.0 specifies to use the
        # Dublin Core Metadata Element Set, Version 1.1
        # http://dublincore.org/documents/2004/12/20/dces/

        dcterms = ElementMaker(nsmap=self.nsmap, namespace=str(NS.dc))

        if dc.publisher:
            self.metadata.append(dcterms.publisher(dc.publisher))
        if dc.rights:
            self.metadata.append(dcterms.rights(dc.rights))

        self.metadata.append(dcterms.identifier(dc.opf_identifier, {'id': 'id'})) 

        for count, author in enumerate(dc.authors):
            pretty_name = dc.make_pretty_name(author.name)
            if author.marcrel in {'aut', 'cre'}:
                self.metadata.append(dcterms.creator(pretty_name, {'id': f'author_{count}' }))
            else:
                self.metadata.append(dcterms.contributor(pretty_name, {'id': f'author_{count}' }))
            self.metadata.append(self.opf.meta(author.name,
                                 {'property':'file-as', 'refines': f'#author_{count}'}))
            self.metadata.append(self.opf.meta(author.marcrel,
                                 {'property':'role',
                                  'refines': f'#author_{count}',
                                  'scheme': 'marc:relators'}))


        # replace newlines with /
        title = re.sub(r'\s*[\r\n]+\s*', ' / ', dc.title)
        self.metadata.append(dcterms.title(title))

        for language in dc.languages:
            self.metadata.append(dcterms.language(language.id))

        for subject in dc.subjects:
            self.metadata.append(dcterms.subject(subject.subject))

        if dc.release_date != datetime.date.min:
            self.metadata.append(dcterms.date(
                dc.release_date.isoformat()))

        self.metadata.append(self.opf.meta(
            datetime.datetime.now(gg.UTC()).isoformat(timespec='seconds').replace('+00:00', 'Z'),
            {'property': 'dcterms:modified'}))

        source = dc.source
        if hasattr(options.config, 'FILESDIR'):
            if source.startswith(options.config.FILESDIR):
                source = source[len(options.config.FILESDIR):]
                source = urllib.parse.urljoin(options.config.PGURL, source)

        self.metadata.append(dcterms.source(source))


    def add_coverpage(self, url, id_):
        """ Add a coverpage for ADE and Kindle.        """

        debug("Adding coverpage id: %s url: %s" % (id_, url))

        # register mobipocket style
        self.meta_item('cover', id_)



class Writer(writers.HTMLishWriter):
    """ Class that writes epub files. """


    @staticmethod
    def strip_pagenumbers(xhtml, strip_classes):
        """ Strip dp page numbers.

        Rationale: DP implements page numbers either with float or
        with absolute positioning. Float is not supported by Kindle.
        Absolute positioning is not allowed in epub.

        If we'd leave these in, they would show up as numbers in the
        middle of the text.

        To still keep links working, we replace all page number
        contraptions we can find with empty <a>'s.

        """

        # look for elements with a class that is in strip_classes

        for class_ in strip_classes:
            xp = "//xhtml:*[@class and contains(concat(' ', normalize-space(@class), ' '), ' %s ')]" % class_

            count = 0
            for elem in xpath(xhtml, xp):

                # save textual content
                text = gg.normalize(etree.tostring(elem,
                                                   method="text",
                                                   encoding=str,
                                                   with_tail=False))
                if len(text) > 10:
                    # safeguard against removing things that are not pagenumbers
                    continue

                if not text:
                    text = elem.get('title')

                # look for id anywhere inside element
                id_ = elem.xpath(".//@id")

                # transmogrify element into empty <a>
                tail = elem.tail
                elem.clear()
                elem.tag = NS.xhtml.a
                if id_:
                    # some blockheaded PPers include more than
                    # one page number in one span. take the last id
                    # because the others represent empty pages.
                    elem.set('id', id_[-1])

                if class_ in DP_PAGENUMBER_CLASSES:
                    # mark element as rewritten pagenumber. we
                    # actually don't use this class for styling
                    # because it is on an empty element
                    elem.set('class', 'x-ebookmaker-pageno')

                if text:
                    elem.set('title', text)
                elem.tail = tail
                count += 1

                # The OPS Spec 2.0 is very clear: "Reading Systems
                # must be XML processors as defined in XML 1.1."
                # Nevertheless many browser-plugin ebook readers use
                # the HTML parsers of the browser.  But HTML parsers
                # don't grok the minimized form of empty elements.
                #
                # This will force lxml to output the non-minimized form
                # of the element.
                elem.text = ''

            if count:
                warning("%d elements having class %s have been rewritten." %
                        (count, class_))


    @staticmethod
    def insert_root_div(xhtml):
        """ Insert a div immediately below body and move body contents
        into it.

        Rationale: We routinely turn page numbers into <a> elements.
        <a> elements are illegal as children of body, but are legal as
        children of <div>. See: `strip_page_numbers ()`

        """
        em = ElementMaker(namespace=str(NS.xhtml),
                          nsmap={None: str(NS.xhtml)})

        for body in xpath(xhtml, "/xhtml:body"):
            div = em.div
            div.set('id', 'pgepub-root-div')
            for child in body:
                div.append(child)
            body.append(div)


    # characters that are not widely supported
    translate_map = {
        0x2012: 0x2013,    # U+2012 FIGURE-DASH    -> U+2013 EN-DASH (ADE lacks this)
        0x2015: 0x2014,    # U+2015 HORIZONTAL BAR -> U+2014 EM-DASH (ADE lacks this)
    }


    @staticmethod
    def fix_incompatible_css(sheet):
        """ Strip CSS properties and values that are not EPUB compatible.
            Unpack "media handheld" rules
        """

        cssclass = re.compile(r'\.(-?[_a-zA-Z]+[_a-zA-Z0-9-]*)')
        html5tag = re.compile(r'(^|[ ,~>+])(figure|figcaption|footer|header|section)')

        for rule in sheet:
            if rule.type == rule.MEDIA_RULE:
                if rule.media.mediaText.find('handheld') > -1:
                    debug("Unpacking CSS @media handheld rule.")
                    rule.media.mediaText = 'all'
                    info("replacing  @media handheld rule with @media all")

            if rule.type == rule.STYLE_RULE:
                #change html5 tags to classes with the same name
                newrule = html5tag.sub(r'\1div.\2', rule.selectorList.selectorText)
                rule.selectorList.selectorText = newrule

                ruleclasses = list(cssclass.findall(rule.selectorList.selectorText))
                for p in list(rule.style):
                    if p.name == 'float' and "x-ebookmaker" not in ruleclasses:
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty('float')
                        rule.style.removeProperty('width')
                        rule.style.removeProperty('height')
                    elif p.name == 'position':
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty('position')
                        rule.style.removeProperty('left')
                        rule.style.removeProperty('right')
                        rule.style.removeProperty('top')
                        rule.style.removeProperty('bottom')
                    elif p.name in ('background-image', 'background-position',
                                    'background-attachment', 'background-repeat'):
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty(p.name)
                    elif 'border' not in p.name and 'px' in p.value:
                        debug("Dropping property with px value %s" % p.name)
                        rule.style.removeProperty(p.name)

        # debug("exit fix_incompatible_css")


    @staticmethod
    def get_classes_that_float(xhtml):
        """ Get a list of all classes that use float or position. """

        classes = set()
        regex = re.compile(r"\.(\w+)", re.ASCII)

        for style in xpath(xhtml, "//xhtml:style"):
            p = parsers.CSSParser.Parser()
            if style.text: # try to fix os-dependent empty style bug
                p.parse_string(style.text)

                for rule in p.sheet:
                    if rule.type == rule.STYLE_RULE:
                        for p in rule.style:
                            if p.name in ('float', 'position'):
                                classes.update(regex.findall(rule.selectorList.selectorText))
                                break

        return classes


    @staticmethod
    def strip_links(xhtml, manifest):
        """
        Strip all links to local resources that aren't in manifest or are images.

        This does not strip inline images, only standalone images that
        are targets of links. EPUB does not allow that.

        """

        for link in xpath(xhtml, '//xhtml:a[@href]'):
            href = urllib.parse.urldefrag(link.get('href'))[0]
            if href in manifest and not manifest[href].startswith('image'):
                continue
            if not href.startswith('file:'):
                continue
            debug("strip_links: Deleting <a> to file not in manifest: %s" % href)
            del link.attrib['href']


    @staticmethod
    def strip_ins(xhtml):
        """
        Strip all <ins> tags.

        There's a bug in the epub validator that trips on class and
        title attributes in <ins> elements.

        """
        for ins in xpath(xhtml, '//xhtml:ins'):
            ins.drop_tag()


    @staticmethod
    def strip_noepub(xhtml):
        """ Strip all <* class='x-ebookmaker-drop'> tags.

        As a way to tailor your html towards epub.

        """

        for e in xpath(xhtml, "//xhtml:*[contains (@class, 'x-ebookmaker-drop')]"):
            e.drop_tree()


    @staticmethod
    def single_child(e):
        """ Resturn true if node contains a single child element and nothing else. """
        p = e.getparent()
        return (len(p) == 1 and
                (p.text is None or p.text.isspace()) and
                (e.tail is None or e.tail.isspace()))


    @staticmethod
    def url2filename(url):
        """ Generate a filename for this url.
            - preserve original filename and fragment
            - map directory path to a cross platform filename string

        """
        if match_link_url.match(url):
            return url
        if url.startswith('file://'):
            url = url[7:]

        url_match = match_non_link.search(url)
        prefix = url[0:-len(url_match.group(0))]
        if prefix:
            prefix = abs(hash(prefix))
            return f'{prefix}_{url_match.group(0)}'
        return url


    @staticmethod
    def rescale_into(dimen, max_dimen):
        """ Scale down dimen to fit into max_dimen. """
        scale = 1.0
        if dimen[0]:
            scale = min(scale, max_dimen[0] / float(dimen[0]))
        if dimen[1]:
            scale = min(scale, max_dimen[1] / float(dimen[1]))

        if scale < 1.0:
            dimen = (int(dimen[0] * scale) if dimen[0] else None,
                     int(dimen[1] * scale) if dimen[1] else None)

        return dimen


    @staticmethod
    def fix_html_image_dimensions(xhtml):
        """
        Remove all width and height that is not specified in '%'.
        """

        for img in xpath(xhtml, '//xhtml:img'):
            a = img.attrib

            if '%' in a.get('width', '%') and '%' in a.get('height', '%'):
                continue

            if 'width' in a:
                del a['width']
            if 'height' in a:
                del a['height']


    def remove_coverpage(self, xhtml, url):
        """ Remove coverpage from flow.

        EPUB readers will display the coverpage from the manifest and
        if we don't remove it from flow it will be displayed twice.

        """
        for img in xpath(xhtml, "//xhtml:img[@src = $url and not(contains(@class, 'x-ebookmaker-important'))]", url=url):
            debug("remove_coverpage: dropping <img> %s from flow" % url)
            img.drop_tree()
            return # only the first one though


    def shipout(self, job, parserlist, ncx):
        """ Build the zip file. """

        try:
            ocf = OEBPSContainer(
                os.path.join(os.path.abspath(job.outputdir), job.outputfile),
                ('%d/' % options.ebook if options.ebook else None))

            opf = ContentOPF()

            opf.metadata_item(job.dc)

            # write out parserlist

            for p in parserlist:
                try:
                    ocf.add_bytes(self.url2filename(p.attribs.url), p.serialize(),
                                  p.mediatype())
                    if p.mediatype() == mt.xhtml:
                        opf.spine_item_from_parser(p)
                    else:
                        opf.manifest_item_from_parser(p)
                except Exception as what:
                    error("Could not process file %s: %s" % (p.attribs.url, what))

            # toc


            opf.toc_item('toc.xhtml')
            ocf.add_unicode('toc.xhtml', str(ncx))

            for p in parserlist:
                if 'icon' in p.attribs.rel:
                    cover_url = p.attribs.url
                    break
            else:
                # no items cover items. should not happen
                critical('no cover image available. turn on --generate_cover option')
                cover_url

            #register an ADE cover
            href = ocf.add_image_wrapper(Writer.url2filename(cover_url), 'Cover')
            opf.spine_item(href, mt.xhtml, id_='coverpage-wrapper', first=True)

            opf.rewrite_links(self.url2filename)
            ocf.add_unicode('content.opf', str(opf))

            ocf.commit()

        except Exception as what:
            exception("Error building Epub: %s" % what)
            ocf.rollback()
            raise


    def validate(self, job):
        """ Validate generated epub using external tools. """

        debug("Validating %s ..." % job.outputfile)

        filename = os.path.join(os.path.abspath(job.outputdir), job.outputfile)

        if hasattr(options.config,'EPUB_VALIDATOR'):
            validator = options.config.EPUB_VALIDATOR 
            info('validating...')
            params = validator.split() + [filename]
            checker = subprocess.Popen(params,
                                       stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)

            (dummy_stdout, stderr) = checker.communicate()
            if stderr:
                error(stderr)
                return 1

        info("%s validates ok." % job.outputfile)
        return 0

    def build(self, job):
        """ Build epub """

        ncx = Toc(job.dc)
        parserlist = []
        css_count = 0

        # add CSS parser
        self.add_external_css(job.spider, None, PRIVATE_CSS, 'pgepub.css')

        try:
            chunker = HTMLChunker.HTMLChunker(version='epub3')
            coverpage_url = None

            # do images early as we need the new dimensions later
            for p in job.spider.parsers:
                if hasattr(p, 'resize_image'):
                    if 'icon' in p.attribs.rel:
                        np = p.resize_image(MAX_IMAGE_SIZE, MAX_COVER_DIMEN)
                        np.id = p.attribs.get('id', 'coverpage')
                        coverpage_url = p.attribs.url
                    elif 'linked_image' in p.attribs.rel:
                        np = p.resize_image(LINKED_IMAGE_SIZE, LINKED_IMAGE_DIMEN)
                        np.id = p.attribs.get('id')
                    else:
                        np = p.resize_image(MAX_IMAGE_SIZE, MAX_IMAGE_DIMEN)
                        np.id = p.attribs.get('id')
                    parserlist.append(np)

            for p in job.spider.parsers:
                if p.mediatype() in OPS_CONTENT_DOCUMENTS:
                    debug("URL: %s" % p.attribs.url)

                    if hasattr(p, 'rst2epub2'):
                        xhtml = p.rst2epub2(job)

                        if options.verbose >= 2:
                            # write html to disk for debugging
                            debugfilename = os.path.join(os.path.abspath(job.outputdir),
                                                         job.outputfile)
                            debugfilename = os.path.splitext(debugfilename)[0] + '.' + \
                                job.maintype + '.debug.html'
                            with open(debugfilename, 'wb') as fp:
                                fp.write(etree.tostring(xhtml, encoding='utf-8'))

                    else:
                        # make a copy so we can mess around
                        p.parse()
                        xhtml = copy.deepcopy(p.xhtml) if hasattr(p, 'xhtml') else None
                    if xhtml is not None:
                        
                        HTMLWriter.Writer.xhtml_to_html(xhtml)

                        # build up TOC
                        # has side effects on xhtml
                        ncx.toc += p.make_toc(xhtml)

                        # allows authors to customize css for epub
                        self.add_body_class(xhtml, 'x-ebookmaker')

                        self.insert_root_div(xhtml)

                        # strip all links to items not in manifest
                        p.strip_links(xhtml, job.spider.dict_urls_mediatypes())
                        self.strip_links(xhtml, job.spider.dict_urls_mediatypes())

                        self.strip_noepub(xhtml)

                        self.fix_html_image_dimensions(xhtml)
                        if coverpage_url and not hasattr(p.attribs, 'nonlinear'):
                            self.remove_coverpage(xhtml, coverpage_url)

                        # externalize and fix CSS
                        for style in xpath(xhtml, '//xhtml:style'):
                            self.add_external_css(
                                job.spider, xhtml, style.text, "%d.css" % css_count)
                            css_count += 1
                            style.drop_tree()

                        self.add_external_css(job.spider, xhtml, None, 'pgepub.css')

                        self.add_meta_generator(xhtml)

                        debug("Splitting %s ..." % p.attribs.url)
                        chunker.next_id = 0
                        chunker.split(xhtml, p.attribs)
                    else:
                        # parsing xml worked, but it isn't xhtml. so we need to reset mediatype
                        # to something that isn't recognized as content
                        p.attribs.mediatype = parsers.ParserAttributes.HeaderElement('text/xml')
            for p in job.spider.parsers:
                if str(p.attribs.mediatype) == 'text/css':
                    p.parse()
                if hasattr(p, 'sheet') and p.sheet:
                    self.fix_incompatible_css(p.sheet)
                    if job.subtype == '.noimages':
                        p.strip_images()
                    p.rewrite_links(self.url2filename)
                    parserlist.append(p)
                if str(p.attribs.mediatype) in OPS_FONT_TYPES:
                    warning('font file embedded: %s ;  check its license!', p.attribs.url)
                    parserlist.append(p)

            # after splitting html into chunks we have to rewrite all
            # internal links in HTML
            chunker.rewrite_internal_links()
            # also in the TOC
            if not ncx.toc:
                ncx.toc.append([job.spider.parsers[0].attribs.url, 'Start', 1])
            chunker.rewrite_internal_links_toc(ncx.toc)

            # make absolute links zip-filename-compatible
            chunker.rewrite_links(self.url2filename)
            ncx.rewrite_links(self.url2filename)

            # Do away with the chunker and copy all chunks into new parsers.
            # These are fake parsers that never actually parsed anything,
            # we just use them to just hold our data.
            for chunk, attribs in chunker.chunks:
                p = ParserFactory.ParserFactory.get(attribs)
                p.xhtml = chunk
                parserlist.append(p)

            self.shipout(job, parserlist, ncx)

        except Exception as what:
            exception("Error building Epub: %s" % what)
            raise
