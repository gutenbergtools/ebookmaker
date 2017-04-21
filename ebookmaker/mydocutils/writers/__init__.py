#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

Mydocutils writer package.

Copyright 2010-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

"""

from __future__ import unicode_literals


__docformat__ = 'reStructuredText'

import collections
import operator

import six
from docutils import nodes, writers
import roman


class Writer (writers.Writer):
    """ A base class for writers. """

    output = None
    """Final translated form of `document`."""

    config_section_dependencies = ('writers', )

    def translate (self):
        visitor = self.translator_class (self.document)
        self.document.walkabout (visitor)
        self.output = visitor.astext ()


class TablePass1 (nodes.SparseNodeVisitor):

    """
    Make a first pass over a table to get a reliable row and column
    count.  Insert placeholder cells for spanned cells.
    """

    def __init__ (self, document):
        nodes.SparseNodeVisitor.__init__ (self, document)

        self.row = -1     # 0-based
        self.column = 0   # 0-based
        self.cells = 0
        self.colspecs = None

    def visit_table (self, table):
        self.colspecs = table.traverse (nodes.colspec)
        width = sum (map (operator.itemgetter ('colwidth'), self.colspecs))
        for colspec in self.colspecs:
            colspec['relative_width'] = float (colspec['colwidth']) / width

    def depart_table (self, table):
        table['rows'] = self.rows ()
        table['columns'] = self.cols ()

    def visit_row (self, dummy_node):
        self.row += 1
        self.column = 0
        for colspec in self.colspecs:
            colspec['spanned'] = max (0, colspec.get ('spanned', 0) - 1)

    def visit_entry (self, node):
        """ Table cell. """

        morerows = node.get ('morerows', 0)
        morecols = node.get ('morecols', 0)

        self.cells += (morecols + 1) * (morerows + 1)

        # skip columns that are row-spanned by preceding entries
        while True:
            colspec = self.colspecs [self.column]
            if colspec.get ('spanned', 0) > 0:
                placeholder = nodes.entry ()
                placeholder.type = 'compound'
                placeholder['column'] = self.column
                placeholder.colspecs = self.colspecs[self.column:self.column + 1]
                placeholder['vspan'] = True
                node.replace_self ([placeholder, node])
                self.column += 1
            else:
                break

        # mark columns we row-span
        if morerows:
            for colspec in self.colspecs [self.column : self.column + 1 + morecols]:
                colspec['spanned'] = morerows + 1

        node['row'] = self.row
        node['column'] = self.column

        node.colspecs = self.colspecs[self.column:self.column + morecols + 1]

        self.column += 1 + morecols

        raise nodes.SkipNode

    def rows (self):
        """ Return the no. of columns. """
        return self.row + 1

    def cols (self):
        """ Return the no. of columns. """
        return self.cells // self.rows ()


class ListEnumerator:
    """ Enumerate labels according to list type. """

    def __init__ (self, node, encoding):
        self.type  = node.get ('enumtype') or node.get ('bullet') or '*'
        self.start = node['start'] if 'start' in node else 1
        self.prefix = node.get ('prefix', '')
        self.suffix = node.get ('suffix', '')
        self.encoding = encoding

        self.indent = len (self.prefix + self.suffix) + 1
        if self.type == 'arabic':
            # indentation depends on end value
            self.indent += len (str (self.start + len (node.children)))
        elif self.type.endswith ('alpha'):
            self.indent += 1
        elif self.type.endswith ('roman'):
            self.indent += 5 # FIXME: calculate real length
        else:
            self.indent += 1 # none, bullets, etc.

    def get_next (self):
        """ Get the next label. """

        if self.type == 'none':
            res = ''
        elif self.type == '*':
            res = '•' if self.encoding == 'utf-8' else '-'
        elif self.type == '-':
            res = '-'
        elif self.type == '+':
            res = '+'
        elif self.type == 'arabic':
            res = "%d" % self.start
        elif self.type == 'loweralpha':
            res = "%c" % (self.start + ord ('a') - 1)
        elif self.type == 'upperalpha':
            res = "%c" % (self.start + ord ('A') - 1)
        elif self.type == 'upperroman':
            res = roman.toRoman (self.start).upper ()
        elif self.type == 'lowerroman':
            res = roman.toRoman (self.start).lower ()
        else:
            res = "%d" % self.start

        self.start += 1

        return self.prefix + res + self.suffix

    def get_width (self):
        """ Get indent width for this list. """

        return self.indent


class Translator (nodes.NodeVisitor):
    """ A base translator """

    admonitions = """
    attention caution danger error hint important note tip warning
    """.split ()

    docinfo_elements = """
    address author contact copyright date organization revision status
    version
    """.split ()

    # see http://docutils.sourceforge.net/docs/ref/doctree.html#simple-body-elements

    # simple_structural_subelements = tuple ((getattr (nodes, n) for n in """
    # title subtitle
    # """.split ()))

    # simple_body_elements = tuple ((getattr (nodes, n) for n in """
    # comment doctest_block image literal_block math_block paragraph
    # pending raw rubric substitution_definition target
    # """.split ()))

    # simple_body_subelements = tuple ((getattr (nodes, n) for n in """
    # attribution caption classifier colspec field_name
    # label line option_argument option_string term
    # """.split ()))

    # simple_elements = (simple_structural_subelements +
    #                    simple_body_elements + simple_body_subelements)

    def __init__ (self, document):
        nodes.NodeVisitor.__init__ (self, document)
        self.settings = document.settings

        self.body = []
        self.context = self.body # start with context == body
        self.docinfo = collections.defaultdict (list)
        self.list_enumerator_stack = []
        self.section_level = 0
        self.vspace = 0 # pending space (need this for collapsing)
        self.src_vspace = 0 # pending space for source pretty printing

        self.field_name = None
        self.compacting = 0 # > 0 if we are inside a compacting list
        self.in_literal = 0 # > 0 if we are inside one or more literal blocks

        self.prefixes = collections.defaultdict (list) # dict of arrays of prefixes in order in
                                                       # which to apply classes
        self.suffixes = collections.defaultdict (list) # reverse order of above

        self.environments = [] # stack of \begin'ed environments

        self.register_classes ()

        for name in self.docinfo_elements:
            setattr (self, 'visit_' + name,
                     lambda node: self.visit_field_body (node, name))
            setattr (self, 'depart_' + name, self.depart_field_body)

        for adm in self.admonitions:
            setattr (self, 'visit_' + adm,
                     lambda node: self.visit_admonition (node, adm))
            setattr (self, 'depart_' + adm, self.depart_admonition)


    def register_classes (self):
        pass


    def dispatch_visit (self, node):
        """
        Call self."``visit_`` + node class name" with `node` as
        parameter.  If the ``visit_...`` method does not exist, call
        self.unknown_visit.

        There are 3 hooks for every visit:

        visit_outer
        visit_<classname>
        visit_inner

        """

        self.visit_outer (node)

        node_name = node.__class__.__name__
        method = getattr (self, 'visit_' + node_name, self.unknown_visit)
        self.document.reporter.debug (
            'docutils.nodes.NodeVisitor.dispatch_visit calling %s for %s'
            % (method.__name__, node_name))
        res = method (node)

        if node.type in ('compound', 'simple', 'inline'):
            self.visit_inner (node)

        return res

    def dispatch_departure (self, node):
        """
        Call self."``depart_`` + node class name" with `node` as
        parameter.  If the ``depart_...`` method does not exist, call
        self.unknown_departure.

        There are 3 hooks for every departure:

        depart_inner
        depart_<classname>
        depart_outer

        """

        if node.type in ('compound', 'simple', 'inline'):
            self.depart_inner (node)

        node_name = node.__class__.__name__
        method = getattr (self, 'depart_' + node_name, self.unknown_departure)
        self.document.reporter.debug (
            'docutils.nodes.NodeVisitor.dispatch_departure calling %s for %s'
            % (method.__name__, node_name))
        res = method (node)

        self.depart_outer (node)

        return res


    def unknown_visit (self, node):
        """ Called if we have no handler for this element. """
        pass

    def unknown_departure (self, node):
        """ Called if we have no handler for this element. """
        pass


    def visit_outer (self, node):
        """ The very first hook called on a node, before
        ``visit_<classname>``. """
        pass

    def visit_inner (self, node):
        """ Called after ``visit_<classname>``. """
        pass

    def depart_inner (self, node):
        """ Called on a block before ``depart_<classname>``. """
        pass

    def depart_outer (self, node):
        """ The very last hook called on a node, after
        ``depart_<classname>``."""
        pass


    def register_class (self, types, class_, prefix, suffix):
        """ Register classes.

        A mechanism to automatically output strings before and after
        elements with specific classes.  For most use cases this is
        easier than to write a handler for the element.

        types: types of node this class will apply to:
               tuple of one or more of (text, inline, simple, compound)
        class_: class that triggers the strings
        prefix: string output before element
        suffix: string output after element

        """

        if isinstance (types, six.string_types):
            types = types.split ()

        for t in types:
            self.prefixes[t].append (   (class_, prefix))
            self.suffixes[t].insert (0, (class_, suffix))

    def get_prefix (self, type_, classes):
        return self._get_prefix (type_, classes, self.prefixes)

    def get_suffix (self, type_, classes):
        return self._get_prefix (type_, classes, self.suffixes)

    def _get_prefix (self, type_, classes, array):
        """ Helper for inline handlers. """
        if isinstance (classes, six.string_types):
            classes = classes.split ()

        res = []
        for s in array[type_]:
            if s[0] in classes:
                res.append (s[1])
        return res


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

    def astext (self):
        """ Return the final formatted document as a string. """
        return self.preamble () + ''.join (self.context) + self.postamble ()

    def comment (self, text):
        """ Output a comment. """
        pass

    def text (self, text):
        """ Output text. """
        pass

    def sp (self, n = 1):
        """ Adds vertical space before the next simple element.

        All spaces added collapse into the largest one. """

        if n == 0:
            self.vspace = 1999
        else:
            self.vspace = max (n, self.vspace)

    def src_sp (self, n = 1):
        """ Add vertical space to the source. """

        if n == 0:
            self.src_vspace = 1999
        else:
            self.src_vspace = max (n, self.src_vspace)

    def output_sp (self):
        pass

    def output_src_sp (self):
        pass

    def push (self):
        """ Push environment. """
        pass

    def pop (self):
        """ Pop environment. """
        pass

    def br_if_line_longer_than (self, length):
        """ Go one line up if the last line was shorter than length.

        Use this to compact lists etc. """
        pass

    def indent (self, by = 2):
        """ Indent text. """
        pass

    def rindent (self, by = 2):
        """ Indent text on the right side. """
        pass

    def preamble (self):
        return ''

    def postamble (self):
        return ''

    def visit_title (self, node):
        """ Switch on the various incarnations the title element can have. """

        if isinstance (node.parent, nodes.section):
            self.visit_section_title (node)
        elif isinstance (node.parent, nodes.document):
            self.visit_document_title (node)
        elif isinstance (node.parent, nodes.table):
            self.visit_table_title (node)
        elif isinstance (node.parent, nodes.topic):
            self.visit_topic_title (node)
        elif isinstance (node.parent, nodes.sidebar):
            self.visit_sidebar_title (node)
        elif isinstance (node.parent, nodes.admonition):
            self.visit_admonition_title (node)
        else:
            assert ("Can't happen.")

    def depart_title (self, node):
        """ Switch on the various incarnations the title element can have. """

        if isinstance (node.parent, nodes.section):
            self.depart_section_title (node)
        elif isinstance (node.parent, nodes.document):
            self.depart_document_title (node)
        elif isinstance (node.parent, nodes.table):
            self.depart_table_title (node)
        elif isinstance (node.parent, nodes.topic):
            self.depart_topic_title (node)
        elif isinstance (node.parent, nodes.sidebar):
            self.depart_sidebar_title (node)
        elif isinstance (node.parent, nodes.admonition):
            self.depart_admonition_title (node)
        else:
            assert ("Can't happen.")

    def visit_subtitle (self, node):
        """ Switch on the various incarnations the subtitle element can have. """

        if isinstance (node.parent, nodes.document):
            self.visit_document_subtitle (node)
        else:
            self.visit_section_subtitle (node)

    def depart_subtitle (self, node):
        """ Switch on the various incarnations the subtitle element can have. """

        if isinstance (node.parent, nodes.document):
            self.depart_document_subtitle (node)
        else:
            self.depart_section_subtitle (node)
