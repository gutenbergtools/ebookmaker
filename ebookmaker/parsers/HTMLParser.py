#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

HTMLParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""
import os
import re
import subprocess
import sys
import unicodedata

from six.moves import urllib

import lxml.html
from lxml import etree

from bs4 import BeautifulSoup

from libgutenberg.GutenbergGlobals import NS, HTML5_DOCTYPE
from libgutenberg.Logger import critical, info, debug, warning, error
from libgutenberg.MediaTypes import mediatypes as mt

from ebookmaker import parsers
from ebookmaker.parsers import HTMLParserBase
from ebookmaker.CommonCode import Options
from ebookmaker.utils import (
    add_class, add_style, css_len, check_lang, gg, replace_elements,  xpath,
)

options = Options()

mediatypes = ('text/html', mt.xhtml)

RE_XMLDECL = re.compile(r'<\?xml[^?]+\?>\s*')

FONT_SIZES = {
    '1': 'xx-small',
    '2': 'x-small',
    '3': 'small',
    '4': 'medium',
    '5': 'large',
    '6': 'x-large',
    '7': 'xx-large',
    '+1': '110%',
    '-1': '90%',
    '+2': '125%',
    '-2': '75%',
}

LIST_STYLES ={
    '1': 'decimal',
    'i': 'lower-roman',
    'I': 'upper-roman',
    'a': 'lower-alpha',
    'A': 'upper-alpha',
}

REPLACE_ELEMENTS = {
    'applet': None,
    'script': None,
    'basefont': None,
    'object': 'div',
    'iframe': None,
    'isindex': None,
    'input': 'div',
    'legend': None,
    'fieldset': None,
    'font': 'span',
    'center': 'div',
    'blink': 'span'  
}

DEPRECATED = {
    'align': 'hr', # should translate this to margin settings
    'alink': 'body',
    'background': 'body',
    'bgcolor': 'body',
    'border': 'img ',
    'compact': '*',
    'hspace': '*',
    'link': 'body',
    'noshade': 'hr',
    'nowrap': '*',
    'start': 'ol',
    'text': 'body',
    'value': 'li',
    'version': 'html',
    'vlink': 'body',
    'vspace': '*',
}

ALLOWED_IN_BODY = {
    NS.xhtml.address, NS.xhtml.blockquote, f'{NS.xhtml.de}l', NS.xhtml.div, NS.xhtml.dl,
    NS.xhtml.h1, NS.xhtml.h2, NS.xhtml.h3, NS.xhtml.h4, NS.xhtml.h5, NS.xhtml.h6,
    NS.xhtml.hr, NS.xhtml.ins, NS.xhtml.noscript, NS.xhtml.ol, NS.xhtml.p, NS.xhtml.pre,     
    NS.xhtml.script, NS.xhtml.table, NS.xhtml.ul,
    NS.svg.svg,
}

REPLACEMENTS = [
    ('*', 'bgcolor', 'color', lambda x: x),
    ('br', 'clear', 'clear', lambda x: x),
    ('caption div h1 h2 h3 h4 h5 h5 p', 'align', 'text-align', lambda x: x),
    ('hr', 'width', 'width', css_len),
    ('hr', 'size', 'border', css_len),
    ('img table', 'align', 'float', lambda x: x),
    ('font', 'color', 'color', lambda x: x),
    ('font', 'face', 'font-family', lambda x: x),
    ('font', 'size', 'font-size', lambda x: FONT_SIZES.get(x.strip(), 'medium')),
    ('table td th', 'height', 'height', css_len),
    ('table td th pre', 'width', 'width', css_len),
    ('li ol ul', 'type', 'list-style-type', lambda x: LIST_STYLES.get(x.strip(), '')),
]

CSS_FOR_REPLACED = {
    'blink': "",
    'center': "",
    'font': "",
}


