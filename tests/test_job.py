#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
run this with
python -m unittest -v tests.test_job
'''
import datetime
import os
import subprocess
import sys
import unittest

from libgutenberg import Logger
from libgutenberg.Logger import debug
from libgutenberg.DublinCore import PGDCObject

import ebookmaker
from ebookmaker import CommonCode, ParserFactory
from ebookmaker.CommonCode import Options
from ebookmaker.EbookMaker import config, get_dc
from ebookmaker.parsers import webify_url

options = Options()
Logger.set_log_level(10) # DEBUG

class TestJob(unittest.TestCase):

    def setUp(self):
        config()
        ParserFactory.load_parsers()
        self.sample_dir = os.path.join(os.path.dirname(__file__), 'files')
        self.out_dir = os.path.join(os.path.dirname(__file__), 'out')
        self.testfile = os.path.join(self.sample_dir, '43172/43172-h/43172-h.htm')
        subprocess.run(["touch", self.testfile])
        self.testdbfile = "file://" + self.testfile
        options.config.CACHEDIR = os.path.join(os.path.dirname(__file__), 'cache/epub')
        options.config.FILESDIR = webify_url(os.path.join(os.path.dirname(__file__), 'files/'))
 
    def test_update(self):
        job = CommonCode.Job('html.images')
        job.ebook = 43172
        job.url = self.testfile
        job.dc = get_dc(job)
        job.last_updated()
        self.assertEqual(job.dc.update_date, datetime.date.today())
        
    def test_update_db(self):        
        job = CommonCode.Job('html.images')
        job.ebook = 43172
        options.is_job_queue = True
        job.url = self.testdbfile
        job.dc = get_dc(job)
        self.assertTrue(len(job.dc.files) > 0)
        job.last_updated()
        self.assertEqual(job.dc.update_date, datetime.date(2013,7,9))
        


