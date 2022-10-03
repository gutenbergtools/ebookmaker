#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-
"""

utils.py

tools for manipulating xhtml
Copyright 2009 by Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.
"""

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import xpath, NS
from libgutenberg.Logger import critical, debug, error, info, warning

def css_len(len_str):
    """ if an int, make px """
    try:
        return str(int(len_str)) + 'px'
    except ValueError:
        return len_str

def add_class(elem, classname):
    if 'class' in elem.attrib and elem.attrib['class']:
        vals = elem.attrib['class'].split()
    else:
        vals = []
    vals.append(classname)
    elem.set('class', ' '.join(vals))

def add_style(elem, style=''):
    if style:
        if 'style' in elem.attrib and elem.attrib['style']:
            prev_style = elem.attrib['style'].strip(' ;')
            style = f'{style.strip(" ;")};{prev_style};'
        elem.set('style', style)

def check_lang(elem, lang_att):
    three2two = {'ita': 'it', 'lat': 'la', 'heb': 'he', 'fra': 'fr', 'spa': 'es', 'deu': 'de'}
    lang_att = three2two.get(lang_att, lang_att)
    lang = elem.attrib[lang_att]
    lang_name = gg.language_map.get(lang, default=None)
    if lang_name:
        if NS.xml.lang in elem.attrib:
             del elem.attrib[NS.xml.lang]
        elem.attrib['lang'] = lang
        return True
    clean_lang = gg.language_map.inverse(lang, default=None)
    if not clean_lang:
        warning("invalid lang attribute %s", lang)
        del elem.attrib[lang_att]
        elem.attrib['data-invalid-lang'] = lang
    elif lang != clean_lang:
        elem.attrib['lang'] = clean_lang
        if NS.xml.lang in elem.attrib:
             del elem.attrib[NS.xml.lang]

def replace_elements(xhtml, deprecated):
    ''' replace a dictionary of deprecated elements with a new element or just delete it.
        return a set of replaced elements 
    '''
    deprecated_used = set()
    for tag in deprecated:
        for elem in xpath(xhtml, "//xhtml:" + tag):
            if deprecated[tag]:
                add_class(elem, 'xhtml_' + tag)
                elem.tag = getattr(NS.xhtml, deprecated[tag])
            else:
                elem.getparent().remove(elem)
            deprecated_used.add(tag)
    return deprecated_used
