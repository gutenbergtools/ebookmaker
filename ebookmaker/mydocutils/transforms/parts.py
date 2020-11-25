#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

parts.py

Copyright 2010-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

New and tweaked transformers.

"""

from __future__ import unicode_literals

import re
import fnmatch

import six

from docutils import nodes
import docutils.transforms
import docutils.transforms.parts

from ebookmaker.mydocutils import nodes as mynodes
from libgutenberg.Logger import error, warning, info, debug
from ebookmaker import Unitame

# pylint: disable=W0142

def copy_and_filter (node, document):
    """ Return a copy of a title, with references, images, etc. removed. """

    visitor = ContentsFilter (document)
    node.walkabout (visitor)
    return visitor.get_entry_text ()


class ContentsFilter (nodes.TreeCopyVisitor):

    def get_entry_text (self):
        return self.get_tree_copy ().children

    def ignore_node (self, node):
        raise nodes.SkipNode

    def ignore_node_but_process_children (self, node):
        raise nodes.SkipDeparture

    def visit_image (self, node):
        if node.hasattr ('alt'):
            self.parent.append (nodes.Text (node['alt']))
        raise nodes.SkipNode

    visit_newline = nodes.TreeCopyVisitor.default_visit
    depart_newline = nodes.TreeCopyVisitor.default_departure

    visit_citation_reference = ignore_node
    visit_footnote_reference = ignore_node
    visit_raw = ignore_node

    visit_interpreted = ignore_node_but_process_children
    visit_problematic = ignore_node_but_process_children
    visit_reference = ignore_node_but_process_children
    visit_target = ignore_node_but_process_children


###########
### 200 ###
###########


class Lineblock2VSpace (docutils.transforms.Transform):
    """
    Turn empty line_blocks into page nodes.

    """

    default_priority = 200 # early, before vspace

    def apply (self):
        for lb in self.document.traverse (nodes.line_block):
            if lb.astext ().strip () == '':
                gap_len = len (lb)
                page = mynodes.page ()
                page['classes'].append ('vspace')
                page['length'] = gap_len
                lb.replace_self (page)


###########
### 300 ###
###########


class DocInfoCollector (docutils.transforms.Transform):
    """
    Collects docinfo in document.meta_block (dict of lists).

    """

    default_priority = 341
    """ After frontmatter.py DocInfo """

    def apply (self):
        doc = self.document

        for docinfo in doc.traverse (nodes.docinfo):
            for field in docinfo:
                if isinstance (field, nodes.field):
                    field_name, field_body = field.children
                    doc.meta_block[field_name.astext ()].append (field_body.astext ())
                elif isinstance (field, nodes.Bibliographic):
                    doc.meta_block[field.__class__.__name__].append (field.astext ())

            docinfo.parent.remove (docinfo)


class TitleLevelTransform (docutils.transforms.Transform):
    """
    Adds some useful classes to sections, titles and captions.

    Add `level-N` to `section`, `title` and `subtitle` nodes.

    Add `document-title` or `section-title`, or ...

    Add `title` or `subtitle`.

    Add `with-subtitle`.

    Add `figure-caption`.

    """

    default_priority = 361 # after title promotion

    def apply (self, **kwargs):
        self.recurse (self.document, 1)

        for caption in self.document.traverse (nodes.caption):
            caption['classes'].append (caption.parent.__class__.__name__ + '-caption')

    def recurse (self, parent, level):
        for node in parent:
            if isinstance (node, nodes.Text):
                continue

            if isinstance (node, (nodes.title, nodes.subtitle)):
                nclass  = node.__class__.__name__
                pclass  = parent.__class__.__name__
                classes = [nclass,
                           '%s-%s' % (pclass, nclass),
                           'level-%d' % level]
                if (isinstance (node, (nodes.title)) and
                    len (parent) >= 2 and
                    isinstance (parent[1], nodes.subtitle)):
                    classes.append ('with-subtitle')
                node['classes'].extend (classes)
                node['level'] = level

            if isinstance (node, nodes.section):
                node['classes'].append ('level-%d' % (level + 1))
                node['level'] = level + 1

                self.recurse (node, level + 1)
            else:
                self.recurse (node, level)


###########
### 700 ###
###########


class TocPageNumberTransform (docutils.transforms.Transform):
    """ Finds the page number all sections, tables and figures are in. """

    default_priority = 715 # before contents transform

    def apply (self, **kwargs):
        pageno = '' # pageno is actually a string

        for n in self.document.traverse ():
            if isinstance (n, nodes.target) and 'pageno' in n:
                pageno = n['pageno']
                # debug ("pageno: >%s<" % self.pageno)
            elif isinstance (n, (nodes.section, nodes.figure, nodes.table)):
                n['pageno'] = pageno


class TocEntryTransform (docutils.transforms.Transform):
    """ Moves data of pending node onto next header. """

    default_priority = 717 # before Contents transform

    def apply (self, **kwargs):
        # debug ("TocEntryTransform %s" % repr (self.startnode.details))

        iter_ = self.startnode.traverse (
            lambda x: isinstance (x, (nodes.title, nodes.caption)), ascend = 1, descend = 1)

        details = self.startnode.details
        for node in iter_:
            title = node
            title['toc_entry'] = details['content']

            # copy depth
            if 'toc_depth' in details:
                section = title.parent
                if isinstance (section, nodes.section):
                    section['toc_depth'] = details['toc_depth']
                    # debug ("Setting toc_depth: %d" % section['toc_depth'])
            break
        self.startnode.parent.remove (self.startnode)


class ContentsTransform (docutils.transforms.Transform):
    """ A modified contents transform that obeys contents-depth directives. """

    default_priority = 720

    def __init__ (self, document, startnode = None):
        docutils.transforms.Transform.__init__ (self, document, startnode)
        self.depth = startnode.details.get ('depth', six.MAXSIZE) if startnode else six.MAXSIZE
        self.toc_depth = six.MAXSIZE
        self.use_pagenos = 'page-numbers' in startnode.details
        self.maxlen = 0 # length of longest page no.

    def apply(self):
        details = self.startnode.details
        if 'local' in details:
            startnode = self.startnode.parent.parent
            while not (isinstance (startnode, nodes.section)
                       or isinstance (startnode, nodes.document)):
                # find the ToC root: a direct ancestor of startnode
                startnode = startnode.parent
        else:
            startnode = self.document

        contents = self.build_contents (startnode)
        if len (contents):
            self.startnode.replace_self (contents)
        else:
            self.startnode.parent.parent.remove (self.startnode.parent)

    def build_contents (self, node, level=0):
        # debug ('build_contents level %d' % level)

        details = self.startnode.details
        backlinks = details.get ('backlinks', self.document.settings.toc_backlinks)
        try:
            toc_id = self.startnode.parent['ids'][0]
        except:
            toc_id = None

        entries = []
        for n in node:
            if isinstance (n, nodes.section):
                if 'toc_depth' in n:
                    self.toc_depth = n['toc_depth']
                    # debug ("New toc_depth: %d" % self.toc_depth)
                if level < self.depth and level < self.toc_depth:
                    subsects = self.build_contents(n, level + 1)
                    title = n[0]
                    if not isinstance (title, nodes.title):
                        continue
                    # debug ('title: %s level: %d depth: %d' % (title, level, self.toc_depth))

                    pagenos = []
                    if self.use_pagenos and 'pageno' in n:
                        self.maxlen = max (self.maxlen, len (n['pageno']))
                        inline = nodes.inline ('', ' ' + n['pageno'])
                        inline['classes'].append ('toc-pageref')
                        pagenos.append (inline)

                    if 'toc_entry' in title:
                        container = title['toc_entry']
                        if container is None: # suppress toc entry if emtpy
                            continue
                        # debug ("Setting TOC entry")
                        entrytext = copy_and_filter (container, self.document)
                    else:
                        entrytext = copy_and_filter (title, self.document)

                    reference = nodes.reference (
                        '', '', refid = n['ids'][0], *entrytext)
                    ref_id = self.document.set_id (reference)

                    entry = nodes.paragraph ('', '', reference, *pagenos)
                    item = nodes.list_item ('', entry)
                    item['refid'] = n['ids'][0]
                    item['classes'].append ('toc-entry')
                    if 'level' in title:
                        item['level'] = title['level']
                        item['classes'].append ('level-%d' % (title['level']))
                    if (backlinks in ('entry', 'top')
                         and title.next_node (nodes.Referential) is None):
                        if backlinks == 'entry':
                            title['refid'] = ref_id
                        elif backlinks == 'top' and toc_id is not None:
                            title['refid'] = toc_id
                    item += subsects
                    entries.append (item)
        if entries:
            return nodes.bullet_list ('', *entries, **{'classes': ['compact', 'toc-list'],
                                                       'enumtype': 'none',
                                                       'pageno_maxlen': self.maxlen})
        else:
            return []


class ListOfAnythingTransform (docutils.transforms.Transform):
    """ Create a List Of Figures or List Of Tables etc. """

    default_priority = 718 # before empty section remover

    def __init__ (self, document, startnode = None):
        docutils.transforms.Transform.__init__ (self, document, startnode)
        self.maxlen = 0 # length of longest page no.

    def apply (self, **kwargs):
        entries = []
        details = self.startnode.details

        self.backlinks = details.get ('backlinks',
                                      self.document.settings.toc_backlinks)
        self.use_pagenos = 'page-numbers' in details
        directive_name = details.get ('directive_name', '')

        condition = None
        if 'selector' in details:
            condition = mynodes.node_selector (details['selector'])
        elif directive_name == 'lof':
            condition = nodes.figure
        elif directive_name == 'lot':
            condition = nodes.table

        if not condition:
            self.document.reporter.warning (
                "directive %s needs an option 'selector'" % directive_name,
                base_node=self.startnode.parent)
            raise docutils.transform.TransformError

        if 'local' in details:
            startnode = self.startnode.parent.parent
            while not isinstance (startnode, (nodes.section, nodes.document)):
                # find the ToC root: a direct ancestor of startnode
                startnode = startnode.parent
        else:
            startnode = self.document

        try:
            toc_id = self.startnode.parent.parent['ids'][0]
        except:
            toc_id = None

        for node in startnode.traverse (condition):

            title = list (node.traverse (nodes.caption) + node.traverse (nodes.title))
            if len (title) != 1:
                # cannot put anonymous X in list of X
                continue

            title = title[0]

            pagenos = []
            if self.use_pagenos and 'pageno' in node:
                self.maxlen = max (self.maxlen, len (node['pageno']))
                inline = nodes.inline ('', ' ' + node['pageno'])
                inline['classes'].append ('toc-pageref')
                pagenos.append (inline)

            if 'toc_entry' in title:
                container = title['toc_entry']
                if container is None: # suppress toc entry if emtpy
                    # debug ("Suppressing TOC entry")
                    continue
                # debug ("Setting TOC entry")
                entrytext = copy_and_filter (container, self.document)
            else:
                entrytext = copy_and_filter (title, self.document) # returns list of nodes

            reference = nodes.reference ('', '', *entrytext, refid = node['ids'][0])
            ref_id = self.document.set_id (reference) # target for backlink

            list_item = nodes.list_item ('', nodes.inline ('', '', reference, *pagenos))
            list_item['refid'] = node['ids'][0]
            list_item['level'] = 2
            list_item['classes'].append ('level-2')
            list_item['classes'].append ('toc-entry')

            if (self.backlinks in ('entry', 'top')
                 and title.next_node (nodes.Referential) is None):
                if self.backlinks == 'entry':
                    title['refid'] = ref_id
                elif self.backlinks == 'top' and toc_id is not None:
                    title['refid'] = toc_id

            entries.append (list_item)

        if entries:
            contents = nodes.bullet_list ('', *entries, **{'classes': ['compact', 'toc-list'],
                                                           'enumtype': 'none',
                                                           'pageno_maxlen': self.maxlen})
            self.startnode.replace_self (contents)
        else:
            self.startnode.parent.remove (self.startnode)
            # self.startnode.parent.parent.remove (self.startnode.parent)


class FootnotesDirectiveTransform (docutils.transforms.Transform):
    """
    Collects footnotes into this section.

    The 'footnotes::' directive creates a section and puts this
    pending transform into it.  This transform either moves all
    footnotes into the generated section or removes this section from
    non-HTML formats.

    """

    # run this before contents transform. contents should not grab
    # this section's title because it can disappear.

    default_priority = 718 # before empty section remover

    def apply (self, **kwargs):
        pending = self.startnode
        section = pending.parent
        section.remove (pending)

        writer = self.document.transformer.components['writer']
        if writer.supports ('html'):
            group = mynodes.footnote_group ()
            section += group

            for footnote in self.document.traverse (nodes.footnote):
                footnote.parent.remove (footnote)
                group += footnote
        #else:
        #    section.parent.remove (section)


class EmptySectionRemover (docutils.transforms.Transform):
    """
    Removes this section if it contains only a title or less.
    Use for footnotes or loa sections.

    """

    # run this before contents transform. contents should not grab
    # this section before we make it disappear.

    default_priority = 719 # before contents transform

    def apply (self, **kwargs):
        pending = self.startnode
        section = pending.parent
        if not isinstance (section, nodes.section):
            return
        # print "\n\n", section
        index = section.index (pending)
        container = section[index + 1]
        # title = section[index - 1] if index > 0 else None
        title = section[0]
        if not isinstance (title, nodes.title):
            title = None
        section.remove (pending)

        if len (container) == 0:
            section.remove (container)
            if title is not None:
                section.remove (title)
            if len (section) == 0:
                section.parent.remove (section)


class PageNumberMoverTransform (docutils.transforms.Transform):
    """ Moves paragraphs that contain only one page number into the
    next paragraph. """

    default_priority = 721 # after contents transform

    def apply (self, **kwargs):
        for target in self.document.traverse (nodes.target):
            if isinstance (target.parent, nodes.paragraph) and len (target.parent) == 1:
                # move onto next appropriate node
                for next_node in target.traverse (nodes.TextElement, include_self = 0, ascend = 1):
                    if not isinstance (next_node, (nodes.Structural, nodes.Special)):
                        target.parent.parent.remove (target.parent)
                        next_node.insert (0, target)
                        break


class DropCapTransform (docutils.transforms.Transform):
    """ Inserts a dropcap into the following paragraph. """

    default_priority = 719 # run before Contents Transform

    def apply (self, **kwargs):
        iter_ = self.startnode.traverse (nodes.paragraph, siblings = 1)

        if len (iter_):
            para = iter_[0]
            iter_ = para.traverse (nodes.Text)
            details = self.startnode.details

            if len (iter_):
                textnode = iter_[0]
                charnode = spannode = restnode = None

                char = details['char']
                if not textnode.startswith (char):
                    error ("Dropcap: next paragraph doesn't start with: '%s'." % char)
                    return

                span = details.get ('span', '')
                if not textnode.startswith (span):
                    error ("Dropcap: next paragraph doesn't start with: '%s'." % span)
                    return
                if span and not span.startswith (char):
                    error ("Dropcap: span doesn't start with: '%s'." % char)
                    return
                if span == char:
                    span = ''

                if span:
                    # split into char/span/rest
                    restnode = nodes.Text (textnode.astext ()[len (span):])
                    spannode = nodes.inline ()
                    spannode.append (nodes.Text (textnode.astext ()[len (char):len (span)]))
                    spannode['classes'].append ('dropspan')
                else:
                    # split into char/rest
                    restnode = nodes.Text (textnode.astext ()[len (char):])
                    spannode = nodes.inline ('', '')
                    spannode['classes'].append ('dropspan')

                if 'image' in details:
                    charnode = nodes.image ()
                    charnode['uri'] = details['image']
                    charnode['alt'] = char
                    # debug ("Inserting image %s as dropcap." % uri)
                else:
                    charnode = nodes.inline ()
                    charnode.append (nodes.Text (char))
                    # debug ("Inserting char %s as dropcap." % char)

                charnode['classes'].append ('dropcap')
                charnode.attributes.update (details)

                para.replace (textnode, [charnode, spannode, restnode])

        self.startnode.parent.remove (self.startnode)


class InlineImageTransform (docutils.transforms.Transform):
    """Set class 'inline' or 'block' on an image according to actual
    usage so it can be used for styling.

    """

    default_priority = 730 # before StyleTransform

    def apply (self):
        for image in self.document.traverse (nodes.image):
            if isinstance (image.parent, nodes.TextElement):
                image['classes'] += ['inline']
            else:
                image['classes'] += ['block']


class StyleTransform (docutils.transforms.Transform):
    """
    Add classes to elements.

    Works in a way similar to CSS, though you can select only on
    element and class.

    Works on all following elements in the section it is used, if used
    before the first section works on the rest of the document.

    """

    default_priority = 731 # after default presentation

    def apply (self, **kwargs):
        pending  = self.startnode
        details  = pending.details

        if 'formats' in details:
            matched = False
            for f in details['formats'].split ():
                if f.startswith ('-'):
                    if not fnmatch.fnmatch (self.document.settings.format, f[1:]):
                        matched = True
                        break
                else:
                    if fnmatch.fnmatch (self.document.settings.format, f):
                        matched = True
                        break

            if not matched:
                pending.parent.remove (pending)
                return

        selector = details.get ('selector', '')

        if selector == 'document':
            # look at document node only
            node_list = [self.document]
        else:
            if 'titlehack' in details:
                # because titles start sections it is often impossible
                # to style titles because the pending node cannot be
                # placed before the title node.

                # traverse all children of parent
                node_list = pending.parent.traverse (
                    mynodes.node_selector (selector), include_self = 0)
            else:
                # traverse all following nodes and their children
                node_list = pending.traverse (
                    mynodes.node_selector (selector), siblings = 1, include_self = 0)

        # classes    = frozenset ([c for c in details.get ('class', []) if not c.startswith ('-')])
        # rmclasses  = frozenset ([c[1:] for c in details.get ('class', []) if c.startswith ('-')])

        classes = frozenset (details.get ('class', []))
        rmclasses = frozenset ()

        for n in node_list:
            n['classes'] = list ((set (n['classes']) | classes) - rmclasses)
            if details.get ('display', '').lower () == 'none':
                n.parent.remove (n)
                continue
            for a in ('align', 'width', 'float', 'hrules', 'vrules',
                      'aligns', 'vertical-aligns', 'tabularcolumns', 'widths'):
                if a in details:
                    n.setdefault (a, details[a]) # style on the element has priority
                    # n[a] = details[a]
            if 'before' in details:
                n[0:0] = [nodes.Text (details['before'])]
            if 'after' in details:
                index = len (n)
                n[index:index] = [nodes.Text (details['after'])]
            if pending.children:
                # replace element
                # print '****** replacing',  n.__class__.__name__
                n.parent.replace (n, [child.deepcopy () for child in pending.children])

        pending.parent.remove (pending)


###########
### 800 ###
###########


class FirstParagraphTransform (docutils.transforms.Transform):
    """
    Mark first paragraphs.

    With indented paragraphs, the first paragraph following a
    vertical space should not be indented. This transform tries
    to figure out which paragraphs should not be indented.

    Add the classes `pfirst` and `pnext` to paragraphs.

    """

    default_priority = 800 # late

    def apply (self, **kwargs):
        self.recurse (self.document, False)

    def recurse (self, parent, follows_paragraph):
        # follows_paragraph = False # flag: previous element is paragraph

        for node in parent:

            if isinstance (node, (nodes.paragraph)):
                node['classes'].append ('pnext' if follows_paragraph else 'pfirst')
                follows_paragraph = True
            elif isinstance (node, (nodes.title, nodes.subtitle)):
                # title may also be output as <html:p>
                node['classes'].append ('pfirst')
                follows_paragraph = False
            elif isinstance (node, (mynodes.page)):
                # explicit vertical space or page breaks
                follows_paragraph = False
            elif isinstance (node, (nodes.container, nodes.compound,
                                    nodes.Invisible, nodes.footnote, nodes.figure)):
                # invisible nodes are neutral, footnotes are not
                # output here so they are neutral too.  figures are
                # neutral because they can float away.  (also,
                # paragraphs in real books may contain block figures
                # so not indenting the following paragraph would look
                # ambiguous.)
                pass
            else:
                # everything else
                follows_paragraph = False

            if not isinstance (node, nodes.Text):
                self.recurse (node, follows_paragraph)



class BlockImageWrapper (docutils.transforms.Transform):
    """
    Wrap a block-level image into a figure.

    """

    default_priority = 801

    def apply (self):

        for image in self.document.traverse (nodes.image):

            # skip inline images
            # (See also: class `TextElement` in `docutils.nodes`.)
            if isinstance (image.parent, nodes.TextElement):
                continue

            # wrap all block images into figures
            if isinstance (image.parent, nodes.figure):
                figure = image.parent
            else:
                figure = nodes.figure ()
                figure['float'] = ('none', ) # do not float bare images
                figure['width'] = image.attributes.get ('width', 'image')
                figure['align'] = image.attributes.get ('align', 'center')
                image['width']  = '100%'
                image.replace_self (figure)
                figure.append (image)

            # set default width, align for block images only
            image.setdefault ('width', '100%')
            image.setdefault ('align', 'center')


class SetDefaults (docutils.transforms.Transform):
    """Set default attributes.

    Set default attributes to simplify writers.

    We need to set default attributes after the style directive
    because the style directive cannot distinguish between user-set
    attributes which must be kept and default attributes which must be
    overridden.

    Also, for simple tables and grid tables, we cannot set the default
    attributes in the directive parser because there is no directive.

    Image default attributes are set in BlockImageWrapper.

    """

    default_priority = 802

    def get_default_width (self, uri):
        """Calculate a sensible default width for images.

        Assume images are processed for a viewport 980px wide, the
        same as the iPhone browser assumes.

        """

        if (self.document.settings.get_image_size and
            six.callable (self.document.settings.get_image_size)):

            size = self.document.settings.get_image_size (uri)
            if size is not None:
                w = int (float (size[0]) / (980.0 * 0.8) * 100.0 + 0.5)
                width = "%d%%" % min (100, w)
                debug ('Got dimension of image: %s: %s' % (uri, width))
                return width

        warning ('Could not get dimension of image: %s' % uri)
        return '100%'


    def apply (self, **kwargs):

        def setdefault (node_type, l):
            for node in self.document.traverse (node_type):
                for name, default in l:
                    node.setdefault (name, default)

        # Image default attributes are set in BlockImageWrapper.

        setdefault (nodes.figure, (
            ('align',          'center'),
            ('float',          ('here', 'top', 'bottom', 'page')),
            ('width',          'image'),
        ))

        for image in self.document.traverse (nodes.image):
            if isinstance (image.parent, nodes.figure):
                figure = image.parent
                if figure['width'] == 'image':
                    figure['width'] = self.get_default_width (image['uri'])
                    figure['classes'].append ('auto-scaled')

        setdefault (nodes.table, (
            ('align',          'center'),
            ('float',          ('here', 'top', 'bottom', 'page')),
            ('hrules',         ('table', 'rows')),
            ('summary',        'no summary'),
            ('tabularcolumns', None),
            ('vrules',         ('none', )),
            ('width',          '100%'),
        ))
        setdefault (nodes.topic, (
            ('float',          ('here', )),
        ))
        setdefault (nodes.sidebar, (
            ('float',          ('here', )),
        ))


class AlignTransform (docutils.transforms.Transform):
    """
    Transforms align attribute into align-* class.

    """

    default_priority = 803 # after SetDefaults

    def apply (self):
        for body in self.document.traverse (
            lambda x: isinstance (x, (nodes.Body, nodes.Structural))):
            if 'align' in body:
                body['classes'].append ('align-%s' % body['align'])


class TextTransform (docutils.transforms.Transform):
    """
    Implements CSS text-transform.

    """

    default_priority = 895 # next to last

    smartquotes_map = {
        0x0027: '’',
        # 0x0022: '”',
        }

    re_quotes_thin_space = re.compile (r'([“„‟’])([‘‚‛”])')

    def apply (self, **kwargs):
        self.recurse (self.document, {})

    # FIXME this has been obsoleted by class inheritance

    def recurse (self, node, text_transform):
        if isinstance (node, nodes.Text):
            if len (text_transform) > 0:
                oldtext = text = node.astext ()
                if text_transform.get ('uppercase', False):
                    text = text.upper ()
                if text_transform.get ('smartquotes', False):
                    text = text.translate (self.smartquotes_map)
                    # insert thin space between quotes
                    text = self.re_quotes_thin_space.sub (r'\1 \2', text)
                if text != oldtext:
                    node.parent.replace (node, nodes.Text (text)) # cannot change text nodes
            return

        ntt = text_transform.copy ()
        classes = node['classes']

        if 'text-transform-uppercase' in classes:
            ntt['uppercase'] = True
        elif 'text-transform-smartquotes' in classes:
            ntt['smartquotes'] = True
        elif 'text-transform-none' in classes:
            ntt['uppercase'] = False
            ntt['smartquotes'] = False

        if 'white-space-pre-line' in classes:
            ntt['pre-line'] = True

        for child in node:
            self.recurse (child, ntt)


class CharsetTransform (docutils.transforms.Transform):
    """
    Translates text into smaller charset.

    This does not change the encoding, it just emulates all characters
    with characters from the smaller charset.

    """

    default_priority = 896

    def apply (self, **kwargs):
        if self.document.settings.encoding != 'utf-8':
            charset = self.document.settings.encoding
            del Unitame.unhandled_chars[:]

            for n in self.document.traverse (nodes.Text):
                text  = n.astext ()
                text2 = text.encode (charset, 'unitame').decode (charset)
                if text != text2:
                    n.parent.replace (n, nodes.Text (text2)) # cannot change text nodes

            if Unitame.unhandled_chars:
                error ("unitame: unhandled chars: %s" % ", ".join (set (Unitame.unhandled_chars)))


class TextNodeWrapper (docutils.transforms.Transform):
    """
    Wrap all naked Text nodes in inline nodes.

    Works in conjunction with the inheritance transform.

    """

    default_priority = 897 # before NodeTypeTransform

    def apply (self):
        for node in self.document.traverse (nodes.Text):

            # skip already wrapped nodes
            if isinstance (node.parent, nodes.Inline):
                continue

            node.parent.replace (node, nodes.inline ('', node.astext ()))


class NodeTypeTransform (docutils.transforms.Transform):
    """
    Determines the type of a node.

    The type can be one of 'empty', 'text', 'inline', 'simple', 'compound'.

    - An empty element contains no other elements nor text. Eg. image,
      transition.

    - A text element contains text.

    - An inline element contains other inline elements or text.

    - A simple element is a block element that contains text or inline
      elements but never contains other block elements.  It is the
      innermost block element.

    - A compound element is a block element that contains other simple
      or compound block elements but never contains inline or text
      elements.

    See: http://docutils.sourceforge.net/docs/ref/doctree.html#body-elements

    """

    # FIXME: there should be a class factory for nodes in docutils, so
    # you could add some type of identification function.

    default_priority = 898

    def apply (self, **kwargs):
        for node in self.document.traverse ():
            node.type = \
                'text'   if isinstance (node, nodes.Text) else (
                'inline' if isinstance (node, nodes.Inline) else (
                'simple' if isinstance (node, nodes.TextElement) else
                'empty'  if isinstance (node, (nodes.transition, nodes.image)) else
                'compound'))

            # this helps distinguish the use of elements than can be
            # both blocks or inline elements (eg. images)
            node.is_block = not node.parent or not isinstance (node.parent, (nodes.TextElement))


class InheritTransform (docutils.transforms.Transform):
    """
    Inheritance for docutil classes. Abstract base class.

    For convenience of use, you may specify a class on a block, that
    has an effect only on inline text. Eg. you may specify a class
    'italic' on a block to make the whole block italic.

    Inheritance is a way to get classes down from the (block) element
    where they are specified onto the (inline) element where they are
    applied.

    Override this class in the writer to gain finer control over which
    classes are inherited.

    """

    default_priority = 899 # last, you should not change the tree after this

    # FIXME: find a way to let the writer specify the classes
    # eg HTML => white-space-pre-line only

    apply_to_simple = frozenset ("""
    left center right justify
    noindent
    """.split ())

    apply_to_inline = frozenset ("""
    italics bold small-caps gesperrt normal antiqua monospaced
    xx-small x-small small medium large x-large xx-large
    smaller larger
    red green blue yellow white gray black
    """.split ())

    apply_to_text = frozenset ("""
    white-space-pre-line
    """.split ())

    # pass on if it applies to a contained class:
    #    compound > simple > inline > text

    pass_on = {
        'text':     frozenset (),
        'inline':   apply_to_text,
        'simple':   apply_to_inline | apply_to_text,
        'compound': apply_to_simple | apply_to_inline | apply_to_text,
        }

    def apply (self, **kwargs):
        self.recurse (None, self.document, set ())

    def recurse (self, parent, node, inherited_classes):
        classes_to_pass_on = self.pass_on[node.type]

        classes = set (node['classes']) | inherited_classes

        # remove classes with 'no-' prefix
        classes -= set ([c[3:] for c in classes if c.startswith ('no-')])

        # remove from node classes we passed on
        # this avoids problems with classes like 'smaller'
        node['classes'] = list (classes - classes_to_pass_on)

        passed_on_classes = classes & classes_to_pass_on

        for n in node.children:
            if isinstance (n, nodes.Text):
                n.attributes = {'classes': list (passed_on_classes) } # HACK! Text has no attributes
            else:
                self.recurse (node, n, passed_on_classes)
