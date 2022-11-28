#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

HTMLWriter.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""


import copy
import os
from pathlib import Path
import re
from urllib.parse import urlparse, urljoin
import uuid

from lxml import etree


from libgutenberg.Logger import debug, exception, info, error, warning

from ebookmaker import writers
from ebookmaker.CommonCode import Options
from ebookmaker.parsers import webify_url
from ebookmaker.parsers.CSSParser import cssutils
from ebookmaker.utils import (
    add_class, add_style, css_len, check_lang, replace_elements, gg, xpath, NS
)
from ebookmaker.writers import HtmlTemplates
options = Options()
cssutils.ser.prefs.validOnly = True


CSS_FOR_REPLACED = {
    'big': ".xhtml_big {font-size: larger;}",
    'tt': ".xhtml_tt {font-family: monospace;}",
    # add some needed CSS3
    '*': '''
    .xhtml_center {text-align: center; display: block;}
    .xhtml_center table {
        display: table;
        text-align: left;
        margin-left: auto;
        margin-right: auto;
        }''',
}

## from https://hg.mozilla.org/mozilla-central/file/3fd770ef6a65/layout/style/html.css#l310

CSS_FOR_RULES = {
    'none': '''
.rules-none > tr > td, .rules-none > * > tr > td, .rules-none > tr > th,
.rules-none > * > tr > th, .rules-none > td, .rules-none > th {
border-width: thin;
border-style: none;}''',
    'all': '''
.rules-all > tr > td, .rules-all > * > tr > td, .rules-all > tr > th,
.rules-all > * > tr > th, .rules-all > td, .rules-all > th {
border-width: thin;
border-style: solid;}''',
    'cols': '''
.rules-cols > tr > td, .rules-cols > * > tr > td,
.rules-cols > tr > th, .rules-cols > * > tr > th {
border-left-width: thin;
border-right-width: thin;
border-left-style: solid;
border-right-style: solid;}''',
    'rows': '''
.rules-rows > tr, .rules-rows > * > tr {
border-top-width: thin;
border-bottom-width: thin;
border-top-style: solid;
border-bottom-style: solid;}''',
    'groups': '''
.rules-groups > tfoot, .rules-groups > thead, .rules-groups > tbody {
border-top-width: thin; border-bottom-width: thin;
border-top-style: solid; border-bottom-style: solid;}
.rules-groups > colgroup {
border-left-width: thin; border-right-width: thin;
border-left-style: solid; border-right-style: solid;}''',
}

CSS_FOR_FRAME = {
    'box': '.frame-box {border: thin outset;}',
    'void': '.frame-void {border-style: hidden;}',
    'above': 'frame-above {border-style: outset hidden hidden hidden;}',
    'below': 'frame-below {border-style: hidden hidden outset hidden;}',
    'lhs': '.frame-lhs {border-style: hidden hidden hidden outset;}',
    'rhs': '.frame-rhs {border-style: hidden outset hidden hidden;}',
    'hsides': '.frame-hsides {border-style: outset hidden;}',
    'vsides': '.frame-vsides {border-style: hidden outset;}',
    'border': 'frame-border {border-style: outset;}',
}
CSS_FOR_REPLACED.update(CSS_FOR_RULES)
CSS_FOR_REPLACED.update(CSS_FOR_FRAME)

REPLACE_ELEMENTS = {
    'big': 'span',
    'tt': 'span',
}

# replacing attributes with css in a style attribute
# (tag, attr, cssprop, val2css)
REPLACEMENTS = [
    ('tbody td tfoot th thead tr', 'align', 'text-align', lambda x: x),
    ('table td', 'background', '', ''),
    ('table', 'border', 'border-width', css_len),
    ('table td tr', 'bordercolor', 'border-color', lambda x: x),
    ('table', 'cellpadding', 'padding', css_len),
    ('table', 'cellspacing', 'border-spacing', css_len),
    ('col td th tr', 'valign', 'vertical-align', lambda x: x),
    ('tbody tfoot thead', 'valign', 'vertical-align', lambda x: x),
    ('col', 'width', 'width', css_len),
]

