#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
from ebookmaker.EbookMaker import config
from ebookmaker.CommonCode import EbookAltText, Options
options = Options()

class TestFromTxt(unittest.TestCase):
    def setUp(self):
        config()
        eat = EbookAltText

    def test_fetch(self):
        # test having a local alt file
        eat = EbookAltText(67098)
        self.assertTrue(len(eat._alt_map) > 100)
        # test a book with no images
        eat = EbookAltText(57448)
        self.assertFalse(eat._alt_map)
        # test a book with images and alt text
        eat = EbookAltText(20782)
        self.assertTrue(eat._alt_map)