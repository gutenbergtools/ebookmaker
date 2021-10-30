# -*- coding: utf-8 -*-
# Copyright: This module is put into the public domain.
# Author: Marcello Perathoner <webmaster@gutenberg.org>

"""
Nroff writer for reStructuredText.

This module is more suitable for writing novel-type books than
documentation.

To process into plain text use:

  ``groff -t -K utf8 -T utf8 input.nroff > output.txt``

"""

from __future__ import unicode_literals

__docformat__ = 'reStructuredText'

import collections
import re

import six

from docutils import nodes, frontend
from docutils.writers.html4css1 import SimpleListChecker

from ebookmaker.mydocutils import writers
from ebookmaker.mydocutils.transforms import parts

from libgutenberg.Logger import info, debug, warning, error


LINE_WIDTH             = 66
TABLE_WIDTH            = 66 # max. table width

BLOCKQUOTE_INDENT      =  4
LIST_INDENT            =  2
FOOTNOTE_INDENT        =  6
CITATION_INDENT        = 10
FIELDLIST_INDENT       =  7
DEFINITION_LIST_INDENT =  7
OPTION_LIST_INDENT     =  7

NROFF_PREAMBLE = r""".\" -*- mode: nroff -*- coding: {encoding} -*-
.\" This file produces plain text. Usage:
.\"   $ groff -t -K {device} -T {device} this_file > output.txt
.
.ll 72m
.po 0
.ad l           \" text-align: left
.nh             \" hyphenation: off
.cflags 0 .?!   \" single sentence space
.cflags 0 -\[hy]\[em]   \" don't break on -
.
.de nop
..
.blm nop        \" do nothing on empty line
.
.nr [env_cnt] 0
.ev 0           \" start in a defined environment
.
.de push_env
.br
.nr last_env \\n[.ev]            \" save current environment name
.nr env_cnt +1   \" generate new environment name
.ev \\n[env_cnt]
.evc \\n[last_env]
..
.de pop_env
.br
.ev
.nr env_cnt -1
..
.
"""

NROFF_POSTAMBLE = r""".
.\" End of File
"""

def nroff_units (length_str, reference_length = None):
    """ Convert rst units to Nroff units. """

    match = re.match (r'(\d*\.?\d*)\s*(\S*)', length_str)
    if not match:
        return length_str

    value, unit = match.groups ()

    if unit in ('', 'u'):
        return value

    # percentage: relate to current line width
    elif unit == '%':
        reference_length = reference_length or LINE_WIDTH
        return int (float (value) / 100.0 * reference_length)

    return length_str


class InheritTransform (parts.InheritTransform):
    pass


