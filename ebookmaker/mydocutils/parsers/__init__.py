#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

RST parser module.

Copyright 2010-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

A slightly modified RST parser for docutils.

"""

from __future__ import unicode_literals

import collections
import re
import itertools
from functools import partial

import six

from docutils import nodes, statemachine
from docutils.utils import unescape
import docutils.parsers.rst
from docutils.parsers.rst import Directive, directives, states, roles, frontend
from docutils.parsers.rst.directives import body
from docutils.parsers.rst.directives import tables
from docutils.parsers.rst.directives import images
from docutils.utils import punctuation_chars

from libgutenberg.Logger import error, warning, info, debug

from ebookmaker.parsers import BROKEN
from ebookmaker.mydocutils import nodes as mynodes
from ebookmaker.mydocutils.transforms import parts

# pylint: disable=W0142, W0102

image_align_values  = ('left', 'center', 'right')
image_float_values  = ('none', 'here', 'top', 'bottom', 'page')
table_hrules_values = ('none', 'table', 'rows')
table_vrules_values = ('none', 'table', 'columns')
entry_align_values  = ('left', 'center', 'right', 'justify')
entry_valign_values = ('top',  'middle', 'bottom')

def float_arg (argument):
    """
    Converts the argument into a float.  Raises ValueError for
    non-numeric values.  (Directive option conversion function.)
    """
    try:
        return float (argument)
    except ValueError:
        raise ValueError ('non-numeric value; must be numeric')

def quoted_string (argument):
    """
    Unquotes the argument into a string.  Raises ValueError for
    unquoted values.  (Directive option conversion function.)
    """

    m = re.match ("^'(.*?)'$", argument)
    if m:
        return m.group (1)
    raise ValueError ('non-numeric value; must be numeric')

def choice (values, argument):
    """
    Checks an actual value against a list of approved values.
    Raises ValueError if the value is not found in the list of values.
    Usage: option_spec = {'option' : functools.partial (choice, list_of_values) }
    """
    return directives.choice (argument, values)


def multi_choice (values, argument):
    """
    Checks a space-separated list of actual values against a list of approved values.
    Raises ValueError if it finds any value that is not in the list.
    Usage: option_spec = {'option' : functools.partial (multi_choice, list_of_values) }
    """
    entries = argument.split ()
    for e in entries:
        directives.choice (e, values)
    return entries


def class_option_add_remove (argument):
    """
    Convert the argument into a list of ID-compatible strings and return it.
    (Directive option conversion function.)

    Raise ``ValueError`` if no argument is found.
    """
    if argument is None:
        raise ValueError('argument required but none supplied')
    names = argument.split()
    class_names = []
    for name in names:
        if name.startswith ('-'):
            class_name = '-' + nodes.make_id(name[1:])
        else:
            class_name = nodes.make_id(name)
        if not class_name:
            raise ValueError('cannot make "%s" into a class name' % name)
        class_names.append(class_name)
    return class_names


def string2lines (astring, tab_width=8, convert_whitespace=0,
                  whitespace=re.compile('[\v\f]')):
    """
    Swiped from statemachine.py and tweaked to only rstrip U+0020 spaces.

    Return a list of one-line strings with tabs expanded, no newlines, and
    trailing whitespace stripped.

    Each tab is expanded with between 1 and `tab_width` spaces, so that the
    next character's index becomes a multiple of `tab_width` (8 by default).

    Parameters:

    - `astring`: a multi-line string.
    - `tab_width`: the number of columns between tab stops.
    - `convert_whitespace`: convert form feeds and vertical tabs to spaces?
    """
    if convert_whitespace:
        astring = whitespace.sub (' ', astring)
    return [s.expandtabs (tab_width).rstrip (' ') for s in astring.splitlines ()]


class Style (Directive):
    """ Set presentational preferences for docutils element.

    """

    optional_arguments = 1
    has_content = True

    option_spec = {
        'class': class_option_add_remove,
        'name': directives.unchanged,
        'language': directives.class_option, # FIXME: a lang not a class
        'before': quoted_string,
        'after': quoted_string,
        'display': directives.unchanged,
        'formats': directives.unchanged,
        'titlehack': directives.flag, # see StyleTransform

        # images
        # note: figwidth and figclass can be set using width and class on the figure node
        'align': partial (choice, entry_align_values + entry_valign_values),
        'width': directives.length_or_percentage_or_unitless,
        'float': partial (multi_choice, image_float_values),

        # tables
        'hrules': partial (multi_choice, table_hrules_values),
        'vrules': partial (multi_choice, table_vrules_values),
        'aligns': partial (multi_choice, entry_align_values),
        'vertical-aligns': partial (multi_choice, entry_valign_values),
        'tabularcolumns': directives.unchanged,
        'widths': directives.positive_int_list,
    }

    def run (self):
        if self.arguments:
            self.options['selector'] = self.arguments[0]
        if 'language' in self.options:
            self.options['class'].extend (['language-' + x for x in self.options['language']])
            del self.options['language']

        pending = nodes.pending (parts.StyleTransform, self.options)
        self.state_machine.document.note_pending (pending)

        if self.content:
            # parse content into pending node
            self.state.nested_parse (self.content, self.content_offset, pending)

        return [pending]


class VSpace (Directive):
    """
    Directive to insert vertical spacing or pagebreaks.
    """

    required_arguments = 0
    optional_arguments = 1

    def run (self):
        arg = self.arguments[0] if self.arguments else self.name

        if arg in ('clearpage', 'cleardoublepage', 'vfill',
                   'frontmatter', 'mainmatter', 'backmatter'):
            page = mynodes.page ()
            page['classes'].append (arg)
            return [page]
        else:
            try:
                arg = abs (int (arg))
            except ValueError:
                raise self.error ('Unknown argument "%s" for "%s" directive.' % (arg, self.name))

            if arg == 0:
                nl = mynodes.newline ()
                nl['classes'].append ('white-space-pre-line')
                return [nl]

            page = mynodes.page ()
            page['classes'].append ('vspace')
            page['length'] = arg
            return [page]


class EndSection (Directive):
    """ Closes section. """

    def run (self):
        debug ('Endsection directive state: %s' % self.state)
        # back out of lists, etc.
        if isinstance (self.state, states.SpecializedBody):
            debug ('Backing out of list')
            self.state_machine.previous_line (2) # why do we need 2 ???
        raise EOFError


class DropCap (Directive):
    """ Puts a dropcap onto the next paragraph.

    """

    required_arguments = 1
    optional_arguments = 1
    final_argument_whitespace = True

    option_spec = { 'class': directives.class_option,
                    'name': directives.unchanged,
                    'image': directives.unchanged,
                    'lines': directives.positive_int,
                    'raise': float_arg,
                    'indents': directives.unchanged, # array of tex dimen
                    'ante': directives.unchanged }

    def run (self):
        self.options['char'] = self.arguments[0]
        if len (self.arguments) >= 2:
            self.options['span'] = self.arguments[1]
        pending = nodes.pending (parts.DropCapTransform, self.options)
        self.state_machine.document.note_pending (pending)
        return [pending]


class Example (Directive):
    """
    Builds a literal block with the example source followed by a rendered block.
    """

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True
    example_count = 0

    option_spec = { 'class': directives.class_option,
                    'name': directives.unchanged,
                    'float': partial (multi_choice, image_float_values),
                    'norender': directives.flag }

    def run(self):
        nodelist = []

        if len (self.arguments) >= 1:
            nodelist.append (nodes.title ('', self.arguments[0]))

        literal = nodes.literal_block ('', '\n'.join (self.content))
        literal['classes'].append ('example-source')
        nodelist.append (literal)

        if 'norender' not in self.options:
            container = nodes.container ()
            container['classes'].append ('example-rendered')
            self.state.nested_parse (self.content, self.content_offset,
                                     container)
            nodelist.append (container)

        topic = nodes.topic ('', *nodelist)
        topic['classes'] += ['example']
        topic['classes'] += self.options.get ('class', [])
        Example.example_count += 1
        target = lox_target (topic, 'example-%d' % Example.example_count)
        self.state_machine.document.note_implicit_target (target, target)
        return [topic]


def lox_target (x, id_):
    id_ = nodes.make_id (id_)
    x['ids'].append (id_)
    return x


class Table (tables.RSTTable):

    option_spec = tables.RSTTable.option_spec.copy ()
    option_spec.update ( {
        'align': partial (choice, image_align_values),
        'float': partial (multi_choice, image_float_values),
        'hrules': partial (multi_choice, table_hrules_values),
        'summary': directives.unchanged,
        'tabularcolumns': directives.unchanged,
        'vrules': partial (multi_choice, table_vrules_values),
        'width': directives.length_or_percentage_or_unitless,

        'aligns': partial (multi_choice, entry_align_values),
        'vertical-aligns': partial (multi_choice, entry_valign_values),
        'widths': directives.positive_int_list,
        } )

    table_count = 0

    def run (self):

        def apply_options_to_colspecs (option, name):
            options = self.options.get (option, [])
            for colspec, option in zip (table.traverse (nodes.colspec), options):
                colspec[name] = option

        res = tables.RSTTable.run (self)
        table = res[0]

        for name in ('align', 'float', 'hrules', 'summary', 'tabularcolumns', 'vrules', 'width'):
            if name in self.options:
                table[name] = self.options[name]

        Table.table_count += 1
        target = lox_target (table, 'table-%d' % Table.table_count)
        self.state_machine.document.note_implicit_target (target, target)

        # HTML doesn't recognize align in colspec ???
        apply_options_to_colspecs ('aligns', 'align')
        apply_options_to_colspecs ('vertical-aligns', 'valign')
        apply_options_to_colspecs ('widths', 'colwidth')

        return res


class Figure (images.Figure):
    """ Override standard figure. Allow use of no filename. """

    option_spec = images.Figure.option_spec.copy ()
    option_spec.update ( {
        'float': partial (multi_choice, image_float_values),
        } )

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    figure_count = 0

    def run (self):
        if not self.arguments:
            # no filename given: use `broken´ picture
            self.arguments.append (BROKEN)
            self.options.setdefault ('figwidth', '80%')
            self.options.setdefault ('width',    '5%')

        res = images.Figure.run (self)

        figure = res[0]
        Figure.figure_count += 1
        target = lox_target (figure, 'figure-%d' % Figure.figure_count)
        self.state_machine.document.note_implicit_target (target, target)

        return res


class TocEntry (Directive):
    """ Directive to inject TOC entry.

    This directive changes the next header, so we can choose the
    text of the TOC entry.

    The 'depth' option changes toc gathering level.

    We insert a pending node that gets transformed in later stages of processing.

    """

    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    has_content = True

    option_spec = { 'class': directives.class_option,
                    'name': directives.unchanged,
                    'depth': directives.nonnegative_int }

    def run (self):
        details = {}
        if 'depth' in self.options:
            details['toc_depth'] = self.options['depth']

        container = nodes.container ()

        if self.arguments:
            container += nodes.inline ('', self.arguments[0])

        self.state.nested_parse (self.content, self.content_offset,
                                 container)

        container['classes'] += self.options.get ('class', [])
        if container.astext ():
            details['content'] = container
        else:
            details['content'] = None # flag: supress toc entry

        pending = nodes.pending (parts.TocEntryTransform, details)
        self.state_machine.document.note_pending (pending)
        return [pending]


def option_check_backlinks (arg): # pylint: disable=E0213
    """ Argument checker function. """
    value = directives.choice (arg, ('top', 'entry', 'none'))
    return None if value == 'none' else value


class GeneratedSection (Directive):
    """ Base class for generated sections (Contents, Footnotes, Citations, etc.). """

    required_arguments = 0
    optional_arguments = 1   # optional section name
    final_argument_whitespace = True

    option_spec = { 'class': directives.class_option,
                    'name': directives.unchanged,
                    'local': directives.flag,
                    'backlinks': option_check_backlinks,
                    'page-numbers': directives.flag }

    def run (self, transform, extraclasses = None):
        """
        extra_classes: classes set on container element
        """

        document = self.state_machine.document
        extraclasses = extraclasses or []

        self.options['directive_name'] = self.name
        extraclasses.append (self.name) # contents, loa, lof, lot, footnotes

        container = nodes.container ()
        container['classes'] += self.options.get ('class', [])
        if 'depth' in self.options:
            container['toc_depth'] = self.options['depth']

        pending = nodes.pending (transform, self.options)
        document.note_pending (pending)
        container += pending

        pending = nodes.pending (parts.EmptySectionRemover)
        document.note_pending (pending)

        entries = []

        if 'local' in self.options:
            container['classes'] += ['local']
            container['classes'] += ['local-' + x for x in extraclasses]
            entries = [container]
        elif self.arguments:
            container['classes'] += extraclasses

            section = nodes.section ()
            title_text = self.arguments[0]
            text_nodes, dummy_messages = self.state.inline_text (title_text,
                                                          self.lineno)
            title = nodes.title (title_text, '', *text_nodes)
            title['toc_entry'] = None # default for generated sections is: no toc entry
            section += title
            section += pending
            section += container
            document.note_implicit_target (section)
            entries = [section]
        else:
            container['classes'] += extraclasses
            entries = [pending, container]

        return entries


class Contents (GeneratedSection):
    """ Table of contents. """

    option_spec = GeneratedSection.option_spec.copy ()
    option_spec.update ( {'depth': directives.nonnegative_int } )

    def run (self):
        return GeneratedSection.run (self, parts.ContentsTransform)


class ListOfAnything (GeneratedSection):
    """ List of Figures or List of Tables or ... """

    option_spec = GeneratedSection.option_spec.copy ()
    option_spec.update ( {'selector': directives.unchanged } )

    def run (self):
        return GeneratedSection.run (self, parts.ListOfAnythingTransform, ['loa'])


class Footnotes (GeneratedSection):
    """ Footnote section. """

    option_spec = GeneratedSection.option_spec.copy ()
    option_spec.update ( {'backlinks': directives.flag } )

    def run (self):
        return GeneratedSection.run (self, parts.FootnotesDirectiveTransform)


class Container (body.Container):
    """ Backward compatibility: reinstate Container :class: option. """

    option_spec = body.Container.option_spec.copy ()
    option_spec.update ( {'class': directives.class_option,
                          'align': partial (choice, image_align_values) } )

    def run (self):
        nodes =  body.Container.run (self)
        nodes[0]['classes'].extend (self.options.get ('class', []))
        if 'align' in self.options:
            nodes[0]['align'] = self.options['align']
        return nodes


class Meta (Directive):
    """ Collect meta fields into document.meta_block, which is a dict of lists. """

    has_content = True

    def run (self):
        self.assert_has_content ()
        doc = self.state_machine.document

        node = nodes.Element () # temp container node

        new_line_offset, blank_finish = self.state.nested_list_parse (
            self.content, self.content_offset, node,
            initial_state='FieldList', blank_finish=1)

        if (new_line_offset - self.content_offset) != len(self.content):
            # incomplete parse of block?
            error = self.state_machine.reporter.error (
                'Invalid meta directive.',
                nodes.literal_block (self.block_text, self.block_text),
                line = self.lineno)
            return [error]

        # walk children of node and extract data
        for field in node:
            if isinstance (field, nodes.field):
                field_name, field_body = field.children
                doc.meta_block[field_name.astext ()].append (field_body.astext ())
            elif isinstance (field, nodes.Bibliographic):
                doc.meta_block[field.__class__.__name__].append (field.astext ())

        return []


# roles

def id_generator (i = 0):
    """ Generate an id for the TOC to link to. """
    while True:
        yield 'autoid-%05d' % i
        i += 1

id_generator = id_generator ()

def mk_pageno_target (title, id_, class_, document):
    """ Create and initialize a target node. """

    id_ = nodes.make_id (id_)

    if id_ in document.ids:
        # already taken, make a new one
        id_ = six.next (id_generator)

    target = nodes.target ('', '')
    target['ids'].append (id_)
    target['classes'].append (class_)
    # if 'classes' in options:
    #     target['classes'].extend (options['classes'])
    target[class_] = title
    target['html_attributes'] = {'title' : title}
    target['refid'] = None # avoid transform moving this target into next section

    document.note_implicit_target (target) # pylint: disable=E1101

    return target


class Role:
    """
    Base class for our roles.
    """

    def __init__ (self, options = {}, content = []):
        self.options = { 'class': directives.class_option }
        self.options.update (options)

    def __call__ (self, role, rawtext, text, lineno, inliner, options={}, content=[]):
        """ return [nodelist], [messagelist] """
        roles.set_classes (options)
        inline = nodes.inline (rawtext, unescape (text), **options)
        inline['classes'].append (role)
        return [ inline ], []


class Inliner (states.Inliner):
    """ Inliner that recognizes [pg n], [ln n], and [var x]. """

    def __init__ (self):
        self.start_string_prefix = (u'(^|(?<=\\s|[%s%s]))' %
                               (punctuation_chars.openers,
                                punctuation_chars.delimiters))
        self.end_string_suffix = (u'($|(?=\\s|[\x00%s%s%s]))' %
                             (punctuation_chars.closing_delimiters,
                              punctuation_chars.delimiters,
                              punctuation_chars.closers))
        self.re_pageno = re.compile (self.start_string_prefix +
                                r"(\[pg!?\s*(?P<pageno>[-ivxlc\d]+)(?:\s+(?P<imgoff>[\d]+))?\])" +
                                self.end_string_suffix + r'\s*', re.IGNORECASE)
        self.re_pageref = re.compile (self.start_string_prefix +
                                r"(\[pg\s*(?P<pageno>[-ivxlc\d]+)\]_)" +
                                self.end_string_suffix, re.IGNORECASE)
        self.re_lineno = re.compile (self.start_string_prefix +
                                r"(\[ln!?\s*(?P<lineno>[\d]+)\])" +
                                self.end_string_suffix + r'\s*', re.IGNORECASE)
        self.re_lineref = re.compile (self.start_string_prefix +
                                r"(\[ln\s*(?P<lineno>[\d]+)\]_)" +
                                self.end_string_suffix, re.IGNORECASE)
        self.re_variable = re.compile (self.start_string_prefix +
                                r"(\[var\s+(?P<name>[-_\w\d]+)\])" +
                                self.end_string_suffix + r'\s*', re.IGNORECASE)
        states.Inliner.__init__ (self)


    def init_customizations (self, settings):
        """ Setting-based customizations; run when parsing begins. """
        super().init_customizations (settings)

        # self.implicit_dispatch.append ((self.re_newline, self.newline))
        self.implicit_dispatch.append ((self.re_variable, self.variable))
        if settings.page_numbers:
            # pylint: disable=E1101
            self.implicit_dispatch.append ((self.re_pageno,  self.pageno_target))
            self.implicit_dispatch.append ((self.re_pageref, self.pageno_reference))
            self.implicit_dispatch.append ((self.re_lineno,  self.lineno_target))
            self.implicit_dispatch.append ((self.re_lineref, self.lineno_reference))


    def variable (self, match, dummy_lineno):
        """ Makes `[var x]` into implicit markup for a variable named x. """
        n = mynodes.variable ()
        n['name'] = match.group ('name')
        return [n]


    def newline (self, match, dummy_lineno):
        """ Makes `[br]` into implicit markup for new line. """
        n = mynodes.newline ()
        n['classes'].append ('white-space-pre-line')
        return [n]


    def pageno_target (self, match, dummy_lineno):
        """ Makes [pg 42 69] into implicit markup for page numbers.

        42 is the page number
        69 is the index of the page into the array of page images

        """

        text = match.group (0)
        if text.startswith ('[pg'):
            title = match.group ('pageno')
            target = mk_pageno_target (title, 'page-%s' % title, 'pageno', self.document)
            imgoff = match.group ('imgoff')
            if imgoff:
                target['imgoff'] = imgoff
            if '!' in text:
                target['classes'].append ('invisible')
            return [target]
        else:
            raise states.MarkupMismatch


    def pageno_reference (self, match, dummy_lineno):
        """ Makes [pg 99]_ into implicit markup for page reference. """

        text = match.group (0)
        if text.startswith ('[pg'):
            text = match.group ('pageno')
            id_ = nodes.make_id ('page-%s' % text)
            reference = nodes.reference ('', unescape (text))
            reference['refid'] = id_
            return [reference]
        else:
            raise states.MarkupMismatch


    def lineno_target (self, match, dummy_lineno):
        """ Makes [ln 999] into implicit markup for line numbers. """

        text = match.group (0)
        if text.startswith ('[ln'):
            title = match.group ('lineno')
            target = mk_pageno_target (title, 'line-%s' % title, 'lineno', self.document)
            if '!' in text:
                target['classes'].append ('invisible')
            return [target]
        else:
            raise states.MarkupMismatch


    def lineno_reference (self, match, dummy_lineno):
        """ Makes [ln 999]_ into implicit markup for line reference. """

        text = match.group (0)
        if text.startswith ('[ln'):
            text = match.group ('lineno')
            id_ = nodes.make_id ('line-%s' % text)
            reference = nodes.reference ('', unescape (text))
            reference['refid'] = id_
            return [reference]
        else:
            raise states.MarkupMismatch

# copy states.Inliner properties to Inliner so that init_customizations method works
# this is needed because init_customizations depends on locals(), which seems like a bad practice
#
for prop, val in states.Inliner.__dict__.items():
    if not prop.startswith('_'):
        setattr(Inliner, prop, val)


class Body (states.Body):
    """ Body class with fix for line block indentation. """

    def nest_line_block_level (self, block, indent_level, indent_levels):
        """ Recursive part of nest_line_block_segment. """

        last_indent = indent_levels[indent_level]
        line_block = nodes.line_block ()
        while len (block):
            indent = block[0].indent
            if indent < last_indent:
                break # end recursion
            if indent > last_indent:
                line_block.append (
                    self.nest_line_block_level (block, indent_level + 1, indent_levels))
                continue
            line_block.append (block.pop (0))
        return line_block


    def nest_line_block_segment (self, block):
        """
        Replacement for docutils.states.Body.nest_line_block_segment
        with fix for correct indentation.
        """

        # indent_levels maps indent level to no. of leading spaces
        indent_levels = sorted (set ( [item.indent for item in block] ))

        new_block = self.nest_line_block_level (block, 0, indent_levels)
        block.replace_self (new_block)


class Parser (docutils.parsers.rst.Parser):
    """ Slightly modified rst parser. """

    def __init__ (self):

        self.settings_spec = self.settings_spec + (
            'reStructuredText Parser Options',
            None,
            (('Recognize page numbers and page references (like "[pg n] and [pg n]_").',
             ['--page-numbers'],
             {'action': 'store_true', 'validator': frontend.validate_boolean}),))

        settings_defaults = {
            'no_figures': False,
            'get_resource': None,
            'get_image_size': None,
            }

        directives.register_directive ('contents',        Contents)  # replaces standard directive
        directives.register_directive ('container',       Container) # replaces standard directive
        directives.register_directive ('lof',             ListOfAnything)
        directives.register_directive ('lot',             ListOfAnything)
        directives.register_directive ('table',           Table)     # replaces standard directive
        directives.register_directive ('figure',          Figure)    # replaces standard directive
        directives.register_directive ('meta',            Meta)      # replaces standard directive
        directives.register_directive ('toc-entry',       TocEntry)
        directives.register_directive ('footnotes',       Footnotes)
        directives.register_directive ('dropcap',         DropCap)
        directives.register_directive ('example',         Example)
        directives.register_directive ('style',           Style)

        directives.register_directive ('endsection',      EndSection)

        directives.register_directive ('vspace',          VSpace)
        directives.register_directive ('vfill',           VSpace)
        directives.register_directive ('clearpage',       VSpace)
        directives.register_directive ('cleardoublepage', VSpace)
        directives.register_directive ('frontmatter',     VSpace)
        directives.register_directive ('mainmatter',      VSpace)
        directives.register_directive ('backmatter',      VSpace)

        docutils.parsers.rst.Parser.__init__ (self)
        self.inliner = Inliner ()


    def register_local_role (self, name, role):
        """ Helper """

        r = role ()
        r.role_name = name
        roles.register_local_role (name, r)


    def parse (self, inputstring, document):
        """Parse `inputstring` and populate `document`, a document tree."""
        document.meta_block = collections.defaultdict (list)

        # following code swiped from docutils/parsers/rst/__init__.py
        # and tweaked to call our own string2lines (that only strips
        # U+0020 trailing whitespace).
        # docutils.parsers.rst.Parser.parse (self, inputstring,
        # document)

        self.setup_parse (inputstring, document)
        self.statemachine = states.RSTStateMachine (
              state_classes = self.state_classes,
              initial_state = self.initial_state,
              debug = document.reporter.debug_flag)
        inputlines = string2lines (
              inputstring, tab_width = document.settings.tab_width,
              convert_whitespace = 1)
        self.statemachine.run (inputlines, document, inliner = self.inliner)
        self.finish_parse ()


    def get_transforms (self):
        tfs = docutils.parsers.rst.Parser.get_transforms (self)
        tfs.extend ([
                parts.PageNumberMoverTransform,
                parts.TocPageNumberTransform,
                parts.TextTransform,
                parts.NodeTypeTransform,
                parts.InlineImageTransform,
                parts.SetDefaults,
                parts.AlignTransform,
                parts.BlockImageWrapper,
                parts.TitleLevelTransform,
                parts.DocInfoCollector,
                parts.FirstParagraphTransform,
                parts.Lineblock2VSpace
                ])
        return tfs


# horrible hack, substitute our bug-fixed Body class
states.state_classes = (Body, ) + states.state_classes[1:]
