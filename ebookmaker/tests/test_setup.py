#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
run this with
python -m unittest -v ebookmaker.tests.test_setup
'''
import os
import unittest
import subprocess

from libgutenberg import Logger
from libgutenberg.Logger import debug

import ebookmaker
from ebookmaker import CommonCode
from ebookmaker import ParserFactory
from ebookmaker import WriterFactory
from ebookmaker.CommonCode import Options
from ebookmaker.EbookMaker import config
from ebookmaker.EbookMaker import DEPENDENCIES, BUILD_ORDER
from ebookmaker.packagers import PackagerFactory
from ebookmaker.parsers import BROKEN

options = Options()

class TestLoad(unittest.TestCase):

    def setUp(self):
        config()
        Logger.set_log_level(options.verbose)
        options.types = options.types or ['all']
        options.types = CommonCode.add_dependencies(options.types, DEPENDENCIES, BUILD_ORDER)
        debug("Building types: %s" % ' '.join(options.types))
 
    def test_parsers(self):
        ParserFactory.load_parsers()
        pf = ParserFactory.ParserFactory()
        
        # check parser created from resource
        broken_parser = pf.create(BROKEN)
        self.assertTrue(hasattr(broken_parser, 'resize_image'))
        broken_parser.pre_parse()
        self.assertTrue(len(broken_parser.image_data) > 0)
        self.assertTrue(broken_parser.get_image_dimen()[0] > 0)

    def test_writers(self):
        WriterFactory.load_writers()

    def test_packagers(self):
        PackagerFactory.load_packagers()

