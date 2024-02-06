#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

boilerplate.py

Copyright 2022 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

This module finds Project Gutenberg boilerplate and, if found puts it into 3 section elements:

pg_header
    usually a title and license declaration
    sometimes, title, book number, release date, authors, language, encoding, credits
    when detected, metadata will be parsed and enclosed in a pg_metadata_raw sub-section

pg_footer
    usually the license

pg_smallprint
    on older books, this will contain license-ish language and other material. it's usually found
    at the top of the text, and is often comically dated.


BeautifulSoup is used for its superior "scraping" tools.

"""

import copy
import re

import soupsieve as sv

from libgutenberg.GutenbergGlobals import xmlspecialchars
from libgutenberg.Logger import critical, info, debug, warning, error


TOP_MARKERS = [
    re.compile(r"\*+ ?START\s+OF\s+TH(E|IS)\s+PROJECT\s+GUTENBERG", re.I),
]
BOTTOM_MARKERS = [
    re.compile(r"\** ?END\s+OF\s+TH(E|IS)\s+PROJECT\s+GUTENBERG", re.I),
    re.compile(r"\** ?Ende\w*dieses\w*Projekt\w*Gutenberg", re.I),
    re.compile(r"\** ?END\s+OF\s+PROJECT\s+GUTENBERG", re.I),
    re.compile(r"\** ?End\s+of\s+the\s+Project\s+Gutenberg", re.I),
]
SMALLPRINT_MARKERS = [
    re.compile(r"\** ?END\*? ?THE\s+SMALL\s+PRINT", re.I),
    re.compile(r"\**END\s+THE\s+SMALL\s+PRINT", re.I),
    re.compile(r"\** ?These\s+\w+\s+Were\s+Prepared\s+By\s+Thousands", re.I),
]
MARKER_END = re.compile(r"\*+")

def prune(root, divider, after=True):
    ''' prune parts of the root element before or after a divider  '''
    def next_or_prev(el, after=True):
        return el.next_sibling if after else el.previous_sibling

    def after_or_before(el, after=True):
        return list(el.next_siblings) if after else list(el.previous_siblings)

    dividers = [divider] + list(divider.parents)
    keep = False
    for elem in dividers:
        if elem is root:
            break
        has_sibling = bool(next_or_prev(elem, after=not after))
        for sibling in after_or_before(elem, after=after):
            sibling.extract()
        keep = has_sibling or keep

def check_patterns(node, patterns):
    ''' finds the element containing the marker pattern '''
    for pattern in patterns:
        found = node.find(string=pattern)
        if found:
            in_bp = sv.filter('.pg_boilerplate', found.parents)
            if not in_bp:
                return found

def mark_soup(soup):
    def mark_bp(node, mark, markers, top=True):
        marked = node.find(id=mark)
        if marked:
            marked.name = 'section'
            return True
        divider = check_patterns(node, markers)
        if divider:

            # the following mess deals with the case where the marker includes 
            # '<span>something</span) end of marker **' (as in titles with language tags)
            if divider.next_sibling and divider.next_sibling.name == 'span':
                if divider.next_sibling.next_sibling and not divider.next_sibling.next_sibling.name:
                    new_divider_string = str(divider.string + divider.next_sibling.string + 
                                          divider.next_sibling.next_sibling.string)
                    divider.insert_before(new_divider_string)
                    divider = divider.previous_sibling
                    divider.next_sibling.extract()
                    divider.next_sibling.extract()
                    divider.next_sibling.extract()

            # first, copy the Node - it contains the divider
            node_for_divider = copy.copy(node)
            divider_copy = check_patterns(node_for_divider, markers)

            # prune all content after (before) the divider
            prune(node_for_divider, divider_copy, after=top)

            #put that into a new section tag
            bp_section = soup.new_tag('section', id=mark)
            bp_section['class'] = 'pg_boilerplate'
            for child in node_for_divider.contents:
                bp_section.append(copy.copy(child))
            
            # now prune all content before (after) the divider 
            # this should be mostly the divider and old boilerplate
            prune(node, divider, after=not top)

            # remove the divider
            divider.extract()

            # re-insert the boilerplate
            if top:
                node.insert(0, bp_section)
            else:
                node.append(bp_section)
            return True
        return False

    try:
        body = soup.html.body
    except:
        return

    found_top = mark_bp(body, 'pg-header', TOP_MARKERS, top=True)
    if not found_top:
        info('No PG header found. This is an ERROR for white-washed files.')

    found_bottom = mark_bp(body, 'pg-footer', BOTTOM_MARKERS, top=False)
    if not found_bottom:
        info('No PG footer found. This is an ERROR for white-washed files.')

    return found_top or found_bottom


def strip_headers_from_txt(text):
    '''
    when input is plain text, strip the heaters and return (stripped_text, pg_header, pg_footer)
    '''
    def markers_split(text, markers):
        for marker in markers:
            divider = marker.search(text)
            if divider:
                before, after = text.split(divider.group(0), maxsplit=1)
                after_sections = MARKER_END.split(after, maxsplit=1)
                if len(after_sections) == 2 and len(after_sections[0]) < 500:
                    after = after_sections[1]
                
                return before, divider.group(0), after
        return  text, None, text
    header_text, divider, text = markers_split(text, TOP_MARKERS + SMALLPRINT_MARKERS)
    if divider is None:
        pg_header = '<pre id="pg-header"></pre>'
        info('No PG header found. This is an ERROR for white-washed files.')

    else:
        divider_tail = ''
        if '\n' in text:
            divider_tail, text = text.split('\n', maxsplit=1)
        pg_header = '\n'.join([
            '<pre id="pg-header">',
            xmlspecialchars(header_text),
            xmlspecialchars(divider),
            xmlspecialchars(divider_tail),
            '</pre>'])

    text, divider, footer_text = markers_split(text, BOTTOM_MARKERS)
    if divider is None:
        pg_footer = '<pre id="pg-footer"></pre>'
        info('No PG footer found. This is an ERROR for white-washed files.')
    else:
        pg_footer = '\n'.join(['<pre id="pg-footer">',
                               divider,
                               xmlspecialchars(footer_text),
                               '</pre>'])
    return text, pg_header, pg_footer
