#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

GutenbergTextParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals

import re

import six
import lxml
from lxml import etree

from pkg_resources import resource_string

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import xpath, Struct, NS
from libgutenberg.Logger import warning, info, debug
from libgutenberg.MediaTypes import mediatypes as mt

from ebookmaker import parsers
from ebookmaker.CommonCode import Options
from ebookmaker.parsers import HTMLParserBase

options = Options()
mediatypes = (mt.txt, )

MAX_BEFORE = 5 # no. of empty lines that mark a <h1>

RE_ITALICS = re.compile(r"\b_([^_]+?)_\b")
RE_INDENT = re.compile(r"^\s+")

THRESHOLD = 1.99

# headers

HEADER_SMELLS = r"^\s*(volume|book|part|chapter|section|act|scene|table of)\b"

# always preformat

PRE_SMELLS = [
    r"gbnewby",
    r"^\s*http://",
    ]

# always reflow

P_SMELLS = [
    r"^title: ",
    r"(?:produced|prepared) by",
    r"\bebook\b",
    r"Give Away One Trillion Etext",
    r"www\.gutenberg",
    r"^\*\*\*\s*start of",
    r"^\*\*\*\s*end of",
    ]

RE_HEADER_SMELLS = re.compile(HEADER_SMELLS, re.I)
RE_P_SMELLS = re.compile("|".join(P_SMELLS), re.I)
RE_PRE_SMELLS = re.compile("|".join(PRE_SMELLS), re.I)

SUBJECTS = set('header verse quote center right'.split())

SPECIALS = {
        ord('&'): '&amp;',
        ord('<'): '&lt;',
        ord('>'): '&gt;',
        ord('"'): '&#x22;',
        0xa0:     '&#xa0;',
        }

def about_same(f1, f2):
    """ Return True if f1 and f2 are about as big. """
    if f1 is None or f2 is None:
        return False
    return max(f1, float(f2)) / min(f1, float(f2)) > 0.8

def count(iterable):
    """ Count elements that are True. """
    return float(len(list(filter(bool, iterable))))

def proportional(iterable):
    """ Return ratio True elements in iterable. """
    if iterable:
        return count(iterable) / len(iterable)
    return 0.5

def most(iterable):
    """ Return True if most of iterable is True """
    if len(iterable) < 2:
        return False
    return proportional(iterable) >= 0.75

def half(iterable):
    """ Return True if at least half of iterable is True """
    if len(iterable) < 2:
        return False
    return proportional(iterable) >= 0.5

def some(iterable):
    """ Return True if some of iterable is True """
    if len(iterable) < 2:
        return False
    return proportional(iterable) >= 0.25

def not_(iterable):
    """ Return iterable with all elements negated. """
    return [not v for v in iterable]

def and_(iterable1, iterable2):
    """ Return iterable with elements from iterables and-ed . """
    return [i[0] and i[1] for i in zip(iterable1, iterable2)]

def or_(iterable1, iterable2):
    """ Return iterable with elements from iterables or-ed . """
    return [i[0] or i[1] for i in zip(iterable1, iterable2)]


class MinMaxAvg(object):
    """ Store min, max, avg of a list of values. """

    __slots__ = "min max avg first last cnt values".split()

    def __init__(self, values):
        self.min = None
        self.max = None
        self.avg = None
        self.first = None
        self.last = None
        self.cnt = len(values)
        self.values = values

        if self.cnt:
            self.min = min(values)
            self.max = max(values)
            self.avg = sum(values) / self.cnt
            self.first = values[0]
            self.last = values[-1]


