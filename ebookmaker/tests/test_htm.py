#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import subprocess


import ebookmaker

class TestFromHtm(unittest.TestCase):
    def setUp(self):
        self.sample_dir = os.path.join(os.path.dirname(__file__),'samples')

    def test_43172(self):
        book_id = '43172'
        dir = os.path.join(self.sample_dir, book_id)
        htmfile = os.path.join(dir, '%s-h' % book_id, '%s-h.htm' % book_id)
        cmd = 'ebookmaker --make=test --output-dir={dir} {htmfile}'.format(
            dir=dir,
            htmfile=htmfile,
        )

        output = subprocess.check_output(cmd, shell=True)

        self.assertFalse(output)
        outs = [
            "%s-epub.epub",
            "%s-images-epub.epub",
            "%s-noimages-h.html",
            "%s-h.html",
            "%s.txt",
            "%s-8.txt",
            "%s-0.txt",
        ]
        for out in outs:
            self.assertTrue(os.path.exists(os.path.join(dir, out % book_id)))
            os.remove(os.path.join(dir, out % book_id))
                
            
        