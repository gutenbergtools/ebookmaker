#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import subprocess


import ebookmaker

class TestFromTxt(unittest.TestCase):
    def setUp(self):
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
            "%s-noimages-h.html",
            "%s-h.html",
        ]
        for out in outs:
            self.assertTrue(os.path.exists(os.path.join(self.out_dir, out % book_id)))
            os.remove(os.path.join(self.out_dir, out % book_id))
        