class ParagraphMetrics(object):
    """ Calculates some metrics. """

    words = None
    if hasattr(options, 'config'):
        try:
            from six.moves import dbm_gnu
            try:
                fn = options.config.RHYMING_DICT
                if fn is not None:
                    words = dbm_gnu.open(fn)
            except dbm_gnu.error:
                warning("File containing rhyming dictionary not found: %s" % fn)
        except (ModuleNotFoundError, ImportError):
            warning("No gnu dbm support found. Rhyming dictionary not used.")
    else:
        warning("No config found. Rhyming dictionary not used.")

    def __init__(self, par):
        """ Calculate metrics about this paragraph. """
        lines = par.lines

        self.cnt_lines = len(lines)

        self.lengths = list(map(len, lines))
        self.centers = list(map(self._center, lines))
        self.indents = list(map(self._indent, lines))

        self.titles = list(map(self._istitle, lines))
        self.uppers = list(map(six.text_type.isupper, lines))

        # skip last line, which is almost always shorter
        self.length = MinMaxAvg(self.lengths[:-1])
        self.length.last = self.lengths[-1]
        # skip first line, which sometimes is indented on every par
        self.indent = MinMaxAvg(self.indents[1:])
        self.indent.first = self.indents[0]
        # all lines must be centered
        self.center = MinMaxAvg(self.centers)

        self.stems = None
        self.rhymes = None
        if self.words:
            self._init_rhymes(par)


    @staticmethod
    def _indent(line):
        """ Find out how much a line is left-indented. """
        return len(line) - len(line.lstrip())

    @staticmethod
    def _center(line):
        """ Find the center pos of a line. """
        len_ = len(line)
        indent = len_ - len(line.lstrip())
        return (len_ + indent) / 2

    @staticmethod
    def _istitle(line):
        """ Return True if the first char is uppercase. """
        m = re.search(r'\w', line)
        return m and m.group(0).isupper()

    def _rhyme_stemmer(self, line):
        """ Return the stem of the rhyme.

        See comments in: rhyme_compiler.py

        """

        line = re.sub(r'\W*$', '', line)

        words = re.split('[- ]+', line)
        try:
            last_word = words[-1].lower()
            return self.words[last_word.encode('utf-8')]
        except (IndexError, KeyError):
            last_word = re.sub('^(un|in)', '', last_word)
            try:
                return self.words[last_word.encode('utf-8')]
            except (IndexError, KeyError):
                return None

    def _init_rhymes(self, par):
        """ Get rhyme stems and see which lines do rhyme. """
        self.stems = list(map(self._rhyme_stemmer, par.lines))
        self.rhymes = len(self.stems) * [0]

        go_back = 8  # how many lines to consider

        for i, stem in enumerate(self.stems):
            if stem is None:
                continue
            try:
                j = self.stems.index(stem, max(0, i - go_back), i)
                self.rhymes[j] = 1
                self.rhymes[i] = 1
            except ValueError:
                pass


class Par(object):
    """ Contains one paragraph with lots of metrics. """
