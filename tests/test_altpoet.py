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
        eat = EbookAltText(67098)
        self.assertTrue(len(eat._alt_map) > 100)
        eat = EbookAltText(57448)
        self.assertFalse(eat._alt_map)
        eat = EbookAltText(20782)
        self.assertTrue(eat._alt_map)
