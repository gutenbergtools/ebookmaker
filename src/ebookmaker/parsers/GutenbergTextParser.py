#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

GutenbergTextParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals

import importlib
import os
import re

import six
import lxml
from lxml import etree

import libgutenberg.GutenbergGlobals as gg
from libgutenberg.GutenbergGlobals import xpath, Struct, NS
from libgutenberg.Logger import debug, error, info, warning
from libgutenberg.MediaTypes import mediatypes as mt

from ebookmaker import parsers
from ebookmaker.CommonCode import Options
from ebookmaker.parsers import HTMLParserBase
from ebookmaker.parsers.boilerplate import strip_headers_from_txt

options = Options()
mediatypes = (mt.txt, )

MAX_BEFORE = 5 # no. of empty lines that mark a <h1>

# A paragraph in which *every* line starts with at least this many spaces was
# hand-indented and hand-wrapped by the transcriber, so its line breaks are
# intentional: keep them instead of reflowing the paragraph.
#
# Without this, verse is recognized mainly by every line starting with a
# capital letter.  Languages that do not capitalize every verse line
# (Finnish, Swedish, German, ...) lose: the penalty grows with the number of
# lines, so long stanzas were always reflowed into a prose block quote.
#
# Set to 0 to restore the old behaviour.  Can be overridden per run with the
# environment variable EBOOKMAKER_VERSE_INDENT.
try:
    VERSE_INDENT = int(os.environ.get('EBOOKMAKER_VERSE_INDENT', 4))
except ValueError:
    VERSE_INDENT = 4

# Strip the common leading indentation from a preformatted (verse) block and
# express it as a CSS margin instead.  The transcriber's indentation is only a
# marker; rendering it as hard &#xa0; characters makes the block start with
# stray spaces and prevents it from adapting to the reader's screen.  Relative
# indentation *inside* the block (a line indented deeper than its siblings) is
# always preserved.
VERSE_STRIP_INDENT = True

# The margin that replaces the stripped indentation.  It is deliberately the
# same for every block: a poem whose stanzas were indented by slightly
# different amounts should still line up, and a title page centered with 30
# spaces should not end up pushed a third of the way across the screen.
VERSE_MARGIN = 5 # per cent

# A block whose longest line falls short of this fraction of the width the
# transcription is filled to was broken by hand, not by a word wrapper.
# Reflowed prose always fills its lines nearly to the margin, so a block that
# never comes close was typed one line at a time: a publisher's imprint, a
# cast of characters, a table of contents, an address, a signature.
SHORT_BLOCK_RATIO = 0.66

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


class MinMaxAvg:
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


class ParagraphMetrics:
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
            debug("No gnu dbm support found. Rhyming dictionary not used.")
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
        self.numbers = list(map(self._isnumbered, lines))
        if most(self.numbers):
            # A numbered list (table of contents, numbered verse, dated
            # entries) is hand-broken just like a capitalized one.  Roman
            # numerals always counted as titles because they are letters;
            # arabic numerals did not, so "1. 2. 3." was reflowed while
            # "I. II. III." was not.  Only applied when most lines are
            # numbered, so that a prose line happening to start with a
            # number ("...Apartment / 60.") is not mistaken for a list.
            self.titles = or_(self.titles, self.numbers)
        self.uppers = list(map(six.text_type.isupper, lines))
        # lines starting with VERSE_INDENT or more spaces
        self.indenteds = [i >= VERSE_INDENT for i in self.indents]

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
    @staticmethod
    def _isnumbered(line):
        """ Return True if the line starts with a number. """
        m = re.search(r'\w', line)
        return bool(m) and m.group(0).isdigit()

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


