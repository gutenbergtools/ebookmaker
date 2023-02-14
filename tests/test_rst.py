#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import unittest
import subprocess


import ebookmaker

class TestFromRst(unittest.TestCase):
    def setUp(self):
        self.sample_dir = os.path.join(os.path.dirname(__file__), 'files')

    def test_33968(self):
        book_id = '33968'
        dir = os.path.join(self.sample_dir, book_id)
        rstfile = os.path.join(dir, '%s-rst' % book_id, '%s-rst.rst' % book_id)
        cmd = 'ebookmaker --make=pdf --output-dir={dir} {rstfile}'.format(
            dir=dir,
            rstfile=rstfile,
        )

        output = subprocess.check_output(cmd, shell=True)

        self.assertFalse(output)
        outs = [
            "%s-pdf.pdf",
            "%s-cover.png",
            "%s-images-pdf.pdf",
        ]
        for out in outs:
            self.assertTrue(os.path.exists(os.path.join(dir, out % book_id)))
            os.remove(os.path.join(dir, out % book_id))
        