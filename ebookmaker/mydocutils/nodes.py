#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

nodes.py

Copyright 2011 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Added nodes for PG.

"""

from docutils import nodes

class page (nodes.Element, nodes.Special):
    """ Hold pagination commands.

    Like clearpage, vspace etc.

    """

class newline (nodes.Element):
    """ A line break.

    Outputs a hard line break if the node or one of its parents belong
    to the class 'white-space-pre-line'.  Else a space.

    """

class footnote_group (nodes.container):
    """ Hold a group of footnotes. """


class variable (nodes.Inline, nodes.TextElement):
    """ A placeholder that gets substituted with actual text before output.

    We do not use substitution refs because they are resolved way too
    early in the transformation stage to be of much use to us.

    """


class node_selector (object):
    """ Allows CSS-like selectors as condition function for nodes.traverse (). """

    def __init__ (self, selector):

        # allow selectors like [element][.class[.class[...]]][, selector[, selector]]

        self.matches = [] # list of 2-tuples

        for sel in selector.split (','):
            sel = sel.strip ()
            if '.' not in sel:
                sel += '.'
            element, classes = sel.split ('.', 1)
            classes = set (classes.split ('.')) if classes else set ()
            self.matches.append ( (getattr (nodes, element, nodes.Element), classes) )


    def __call__ (self, node):
        """ returns True if the node matches the selector. """

        for match in self.matches:
            if isinstance (node, match[0]) and match[1].issubset (node['classes']):
                return True

        return False
