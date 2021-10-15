#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""

xhtml1.py

Copyright 2010-2012 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

A modified XHTML writer.

"""

from __future__ import unicode_literals

# FIXME: move hr.pb out of sections

import six

from docutils import nodes
from docutils.writers import html4css1

from libgutenberg.Logger import info, debug, warning, error

from ebookmaker.mydocutils.transforms import parts
from ebookmaker.mydocutils import writers

class InheritTransform (parts.InheritTransform):
    pass


class Writer (html4css1.Writer):
    """ XHTML 1 Writer. """

    def __init__ (self):
        html4css1.Writer.__init__ (self)
        self.translator_class = Translator

    def fixup_xhtml (self, xhtml):
        return xhtml


    def get_transforms (self):
        tfs = html4css1.Writer.get_transforms (self)
        return tfs + [parts.TextNodeWrapper, InheritTransform]


class Translator (writers.Translator, html4css1.HTMLTranslator):
    """ XHTML 1 Translator. """

    htmlspecialchars = {
        ord('&'): '&amp;',
        ord('<'): '&lt;',
        ord('>'): '&gt;',
        ord('"'): '&#x22;',
        0xa0:     '&#xa0;',
        }

    head_prefix_template = ('<html xmlns="http://www.w3.org/1999/xhtml"'
                            ' xml:lang="%(lang)s">\n<head>\n')

    def __init__ (self, document):
        writers.Translator.__init__ (self, document)
        html4css1.HTMLTranslator.__init__ (self, document)
        self.init_css ()
        self.imgoff = None

    def init_css (self):
        for css_file in ('rst2all.css', 'rst2html.css'):
            self.head.append ('<style type="text/css">\n%s</style>\n' %
                              self.encode (self.read_css (css_file)))

    def read_css (self, css_file):
        if self.document.settings.get_resource and six.callable (
            self.document.settings.get_resource):
            return self.document.settings.get_resource ('mydocutils.writers', css_file)
        return None

    def encode (self, text):
        """ Encode special html characters.

        Tweak: Use numeric entities that work in HTML and XHTML. """

        return six.text_type (text).translate (self.htmlspecialchars)

    def visit_Text (self, node):
        text = node.astext ()
        encoded = self.encode (text)
        if self.in_mailto and self.settings.cloak_email_addresses:
            encoded = self.cloak_email (encoded)

        if hasattr (node, 'attributes') and 'white-space-pre-line' in node.attributes['classes']:
            for line in encoded.splitlines (True):
                self.body.append (line)
                if '\n' in line:
                    self.body.append ('<br />')
        else:
            self.body.append (encoded)

    def starttag (self, node, tagname, suffix='\n', empty=0, **attributes):
        """
        Tweak is: implement custom html attributes.

        Tweak is: original starttag produces side-effects on the node
        it operates on: ie. it changes the `classes` dict. Fix that.

        Construct and return a start tag given a node (id & class attributes
        are extracted), tag name, and optional attributes.

        """

        tagname = tagname.lower ()
        prefix = []
        atts = {}

        for (name, value) in attributes.items ():
            atts[name.lower()] = value
        if 'html_attributes' in node:
            atts.update (node['html_attributes'])

        classes = node.get ('classes', [])[:] # fix: make a copy

        if 'class' in atts:
            class_ = atts['class']
            if isinstance (class_, six.string_types):
                class_ = [class_]
            classes.extend (class_)
            del atts['class']

        # language hack
        for c in classes:
            if c.startswith ('language-'):
                atts['xml:lang'] = c[9:]

        styles = node.get ('styles', [])[:] # fix: make a copy

        if 'style' in atts:
            style = atts['style']
            if isinstance (style, six.string_types):
                style = [style]
            styles.extend (style)
            del atts['style']
        styles = [s.strip (' ;') for s in styles]

        assert 'id' not in atts
        ids = node.get ('ids', [])
        if 'ids' in atts:
            ids.extend (atts['ids'])
            del atts['ids']
        if ids:
            atts['id'] = ids[0]
            for id_ in ids[1:]:
                # Add empty "span" elements for additional IDs.  Note
                # that we cannot use empty "a" elements because there
                # may be targets inside of references, but nested "a"
                # elements aren't allowed in XHTML (even if they do
                # not all have a "href" attribute).
                if empty:
                    # Empty tag.  Insert target right in front of element.
                    prefix.append('<span id="%s"></span>' % id_)
                else:
                    # Non-empty tag.  Place the auxiliary <span> tag
                    # *inside* the element, as the first child.
                    suffix += '<span id="%s"></span>' % id_

        parts = []
        if classes:
            parts.append ('class="%s"' % ' '.join (sorted (set (classes))))
        if styles:
            parts.append ('style="%s"' % '; '.join (sorted (set (styles))))
        for name, value in sorted (atts.items ()):
            parts.append ('%s="%s"' % (name.lower (), self.attval (six.text_type (value))))

        infix = ' /' if empty else ''

        return ''.join(prefix) + '<%s %s%s>' % (tagname, ' '.join(parts), infix) + suffix


    def set_first_last (self, node):
        """ Set class 'first' on first child, 'last' on last child. """
        self.set_class_on_child (node, 'first', 0)
        self.set_class_on_child (node, 'last', -1)

    link_data = {'coverpage':('icon', 'image/x-cover'), 'page-images':('alt', 'text/*')}
    def depart_document (self, node):
        for key, values in node.meta_block.items ():
            for val in values:
                val = self.attval (six.text_type (val))
                if key in link_data:
                    key, type_ = link_data[key]        
                    self.head.append('<link rel="%s" href="%s" type= "%s" />\n' % (key, val, type_))
                else:
                    self.head.append ('<meta name="%s" content="%s" />\n' % (key, val))

        html4css1.HTMLTranslator.depart_document (self, node)

    def visit_meta (self, node):
        # not used any more
        pass

    def visit_title (self, node):
        if isinstance (node.parent, nodes.table):
            self.body.append (self.starttag (node, 'caption'))
            if node.hasattr('refid'):
                atts = {
                    'class': 'toc-backref',
                    'href': '#' + node['refid'],
                    }
                self.body.append (self.starttag ({}, 'a', **atts))
                self.context.append ('</a></caption>\n')
            else:
                self.context.append ('</caption>\n')
        else:
            html4css1.HTMLTranslator.visit_title (self, node)


    def depart_title (self, node):
        html4css1.HTMLTranslator.depart_title (self, node)


    def visit_subtitle (self, node):
        """ Tweak is: use <p> instead of <h?> """

        if isinstance (node.parent, (nodes.document, nodes.section, nodes.topic)):
            self.body.append (self.starttag (node, 'p'))
            self.context.append ('</p>\n')
            if isinstance (node.parent, nodes.document):
                self.in_document_title = len (self.body)
            return

        html4css1.HTMLTranslator.visit_subtitle (self, node)


    def depart_subtitle (self, node):
        html4css1.HTMLTranslator.depart_subtitle (self, node)


    def visit_caption (self, node):
        """ Tweak is: use <div> instead of <p> """
        self.body.append (self.starttag (node, 'div', CLASS='caption'))

        atts = {}
        if node.hasattr ('refid'):
            atts['class'] = 'toc-backref'
            atts['href'] = '#' + node['refid']
            self.body.append (self.starttag ({}, 'a', **atts))


    def depart_caption (self, node):
        """ Tweak is: use <div> instead of <p> """
        if node.hasattr ('refid'):
            self.body.append ('</a>')
        self.body.append ('</div>\n')


    def visit_line (self, node):
        """ Tweak is: fix empty lines on ADE. """

        self.body.append (self.starttag (node, 'div', '', CLASS='line'))
        if not len (node):
            self.body.append (' ') # U+00A0 nbsp


    def visit_line_block (self, node):
        """ Tweak is: noindent if centered or right-aligned. """

        extraclasses = ['line-block']
        if isinstance (node.parent, nodes.line_block):
            extraclasses.append ('inner')
        else:
            extraclasses.append ('outermost')
        if 'center' in node['classes'] or 'right' in node['classes']:
            extraclasses.append ('noindent')
        self.body.append (self.starttag (node, 'div', **{ 'class': extraclasses }))


    def visit_table (self, node):
        self.context.append (self.compact_p)
        self.compact_p = True

        node['styles'] = []
        node['html_attributes'] = {}

        pass_1 = writers.TablePass1 (self.document)
        node.walkabout (pass_1)

        options = { 'class': ['table'] }
        if 'align' in node:
            options['class'].append ('align-%s' % node['align'])
        if 'summary' in node:
            options['summary'] = node['summary']
        if 'table' in node['hrules']:
            options['class'].append ('hrules-table')
        if 'rows' in node['hrules']:
            options['class'].append ('hrules-rows')
        if 'table' in node['vrules']:
            options['class'].append ('vrules-table')
        if 'columns' in node['vrules']:
            options['class'].append ('vrules-columns')
        self.calc_centering_style (node)
        self.body.append (self.starttag (node, 'table', **options))

    def depart_table (self, node):
        self.compact_p = self.context.pop ()
        self.body.append ('</table>\n')

    def visit_thead (self, node):
        self.set_first_last (node)
        html4css1.HTMLTranslator.visit_thead (self, node)

    def visit_tbody (self, node):
        self.set_first_last (node)
        html4css1.HTMLTranslator.visit_tbody (self, node)

    def visit_entry (self, node):
        """ Tweak is: put alignment on element. """

        if 'vspan' in node:
            # HTML spans natively
            raise nodes.SkipNode

        node['styles'] = []
        align = node.colspecs[0].get ('align', 'left')
        if align != 'left':
            node['styles'].append ("text-align: %s" % align)
        valign = node.colspecs[0].get ('valign', 'middle')
        if valign != 'middle':
            node['styles'].append ("vertical-align: %s" % valign)

        html4css1.HTMLTranslator.visit_entry (self, node)

    def visit_target (self, node):
        if 'pageno' in node['classes'] or 'lineno' in node['classes']:
            options = { 'class': 'target' }
            # the ' ' avoids an empty span which will cause trouble if
            # parsed by a HTML parser.
            # FIXME: move pageno out of caption

            # bump image offset
            if self.imgoff:
                self.imgoff += 1
            if 'imgoff' in node:
                self.imgoff = int (node['imgoff'])

            if self.imgoff and 'page-images' in self.document.meta_block:
                href = self.document.meta_block['page-images'][0]
                href = href.format (page = self.imgoff)
                node['html_attributes']['href'] = href
                if 'invisible' in node['classes']:
                    node['html_attributes']['title'] = ' '
                    del node['classes'][node['classes'].index ('invisible')]
                self.body.append (self.starttag (node, 'a', ' ', **options))
                self.context.append('</a>')
            else:
                self.body.append (self.starttag (node, 'span', ' ', **options))
                self.context.append('</span>')
            return
        html4css1.HTMLTranslator.visit_target (self, node)


    def visit_page (self, node):
        if 'vspace' in node['classes']:
            node['styles'] = [ 'height: %dem' % node['length'] ]
        self.body.append (self.starttag (node, 'div'))

    def depart_page (self, node):
        self.body.append ('</div>\n')

        #c = node['classes']
        #if 'clearpage' in c or 'cleardoublepage' in c:
        #    self.body.append (self.starttag (node, 'hr', empty = 1))

    def visit_newline (self, node):
        if 'white-space-pre-line' in node['classes']:
            self.body.append ('<br />\n')
        else:
            self.body.append ('\n')

    def depart_newline (self, node):
        pass

    def visit_inline (self, node, extra_classes = []):
        options = {}
        if 'dropcap' in node['classes']:
            node['styles'] = [ "font-size: %.2fem" % (
                float (node.get ('lines', '2')) * 1.5) ]
        self.body.append (self.starttag (node, 'span', '', **options))


    def calc_centering_style (self, node):
        """
        To be overwritten in derived writers.

        :align: center has not the same semantics as :class: center.
        Former centers the block, eg. the whole table, latter centers
        the text, eg, the text in every table cell.

        :align: is supposed to work on blocks. It floats or centers
        a block.

            `:align: center`
                Used on image: centers image
                Used on figure: centers image and caption
                Used on table: centers table and caption

        """

        styles = node['styles']
        if 'width' in node and node ['width'] != 'image':
            styles.append ('width: %s' % node ['width'])


    def visit_image (self, node):
        node['styles'] = []
        node['html_attributes'] = {}
        if not node.get ('alt'):
            node['alt'] = ' '

        if 'dropcap' in node['classes']:
            node['height'] = "%.2fem" % (float (node.get ('lines', '2')) * 1.2)

        # check if we are a block image.
        # see class `TextElement` in `docutils.nodes`.
        if not isinstance (node.parent, nodes.TextElement):
            self.calc_centering_style (node)
            node['styles'].append ('display: block')

        html4css1.HTMLTranslator.visit_image (self, node)


    def depart_image (self, node):
        html4css1.HTMLTranslator.depart_image (self, node)


    def visit_figure (self, node):
        node['styles'] = []
        node['html_attributes'] = {}
        options = {}

        class_ = ['figure']
        if 'align' in node:
            class_.append ('align-' + node['align'])
        options['class'] = class_

        self.calc_centering_style (node)

        self.body.append (self.starttag (node, 'div', **options))


    def visit_block_quote (self, node):
        self.body.append (self.starttag (node, 'blockquote'))
        self.body.append ('<div>\n')

    def depart_block_quote(self, node):
        self.body.append ('</div>\n</blockquote>\n')


    def visit_footnote_group (self, node):
        self.body.append (self.starttag (node, 'div', CLASS='footnote-group'))

    def depart_footnote_group (self, node):
        self.body.append ('</div>\n')


    def visit_transition (self, node):
        self.body.append (self.starttag (node, 'div', CLASS='transition'))

    def depart_transition (self, node):
        self.body.append ('</div>\n')


    def visit_attribution(self, node):
        self.body.append (self.starttag (node, 'div', CLASS='attribution'))

    def depart_attribution(self, node):
        self.body.append ('</div>\n')
