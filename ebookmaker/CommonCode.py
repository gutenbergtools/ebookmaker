#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""
CommonCode.py

Copyright 2014 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Common code for EbookMaker and EbookConverter.

"""


from six.moves import configparser


class Struct (object):
    pass


class Job (object):
    """Hold 'globals' for a job.

    A job is defined as one unit of work, preferably acting on one url
    and with one set of parsers.

    """

    def __init__ (self):
        self.url = None
        self.dc = None
        self.types = []
        self.outputdir = None
        self.logfile = None

        self.type = None
        self.outputfile = None

    def __str__ (self):
        l = []
        for k, v in self.__dict__.items ():
            l.append ("%s: %s" % (k, v))
        return '\n'.join (l)


def add_dependencies (targets, deps, order = None):
    """ Add dependent formats and optionally put into right build order. """

    for target, deps in deps.items ():
        if target in targets:
            targets += deps
    if order:
        return list (filter (targets.__contains__, order))
    return targets


def null_translation (s):
    """ Translate into same language. :-) """
    return s


def add_common_options (ap, user_config_file):
    """ Add aptions common to all programs. """

    ap.add_argument (
        "--verbose", "-v",
        action   = "count",
        default  = 0,
        help     = "be verbose (-v -v be more verbose)")

    ap.add_argument (
        "--config",
        metavar  = "CONFIG_FILE",
        dest     = "config_file",
        action   = "append",
        default  = user_config_file,
        help     = "read config file (default: %(default)s)")

    ap.add_argument (
        "--validate",
        dest     = "validate",
        action   = "count",
        help     = "validate epub through epubcheck")

    ap.add_argument (
        "--section",
        metavar  = "TAG.CLASS",
        dest     = "section_tags",
        default  = [],
        action   = "append",
        help     = "split epub on TAG.CLASS")


def parse_config_and_args (ap, sys_config, defaults = None):

    options = ap.parse_args ()

    cp = configparser.ConfigParser (defaults)
    cp.read ((sys_config, options.config_file))

    options.config = Struct ()

    for name, value in defaults.items ():
        setattr (options.config, name.upper (), value)

    for section in cp.sections ():
        for name, value in cp.items (section):
            setattr (options.config, name.upper (), value)

    return options
