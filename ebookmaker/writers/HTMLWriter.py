#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

HTMLWriter.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""


import os
import copy

from lxml import etree

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import xpath
from libgutenberg.Logger import debug, exception, info

from ebookmaker import writers
from ebookmaker.CommonCode import Options
from ebookmaker.parsers import webify_url

options = Options()

class Writer(writers.HTMLishWriter):
    """ Class for writing HTML files. """
    mainsourceurl = None

    def add_dublincore(self, job, tree):
        """ Add dublin core metadata to <head>. """
        source = gg.archive2files(
            options.ebook, job.url)

        if hasattr(options.config, 'FILESDIR'):
            job.dc.source = source.replace(options.config.FILESDIR, options.config.PGURL)

        for head in xpath(tree, '//xhtml:head'):
            for e in job.dc.to_html():
                e.tail = '\n'
                head.append(e)

    def outputfileurl(self, job, url):
        """ make the output path for the parser """

        # the first html doc is the main file
        self.mainsourceurl = self.mainsourceurl if self.mainsourceurl else url
        relativeURL = gg.make_url_relative(self.mainsourceurl, url)
        if not relativeURL:
            relativeURL = os.path.basename(url)
        info("source: %s relative: %s", url, relativeURL)
        return os.path.join(os.path.abspath(job.outputdir), relativeURL)
        

    def build(self, job):
        """ Build HTML file. """

        jobfilename = os.path.join(os.path.abspath(job.outputdir),
                                    job.outputfile)
        try:
            os.remove(jobfilename)
        except OSError:
            pass

        info("Creating HTML file: %s" % jobfilename)

        for p in job.spider.parsers:
            # Do html only. The images were copied earlier by PicsDirWriter.

            outfile = self.outputfileurl(job, p.attribs.url)
            
            if p.attribs.url.startswith(webify_url(job.outputdir)):
                debug('%s is same as %s: already there' 
                      % (p.attribs.url, job.outputdir))
                continue
            if gg.is_same_path(p.attribs.url, outfile):
                debug('%s is same as %s: should not overwrite source' 
                      % (p.attribs.url, outfile))
                continue
            
            gg.mkdir_for_filename(outfile)

            xhtml = None
            if hasattr(p, 'rst2html'):
                xhtml = p.rst2html(job)
                self.make_links_relative(xhtml, p.attribs.url)
            elif hasattr(p, 'xhtml'):
                p.parse()
                xhtml = copy.deepcopy(p.xhtml)
            else:
                p.parse()

            try:
                if xhtml is not None:
                    self.add_dublincore(job, xhtml)

                    # makes iphones zoom in
                    self.add_meta(xhtml, 'viewport', 'width=device-width')
                    self.add_meta_generator(xhtml)

                    html = etree.tostring(xhtml,
                                          method='html',
                                          encoding='utf-8',
                                          pretty_print=True)

                    self.write_with_crlf(outfile, html)
                    info("Done generating HTML file: %s" % outfile)
                else:
                    #images and css files
                    try:
                        with open(outfile, 'wb') as fp_dest:
                            fp_dest.write(p.serialize())
                    except IOError as what:
                        error('Cannot copy %s to %s: %s' % (job.attribs.url, outfile, what))

            except Exception as what:
                exception("Error building HTML %s: %s" % (outfile, what))
                if os.access(outfile, os.W_OK):
                    os.remove(outfile)
                raise what

        # for when the main source file name is not the desired generated source file name
        if not os.access(jobfilename, os.F_OK):
            os.link(self.outputfileurl(job, self.mainsourceurl), jobfilename)
        
        info("Done generating HTML: %s" % jobfilename)

