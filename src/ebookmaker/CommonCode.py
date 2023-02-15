#!/usr/bin/env python


"""
CommonCode.py

Copyright 2014-2021 by Marcello Perathoner and Project Gutenberg

Distributable under the GNU General Public License Version 3 or newer.

Common code for EbookMaker and EbookConverter.

"""
import datetime
import os
import re

from six.moves import configparser

from libgutenberg.CommonOptions import Options
from libgutenberg.GutenbergGlobals import archive2files
from libgutenberg.Logger import debug, error, warning
from libgutenberg.Models import File
from . import parsers

class Struct(object):
    pass

options = Options()

class EbookmakerBadFileException(Exception):
    pass

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


    def last_updated(self):
        if not self.url:
            return None
        if hasattr(self.dc, 'files'):
            for file in self.dc.files:
                file_url = parsers.webify_url(path_from_file(file))
                if self.url == file_url:
                    self.dc.update_date = file.modified.date()
                    return file.modified

        path = self.url[7:] if self.url.startswith('file:///') else self.url
        try:
            statinfo = os.stat(path)
            modified = datetime.datetime.fromtimestamp(statinfo.st_mtime)
            if self.dc:
                self.dc.update_date = modified.date()
            return modified
        except FileNotFoundError as e:
            error(e)
            return


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
        action="store",
        default=user_config_file,
        help="read config file (default: %(default)s)")

    ap.add_argument(
        "--validate",
        dest="validate",
        action="store_true",
        help="validate epub and html through epubcheck/nu")

    ap.add_argument(
        "--notify",
        dest="notify",
        action="store_true",
        help="write CRITICAL messages to notifier logs")


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
    if os.path.isdir(url):
        return url
    if url.startswith('file://'):
        dir = os.path.dirname(os.path.abspath(url[7:]))
    elif url.startswith('file:'):
        dir = os.path.dirname(os.path.abspath(url[5:]))
    else:
        dir = os.path.dirname(os.path.abspath(url))
    return dir


RE_SIMPATH = re.compile(r'^\d/')
RE_PGNUM = re.compile(r'/(\d\d+/.*)')
def path_from_file(f):
    """
    In some places, we need to get a file system path from a database file object
    these objects have `archive_path` properties, which are meant to be resolved with respect to a 
    home directory with the assistance of some simlinks. There are 2 types, one that
    starts with 'cache/epub/NNNN' (where NNNN is the ebook number) and another that 
    starts with 'N/N/N/NNNN', which gets simlinked to 'files/NNNN`. (a third type, 
    starting with 'etext' is obsolete and should no longer be encountered.
    
    this method need to deal with three cases.
    1. the production environment
    2. a development environment
    3. a test environment
    
    These environments are characterized by configuration variables (set by parse_config_and_args): 
    FILESDIR  - should be a 'file:' URL
        on prod: file:///public/vhost/g/gutenberg/html/
    CACHEDIR - should be a file system path
        on prod: /public/vhost/g/gutenberg/html/cache/epub

    for good measure, the paths might include Windows partitions ('c:')
    
    """
    if isinstance(f, File):
        archive_path = f.archive_path
    elif isinstance(f, str):
        archive_path = f
    else:       
        error('%s is not a string or a libgutenberg.Models.File object', f)
        return

    if hasattr(options.config, 'FILESDIR'):
        if not options.config.FILESDIR[-1] == '/':
            filesdir = dir_from_url(options.config.FILESDIR + '/')
        else:
            filesdir = dir_from_url(options.config.FILESDIR)
    else:
        # use home dir
        filesdir = os.path.expanduser("~")
        warning('Not configured, using %s for FILESDIR', filesdir)
    if hasattr(options.config, 'CACHEDIR'):
        cachedir = dir_from_url(options.config.CACHEDIR)        
    else:
        # use home dir
        cachedir = os.path.expanduser("~/cache/epub/")
        info('Not configured, using %s for CACHE', cachedir)
    if archive_path.startswith('cache/epub/'):
        # generated file
        return os.path.join(cachedir, archive_path[11:])
    if RE_SIMPATH.search(archive_path):
        # files directory, replace 1/2/3/1234 with files/1234
        if archive_path[0] == '0':
            # special case for single digits
            return os.path.join(filesdir, 'files', archive_path[2:])
        else:
            pgnum = RE_PGNUM.search(archive_path)
            if pgnum:
                return os.path.join(filesdir, 'files', pgnum.group(1))
    # legacy pattern, shouldn't be there, but give it a try
    warning('%s is an obsolete or incomplete archive path', archive_path)
    return os.path.join('filesdir', 'dirs', archive_path)
            

def find_candidates(path, file_filter=lambda x: True):
    """ walk the directory containing path, return files satisfying file_filter 
    """
    path = dir_from_url(path)
    for (root, dirs, files) in os.walk(path):
        if '/.' in root or root.startswith('.'):
            continue
        for fname in files:
            fpath = os.path.join(root, fname)
            if file_filter(fpath):
                yield fpath