class Writer (writers.Writer):
    """ A plaintext writer thru nroff. """

    supported = ('nroff',)
    """Formats this writer supports."""

    output = None
    """Final translated form of `document`."""

    settings_spec = (
        'Nroff-Specific Options',
        None,
        (('Should lists be compacted when possible?',
          ['--compact-lists'],
          {'default': 1,
           'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Which encoding are we targeting? (As hint to the writer.).',
          ['--encoding'],
          {'default': 'utf-8',
           'validator': frontend.validate_encoding}),
         ))

    settings_defaults = {
        'encoding': 'utf-8',
        }

    config_section = 'NROFF writer'

    def get_transforms (self):
        tfs = writers.Writer.get_transforms (self)
        return tfs + [parts.TextNodeWrapper, InheritTransform]

    def __init__ (self):
        writers.Writer.__init__ (self)
        self.translator_class = Translator


class TablePass2 (nodes.SparseNodeVisitor):

    """
    Makes a second pass over table to build tbl format specification.
    """

    def __init__ (self, document, table, rows, cols):
        nodes.SparseNodeVisitor.__init__ (self, document)
        self.cols = cols
        self.types = ['-'] * (rows * cols)
        self.i = 0

        self.table_width = nroff_units (table.get ('width', '100%'), TABLE_WIDTH)
        colspecs = list (table.traverse (nodes.colspec))
        self.table_width -= len (colspecs) * 2

    def visit_entry (self, node):
        """ Called on each table cell. """

        if 'vspan' in node:
            raise nodes.SkipNode

        rows = node.get ('morerows', 0) + 1
        cols = node.get ('morecols', 0) + 1

        for j in range (0, cols):
            self.types[self.i + j] = 's'
            for k in range (1, rows):
                self.types[self.i + (k * self.cols) + j] = '^'

        align = node.colspecs[0].get ('align', 'left')
        align = { 'right': 'r', 'center': 'c' }.get (align, 'l')
        self.types[self.i] = align # l, r or c

        valign = node.colspecs[0].get ('valign', 'middle')
        valign = { 'top': 't', 'bottom': 'd' }.get (valign, '')
        self.types[self.i] += valign # t or d

        if len (node.colspecs) == 1: # no span
            self.types[self.i] += 'w(%d)' % (
                node.colspecs[0]['relative_width'] * self.table_width)

        while self.i < len (self.types) and self.types[self.i] != '-':
            self.i += 1

        raise nodes.SkipNode

    def build_format_spec (self):
        """ Build a tbl format specification for this table. """
        types = zip (*[iter (self.types)] * self.cols) # cluster by row

        types = [' '.join (x) for x in types]
        types = ','.join (types)

        # print types

        return '%s.\n' % types


class Translator (writers.Translator):
    """ nroff translator """

    superscript_digits = '⁰¹²³⁴⁵⁶⁷⁸⁹'

    subscript_digits   = '₀₁₂₃₄₅₆₇₈₉'

    def __init__ (self, document):
        writers.Translator.__init__ (self, document)
        self.settings = document.settings

        self.encoding = self.settings.encoding
        # the name of the groff device
        self.device = { 'utf-8':      'utf8',
                        'iso-8859-1': 'latin1',
                        'us-ascii':   'ascii' }.get (self.encoding, '<device>')
        self.init_translate_maps ()
        self.body = []
        self.context = self.body # start with context == body
        self.docinfo = collections.defaultdict (list)
        self.list_enumerator_stack = []
        self.section_level = 0
        self.vspace = 0 # pending space (need this for collapsing)
        self.last_output_char = '\n' # used to make sure we output \n before commands
        self.field_name = None
        self.compacting = 0 # > 0 if we are inside a compacting list
        self.in_literal = 0 # are we inside one or more literal blocks?


    def preamble (self):
        """ Inserts nroff preamble. """
        return NROFF_PREAMBLE.format (encoding = self.encoding, device = self.device)


    def postamble (self):
        """ Inserts nroff postamble. """
        return NROFF_POSTAMBLE.format (encoding = self.encoding, device = self.device)


    def init_translate_maps (self):
        # see: man groff_char
        self.translate_map = {
            0x0027: r"\(cq",     # ' is non-breaking command
            0x002e: r"\N'46'",   # . is breaking command
            0x005c: r"\(rs",     # \ is escape char
            0x00a0: r"\ ",       # nbsp
            0x00ad: r"\%",       # shy
            0x03c6: r"\(+F",     # curly (text) phi,  | groff inverts
            0x03d5: r"\(*F",     # stroked (math) phi | these two
            }

        self.translate_map_literal = {}
        self.translate_map_literal.update (self.translate_map)
        self.translate_map_literal.update ({
                # by default groff substitutes these chars with chars
                # better suited for typography, but less suited for
                # source code display.  we want the original chars.
                # see: man groff_char
                0x0027: r'\(aq', # apos
                0x002d: r'\-',   # hyphen-minus
                0x005e: r'\(ha', # circumflex
                0x0060: r'\`',   # backtick
                0x007e: r'\(ti', # tilde
                })


    def translate (self, text):
        """ Reduce the charset while keeping text a unicode string. """

        if self.in_literal:
            text = text.translate (self.translate_map_literal)
        else:
            text = text.translate (self.translate_map)

        return text


    def register_classes (self):
        """ Register classes.

        Use a fairly general set of font attributes.

        """

        self.register_class ('simple', 'left',         '.ad l',   '')
        self.register_class ('simple', 'center',       '.ad c',   '')
        self.register_class ('simple', 'centerleft',   '.ad c',   '')
        self.register_class ('simple', 'right',        '.ad r',   '')

        self.register_class ('inline', 'italics',      r'\fI',    r'\fP')
        self.register_class ('inline', 'bold',         r'\fB',    r'\fP')
        self.register_class ('inline', 'monospaced',   r'\fM',    r'\fP')
        self.register_class ('inline', 'superscript',  r'\s-2\u', r'\d\s0')
        self.register_class ('inline', 'subscript',    r'\s-2\d', r'\u\s0')
        self.register_class ('inline', 'small-caps',   r'\fI',    r'\fP')
        self.register_class ('inline', 'gesperrt',     r'\fI',    r'\fP')
        self.register_class ('inline', 'antiqua',      r'\fI',    r'\fP')
        self.register_class ('inline', 'larger',       r'\fI',    r'\fP')
        self.register_class ('inline', 'smaller',      r'\fI',    r'\fP')


    def set_class_on_child (self, node, class_, index = 0):
        """
        Set class `class_` on the visible child no. index of `node`.
        Do nothing if node has fewer children than `index`.
        """
        children = [n for n in node if not isinstance (n, nodes.Invisible)]
        try:
            child = children[index]
        except IndexError:
            return
        child['classes'].append (class_)

    def set_first_last (self, node):
        """ Set class 'first' on first child, 'last' on last child. """
        self.set_class_on_child (node, 'first', 0)
        self.set_class_on_child (node, 'last', -1)

    def cmd (self, cmds):
        """ Add nroff commands. """
        if isinstance (cmds, six.string_types):
            cmds = [cmds]

        if self.last_output_char != '\n':
            self.context.append ('\n')
        for c in cmds:
            if c:
                self.context.append (".%s\n" % c)
                self.last_output_char = '\n'

    def text (self, text):
        """ Output text. """
        if isinstance (text, six.string_types):
            text = [text]

        for t in text:
            if t:
                self.context.append (t)
                self.last_output_char = t[-1]

    def text_or_cmd (self, text_or_cmds):
        """ Try to output the string appropriately. """
        if isinstance (text_or_cmds, six.string_types):
            text_or_cmds = [text_or_cmds]

        for item in text_or_cmds:
            if not item:
                continue
            if item[0] == '.':
                self.cmd (item[1:])
            else:
                self.text (item)

    def backspace (self):
        """ Remove last character from output. """
        self.context[-1] = self.context[-1][:-1]
        while not self.context[-1]:
            self.context.pop ()
        if self.context and self.context[-1]:
            self.last_output_char = self.context[-1][-1]

    def comment (self, text):
        """ Output nroff comment. """
        self.cmd ('\\"%s' % self.translate (text))

    def output_sp (self):
        """ Output spacing and pending stuff. """
        if self.vspace == 1999: # magic number to eat all space
            self.vspace = 0
        if self.vspace:
            self.cmd ('sp' if self.vspace == 1 else 'sp %d' % self.vspace)
            self.vspace = 0

    def br (self):
        """ Insert br command. """
        if self.context[-1] == '.br\n':
            self.cmd ('sp')
        self.cmd ('br')

    def ta (self, indent, text):
        """ Right-tabulate text to indent position. """
        if indent > 1:
            self.cmd ('ta %dmR' % (indent - 1))
            self.text ('\t')
        self.text (text)

    def push (self):
        """ Push environment. """
        self.cmd ('push_env')

    def pop (self):
        """ Pop environment. """
        self.cmd ('pop_env')

    def as_superscript (self, n):
        """ Return n as string using superscript unicode chars. """
        if self.encoding != 'utf-8':
            return '[%d]' % n
        res = ''
        for d in str (n):
            res += self.superscript_digits [int (d)]
        return res

    def br_if_line_longer_than (self, length):
        """ Insert a line break if the line was longer than length.

        Use this to compact lists etc. """

        # we have to break the line to get the length,
        # then we eventually go back
        self.cmd (('br', 'if (\\n[.n] < %dm) .sp -1' % length))
        self.sp (0)

    def indent (self, by = 2):
        """ Indent text. """
        self.cmd ('in +%dm' % by)

    def rindent (self, by = 2):
        """ Indent text on the right side. """
        self.cmd ('ll -%dm' % by)


    def visit_outer (self, node):
        """ Called before visiting a node. """
        # self.comment ("visiting outer: %s" % node.__class__.__name__)

        if node.type != 'text' and 'margin' in node['classes']:
            self.sp ()

        if node.type in ('compound', 'simple'):
            if not isinstance (node, nodes.entry):
                # tbl preprocessor eats some contents of rows
                self.push ()

    def visit_inner (self, node):
        """ Called after visiting a node. """

        # self.comment ("visiting inner: %s" % node.__class__.__name__)

        if node.type == 'simple':
            self.output_sp ()

        if node.type != 'text':
            self.text_or_cmd (self.get_prefix (node.type, node['classes']))

    def depart_inner (self, node):
        """ Called before departing from a node. """

        if node.type != 'text':
            self.text_or_cmd (self.get_suffix (node.type, node['classes']))

        # self.comment ("departing inner: %s" % node.__class__.__name__)

    def depart_outer (self, node):
        """ Called after departing from a node. """

        if node.type != 'text' and 'margin' in node['classes']:
            self.sp ()

        if node.type in ('compound', 'simple'):
            if not isinstance (node, nodes.entry):
                self.pop ()

        # self.comment ("departing outer: %s" % node.__class__.__name__)


    def visit_Text (self, node):
        text = self.translate (node.astext ())

        if hasattr (node, 'attributes') and 'white-space-pre-line' in node.attributes['classes']:
            for line in text.splitlines (True):
                self.text (line)
                if '\n' in line:
                    self.br ()
        else:
            self.text (text)


    def depart_Text (self, node):
        pass


    def visit_inline (self, node):
        pass

    def depart_inline (self, node):
        pass


    # start docinfo elements (parse only for now)

    def visit_docinfo (self, node):
        pass

    def depart_docinfo (self, node):
        pass

    def visit_authors (self, node):
        pass

    def depart_authors (self, node):
        pass

    def visit_field (self, node):
        pass

    def depart_field (self, node):
        pass

    def visit_field_name (self, node):
        self.field_name = node.astext ().lower ().replace (' ', '_')
        raise nodes.SkipNode

    def depart_field_name (self, node):
        pass

    def visit_field_body (self, node, name = None):
        # name either from element or stored by <field_name>
        self.context = self.docinfo[name or self.field_name]

    def depart_field_body (self, node):
        self.context = self.body

    def visit_field_list (self, node):
        self.sp ()
        self.indent (FIELDLIST_INDENT)

    def depart_field_list (self, node):
        pass

    # start admonitions

    def visit_admonition (self, node, name = None):
        if name:
            self.text (name)
            self.sp ()
        else:
            self.br ()
        self.indent (BLOCKQUOTE_INDENT)

    def depart_admonition (self, node):
        pass

    # start definition lists

    def visit_definition_list (self, node):
        self.sp ()
        # self.output_sp ()

    def depart_definition_list (self, node):
        pass

    def visit_definition_list_item (self, node):
        pass

    def depart_definition_list_item (self, node):
        pass

    def visit_term (self, node):
        pass

    def depart_term (self, node):
        self.br_if_line_longer_than (DEFINITION_LIST_INDENT)

    def visit_classifier (self, node):
        pass

    def depart_classifier (self, node):
        pass

    def visit_definition (self, node):
        self.indent (DEFINITION_LIST_INDENT)

    def depart_definition (self, node):
        self.sp ()

    # start option lists

    def visit_option_list (self, node):
        self.sp ()
        # self.output_sp ()

    def depart_option_list (self, node):
        self.output_sp () # clear sp (0)
        self.sp ()

    def visit_option_list_item (self, node):
        pass

    def depart_option_list_item (self, node):
        pass

    def visit_option_group (self, node):
        pass

    def depart_option_group (self, node):
        self.br_if_line_longer_than (OPTION_LIST_INDENT)

    def visit_option (self, node):
        pass

    def depart_option (self, node):
        if 'last' not in node['classes']:
            self.text (', ')

    def visit_option_string (self, node):
        pass

    def depart_option_string (self, node):
        pass

    def visit_option_argument (self, node):
        self.text (node.get ('delimiter', ' '))
        self.text (r'\fI')

    def depart_option_argument (self, node):
        self.text (r'\fP')

    def visit_description (self, node):
        self.indent (OPTION_LIST_INDENT)

    def depart_description (self, node):
        self.sp (0)

    # lists

    def check_simple_list (self, node):
        """Check for a simple list that can be rendered compactly."""
        try:
            node.walk (SimpleListChecker (self.document))
            return True
        except nodes.NodeFound:
            return False

    def is_compactable (self, node):
        return ('compact' in node['classes']
                or (self.settings.compact_lists
                    and 'open' not in node['classes']
                    and (# self.compact_simple or
                         # self.topic_classes == ['contents'] or
                         self.check_simple_list (node))))

    def list_start (self, node):
        if not isinstance (node.parent, nodes.list_item):
            self.sp ()
            self.output_sp () # list entry will eat all space, so output it now
            self.indent (LIST_INDENT)
        self.compacting += self.is_compactable (node)
        self.comment ('compacting: %d' % self.compacting)
        self.list_enumerator_stack.append (writers.ListEnumerator (node, self.encoding))

    def list_end (self, node):
        self.list_enumerator_stack.pop ()
        self.compacting = max (0, self.compacting - 1)
        if not isinstance (node.parent, nodes.list_item):
            self.output_sp ()
            self.sp ()

    def visit_list_item (self, node):
        self.sp (0)
        self.br ()
        indent = self.list_enumerator_stack[-1].get_width ()
        label = self.list_enumerator_stack[-1].get_next ()
        if label:
            self.ta (indent, label)
            self.br_if_line_longer_than (indent)
        self.push ()
        self.indent (indent)

    def depart_list_item (self, node):
        self.pop ()
        if self.compacting:
            self.sp (0)
        else:
            self.sp ()
            self.output_sp ()

    def visit_bullet_list (self, node):
        self.list_start (node)

    def depart_bullet_list (self, node):
        self.list_end (node)

    def visit_enumerated_list (self, node):
        self.list_start (node)

    def depart_enumerated_list (self, node):
        self.list_end (node)

    # end lists

    def visit_block_quote (self, node):
        self.set_first_last (node)
        self.sp ()
        self.indent (BLOCKQUOTE_INDENT)
        self.rindent (BLOCKQUOTE_INDENT)

    def depart_block_quote (self, node):
        classes = node['classes']
        if 'epigraph' in classes:
            self.sp (2)
        if 'highlights' in classes:
            self.sp (2)

    def visit_comment (self, node):
        for line in node.astext ().splitlines ():
            self.comment (line)
        raise nodes.SkipNode

    def visit_container (self, node):
        pass

    def depart_container (self, node):
        pass

    def visit_compound (self, node):
        pass

    def depart_compound (self, node):
        pass

    def visit_decoration (self, node):
        pass

    def depart_decoration (self, node):
        pass

    def visit_doctest_block (self, node):
        self.visit_literal_block (node)

    def depart_doctest_block (self, node):
        self.depart_literal_block (node)

    def visit_document (self, node):
        pass

    def depart_document (self, node):
        pass

    def visit_footer (self, node):
        self.document.reporter.warning (
            'footer not supported', base_node = node)

    def depart_footer (self, node):
        pass

    # footnotes, citations, labels

    def visit_label (self, node):
        # footnote and citation
        indent = 0
        if isinstance (node.parent, nodes.footnote):
            indent = FOOTNOTE_INDENT
        elif isinstance (node.parent, nodes.citation):
            indent = CITATION_INDENT
        else:
            self.document.reporter.warning ('label unsupported',
                base_node = node)

        try:
            label = self.as_superscript (int (node.astext ()))
        except ValueError:
            label = '[%s]' % self.translate (node.astext ())

        if label:
            self.ta (indent, label)
            self.br_if_line_longer_than (indent)
        self.push ()
        self.indent (indent)
        raise nodes.SkipNode

    def depart_label (self, node):
        pass

    def visit_footnote (self, node):
        self.sp ()
        self.output_sp ()

    def depart_footnote (self, node):
        self.pop ()
        self.sp ()

    def visit_footnote_reference (self, node):
        try:
            self.text (
                self.as_superscript (int (node.astext ())))
        except ValueError:
            self.text (node.astext ())
        raise nodes.SkipNode

    def visit_citation (self, node):
        self.visit_footnote (node)

    def depart_citation (self, node):
        self.depart_footnote (node)

    def visit_citation_reference (self, node):
        self.text ('[%s]' % self.translate (node.astext ()))
        raise nodes.SkipNode

    # end footnotes

    def visit_generated (self, node):
        pass

    def depart_generated (self, node):
        pass

    def visit_header (self, node):
        self.document.reporter.warning (
            'header not supported', base_node = node)

    def depart_header (self, node):
        pass

    def visit_figure (self, node):
        self.sp (2)
        self.indent (BLOCKQUOTE_INDENT)
        self.rindent (BLOCKQUOTE_INDENT)

    def depart_figure (self, node):
        self.sp (2)

    def visit_image (self, node):
        self.text ('%s' % self.translate (node.attributes.get ('alt', '[image]')))

    def depart_image (self, node):
        pass

    def visit_caption (self, node):
        pass

    def depart_caption (self, node):
        pass

    def visit_legend (self, node):
        pass

    def depart_legend (self, node):
        pass

    def visit_line_block (self, node):
        if not isinstance (node.parent, nodes.line_block):
            # outermost block
            self.sp ()
        else:
            self.br ()
        if isinstance (node.parent, nodes.line_block):
            self.indent ()
        self.cmd ('ad l')

    def depart_line_block (self, node):
        if not isinstance (node.parent, nodes.line_block):
            # outermost block
            self.sp ()

    def visit_line (self, node):
        if node.children:
            self.push ()
            self.indent (8)
            self.cmd ('ti -8')
        else:
            # empty line
            self.sp ()
            self.output_sp ()

    def depart_line (self, node):
        if node.children:
            self.br ()
            self.pop ()

    def visit_literal_block (self, node):
        self.sp ()
        self.indent (BLOCKQUOTE_INDENT)
        self.cmd (('nf', 'ft C', 'blm'))
        self.in_literal += 1

    def depart_literal_block (self, node):
        self.in_literal -= 1
        self.cmd ('blm nop')
        self.sp ()

    #
    #
    #

    def visit_paragraph (self, node):
        self.sp ()
        # self.output_sp ()

    def depart_paragraph (self, node):
        self.sp ()

    def visit_section (self, node):
        self.section_level += 1

    def depart_section (self, node):
        self.section_level -= 1

    def visit_raw (self, node):
        if 'nroff' in node.get ('format', '').split():
            raw = node.astext ()
            if raw[0] == '.':
                self.cmd (raw[1:])
            else:
                self.text (raw)

        # ignore other raw formats
        raise nodes.SkipNode

    def visit_substitution_definition (self, node):
        """Internal only."""
        raise nodes.SkipNode

    def visit_substitution_reference (self, node):
        self.document.reporter.warning ('"substitution_reference" not supported',
                base_node=node)

    def visit_target (self, node):
        # internal hyperlink target, no such thing in nroff
        pass

    def depart_target (self, node):
        pass

    def visit_system_message (self, node):
        self.sp ()
        line = ', line %s' % node['line'] if 'line' in node else ''
        self.text ('"System Message: %s/%s (%s:%s)"'
                  % (node['type'], node['level'], node['source'], line))
        self.sp ()
        self.indent (BLOCKQUOTE_INDENT)

    def depart_system_message (self, node):
        self.sp ()

    # tables

    def visit_table (self, node):
        self.sp (2)
        pass_1 = writers.TablePass1 (self.document)
        node.walk (pass_1)
        rows = pass_1.rows ()
        cols = pass_1.cols ()

        pass_2 = TablePass2 (self.document, node, rows, cols)
        node.walk (pass_2)
        node.pass_2 = pass_2

    def depart_table (self, node):
        self.cmd ('TE')
        self.sp (2)

    def visit_table_title (self, node):
        pass

    def depart_table_title (self, node):
        self.sp ()

    def visit_tgroup (self, node):
        table = node.parent
        # output this after table caption
        self.output_sp ()
        self.cmd ('TS')
        options = ['center']
        self.text (' '.join (options) + ';\n')
        self.text (node.parent.pass_2.build_format_spec ())

    def depart_tgroup (self, node):
        pass

    def visit_colspec (self, node):
        pass

    def depart_colspec (self, node):
        pass

    def visit_thead (self, node):
        self.set_first_last (node) # mark first row of head
        self.text ('=\n')

    def depart_thead (self, node):
        pass

    def visit_tbody (self, node):
        self.text ('=\n')
        self.set_first_last (node) # mark first row of body

    def depart_tbody (self, node):
        self.text ('=')

    def visit_row (self, node):
        self.set_first_last (node) # mark first and last cell
        if 'first' not in node['classes']:
            if 'rows' in node.parent.parent.parent['hrules']:
                self.text ('_\n')
            else:
                self.sp ()

    def depart_row (self, node):
        pass

    def visit_entry (self, node):
        self.sp (0)
        if 'first' in node['classes']:  # first cell in row
            self.text ('T{\n')
            self.last_output_char = '\n'

    def depart_entry (self, node):
        # self.sp (0)
        if self.last_output_char != '\n':
            self.context.append ('\n')
        if 'last' in node['classes']:  # last cell in row
            self.text ('T}\n')
        else:
            self.text ('T}\tT{\n')
        self.last_output_char = '\n'

    # end tables

    def visit_document_title (self, node):
        self.cmd ('ad c')

    def depart_document_title (self, node):
        if 'with-subtitle' in node['classes']:
            self.sp (1)
        else:
            self.sp (2)

    def visit_document_subtitle (self, node):
        self.sp (1)
        self.cmd ('ad c')

    def depart_document_subtitle (self, node):
        self.sp (2)

    def visit_section_title (self, node):
        self.sp (3)

    def depart_section_title (self, node):
        self.sp (2)

    def visit_section_subtitle (self, node):
        self.sp (1)

    def depart_section_subtitle (self, node):
        self.sp (2)

    def visit_topic (self, node):
        self.sp (4)

    def depart_topic (self, node):
        self.sp (4)

    def visit_topic_title (self, node):
        pass

    def depart_topic_title (self, node):
        self.sp (2)

    def visit_sidebar (self, node):
        pass

    def depart_sidebar (self, node):
        pass

    def visit_rubric (self, node):
        pass

    def depart_rubric (self, node):
        pass

    def visit_page (self, node):
        if 'vspace' in node['classes']:
            self.sp (node['length'])
        elif 'clearpage' in node['classes']:
            self.cmd ('bp')
        elif 'cleardoublepage' in node['classes']:
            self.cmd ('bp')
        elif 'vfill' in node['classes']:
            self.sp (4)

    def depart_page (self, node):
        pass

    def visit_newline (self, node):
        self.br ()

    def depart_newline (self, node):
        pass


    def visit_transition (self, node):
        pass

    def depart_transition (self, node):
        pass


    def visit_attribution (self, node):
        pass

    def depart_attribution (self, node):
        pass


    def visit_problematic (self, node):
        self.cmd ('nf')

    def depart_problematic (self, node):
        self.cmd ('fi')

    def visit_meta (self, node):
        raise NotImplementedError (node.astext ())

    def unimplemented_visit (self, node):
        raise NotImplementedError ('visiting unimplemented node type: %s'
                                  % node.__class__.__name__)