class Parser(HTMLParserBase):
    """ Parse a HTML Text

    and convert it to xhtml suitable for ePub packaging.

    """

    @staticmethod
    def _fix_id(id_):
        """ Fix more common mistakes in ids.

        xml:id cannot start with digit, very common in pg.

        """

        if not parsers.RE_XML_NAME.match(id_):
            id_ = 'id_' + id_

        # debug("_fix_id: id = %s" % id_)
        return id_


    def _fix_internal_frag(self, id_):
        """ Fix more common mistakes in ids. """

        # Non-ascii hrefs must be %-escaped, but id attributes must
        # not be %-escaped.  Some producers %-escape ids to make id
        # and href look the same.  But '%' is an invalid character in
        # xml ids.
        #
        # See HTML 4.01 spec section B.2.

        if '%' in id_:
            try:
                bytes_id = urllib.parse.unquote(id_.encode('us-ascii')) # undo the %-escaping
                try:
                    id_ = bytes_id.decode('utf-8')
                except UnicodeError:
                    doc_encoding = self.attribs.orig_mediatype.params.get('charset')
                    if doc_encoding:
                        id_ = bytes_id.decode(doc_encoding)
            except Exception:
                pass # too broken to fix

        # An xml:id cannot start with a digit, a very common mistake
        # in pg.

        if not parsers.RE_XML_NAME.match(id_):
            id_ = 'id_' + id_

        if not parsers.RE_XML_NAME.match(id_):
            # still invalid ... we tried
            return None

        # debug("_fix_internal_frag: frag = %s" % id_)
        return id_


    def _fix_anchors(self):
        """ Move name to id and fix hrefs and ids. """

        def ids_and_names(xhtml):
            """iterator that runs over id attributes and name attributes"""
            for node in xpath(xhtml, "//xhtml:*[@id]"):
                yield node
            for node in xpath(xhtml, "//xhtml:a[@name]"):
                yield node

        # move anchor name to id
        # 'id' values are more strict than 'name' values
        # try to fix ill-formed ids
        if self.xhtml is None:
            return
        seen_ids = set()

        for anchor in ids_and_names(self.xhtml):
            id_ = anchor.get('id') or anchor.get('name')

            if 'name' in anchor.attrib:
                del anchor.attrib['name']
            if 'id' in anchor.attrib:
                del anchor.attrib['id']
            if NS.xml.id in anchor.attrib:
                del anchor.attrib[NS.xml.id]

            id_ = self._fix_id(id_)

            if not parsers.RE_XML_NAME.match(id_):
                error("Dropping ill-formed id '%s' in %s" % (id_, self.attribs.url))
                continue

            # well-formed id
            if id_ in seen_ids:
                error("Dropping duplicate id '%s' in %s" % (id_, self.attribs.url))
                continue

            seen_ids.add(id_)
            anchor.set('id', id_)


        # try to fix bogus fragment ids
        # 1. fragments point to xml:id, so must be well-formed ids
        # 2. the ids they point to must exist

        for link in xpath(self.xhtml, "//xhtml:*[@href]"):
            href = link.get('href')
            hre, frag = urllib.parse.urldefrag(href)
            if frag:
                frag = self._fix_internal_frag(frag)

                if not frag:
                    # non-recoverable ill-formed frag
                    del link.attrib['href']
                    self.add_class(link, 'pgkilled')
                    error('Dropping ill-formed frag in %s' % href)
                    continue

                # well-formed frag
                if hre:
                    # we have url + frag
                    link.set('href', "%s#%s" % (hre, urllib.parse.quote(frag.encode('utf-8'))))
                    self.add_class(link, 'pgexternal')
                elif frag in seen_ids:
                    # we have only frag
                    link.set('href', "#%s" % urllib.parse.quote(frag.encode('utf-8')))
                    self.add_class(link, 'pginternal')
                else:
                    del link.attrib['href']
                    self.add_class(link, 'pgkilled')
                    error("Dropping frag to non-existing id in %s" % href)


    def enclose_text(self):
        """ same as setting enclose-text option on tidy; 
        ' enclose any text it finds in the body element within a <P> element. 
        This is useful when you want to take existing HTML and use it with a style sheet.'
        """
        for elem in self.xhtml.body:
            if elem.tag not in ALLOWED_IN_BODY:
                new_p = elem.makeelement(NS.xhtml.p)
                elem.addprevious(new_p)
                new_p.append(elem)
                
    def _to_xhtml11(self):
        """ Make vanilla xhtml more conform to xhtml 1.1 """

        # Change content-type meta to application/xhtml+xml.
        for meta in xpath(self.xhtml, "/xhtml:html/xhtml:head/xhtml:meta[@http-equiv]"):
            if meta.get('http-equiv').lower() == 'content-type':
                meta.getparent().remove(meta)

        # drop javascript

        for script in xpath(self.xhtml, "//xhtml:script"):
            script.drop_tree()

        # drop form

        for form in xpath(self.xhtml, "//xhtml:form"):
            form.drop_tree()

        # blockquotes

        for bq in xpath(self.xhtml, "//xhtml:blockquote"):
            # no naked text allowed in <blockquote>
            div = etree.Element(NS.xhtml.div)
            for child in bq:
                div.append(child)
            div.text = bq.text
            bq.text = None
            bq.append(div)
            # lxml.html.defs.block_tags

        # insert tbody

        for table in xpath(self.xhtml, "//xhtml:table[xhtml:tr]"):
            # no naked <tr> allowed in <table>
            tbody = etree.Element(NS.xhtml.tbody)
            for tr in table:
                if tr.tag == NS.xhtml.tr:
                    tbody.append(tr)
            table.append(tbody)

        # move lang to xml:lang

        for elem in xpath(self.xhtml, "//xhtml:*[@lang]"):
            # bug in lxml 2.2.2: sometimes deletes wrong element
            # so we delete both and reset the right one
            lang = elem.get('lang')
            try:
                del elem.attrib[NS.xml.lang]
            except KeyError:
                pass
            del elem.attrib['lang']
            elem.set(NS.xml.lang, lang)

        # strip deprecated attributes
        for (tags, attr, cssattr, val2css) in REPLACEMENTS:
            for tag in tags.split():
                for elem in xpath(self.xhtml, f"//xhtml:{tag}[@{attr}]"):
                    if elem.attrib[attr]:
                        val = elem.attrib[attr]
                    del elem.attrib[attr]
                    if cssattr:
                        add_style(elem, style=f'{cssattr}: {val2css(val)};')

        for a, t in DEPRECATED.items():
            for tag in t.split():
                for elem in xpath(self.xhtml, "//xhtml:%s[@%s]" % (tag, a)):
                    del elem.attrib[a]

        # strip empty class attributes

        for elem in xpath(self.xhtml,
                          "//xhtml:*[@class and normalize-space(@class) = '']"):
            del elem.attrib['class']

        # fix attribute values
        attrs_to_fix = [('align frame rules', lambda x: x.lower())]
        for attrs, fix in attrs_to_fix:
            for attr in attrs.split():
                for elem in xpath(self.xhtml, f"//xhtml:*[@{attr}]"):
                    elem.attrib[attr] = fix(elem.attrib[attr])

        # strip bogus header markup by Joe L.
        for elem in xpath(self.xhtml, "//xhtml:h1"):
            if elem.text and elem.text.startswith("The Project Gutenberg eBook"):
                elem.tag = NS.xhtml.p
        for elem in xpath(self.xhtml, "//xhtml:h3"):
            if elem.text and elem.text.startswith("E-text prepared by"):
                elem.tag = NS.xhtml.p

        # deprecated elements -  replace with <span/div class="xhtml_{tag name}">
        deprecated_used = replace_elements(self.xhtml, REPLACE_ELEMENTS)

        # enclose text the way tidy does
        self.enclose_text()
        
        ##### cleanup #######

        css_for_deprecated = ' '.join([CSS_FOR_REPLACED.get(tag, '') for tag in deprecated_used])
        if css_for_deprecated.strip():
            print(f'css_for_deprecated: {css_for_deprecated}')
            elem = etree.Element(NS.xhtml.style)
            elem.text = css_for_deprecated
            self.xhtml.find(NS.xhtml.head).insert(1, elem) # right after charset declaration


    def _make_coverpage_link(self, coverpage_url=None):
        """ Insert a <link rel="icon"> in the html head.

        First we determine the coverpage url.  In HTML we find the
        coverpage by appling these rules:

          0. the image specified by the --cover command-line option
          1. the image specified in <link rel='icon'> or <link rel='coverpage'>,
          2. the image with an id of 'coverpage' or
          3. the image with an url containing 'cover'
          4. the image with an url containing 'title'

        If one rule returns images we take the first one in document
        order, else we proceed with the next rule.
        """

        coverpages = xpath(self.xhtml, "//xhtml:link[@rel='icon' or @rel='coverpage']")
        cover_attrs = {'rel': 'icon', 'type': 'image/x-cover'}
        if coverpage_url:
            for coverpage in coverpages:
                coverpage.set('href', coverpage_url)
                coverpage.attrib.update(cover_attrs)
                debug("overrode link to coverpage with %s." % coverpage_url)
                
            else:
                for head in xpath(self.xhtml, "/xhtml:html/xhtml:head"):
                    head.append(parsers.em.link(rel='icon', href=coverpage_url, type='image/x-cover'))
                    debug("Inserted link to coverpage %s." % coverpage_url)
            return

        for coverpage in coverpages:
            if 'type' in coverpage.attrib and coverpage.attrib['type'] != 'image/x-cover':
                continue
            url = coverpage.get('href')
            debug("Found link to coverpage %s." % url)
            if coverpage.attrib['rel'] == 'coverpage':
                coverpage.attrib.update(cover_attrs)
            return   # already provided by user

        # look for a suitable candidate
        coverpages = xpath(self.xhtml, "//xhtml:img[@id='coverpage']")
        if not coverpages:
            coverpages = xpath(self.xhtml, "//xhtml:img[contains(@src, 'cover')]")
        if not coverpages:
            coverpages = xpath(self.xhtml, "//xhtml:img[contains(@src, 'title')]")

        for coverpage in coverpages:
            for head in xpath(self.xhtml, "/xhtml:html/xhtml:head"):
                url = coverpage.get('src')
                head.append(parsers.em.link(rel='icon', href=url, type='image/x-cover'))
                debug("Inserted link to coverpage %s." % url)


    def __parse(self, html):
        # remove xml decl and doctype, we will add the correct one before serializing
        # html = re.compile('^.*<html ', re.I | re.S).sub('<html ', html)

        re_xml_decl = re.compile(r'^.*?<\?xml.*?\?>', re.S)
        re_doctype = re.compile(r'<!DOCTYPE[^>]*>\s*', re.I)
        html = re_xml_decl.sub('', html)
        html = re_doctype.sub('<!DOCTYPE html >', html)

        try:
            return etree.fromstring(
                html,
                lxml.html.XHTMLParser(huge_tree=True),
                base_url=self.attribs.url)
        except etree.ParseError as what:
            # cannot try HTML parser because we depend on correct xhtml namespace
            m = re.search(r"Entity '([^']+)'", str(what))
            if m:
                warning("Missing entity: '%s'" % m.group(1))
            else:
                error("Failed to parse file because: %s" % what)
            m = re.search(r'line\s(\d+),', str(what))
            if m:
                lineno = int(m.group(1))
                if html:
                    error("Line %d: %s" % (lineno, html.splitlines()[lineno - 1]))
                else:
                    error("empty document")



    def pre_parse(self):
        """
        Pre-parse a html ebook.

        Does a full parse because a lightweight parse would be almost
        as much work.

        """

        # cache
        if self.xhtml is not None:
            return

        debug("HTMLParser.pre_parse() ...")

        try:
            soup = BeautifulSoup(self.bytes_content(), 'lxml')
        except:
            critical('failed to parse %s', self.attribs.url)
            return
        soup.html['xmlns'] = NS.xhtml
        html = str(soup)
        if not html:
            critical('no content in %s', self.attribs.url)
            return
            
        html = html.replace('&#13;', '&#10;')
        html = html.replace('&#xD;', '&#10;')
        if '\r' in html or '\u2028' in html:
            html = '\n'.join(html.splitlines())
        self.unicode_buffer = html

        self.xhtml = self.__parse(html)     # let exception bubble up

        self._fix_anchors() # needs relative paths

        self.xhtml.make_links_absolute(base_url=self.attribs.url)

        self._to_xhtml11()

        self._make_coverpage_link()

        debug("Done parsing %s", self.attribs.url)


    def parse(self):
        """ Fully parse a html ebook. """

        debug("HTMLParser.parse() ...")

        self.pre_parse()
