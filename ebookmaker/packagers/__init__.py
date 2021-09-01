#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

Packager package

Copyright 2009-2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Base class for Packager modules.

"""


import os.path
import gzip
import zipfile

from pkg_resources import resource_listdir  # pylint: disable=E0611

from libgutenberg.Logger import debug, info, warning, error
import libgutenberg.GutenbergGlobals as gg

GZIP_EXTENSION = '.gzip'

class BasePackager (object):
    """
    Base class for Packagers.

    """

    def __init__ (self):
        self.path_name_ext = None
        self.path = None
        self.name = None
        self.ext = None


    def setup (self, job):
        """ Setup """

        self.path_name_ext = os.path.join(os.path.abspath(job.outputdir), job.outputfile)
        self.path, name = os.path.split (self.path_name_ext)
        self.name, self.ext = os.path.splitext (name)


    def package (self, job):
        """ Package files. """
        pass


class OneFileGzipPackager (BasePackager):
    """ Gzips one file. """

    def package (self, job):
        self.setup (job)
        filename = self.path_name_ext
        gzfilename = filename + GZIP_EXTENSION

        try:
            info ('Creating Gzip file: %s' % gzfilename)
            info ('  Adding file: %s' % filename)
            with open (filename, 'rb') as fp:
                with gzip.open (gzfilename, 'wb') as fpgz:
                    fpgz.writelines (fp)
            info ('Done Zip file: %s' % gzfilename)
        except IOError as what:
            error (what)


class ZipPackager (BasePackager):
    """ Packages a zip file. """

    @staticmethod
    def create (zipfilename):
        """ Create a zip file. """

        info ('Creating Zip file: %s' % zipfilename)
        return  zipfile.ZipFile (zipfilename, 'w', zipfile.ZIP_DEFLATED)


    @staticmethod
    def add (zip_, filename, memberfilename):
        """ Add one file to the zip. """

        try:
            os.stat (filename)
            dummy_name, ext = os.path.splitext (filename)
            info ('  Adding file: %s as %s' % (filename, memberfilename))
            zip_.write (filename, memberfilename,
                        zipfile.ZIP_STORED if ext in ['.zip', '.png']
                        else zipfile.ZIP_DEFLATED)
        except OSError:
            warning ('ZipPackager: Cannot add file %s', filename)


class OneFileZipPackager (ZipPackager):
    """ Packages one file in zip of the same name. """

    def package (self, job):
        self.setup (job)
        filename = self.path_name_ext
        zipfilename = os.path.join (self.path, self.name) + '.zip'
        memberfilename = self.name + self.ext

        zip_ = self.create (zipfilename)
        self.add (zip_, filename, memberfilename)
        zip_.close ()

        info ('Done Zip file: %s' % zipfilename)


class HTMLishPackager (ZipPackager):
    """ Package a file with images. """

    def package (self, job):
        self.setup (job)

        try:
            aux_file_list = list (job.spider.aux_file_iter ())
        except AttributeError:
            aux_file_list = []

        filename = job.outputfile
        zipfilename = os.path.join (self.path, self.name) + '.zip'
        memberfilename = os.path.join (self.name, self.name) + self.ext

        zip_ = self.create (zipfilename)
        self.add (zip_, filename, memberfilename)

        # now images
        for url in aux_file_list:
            rel_url = gg.make_url_relative (job.base_url, url)
            filename = os.path.join (self.path, rel_url)
            memberfilename = os.path.join (self.name, rel_url)
            self.add (zip_, filename, memberfilename)

        zip_.close ()
        info ('Done Zip file: %s' % zipfilename)


class PackagerFactory (object):
    """ Implements Factory pattern for packagers. """

    packagers = {}

    @staticmethod
    def mk_key (type_, format_):
        """ Make a key for the packager map. """

        return (type_ or '') + '/' + format_


    @classmethod
    def load_packagers (cls):
        """ Load the packagers in the packagers directory. """

        for fn in resource_listdir ('ebookmaker.packagers', ''):
            modulename, ext = os.path.splitext (fn)
            if ext == '.py':
                if modulename.endswith ('Packager'):
                    module = __import__ ('ebookmaker.packagers.' + modulename,
                                         fromlist = [modulename])
                    debug ("Loading packager type: %s from module: %s for formats: %s" % (
                        module.TYPE, modulename, ', '.join (module.FORMATS)))
                    for format_ in module.FORMATS:
                        cls.packagers[cls.mk_key (module.TYPE, format_)] = module

        return cls.packagers.keys ()


    @classmethod
    def unload_packagers (cls):
        """ Unload packager modules. """

        for k in list (cls.packagers.keys ()):
            del cls.packagers[k]


    @classmethod
    def create (cls, type_, format_):
        """ Create a packager for format. """

        module = cls.packagers.get (cls.mk_key (type_, format_))
        if module:
            return module.Packager ()
        return None