DIVIDER = re.compile(r'\*\*+.*\*\*+')

def serialize(xhtml):
    """ mode is html or xml """
    htmlbytes = etree.tostring(xhtml,
                          method='html',
                          doctype=gg.HTML5_DOCTYPE,
                          encoding='utf-8',
                          pretty_print=False)

    # lxml refuses to omit close tags for these elements
    for newtag in [b'</wbr>',]:
        htmlbytes = htmlbytes.replace(newtag, b'')

    return htmlbytes


class Writer(writers.HTMLishWriter):
    """ Class for writing HTML files. """
    VALIDATOR = 'HTML_VALIDATOR'

    def add_dublincore(self, job, tree):
        """ Add dublin core metadata to <head>. """
        source = gg.archive2files(
            options.ebook, job.url)

        if hasattr(options.config, 'FILESDIR'):
            job.dc.source = source.replace(options.config.FILESDIR, options.config.PGURL)

        for head in xpath(tree, '//xhtml:head'):
            for e in job.dc.to_html():
                e.tail = '\n'
                head.append(e)

    def add_moremeta(self, job, tree, url):

        self.add_prop(tree, "og:title", job.dc.title)

        for dcmitype in job.dc.dcmitypes:
            self.add_prop(tree, "og:type", dcmitype.id)
        info(job.main)
        web_url = urljoin(job.dc.canonical_url, job.outputfile)
        self.add_prop(tree, "og:url", web_url)
        canonical_cover_name = 'pg%s.cover.medium.jpg' % job.dc.project_gutenberg_id
        cover_url = urljoin(job.dc.canonical_url, canonical_cover_name)
        self.add_prop(tree, "og:image", cover_url)

        # fix empty title elements
        for title in xpath(tree, '//xhtml:title[not(text())]'):
            title.text = job.dc.title

    @staticmethod
    def replace_boilerplate(job, tree):
        # get text after the divider, put in dc.credit if not already there
        for pre in xpath(tree, '//*[@id="pg-header"]//xhtml:pre'):
            divided = DIVIDER.split(' '.join(pre.itertext()))
            if len(divided) > 1:
                job.dc.add_credit(divided[1])

        body = None
        for body in xpath(tree, '//xhtml:body'):
            break
        else:
            error('No Body!!!')
            return
        
        new_bp = HtmlTemplates.pgheader(job.dc)

        for pg_header in xpath(tree, '//*[@id="pg-header"]'):
            prev = pg_header.getprevious()
            parent = pg_header.getparent()
            while prev is not None:
                parent.remove(prev)
                prev = pg_header.getprevious()
            parent.replace(pg_header, new_bp)
            break
        else:
            body.insert(0, new_bp)
            warning('No pg-header found, inserted a generated one')
            
        new_bp = HtmlTemplates.pgfooter(job.dc)

        for pg_footer in xpath(tree, '//*[@id="pg-footer"]'):
            next = pg_footer.getnext()
            parent = pg_footer.getparent()
            while next is not None:
                parent.remove(next)
                next = pg_footer.getnext()
            parent.replace(pg_footer, new_bp)
            break
        else:
            body.append(new_bp)
            warning('No pg-footer found, inserted a generated one')

        for pg_smallprint in xpath(tree, '//*[@id="pg-smallprint"]'):
            pg_smallprint.getparent().remove(pg_smallprint)


    def outputfileurl(self, job, url):
        """
        Make the output path for the parser.
        Consider an image referenced in a source html file being moved to a destination directory.
        The image must be moved to a Location that is the same, relative to the job's destination,
        as it was in the source file.
        The constraints are that
        1. we must not over-write the source files, and
        2. the destination directory may be the same as the source directory.
        In case (2), we'll create a new "out" directory to contain the written files; we'll also
        stop with an error if our source path is below an "out" directory.

        Complication: generated covers are already in the output directory.

        """

        if not job.main:
            # this is the main file.
            job.main = url

            # check that the source file is not in the outputdir
            if gg.is_same_path(os.path.abspath(job.outputdir), os.path.dirname(url)):
                # make sure that source is not in an 'out" directory
                newdir = 'out'
                for parent in Path(url).parents:
                    if parent.name == newdir:
                        # not allowed
                        newdir = uuid.uuid4().hex
                        warning("can't use an 'out' directory for both input and output; using %s",
                                newdir)
                        break

                job.outputdir = os.path.join(job.outputdir, newdir)

            jobfilename = os.path.join(os.path.abspath(job.outputdir), job.outputfile)

            info("Creating HTML file: %s" % jobfilename)

            relativeURL = os.path.basename(url)
            if relativeURL != job.outputfile:
                # need to change the name for main file
                debug('changing %s to   %s', relativeURL, job.outputfile)
                job.link_map[relativeURL] = jobfilename
                relativeURL = job.outputfile

        else:
            if url.startswith(webify_url(job.outputdir)):
                relativeURL = gg.make_url_relative(webify_url(job.outputdir) + '/', url)
                debug('output relativeURL for %s to %s : %s', webify_url(job.outputdir), url, relativeURL)
            else:
                relativeURL = gg.make_url_relative(job.main, url)
                debug('relativeURL for %s to %s : %s', job.main, url, relativeURL)

        return os.path.join(os.path.abspath(job.outputdir), relativeURL)


    @staticmethod
    def fix_incompatible_css(sheet):
        """ Strip CSS properties and values that are not HTML5 compatible.
            Unpack "media handheld" rules
        """
        for rule in sheet:
            if rule.type == rule.STYLE_RULE:
                for p in list(rule.style):
                    if p.name == 'speak':
                        val = rule.style.getPropertyValue('speak')
                        if val == 'spell-out':
                            rule.style.removeProperty('speak')
                            rule.style.setProperty('speak-as', 'spell-out')
                        elif val == 'none':
                            rule.style.setProperty('speak', 'never')
                        elif val == 'inherit':
                            rule.style.setProperty('speak', 'auto')

    @staticmethod
    def fix_css_for_deprecated(sheet, tags='', replacement='span'):
        """ for deprecated tags, change selector to {replacement}.xhtml_{tag name};
            if no existing selector, add the selector with a style
        """
        for tag in tags:
            tagre = re.compile(f'(^| |\\+|,|>|~){tag}')
            tagsub = f'\\1{replacement}.xhtml_{tag}'
            for rule in sheet:
                if rule.type == rule.STYLE_RULE:
                    for selector in rule.selectorList:
                        selector.selectorText = tagre.sub(tagsub, selector.selectorText)

    @staticmethod
    def xhtml_to_html(html):
        '''
        try to convert the html4 DOM to an html5 DOM
        (assumes xhtml namespaces have been removed, except from attribute values)
        '''

        # fix metas
        for meta in xpath(html, "//xhtml:meta[translate(@http-equiv, 'CT', 'ct')='content-type']"):
            meta.getparent().remove(meta)
        for meta in xpath(html, "//xhtml:meta[translate(@http-equiv, 'CST', 'cst')='content-style-type']"):
            meta.getparent().remove(meta)
        for meta in xpath(html, "//xhtml:meta[translate(@http-equiv, 'CL', 'cl')='content-language']"):
            meta.getparent().remove(meta)
        for meta in xpath(html, "//xhtml:meta[@charset]"): # html5 doc, we'll replace it
            meta.getparent().remove(meta)
        for meta in xpath(html, "//xhtml:meta[@scheme]"): # remove obsolete formatted metas
            meta.getparent().remove(meta)
        for elem in xpath(html, "//xhtml:*[@xml:space]"):
            if elem.tag in ('pre', 'style'):
                del elem.attrib[NS.xml.space]

        #check values of lang; lang attributes moved to xml:lang in pre_parse
        for elem in xpath(html, "//xhtml:*[@lang]"):
            check_lang(elem, 'lang')
        for elem in xpath(html, "//xhtml:*[@xml:lang and not(@lang)]"):
            check_lang(elem, NS.xml.lang)

        # remove obsolete attributes
        attrs_to_remove = [('style', 'type'), ('img', 'longdesc')]
        for (tag, attr) in attrs_to_remove:
            for elem in xpath(html, f"//xhtml:{tag}[@{attr}]"):
                del elem.attrib[attr]

        # set required attributes
        attrs_to_fill = [('img', 'alt', '')]
        for (tag, attr, fill) in attrs_to_fill:
            for elem in xpath(html, f"//xhtml:{tag}[not(@{attr})]"):
                elem.set(attr, fill)

        # remove not_empty attributes
        nullattrs_to_remove = ['height', 'width']
        for attr in nullattrs_to_remove:
            for elem in xpath(html, f"//xhtml:*[@{attr}='' or @{attr}=0]"):
                del elem.attrib[attr]

        # put a space in empty headings
        for heading in [f'h{n}' for n in range(1,6)]:
            for elem in xpath(html, f"//xhtml:{heading}[not(text())]"):
                elem.text = ' '

        for (tags, attr, cssattr, val2css) in REPLACEMENTS:
            for tag in tags.split():
                for elem in xpath(html, f"//xhtml:{tag}[@{attr}]"):
                    if elem.attrib[attr]:
                        val = elem.attrib[attr]
                        del elem.attrib[attr]
                        if cssattr:
                            add_style(elem, style=f'{cssattr}: {val2css(val)};')


        # width and height attributes must be integer
        for elem in xpath(html, "//xhtml:*[@width or @height]"):
            rules = []
            for key in ['width', 'height']:
                if key in elem.attrib and elem.attrib[key]:
                    val = elem.attrib[key]
                    try:
                        val = int(val)
                    except ValueError:
                        del elem.attrib[key]
                        rules.append('%s: %s' % (key, val))
            if rules:
                elem.attrib['style'] = '; '.join(rules) + '; ' + elem.attrib.get('style', '')

        # fix missing <dd>,<dt> elements
        for dt in xpath(html, "//xhtml:dt"):
            if dt.getnext() is None or dt.getnext().tag != NS.xhtml.dd:
                dt.addnext(etree.Element(NS.xhtml.dd))
        for dd in xpath(html, "//xhtml:dd"):
            if dd.getprevious() is None:
                dd.addprevious(etree.Element(NS.xhtml.dt))

        # deprecated elements -  replace with <span/div class="xhtml_{tag name}">
        deprecated_used = replace_elements(html, REPLACE_ELEMENTS)


        html.head.insert(0, etree.Element(NS.xhtml.meta, charset="utf-8"))

        ##### tables #######

        # remove summary attribute
        for table in xpath(html, '//xhtml:table[@summary]'):
            summary = table.attrib['summary']
            del table.attrib['summary']
            if summary:
                table.attrib['data-summary'] = summary


        # replace frame and rules attributes on tables

        deprecated_atts = {'frame': CSS_FOR_FRAME, 'rules': CSS_FOR_RULES, 'background': {}}
        for att in deprecated_atts:
            for table in xpath(html, f'//xhtml:table[@{att}]'):
                att_value = table.attrib[att].lower()
                if att_value in deprecated_atts[att]:
                    add_class(table, f'{att}-{att_value}')
                    deprecated_used.add(att_value)
                del table.attrib[att]

        # remove span attribute from colgroups that have col children
        for colgroup in xpath(html, "//xhtml:colgroup[@span and xhtml:col]"):
            del colgroup.attrib['span']

        # move tfoot elements to end of table
        for tfoot in xpath(html, "//xhtml:table/xhtml:tfoot"):
            table = tfoot.getparent()
            table.append(tfoot)

        ##### cleanup #######

        # fix css in style elements
        cssparser = cssutils.CSSParser()
        for style in xpath(html, "//xhtml:style"):
            if style.text:
                sheet = cssparser.parseString(style.text)
                Writer.fix_incompatible_css(sheet)
                Writer.fix_css_for_deprecated(sheet, tags=deprecated_used)
                style.text = sheet.cssText.decode("utf-8")

        deprecated_used.add('*')  # '*' provides for css rules that are always added
        css_for_deprecated = ' '.join([CSS_FOR_REPLACED.get(tag, '') for tag in deprecated_used])
        if css_for_deprecated.strip():
            elem = etree.Element(NS.xhtml.style)
            elem.text = css_for_deprecated
            html.find(NS.xhtml.head).insert(1, elem) # right after charset declaration


    def build(self, job):
        """ Build HTML file. """

        def rewrite_links(job, node):
            """ only needed if the mainsource filename has been changed """
            for renamed_path in job.link_map:
                for link in xpath(node, '//xhtml:*[@href]'):
                    old_link = link.get('href')
                    parsed_url = urlparse(old_link)
                    if os.path.basename(parsed_url.path) == renamed_path:
                        new_path = parsed_url.path[0:-len(renamed_path)]
                        new_link = job.link_map[renamed_path]
                        new_link = '%s%s#%s' % (new_path, new_link, parsed_url.fragment)
                        link.set('href', new_link)

        for p in job.spider.parsers:
            # Do html only. The images were copied earlier by PicsDirWriter.

            outfile = self.outputfileurl(job, p.attribs.url)
            outfile = gg.normalize_path(outfile)

            if gg.is_same_path(p.attribs.url, outfile):
                # debug('%s is same as %s: won't override source', p.attribs.url, outfile)
                continue

            gg.mkdir_for_filename(outfile)

            xhtml = None
            if hasattr(p, 'rst2html'):
                xhtml = p.rst2html(job)
                self.make_links_relative(xhtml, p.attribs.url)
                rewrite_links(job, xhtml)

            elif hasattr(p, 'xhtml'):
                p.parse()
                xhtml = copy.deepcopy(p.xhtml)
                self.make_links_relative(xhtml, p.attribs.url)
                rewrite_links(job, xhtml)

            else:
                p.parse()

            try:

                if xhtml is not None:
                    html = copy.deepcopy(xhtml)

                    if NS.xml.lang in html.attrib:
                        lang = html.attrib[NS.xml.lang]
                        html.attrib['lang'] = job.dc.languages[0].id or lang
                        del html.attrib[NS.xml.lang]
                    else:
                        html.attrib['lang'] = job.dc.languages[0].id 

                    self.add_dublincore(job, html)
                    self.add_meta_generator(html)
                    self.add_moremeta(job, html, p.attribs.url)

                    self.replace_boilerplate(job, html)
                    self.xhtml_to_html(html)

                    # strip xhtml namespace
                    # https://stackoverflow.com/questions/18159221/
                    for elem in html.getiterator():
                        if elem.tag is not etree.Comment:
                            elem.tag = etree.QName(elem).localname
                    # Remove unused namespace declarations
                    etree.cleanup_namespaces(html)

                    self.write_with_crlf(outfile, serialize(html))                   
                    info("Done generating HTML file: %s" % outfile)

                else:
                    #images and css files

                    if hasattr(p, 'sheet') and p.sheet:
                        self.fix_incompatible_css(p.sheet)

                    try:
                        with open(outfile, 'wb') as fp_dest:
                            fp_dest.write(p.serialize())
                    except IOError as what:
                        error('Cannot copy %s to %s: %s', job.attribs.url, outfile, what)

            except Exception as what:
                exception("Error building HTML %s: %s" % (outfile, what))
                if os.access(outfile, os.W_OK):
                    os.remove(outfile)
                raise what

        info("Done generating HTML: %s" % job.outputfile)
