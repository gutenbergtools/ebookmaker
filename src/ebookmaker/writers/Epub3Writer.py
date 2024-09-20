#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

Epub3Writer.py

Copyright 2022 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Writes an EPUB3 file.

"""

import re
import datetime
import os
import copy
from xml.sax.saxutils import quoteattr

from six.moves import urllib
from lxml import etree
from lxml.builder import ElementMaker

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import NS, xpath
from libgutenberg.Logger import critical, debug, error, exception, info, warning
from libgutenberg.MediaTypes import mediatypes as mt

from ebookmaker import parsers
from ebookmaker import ParserFactory
from ebookmaker import HTMLChunker
from ebookmaker.CommonCode import Options
from ebookmaker.Version import VERSION, GENERATOR

from .EpubWriter import (
    MAX_IMAGE_SIZE,
    MAX_COVER_DIMEN,
    MAX_IMAGE_DIMEN,
    LINKED_IMAGE_SIZE,
    LINKED_IMAGE_DIMEN,
    OPS_CONTENT_DOCUMENTS,
    OPS_FONT_TYPES,
    OutlineFixer,
    EPUB_TYPE,
    STRIP_CLASSES,
    TocNCX
)
HANDHELD_QUERY = 'max-width: 480px'
from . import EpubWriter, HTMLWriter

options = Options()


match_link_url = re.compile(r'^https?://', re.I)
match_non_link = re.compile(r'[a-zA-Z0-9_\-\.]*(#.*)?$')


PRIVATE_CSS = """\
@charset "utf-8";

body, body.tei.tei-text {
   color: black;
   background-color: white;
   width: auto;
   border: 0;
   padding: 0;
   }
div, p, pre, h1, h2, h3, h4, h5, h6 {
   margin-left: 0;
   margin-right: 0;
   display: block
   }
section.pgheader{
    page-break-after: always;
    }
section.pgfooter{
    page-break-before: always;
    }
div.pgebub-root-div {
   margin: 0
   }
h2 {
   page-break-before: always;
   padding-top: 1em
   }
div.figcenter span.caption {
   display: block;
   }
.pgmonospaced {
   font-family: monospace;
   font-size: 0.9em
   }
a.pgkilled {
   text-decoration: none;
   }
.x-ebookmaker-cover {
      background-color: grey;
      text-align: center;
      padding: 0pt;
      margin: 0pt;
      page-break-after: always;
      text-indent: 0;
      width: 100%;
      height: 100%;
    }

