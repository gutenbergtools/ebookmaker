#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

WriterFactory.py

Copyright 2009-14 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Writer factory. Dynamically loads writers from directories.

"""


import os.path

from pkg_resources import resource_listdir # pylint: disable=E0611

from libgutenberg.Logger import error, debug
from ebookmaker.CommonCode import Options

options = Options()

writers = {}

def __load_writers_from (package_name):
    """ See what types we can write. """

    for fn in resource_listdir (package_name, ''):
        modulename, ext = os.path.splitext (fn)
        if ext == '.py' and modulename.endswith ('Writer'):
            type_ = modulename.lower ().replace ('writer', '')
            try:
                debug ("Loading writer type %s from module %s" % (type_, modulename))
                module = __import__ (package_name + '.' + modulename, fromlist = [modulename])
                writers[type_] = module
            except ImportError as what:
                error (
                    "Could not load writer type %s from module %s. %s" %
                    (type_, modulename, what)
                )


def load_writers ():
    """ See what types we can write. """

    __load_writers_from ('ebookmaker.writers')

    for package in options.extension_packages:
        __load_writers_from (package)

    return writers.keys ()


def unload_writers ():
    """ Unload writer modules. """
    for k in writers.keys ():
        del writers[k]


def create (type_):
    """ Load writer module for type. """
    try:
        if type_ == 'kf8':
            type_ = 'kindle'
        return writers[type_].Writer ()
    except KeyError:
        raise KeyError ('No writer for type %s' % type_)
