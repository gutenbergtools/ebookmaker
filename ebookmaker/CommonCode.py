#!/usr/bin/env python


"""
CommonCode.py

Copyright 2014-2021 by Marcello Perathoner and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Common code for EbookMaker and EbookConverter.

"""
import os
import os.path

from six.moves import configparser

from libgutenberg.CommonOptions import Options

class Struct(object):
    pass

options = Options()

class Job(object):
    """Hold 'globals' for a job.

    A job is defined as one unit of work, acting on one input url.

    """

    def __init__(self, type_):
        self.type = type_
        self.maintype, self.subtype = os.path.splitext(self.type)

        self.url = None
        self.outputdir = None
        self.outputfile = None
        self.logfile = None
        self.dc = None
        self.source = None
        self.opf_identifier = None
        self.main = None
        self.link_map = {}


    def __str__(self):
        l = []
        for k, v in self.__dict__.items():
            l.append("%s: %s" % (k, v))
        return '\n'.join(l)


def add_dependencies(targets, deps, order=None):
    """ Add dependent formats and optionally put into right build order. """

    for target, deps in deps.items():
        if target in targets:
            targets = list(set(targets).union(deps))
    if order:
        return list(filter(targets.__contains__, order))
    return targets


def add_common_options(ap, user_config_file):
    """ Add aptions common to all programs. """

    ap.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="be verbose (-v -v be more verbose)")

    ap.add_argument(
        "--config",
        metavar="CONFIG_FILE",
        dest="config_file",
        action="append",
        default=user_config_file,
        help="read config file (default: %(default)s)")

def set_arg_defaults(ap, config_file):
    # get default command-line args
    cp = configparser.ConfigParser()
    cp.read(config_file)
    if cp.has_section('DEFAULT_ARGS'):
        ap.set_defaults(**dict(cp.items('DEFAULT_ARGS')))

def parse_config_and_args(ap, sys_config, defaults=None):

    # put command-line args into options
    options.update(vars(ap.parse_args()))

    cp = configparser.ConfigParser()
    cp.read((sys_config, options.config_file))

    options.config = Struct()

    for name, value in defaults.items():
        setattr(options.config, name.upper(), value)

    for section in cp.sections():
        for name, value in cp.items(section):
            setattr(options.config, name.upper(), value)

    return options


PRIVATE = os.getenv('PRIVATE') or ''
NOTIFICATION_DIR = os.path.join(PRIVATE, 'logs', 'notifications')

def queue_notifications(ebook, message, subject='EbookMaker Notification'):
    message_queue = os.path.join(NOTIFICATION_DIR, '%s.txt' % ebook)
    with open(message_queue, 'a+') as messagefile:
        messagefile.write('Subject: %s\n' % subject)
        messagefile.write(message)


def dir_from_url(url):
    if url.startswith('file://'):
        dir = os.path.dirname(os.path.abspath(url[7:]))
    elif url.startswith('file:'):
        dir = os.path.dirname(os.path.abspath(url[5:]))
    else:
        dir = os.path.dirname(os.path.abspath(url))
    return dir


def find_candidates(path, file_filter=lambda x: True):
    """ walk the directory containing path, return files satisfying file_filter 
    """
    for (root, dirs, files) in os.walk(path):
        if '/.' in root or root.startswith('.'):
            continue
        for fname in files:
            fpath = os.path.join(root, fname)
            if file_filter(fpath):
                yield fpath
