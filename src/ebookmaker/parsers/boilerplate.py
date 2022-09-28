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
    re.compile(r"\*+ ?START OF TH(E|IS) PROJECT GUTENBERG", re.I),
]
BOTTOM_MARKERS = [
    re.compile(r"\** ?END OF TH(E|IS) PROJECT GUTENBERG", re.I),
    re.compile(r"\** ?Ende dieses Projekt Gutenberg", re.I),
    re.compile(r"\** ?END OF PROJECT GUTENBERG", re.I),
    re.compile(r"\** ?End of the Project Gutenberg", re.I),
]
SMALLPRINT_MARKERS = [
    re.compile(r"\** ?END\*? ?THE SMALL PRINT", re.I),
    re.compile(r"\**END THE SMALL PRINT", re.I),
    re.compile(r"\** ?These \w+ Were Prepared By Thousands", re.I),
]

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
        print('no body')
        return

    found_top = mark_bp(body, 'pg-header', TOP_MARKERS, top=True)
    found_bottom = mark_bp(body, 'pg-footer', BOTTOM_MARKERS, top=False)
    '''if not found_bottom:
        found_smallprint = mark_bp(body, 'pg-smallprint', SMALLPRINT_MARKERS, top=True)
    else:
        found_smallprint = False'''
    return found_top or found_bottom #or found_smallprint


def strip_headers_from_txt(text):
    '''
    when input is plain text, strip the heaters and return (stripped_text, pg_header, pg_footer)
    '''
    def markers_split(text, markers):
        for marker in markers:
            divider = marker.search(text)
            if divider:
                sections = text.split(divider.group(0))
                if len(sections) == 2:
                    (before, after) = sections
                else:
                    before = ' '.join(sections[0:-1])
                    after = sections[-1]
                return before, divider.group(0), after
        return  text, None, text
    header_text, divider, text = markers_split(text, TOP_MARKERS)
    if divider is None:
        pg_header = ''
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
        pg_footer = ''
    else:
        pg_footer = '\n'.join(['<pre id="pg-footer">',
                               divider,
                               xmlspecialchars(footer_text),
                               '</pre>'])
    return text, pg_header, pg_footer