class Par:
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
        self.next = None
        self.debug_message = ''
        self.force_verse = False
        self.short_block = False
        self.strip_indent = 0
        self.fill_width = 0

        self.scores = Struct()
        for subject in SUBJECTS:
            setattr(self.scores, subject, 1.0)

    def __len__(self):
        return min(len(self.lines), 50)

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

    def deeply_indented(self):
        """ Return True if *every* line starts with VERSE_INDENT+ spaces. """
        if not VERSE_INDENT:
            return False
        return bool(self.metrics.indenteds) and all(self.metrics.indenteds)
    def is_block(self):
        """ Return True if this par is shipped as a hand-broken block. """
        return self.force_verse or self.scores.quote > THRESHOLD
    def is_flowed_prose(self):
        """ Return True if this par is an ordinary, re-wrapped prose par.

        Only such a par wants the first-line indent that the stylesheet gives
        to every <p>.  Hand-broken blocks (verse, title pages, tables of
        contents) do not: their first line would start with a stray indent
        that the transcription does not have.
        """

        return not (self.is_block() or self.short_block or
                    self.scores.header > THRESHOLD)
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

        # hand-indented block: never reflow

        if not any(self.p_smells()):
            if self.deeply_indented():
                self.msg("every line indented >= %d" % VERSE_INDENT)
                self.force_verse = True

            elif (self.fill_width and self.metrics.lengths and
                  max(self.metrics.lengths) < self.fill_width * SHORT_BLOCK_RATIO):
                self.msg("no line reaches %d of %d columns" % (
                    max(self.metrics.lengths), self.fill_width))
                self.short_block = True
                if self.metrics.cnt_lines > 1:
                    self.force_verse = True

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
        self.scores.verse *= 1.2 ** (min(c - len(self.lines), 50) / 2.0)
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
        self.text = ""
        self.pg_header = ""
        self.pg_footer = ""
        
    def unicode_content(self):
        return self.pg_header + self.text + self.pg_footer

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

        # The width the transcription is filled to.  Taken as a high
        # percentile rather than the maximum, so that one stray long line
        # does not set the standard for the whole book.
        lengths = sorted(len(line) for par in self.pars for line in par.lines)
        fill_width = lengths[int(len(lengths) * 0.9)] if lengths else 0
        for par in self.pars:
            par.fill_width = fill_width

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
                # Kill the stylesheet's first-line indent on blocks that were
                # broken by hand.  The stylesheet only suppresses it after a
                # heading, so the *first* stanza of a poem looked right while
                # every following stanza -- and every line of a title page or
                # a table of contents -- started with a stray indent.
                if par.is_block():
                    par.styles['text-indent'] = '0'
                elif par.short_block or par.metrics.cnt_lines == 1:
                    # A lone line is ambiguous: in a novel it is a one line
                    # prose paragraph and keeps its indent; between headings
                    # and hand-broken blocks it is front matter -- a byline,
                    # an imprint, a section title, a numbered subtitle.
                    neighbours = [p for p in (par.prev, par.next) if p]
                    if not any(p.is_flowed_prose() for p in neighbours):
                        par.styles['text-indent'] = '0'

                if par.is_block():
                    # force_verse: hand-indented, keep the line breaks
                    if par.force_verse or par.scores.verse > 1.0:
                        par.styles['white-space'] = 'pre'
                        if VERSE_STRIP_INDENT and par.metrics.indents:
                            par.strip_indent = min(par.metrics.indents)
                            if par.strip_indent:
                                par.styles['margin-left'] = '%d%%' % VERSE_MARGIN
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
            if par.strip_indent:
                n = par.strip_indent
                par.lines = [line[n:] for line in par.lines]
            if par.lines:
                # A block never starts indented relative to its own body:
                # the blank line above it is what separates it from the
                # previous paragraph.  Indentation on *later* lines is
                # meaningful and is kept.
                par.lines[0] = par.lines[0].lstrip(' ')
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


    def iterlinks(self):
        """ There are no links in text files. """
        return []


    def rewrite_links(self, f):
        """ There are no links in text files. """
        return


    def pre_parse(self):
        """ Nothing to do here, because there are no links in text
        files.  iterlinks() will simply return an empty list."""

        debug("GutenbergTextParser.pre_parse() ...")


    def css_content(self):
        ref = importlib.resources.files('ebookmaker.parsers').joinpath('txt2all.css')
        default_css = ref.read_bytes().decode('utf-8')

        return default_css


    def parse(self):
        """ Parse the plain text.

        Try to find semantic units in the character soup. """

        debug("GutenbergTextParser.parse() ...")

        if self.xhtml is not None:
            return

        text = HTMLParserBase.unicode_content(self)
        self.text, self.pg_header, self.pg_footer = strip_headers_from_txt(text)
        if 'x-header' in self.pg_header and options.production:
            error('header marker is missing in %s', self.attribs.url)
        if 'x-header' in self.pg_footer and options.production:
            error('footer marker is missing in %s', self.attribs.url)
        text = self.text
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
                em.meta(**{'name': 'viewport',
                           'content': 'width=device-width, initial-scale=1'}),
                em.meta(**{'http-equiv': 'Content-Style-Type',
                           'content': 'text/css'}),
                em.meta(**{'http-equiv': 'Content-Type',
                           'content': mt.xhtml + '; charset=utf-8'}),
                em.style(self.css_content(), **{'type': 'text/css'})
            ),
            em.body()
        )

        for body in xpath(self.xhtml, '//xhtml:body'):
            xhtmlparser = lxml.html.XHTMLParser(huge_tree=True)
            pg_header_pre = etree.Element(NS.xhtml.pre)
            pg_header_pre.attrib['id'] = 'pg-header'
            pg_header_pre.text = self.pg_header
            body.append(pg_header_pre)
            for par in self.pars:
                p = etree.fromstring(self.ship_out(par), xhtmlparser)
                p.tail = '\n\n'
                body.append(p)
            pg_footer_pre = etree.Element(NS.xhtml.pre)
            pg_footer_pre.text = self.pg_footer
            pg_footer_pre.attrib['id'] = 'pg-footer'
            body.append(pg_footer_pre)

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
        """ add title from dc object """
        if dc.title:
            for elem in xpath(self.xhtml, '//xhtml:title'):
                dc.title = re.sub(r'\s*[\r\n]+\s*', '\n', dc.title)
                elem.text = f'The Project Gutenberg eBook of {dc.title}, by {dc.authors_short()}'
                break
