#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import subprocess


import ebookmaker
from ebookmaker.ParserFactory import load_parsers, ParserFactory
from ebookmaker.CommonCode import Options
from ebookmaker.EbookMaker import config

options = Options()

class TestFromTxt(unittest.TestCase):
    def setUp(self):
        config()
        self.sample_dir = os.path.join(os.path.dirname(__file__), 'files')
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')

    def test_69030(self):
        book_id = '69030'
        dir = os.path.join(self.sample_dir, book_id)
        srcfile = os.path.join(dir, '%s-0.txt' % book_id)
        cmd = 'ebookmaker '
        cmd += f'--ebook={book_id} --make=txt --make=html --output-dir={self.out_dir} '
        cmd += f'--validate {srcfile}'

        output = subprocess.check_output(cmd, shell=True)

        self.assertFalse(output)
        outs = [
            "%s.txt",
            "%s-0.txt",
            "%s-8.txt",
            "%s-h.html",
            "%s-cover.png",
        ]
        for out in outs:
            self.assertTrue(os.path.exists(os.path.join(self.out_dir, out % book_id)))
            os.remove(os.path.join(self.out_dir, out % book_id))

    def test_parser(self):
        load_parsers()
        options.outputdir = ''
        book_id = '69030'
        dir = os.path.join(self.sample_dir, book_id)
        srcfile = os.path.join(dir, '%s-0.txt' % book_id)
        parser = ParserFactory.create(srcfile)
        parser.parse()
        self.assertTrue(len(parser.unicode_content()) > len(parser.text))
        self.assertTrue(len(parser.pg_header) > 500)
        self.assertTrue(len(parser.pg_footer) > 1500)
