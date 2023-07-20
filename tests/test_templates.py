#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
run this with
python -m unittest -v tests.test_templates
'''

import os
import unittest

from libgutenberg.DublinCore import GutenbergDublinCore

from ebookmaker.writers import HtmlTemplates, TemplateStrings


class TestHeaders(unittest.TestCase):

    def setUp(self):
        self.dc = GutenbergDublinCore()
        book_id = '69030'
        self.sample_dir = os.path.join(os.path.dirname(__file__), 'files')
        dir = os.path.join(self.sample_dir, book_id)
        srcfile = os.path.join(dir, '%s-0.txt' % book_id)
        with open(srcfile, 'r') as f:
            sampledata = f.read()
        self.dc.load_from_pgheader(sampledata)
 
    def test_templates(self):
        self.assertTrue('in the United States' in TemplateStrings.headera)
        self.assertTrue('FULL PROJECT GUTENBERG LICENSE' in TemplateStrings.headerb)
        self.assertTrue('COPYRIGHTED' in TemplateStrings.headera_copy)
        self.assertTrue('This particular' in TemplateStrings.headerb_copy)
        self.assertTrue('<div>' not in TemplateStrings.headera_txt)
        self.assertTrue('<div>' not in TemplateStrings.headerb_txt)
        self.assertTrue('Gutenberg License' in TemplateStrings.headera_copy_txt)
        self.assertTrue('where you are located' in TemplateStrings.headerb_copy_txt)

    def test_headdata(self):
        self.assertTrue('The girl in the crowd' in HtmlTemplates.pgheader(self.dc).text_content())
