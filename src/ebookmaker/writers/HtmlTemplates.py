#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
HtmlTemplates.py

Copyright 2022 by Project Gutenberg

Use f-strings to render boilerplate trees
"""
import datetime
import html
import lxml
from lxml import etree

from .TemplateStrings import COPYRIGHT_ADDITION, COPYRIGHTED, CSS_FOR_HEADER, HEADERA, HEADERB

pg_date = datetime.date(1971, 12, 1)
try:
    hr_format = "%B %-d, %Y"
    f'{pg_date.strftime(hr_format)}'
except ValueError:
    # https://strftime.org/
    hr_format = "%B %#d, %Y"


def pgheader(dc):
    def pstyle(key, val):
        key = key.capitalize()
        if not key or not val:
            return ''
        val = f'<br/>\n{padding}'.join([html.escape(v) for v in val.split('\n')])
        if key == 'Previous':
            return f'''<p style='margin-top:0'><span style='padding-left: 7.5ex'>{padding}</span>{val}</p>{nl}'''
        else:
            return f'''<p><strong>{key}</strong>: {val}</p>{nl}'''

    def dcauthlist(dc):
        cre_list = ''
        block_role = ''
        for creator in dc.authors:
            if block_role != creator.role:
                cre_list +=  nl + pstyle(creator.role, dc.make_pretty_name(creator.name))
                block_role = creator.role
            else:
                # roughly line up additional vals under previous 
                cre_list += pstyle('Previous', dc.make_pretty_name(creator.name))
        return cre_list

    language_list = []
    lang = ''
    padding = "        "
    nl = '\n'
    for language in dc.languages:
        lang = lang if lang else language.id 
        language_list.append(language.language)

    if 'copyright' in dc.rights.lower():
        rights = HEADERA.format(copyrighted=COPYRIGHTED)    
    else:
        rights = HEADERA.format(copyrighted='')

    if dc.update_date - dc.release_date < datetime.timedelta(days=14):
        updated = ''
    else:
        updated = f'{nl}{padding}Most recently updated: {dc.update_date.strftime(hr_format)}'
    pg_header = '<section class="pg-boilerplate pgheader" id="pg-header" xml:lang="en" lang="en" xmlns="http://www.w3.org/1999/xhtml">'
    pg_header += "<h2 id='pg-header-heading' title=''>"
    pg_header += 'The Project Gutenberg eBook of '
    pg_header += f'''<span lang='{lang}' xml:lang='{lang}' id='pg-title-no-subtitle'>{
        html.escape(dc.title_no_subtitle)
    }</span></h2>
    {rights}<div class='container' id='pg-machine-header'>{
        pstyle('Title', dc.title_no_subtitle)
    }{
        pstyle('Previous', dc.subtitle) if dc.subtitle  else ''
    }<div id='pg-header-authlist'>{
        dcauthlist(dc)
    }</div>
{pstyle('Release Date', 
            f'{dc.release_date.strftime(hr_format)} [eBook #{dc.project_gutenberg_id}]' + updated)}
{pstyle('Language', ', '.join(language_list))}
{pstyle('Original Publication', str(dc.pubinfo))}
{pstyle('Credits', dc.credit)}
</div><div id='pg-start-separator'>
<span>*** START OF THE PROJECT GUTENBERG EBOOK {html.escape(dc.title_no_subtitle.upper())} ***</span>
</div></section>
'''
    return etree.fromstring(pg_header.replace('\n\n\n', '\n\n'), lxml.html.XHTMLParser())
    

def pgfooter(dc):
    copyright_addition = COPYRIGHT_ADDITION if 'copyright' in dc.rights.lower() else ''

    pg_footer = f'''
<section class="pg-boilerplate pgheader" id="pg-footer" lang='en' xml:lang='en' xmlns="http://www.w3.org/1999/xhtml">
<div id='pg-end-separator'>
<span>*** END OF THE PROJECT GUTENBERG EBOOK {html.escape(dc.title_no_subtitle.upper())} ***</span>
</div>

    {HEADERB.format(copyright_addition=copyright_addition)}
</section>
'''
    return etree.fromstring(pg_footer, lxml.html.XHTMLParser())