#    __slots__ = ('lines styles tag before after id scores'.split())

    def __init__(self):
        self.lines = []
        self.styles = {}
        self.metrics = None
        self.tag = None
        self.before = 0
        self.after = 0
        self.id = None
        self.prev = None
        self.debug_message = ''

        self.scores = Struct()
        for subject in SUBJECTS:
            setattr(self.scores, subject, 1.0)

    def __len__(self):
        return len(self.lines)

    def flush_left_lines(self):
        """ Return lines that are flush left.

        Note that those lines may well be indented.

        Returns array bitfield.

        """
        return [v == self.metrics.indent.min for v in self.metrics.indents]

    def centered_lines(self):
        """ Return lines that are centered. """
        return [abs(v - self.metrics.center.avg) < 2 for v in self.metrics.centers]

    def flush_right_lines(self):
        """ Return lines that are flush right.

        Note that those lines may well be very short.

        """
        return [v == self.metrics.length.max for v in self.metrics.lengths]

    def short_lines(self):
        """ Return lines much shorter than average. """
        if self.metrics.length.avg is None:
            return []
        thresh = self.metrics.length.avg / 2.0
        return [v < thresh for v in self.metrics.lengths]

    def internal_short_lines(self):
        """ Return lines much shorter than average. Except last line. """
        if self.metrics.length.avg is None:
            return []
        res = self.short_lines()
        # last line should not be considered `short´ even if it is
        res[-1] = False
        return res

    def long_lines(self):
        """ Return lines longer than average. """
        if self.metrics.length.avg is None:
            return []
        return [v > self.metrics.length.avg for v in self.metrics.lengths]

        # a sequence of pars of the same length

        # same indentation pattern as pars before and after

    def header_smells(self):
        """ Test some words we know hint at headers """
        return RE_HEADER_SMELLS.findall(" ".join(self.lines))

    def p_smells(self):
        """ Test some words we know hint at reflowed text. """
        return RE_P_SMELLS.findall(" ".join(self.lines))

    def pre_smells(self):
        """ Test some words we know hint at preformatted text. """
        return RE_PRE_SMELLS.findall(" ".join(self.lines))

    def msg(self, m):
        """ Add to debug message. """
        self.debug_message += m + ' -- '
        return m

    def fix_shorties(self):
        """ Fix any internal short lines. """

        # We also fix the last line, that may naturally be shorter on
        # paragraphs, because it doesn't matter in the case of
        # paragraphs but helps in the case of verse.

        lines = self.lines
        for i in range(1, len(lines) - 1):
            if len(lines[i]) < 25: # ad-hocked value
                if len(lines[i-1]) > 50 and lines[i-1][-1:] != '-':
                    lines[i-1] += ' ' + lines[i]
                    lines[i] = ''
        self.lines = filter(len, lines)



    def analyze(self):
        """ Guess paragraph type -- Part 1.

        Guess if this paragraph is a header, verse, quote or
        anything. Run lots of cunning tests and assign fuzzy scores.

        """

        # header ?

        if all(self.metrics.uppers):
            self.msg("all uppercase")
            self.scores.header *= 2.0

        if any(self.header_smells()):
            self.msg("any header smells")
            self.scores.header *= 2.0

        # analyze indentation

        if half(self.metrics.indents):
            self.msg("half indents")
            self.scores.quote = 2.00

        if most(or_(self.metrics.titles, self.internal_short_lines())):
            self.msg("most (titles or internal_short)")
            self.scores.quote = 2.00
            self.scores.verse *= 1.1 ** len(self)

        # verse or quote ?

        c = count(self.metrics.titles)
        self.scores.verse *= 1.2 ** (c - len(self) / 2.0)
        self.msg("%d titles in %d" % (c, len(self)))

        if self.metrics.rhymes:
            if all(self.metrics.rhymes):
                self.msg("all rhyming_lines")
                self.scores.quote *= 1.2 ** len(self)
                self.scores.verse *= 1.2 ** len(self)

            c = count(self.metrics.rhymes)
            self.scores.verse *= 1.1 ** (c - len(self) / 2.0)
            self.msg("%d rhyming_lines in %d" % (c, len(self)))

            c = count(and_(self.metrics.rhymes, self.short_lines()))
            d = count(self.short_lines())
            self.scores.verse *= 1.1 ** (c - d / 2.0)
            self.msg("%d short rhyming_lines in %d" % (c, d))

        # FIXME: inspect punctuation at end-of-line

        if some(not_(self.flush_left_lines()[1:])):
            self.msg("some (not flush_left)")
            self.scores.verse *= 20.0 # strong indicator

        if any(self.internal_short_lines()):
            self.msg("any internal_short_lines")
            self.scores.verse *= 20.0 # strong indicator

        if any(self.p_smells()):
            self.msg("any p smells")
            self.scores.header = 0.0
            self.scores.quote = 0.0

        if any(self.pre_smells()):
            self.msg("any pre smells")
            self.scores.header = 0.0
            self.scores.quote = 2.0
            self.scores.verse = 2.0


    def analyze_multi(self):
        """ Guess paragraph type -- Part 2.

        Tests spanning multiple paragraphs.

        """

        if self.prev:
            if (any(not_(self.flush_left_lines())) and
                    self.prev.metrics.indents == self.metrics.indents):
                # same indentation scheme (implies same line count)
                self.msg(self.prev.msg("same indentation as neighbor"))
                self.scores.verse *= 2.0
                self.prev.scores.verse *= 2.0

            if self.prev.scores.quote > THRESHOLD and self.prev.scores.verse > 1.0:
                self.msg("follows verse")
                self.scores.quote *= 1.2
                self.scores.verse *= 1.2

            if self.scores.quote > THRESHOLD and self.scores.verse > 1.0:
                self.prev.msg("precedes verse")
                self.prev.scores.quote *= 1.2
                self.prev.scores.verse *= 1.2

            if (self.metrics.cnt_lines == self.prev.metrics.cnt_lines and
                    about_same(self.metrics.length.avg, self.prev.metrics.length.avg)):
                self.msg(self.prev.msg("same look as neighbor"))
                self.scores.verse *= 1.2
                self.prev.scores.verse *= 1.2