body.x-ebookmaker-coverpage {
    margin: 0;
    padding: 0;
}
"""

def alt_text_good(book_id):
    # stub implementation which allows listing books with good alt text in config file
    return str(book_id) in options.good_alt_text.split() if hasattr(
        options, 'good_alt_text') else False


class OEBPSContainer(EpubWriter.OEBPSContainer):
    """ Class representing an OEBPS Container. """


    def add_cover_wrapper(self, parser):
        """ Add a HTML file wrapping img_url. """
        filename = 'wrap%04d.xhtml' % self.wrappers
        self.wrappers += 1
        (cover_x, cover_y) = parser.get_image_dimen()
        wrapper = f'''
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="en">
  <head>
    <title>"Cover"</title>
    <link href="pgepub.css" rel="stylesheet"/>
  </head>
<body class="x-ebookmaker-coverpage">
  <div class="x-ebookmaker-cover">
    <svg xmlns="http://www.w3.org/2000/svg" height="100%" preserveAspectRatio="xMidYMid meet" version="1.1" viewBox="0 0 {cover_x} {cover_y}" width="100%" xmlns:xlink="http://www.w3.org/1999/xlink">
      <image width="{cover_x}" height="{cover_y}" xlink:href="{Writer.url2filename(parser.attribs.url)}"/>
    </svg>
  </div>
</body>
</html>        
'''
        self.add_bytes(filename, wrapper, mt.xhtml)
        return filename


class Toc(TocNCX):
    """ Class that builds toc.xhtml. derived from EpubWriter.TocNCX"""

    def __init__(self, dc):
        self.toc = []
        self.dc = dc
        self.seen_urls = {}
        self.elementmaker = ElementMaker(namespace=str(NS.xhtml),
                                         nsmap={None: str(NS.xhtml), 'epub': str(NS.epub)})



    def __unicode__(self):
        """ Serialize toc.em as unicode string. """
        em = self.elementmaker
        tocdepth = 1

        if self.toc:
            self.normalize_toc()

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
            body.append(self._make_pagelist(self.toc))

        # Ugly workaround for error: "Serialisation to unicode must not
        # request an XML declaration"

        toc_ncx = "%s\n\n%s" % (gg.XML_DECLARATION, etree.tostring(ncx,
                                                                   doctype=None,
                                                                   encoding=str,
                                                                   pretty_print=True))

        if options.verbose >= 3:
            debug(toc_ncx)
        return toc_ncx


    def _make_navmap(self, toc):
        """ Build the toc. """
        em = self.elementmaker

        root = em.nav(**{EPUB_TYPE: 'toc', 'role': 'doc-toc', 'aria-label': 'Table of Contents'})
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
        root = em.nav(**{EPUB_TYPE: 'landmarks', 'aria-label': 'Page List'})
        pagelist_top = em.ol(**{'id': 'pages', 'class': 'pagelist'})
        root.append(pagelist_top)

        for url, pagename, depth in toc:
            if depth == -1:
                toc_item = em.a(pagename, **{
                    'href': url,
                    'id': "pt-%d" % len(pagelist_top),
                    EPUB_TYPE: 'normal' if re.search('[0-9]', pagename) else 'frontmatter',
                })
                pagelist_top.append(em.li(toc_item))

        return root


class ContentOPF(object):
    """ Class that builds content.opf metadata. """

    def __init__(self):
        self.nsmap = gg.build_nsmap('opf dc dcterms xsi')
        self.lang = None

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
            **{'version': '3.0', 'unique-identifier': 'id', NS.xml.lang: self.lang})
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
            return prop

        if id_ is None or xpath(self.manifest, "//*[@id = '%s']" % id_):
            self.item_id += 1
            id_ = 'item%d' % self.item_id

        if prop == 'cover-image':
            self.add_coverpage(url, id_)
        manifest_atts = {'href': url, 'id': id_, 'media-type': mediatype}
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

        prop = 'svg' if id_ == 'coverpage-wrapper' else None
        id_ = self.manifest_item(url, mediatype, id_, prop=prop)

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

    def toc2_item(self, url):
        """ Add epub2 TOC to manifest and spine. """
        self.manifest_item(url, 'application/x-dtbncx+xml', id_='ncx2')
        self.spine.attrib['toc'] = 'ncx2'

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
                self.metadata.append(dcterms.creator(pretty_name, {'id': f'author_{count}'}))
            else:
                self.metadata.append(dcterms.contributor(pretty_name, {'id': f'author_{count}'}))
            self.metadata.append(self.opf.meta(author.name,
                                               {'property':'file-as',
                                                'refines': f'#author_{count}'}))
            self.metadata.append(self.opf.meta(author.marcrel,
                                               {'property':'role',
                                                'refines': f'#author_{count}',
                                                'scheme': 'marc:relators'}))


        # replace newlines with /
        title = re.sub(r'\s*[\r\n]+\s*', ' / ', dc.title)
        self.metadata.append(dcterms.title(title))

        for language in dc.languages:
            self.metadata.append(dcterms.language(language.id))
            if not self.lang:
                self.lang = language.id  # assume first lang is main lang
 
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
        
        # accessibility Metadata
        self.metadata.append(self.opf.meta('textual', {'property': 'schema:accessMode'}))
        self.metadata.append(self.opf.meta('readingOrder', {
            'property': 'schema:accessibilityFeature'}))
        self.metadata.append(self.opf.meta('none', {'property': 'schema:accessibilityHazard'}))
        if alt_text_good(dc.project_gutenberg_id):
            self.metadata.append(self.opf.meta('alternativeText', {
                'property': 'schema:accessibilityFeature'}))
            a11y_summary = 'This publication has complete alternative text descriptions.'
        else:
            a11y_summary = 'This publication may not have complete alternative text descriptions.'
        # TODO: reimplement this indicators when audio included
        self.metadata.append(self.opf.meta('textual,visual', {
            'property': 'schema:accessModeSufficient'}))
        self.metadata.append(self.opf.meta(a11y_summary, {
            'property': 'schema:accessibilitySummary'}))


    def add_coverpage(self, url, id_):
        """ Add a coverpage for ADE and Kindle.        """

        debug("Adding coverpage id: %s url: %s" % (id_, url))

        # register mobipocket style
        self.meta_item('cover', id_)



class Writer(EpubWriter.Writer):
    """ Class that writes epub files. """

    VALIDATOR = 'EPUB_VALIDATOR'

    def remove_coverpage(self, xhtml, url):
        """ Remove coverpage from flow.

        EPUB readers will display the coverpage from the manifest and
        if we don't remove it from flow it will be displayed twice.

        """
        for img in xpath(
                xhtml,
                "//xhtml:img[@src = $url and not(contains(@class, 'x-ebookmaker-important'))]",
                url=url):
            debug("remove_coverpage: dropping <img> %s from flow" % url)
            img.drop_tree()
            return # only the first one though

    @staticmethod
    def html_for_epub3(xhtml):
        """ Convert data-epub attribute to ebub attributes
        """
        for e in xpath(xhtml, "//@*[starts-with(name(), 'data-epub')]/.."):
            for key in e.attrib.keys():
                if key.startswith('data-epub-'):
                    val = e.attrib[key]
                    del e.attrib[key]
                    new_key = getattr(NS.epub, key[10:])
                    e.attrib[new_key] = val

    @staticmethod
    def fix_incompatible_css(sheet):
        """ Strip CSS properties and values that are not EPUB3 compatible.
            Remove "media handheld" rules
        """
        cssclass = re.compile(r'\.(-?[_a-zA-Z]+[_a-zA-Z0-9-]*)')
        for rule in sheet:
            if rule.type == rule.MEDIA_RULE:
                for medium in rule.media:
                    info(f'{medium}')
                    if medium == 'handheld':
                        rule.media.deleteMedium(medium)
                        rule.media.appendMedium(HANDHELD_QUERY)

            if rule.type == rule.STYLE_RULE:
                ruleclasses = list(cssclass.findall(rule.selectorList.selectorText))
                for p in list(rule.style):
                    # Apple books only allows position property in fixed-layout books
                    if p.name == 'position':
                        debug("Dropping property %s" % p.name)
                        rule.style.removeProperty('position')
                        rule.style.removeProperty('left')
                        rule.style.removeProperty('right')
                        rule.style.removeProperty('top')
                        rule.style.removeProperty('bottom')

    def shipout(self, job, parserlist, ncx, ncx2):
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
            
            opf.toc2_item('toc.ncx')
            ocf.add_unicode('toc.ncx', str(ncx2))


            for p in parserlist:
                if 'icon' in p.attribs.rel:
                    cover_parser = p
                    break
            else:
                # no  cover items. should not happen
                critical('no cover image available. turn on --generate_cover option')
                cover_parser = None

            #register an ADE cover
            if cover_parser:
                href = ocf.add_cover_wrapper(cover_parser)
                opf.spine_item(href, mt.xhtml, id_='coverpage-wrapper', first=True)
                

            opf.rewrite_links(self.url2filename)
            ocf.add_unicode('content.opf', str(opf))

            ocf.commit()

        except Exception as what:
            exception("Error building Epub: %s" % what)
            ocf.rollback()
            raise


    def build(self, job):
        """ Build epub """

        ncx = Toc(job.dc)
        ncx2 = TocNCX(job.dc)
        parserlist = []
        css_count = 0
        boilerplate_done = False
        idmap = {}

        # add CSS parsers
        self.add_external_css(job.spider, None, PRIVATE_CSS, 'pgepub.css')

        try:
            chunker = HTMLChunker.HTMLChunker(version='epub3')
            coverpage_url = None

            # do images early as we need the new dimensions later
            for p in job.spider.parsers:
                if hasattr(p, 'resize_image'):
                    unsized_url = p.attribs.url
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
                    if unsized_url != p.attribs.url:
                        idmap[unsized_url] = p.attribs.url
                    parserlist.append(np)

            for p in job.spider.parsers:
                if p.mediatype() in OPS_CONTENT_DOCUMENTS:
                    debug("URL: %s" % p.attribs.url)

                    if hasattr(p, 'rst2epub2'):
                        xhtml = p.rst2epub2(job)
                        xhtml = copy.deepcopy(xhtml)

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

                        # rewrite the changed image links
                        p.remap_links(idmap)

                        xhtml = copy.deepcopy(p.xhtml) if hasattr(p, 'xhtml') else None

                    if xhtml is not None:
                    
                        # can't have absolute positions in reflowable EPUB3
                        strip_classes = self.get_classes_with_prop(xhtml, props=('position'))                        
                        strip_classes = strip_classes.intersection(STRIP_CLASSES)
                        if strip_classes:
                            self.strip_pagenumbers(xhtml, strip_classes)

                        if not boilerplate_done:
                            HTMLWriter.Writer.replace_boilerplate(job, xhtml)
                            boilerplate_done = True
                        HTMLWriter.Writer.xhtml_to_html(xhtml)

                        self.html_for_epub3(xhtml)
                        xhtml.make_links_absolute(base_url=p.attribs.url)

                        # build up TOC
                        # has side effects on xhtml
                        ncx.toc += p.make_toc(xhtml)
                        ncx2.toc += p.make_toc(xhtml)

                        # allows authors to customize css for epub
                        self.add_body_class(xhtml, 'x-ebookmaker')
                        self.add_body_class(xhtml, 'x-ebookmaker-3')

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
            if not ncx2.toc:
                ncx2.toc.append([job.spider.parsers[0].attribs.url, 'Start', 1])
            chunker.rewrite_internal_links_toc(ncx.toc)
            chunker.rewrite_internal_links_toc(ncx2.toc)

            # make absolute links zip-filename-compatible
            chunker.rewrite_links(self.url2filename)
            ncx.rewrite_links(self.url2filename)
            ncx2.rewrite_links(self.url2filename)

            # Do away with the chunker and copy all chunks into new parsers.
            # These are fake parsers that never actually parsed anything,
            # we just use them to just hold our data.
            for chunk, attribs in chunker.chunks:
                p = ParserFactory.ParserFactory.get(attribs)
                p.xhtml = chunk
                parserlist.append(p)

            self.shipout(job, parserlist, ncx, ncx2)

        except Exception as what:
            exception("Error building Epub: %s" % what)
            raise