class Parser(HTMLParserBase):
    """Parse a Project Gutenberg 'Plain Vanilla Text'

    and convert to xhtml suitable for ePub packaging.

    """

    def __init__(self, attribs=None):
        HTMLParserBase.__init__(self, attribs)
        self.body = 0
        self.max_blanks = 0
        self.pars = []


    def get_charset_from_meta(self):
        """ Parse text for hints about charset. """

        charset = None

        match = parsers.REB_PG_CHARSET.search(self.bytes_content())
        if match:
            charset = match.group(1).decode('ascii')
            info('Got charset %s from pg header' % charset)

        return charset


    def analyze(self):
        """ analyze parsed paragraphs

        do all sorts of smart stuff here

        """

        last_par = None
        for par in self.pars:
            # par.fix_shorties()
            par.metrics = ParagraphMetrics(par)
            par.prev = last_par
            if last_par:
                last_par.next = par
            last_par = par

        for par in self.pars:
            par.analyze()

        # second run for analyses spanning multiple paragraphs
        # may use results from first run
        for par in self.pars:
            par.analyze_multi()

        for par in self.pars:
            par.msg("header: %f" % par.scores.header)
            par.msg("verse: %f" % par.scores.verse)
            par.msg("quote: %f" % par.scores.quote)
            par.msg("center: %f" % par.scores.center)
            par.msg("right: %f" % par.scores.right)


        # translate findings into css styles

        for n, par in enumerate(self.pars):
            par.tag = 'p'
            par.id = "id%05d" % n

            if par.before > 1:
                par.styles['margin-top'] = "%dem" % par.before

            if par.scores.header > THRESHOLD:
                level = max(MAX_BEFORE - par.before, 0)
                par.tag = "h%d"  % (level + 1)
            else:
                if par.scores.quote > THRESHOLD:
                    if par.scores.verse > 1.0:
                        par.styles['white-space'] = 'pre'
                    else:
                        par.styles['margin-left'] = '%d%%' % (
                            par.metrics.indent.first * 100 / 72)
                        par.styles['margin-right'] = par.styles['margin-left']

                    if par.scores.right > THRESHOLD:
                        par.styles['text-align'] = 'right'
                    if par.scores.center > THRESHOLD:
                        par.styles['text-align'] = 'center'

    @staticmethod
    def preformat(line):
        """ Format paragraph as pre. """
        m = RE_INDENT.match(line)
        if m:
            # 0x0a   no-break space
            # 0x2003 em-space
            # 0x2007 figure space
            line = ('&#xa0;' * (m.end() - m.start())) + line[m.end():]
        return line + "<br />\n"


    def ship_out(self, par):
        """ ready paragraph for shipping """
        def italics(s):
            """ replace underscores with <i>...</i> """
            def it_repl(matchobj):
                """ helper """
                return '<i>%s</i>' % matchobj.group(1)

            return RE_ITALICS.sub(it_repl, s)

        if par.styles.get('white-space', '') == 'pre':
            par.lines = map(self.preformat, par.lines)
            del par.styles['white-space']

        text = italics("\n".join(par.lines))
        text = text.replace("--", "&#x2014;")
        text = text.replace("...", "&#x2026;")

        style = ''
        if par.styles:
            styles = []
            for s, v in par.styles.items():
                styles.append("%s: %s" % (s, v))
            style = ' style="' + "; ".join(styles) + '"'

        id_ = ''
        if par.id:
            id_ = ' id="%s"' % par.id

        title = ''
        if options.verbose >= 3 and par.debug_message:
            title = ' title="%s"' % par.debug_message
        # title = ' title="%s"' % repr(most(not_(par.metrics.titles)))

        ns = ' xmlns="%s"' % str(NS.xhtml)
        return '<%s%s%s%s%s>%s</%s>' % (par.tag, ns, id_, style, title, text, par.tag)


    def iterlinks(self): # pylint: disable=R0201
        """ There are no links in text files. """
        return []


    def rewrite_links(self, f): # pylint: disable=R0201
        """ There are no links in text files. """
        return


    def pre_parse(self):
        """ Nothing to do here, because there are no links in text
        files.  iterlinks() will simply return an empty list."""

        debug("GutenbergTextParser.pre_parse() ...")


    def css_content(self):
        default_css = resource_string(
            'ebookmaker.parsers', 'txt2all.css').decode('utf-8')
        return default_css.translate(SPECIALS)


    def parse(self):
        """ Parse the plain text.

        Try to find semantic units in the character soup. """

        debug("GutenbergTextParser.parse() ...")

        if self.xhtml is not None:
            return

        text = self.unicode_content()
        text = parsers.RE_RESTRICTED.sub('', text)
        text = gg.xmlspecialchars(text)

        lines = [line.rstrip() for line in text.splitlines()]
        lines.append("")
        del text

        blanks = 0
        par = Par()

        for line in lines:
            if len(line) == 0:
                blanks += 1
            else:
                if blanks and par.lines: # don't append empty pars
                    par.after = blanks
                    self.pars.append(par)
                    if self.body == 1:
                        self.max_blanks = max(blanks, self.max_blanks)
                    par = Par()
                    par.before = blanks
                    blanks = 0

                par.lines.append(line)

        par.after = blanks
        if par.lines:
            self.pars.append(par)

        lines = None

        self.analyze()

        # build xhtml tree

        em = parsers.em
        self.xhtml = em.html(
            em.head(
                em.title(' '),
                em.meta(**{'http-equiv': 'Content-Style-Type',
                           'content': 'text/css'}),
                em.meta(**{'http-equiv': 'Content-Type',
                           'content': mt.xhtml + '; charset=utf-8'}),
                em.style(self.css_content(), **{'type': 'text/css'})
            ),
            em.body()
        )

        for body in xpath(self.xhtml, '//xhtml:body'):
            xhtmlparser = lxml.html.XHTMLParser()
            for par in self.pars:
                p = etree.fromstring(self.ship_out(par), xhtmlparser)
                p.tail = '\n\n'
                body.append(p)

        self.pars = []

    def _make_coverpage_link(self, coverpage_url=None):
        """ Insert a <link rel="coverpage"> in the html head
        using the image specified by the --cover command-line option
        """

        if coverpage_url:
            for head in xpath(self.xhtml, "/xhtml:html/xhtml:head"):
                head.append(parsers.em.link(rel='icon', href=coverpage_url, format='image/x-cover'))
                debug("Inserted link to coverpage %s." % coverpage_url)
            return

    def add_title(self, dc):
        if dc.title:
            for elem in xpath(self.xhtml, '//xhtml:title'):
                elem.text = f'The Project Gutenberg eBook of {dc.title}, by {dc.authors_short()}'
                break