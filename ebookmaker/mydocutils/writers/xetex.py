# -*- coding: utf-8 -*-
# Copyright: This module is put into the public domain.
# Author: Marcello Perathoner <webmaster@gutenberg.org>

"""
Xetex writer for reStructuredText.

This module is more suitable for writing novel-type books than
documentation.

"""

from __future__ import unicode_literals

__docformat__ = 'reStructuredText'

import operator
import os
import re

import six

from docutils import nodes, frontend, transforms
from docutils.writers.html4css1 import SimpleListChecker

from libgutenberg.Logger import error, warning, info, debug
from libgutenberg import DublinCore
from ebookmaker.Version import VERSION

from ebookmaker.mydocutils import writers
from ebookmaker.mydocutils.transforms import parts

XETEX_PREAMBLE = r"""% -*- mode: tex -*- coding: utf-8 -*-
% Converted from RST master
%
\documentclass[a5paper]{book}

\usepackage{polyglossia}
\setotherlanguages{<otherlanguages>}

\usepackage{xltxtra}

\defaultfontfeatures{Scale=MatchLowercase}
\setmainfont{Libertinus Serif}
\setsansfont{Libertinus Sans}
\setmonofont[HyphenChar=None]{DejaVu Sans Mono}

\usepackage{calc}
\usepackage{graphicx}
\usepackage{alltt}
\usepackage{float}

\usepackage{array} % longtable uses array if loaded
\usepackage{longtable}

\usepackage{booktabs} % typographical tables
\newcommand{\otoprule}{\midrule[\heavyrulewidth]}

\usepackage{lettrine} % dropcaps
\usepackage[implicit=false,colorlinks=true,linkcolor=blue]{hyperref}
<hypersetup>
\usepackage[open,openlevel=1]{bookmark}

\tolerance 10000  % dont make overfull boxes
\hbadness 1000    % warn if badness exceeds 1000

\catcode`@=11     % make 'private' LaTeX variables public
\catcode`\^^J=10  % don't let empty lines end paragraphs
\catcode`\^^M=10
\catcode`\"=12    % no electric quotes

\setlength{\textwidth} {\paperwidth  * 7 / 9}
\setlength{\textheight}{\paperheight * 7 / 9}

% round textheight to baselineskip
\small\normalsize
\advance\textheight by .5\baselineskip
\divide\textheight by \baselineskip
\multiply\textheight by \baselineskip
\advance\textheight by \topskip

\setlength{\topmargin}     {\paperheight / 9 - \topskip - \headsep - \headheight - 1in}

\setlength{\evensidemargin}{\paperwidth / 9 - 1in}
\setlength{\oddsidemargin} {\paperwidth / 9 - 1in}

% \setlength{\fboxsep}{0pt} % fbox used for debugging

\let\par=\endgraf % elude macro parameter protection

\begin{document}

\newcommand{\parindentamount}{24pt}
\setlength{\parindent}{\parindentamount}
\setlength{\parskip}{0pt}
\setlength{\parsep}{0pt}
% \setlength{\topsep}{0pt plus6pt}
\setlength{\footnotesep}{0pt}

% relax float restrictions
\renewcommand{\topfraction}{.85}
\renewcommand{\bottomfraction}{.7}
\renewcommand{\textfraction}{.15}
\renewcommand{\floatpagefraction}{.66}
\renewcommand{\dbltopfraction}{.66}
\renewcommand{\dblfloatpagefraction}{.66}
\setcounter{topnumber}{9}
\setcounter{bottomnumber}{9}
\setcounter{totalnumber}{20}
\setcounter{dbltopnumber}{9}

\setcounter{LTchunksize}{10000} % process tables in one chunk

% latex always wants a numeric parameter to \footnotemark and \footnotetext
% hack to get latex to accept any string as footnote label
\def\@xfootnotemark[#1]{%
   \begingroup
      \unrestored@protected@xdef\@thefnmark{#1}%
   \endgroup
   \@footnotemark}

\def\@xfootnotenext[#1]{%
  \begingroup
     \unrestored@protected@xdef\@thefnmark{#1}%
  \endgroup
  \@footnotetext}


% headers

% HACK! to avoid a page break between labels and section title
% standard secpenalty is -300
\@secpenalty = 0

\setcounter{secnumdepth}{-1} % no automatic section numbering
% \setcounter{tocdepth}{1} we don't use auto toc at present

% \def\pgpageno#1{\marginpar[\hfill\fbox{#1}]{\fbox{#1}}}

% \def\pglineno#1{\@mparswitchfalse\marginparsep-24pt\marginpar{#1}}

\def\sd{\dp\strutbox}

\def\pgpageno#1{\strut\vadjust{\kern-\sd\vtop to \sd{\baselineskip\sd\vss\vbox{\hbox to 0pt{\hss\footnotesize(#1)\kern 18pt}\null}}}}

\def\pglineno#1{\strut\vadjust{\kern-\sd\vtop to \sd{\baselineskip\sd\vss\vbox{\hbox to \hsize{\hfill #1\kern 24pt}\null}}}}

\floatstyle{boxed}
\newfloat{topic}{tbp}{loc}
\newfloat{sidebar}{tbp}{los}

\long\def\centerleft#1{%
  {\sbox\@tempboxa{#1}%
  \ifdim \wd\@tempboxa >\hsize
    #1\par
  \else
    {\centering #1\par}
  \fi}}

\setlength{\belowcaptionskip}{\smallskipamount}

\def\raggedright{%
  \let\\\@centercr
  \advance\rightskip\@flushglue
  \parindent\z@}

\def\centering{%
  \let\\\@centercr
  \advance\rightskip\@flushglue\advance\leftskip\@flushglue
  \parindent\z@\parfillskip\z@skip}

\def\raggedleft{%
  \let\\\@centercr
  \advance\leftskip\@flushglue
  \parindent\z@\parfillskip\z@skip}

\renewenvironment{verse}{\parindent\z@}{}

% insert vertical spacing
\def\vs#1{\vspace{#1\baselineskip}}

% one line of verse
\def\vl{\advance\leftskip48pt\hskip-48pt}

% define environments for most of the
% standard building blocks of a book

\def\startenv{%
  \thispagestyle{empty}%
}
\def\endenv{%
}

\newenvironment{container}{}{\par}

<environments>

\newdimen{\tablewidth} % helper

% \tracingpages=1

\frontmatter

\thispagestyle{empty}

"""

XETEX_POSTAMBLE = r"""
\end{document}

% Local Variables:
% mode: tex
% encoding: utf-8
% End:
"""

class InheritTransform (parts.InheritTransform):
    pass


class FootnotesTransform (transforms.Transform):
    """
    Moves footnote bodies near to footnote references.

    Inserts the footnote body immediately after the footnote reference
    in Xetex format.

    """

    default_priority = 717

    def apply (self, **kwargs):
        # reversed () makes footnotes inside of footnotes come out in
        # the right order
        footnote_refs = list (self.document.traverse (nodes.footnote_reference))
        for footnote_reference in reversed (footnote_refs):
            if 'refid' not in footnote_reference:
                # further references to footnote
                continue
            # pull in footnote body
            footnote = self.document.ids [footnote_reference['refid']]
            footnote_section = footnote.parent
            footnote_section.remove (footnote)

            parent = footnote_reference.parent
            index = parent.index (footnote_reference)
            parent.insert (index + 1, footnote)

            # if the footnote is inside a table environment, move the
            # footnote behind the table
            while parent:
                table = parent
                parent = parent.parent
                if isinstance (table, (nodes.table, nodes.title, nodes.footnote)):
                    footnote.parent.remove (footnote)
                    index = parent.index (table)
                    parent.insert (index + 1, footnote)


class Writer (writers.Writer):
    """ A xetex/pdf writer. """

    supported = ('xetex',)
    """Formats this writer supports."""

    output = None
    """Final translated form of `document`."""

    settings_spec = (
        'Xetex-Specific Options',
        None,
        (('Should lists be compacted when possible?',
          ['--compact-lists'],
          {'default': 1,
           'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Image Size Function',
          ['--get-image-size'],
          {'default': None,
           'dest': 'get_image_size',
           'metavar': '<python function>'}),
         ))

    config_section = 'XeTeX writer'


    def get_transforms (self):
        tfs = writers.Writer.get_transforms (self)
        return tfs + [parts.TextNodeWrapper, InheritTransform, FootnotesTransform]


    def __init__ (self):
        writers.Writer.__init__ (self)
        self.translator_class = Translator


    def translate (self):
        visitor = self.translator_class (self.document)
        self.document.walkabout (visitor)
        self.output = visitor.astext ()


class MakeTableRules (nodes.SparseNodeVisitor):

    """
    Makes a pass over a table row to output rules.
    """

    def __init__ (self, document, translator):
        nodes.SparseNodeVisitor.__init__ (self, document)
        self.translator = translator

    def unknown_visit (self, node):
        pass

    def visit_entry (self, node):
        """ Called on each table cell. """

        if 'vspan' in node:
            raise nodes.SkipNode

        firstcol = node['column']
        lastcol = firstcol + len (node.colspecs) - 1
        self.translator.cmd (r'\cmidrule{%d-%d}' % (firstcol + 1, lastcol + 1)) # 1-based


class ContentsFilter (nodes.TreeCopyVisitor):
    """ Clean a title for inclusion in a TOC. """

    def visit_citation_reference (self, node):
        raise nodes.SkipNode

    def visit_footnote_reference (self, node):
        raise nodes.SkipNode

    def visit_bullet_list (self, node):
        # skip titles of lesser sections (TOCs are nested lists)
        raise nodes.SkipNode

    def visit_inline (self, node):
        if 'toc-pageref' in node['classes']:
            raise nodes.SkipNode
        self.default_visit (node)

    def visit_newline (self, node):
        self.parent.append (nodes.Text (' '))
        self.default_visit (node)

    def depart_newline (self, node):
        self.default_departure (node)

    def visit_image (self, node):
        if 'alt' in node:
            self.parent.append (nodes.Text (node['alt']))
        raise nodes.SkipNode

    def ignore_node_but_process_children (self, node):
        raise nodes.SkipDeparture

    visit_interpreted = ignore_node_but_process_children
    visit_problematic = ignore_node_but_process_children
    visit_reference = ignore_node_but_process_children
    visit_target = ignore_node_but_process_children


class Translator (writers.Translator):
    """ XeTeX translator """

    # beforeskip, afterskip and font
    # values from latex book.cls
    section_params = (
        (r'\vspace*{50pt}\thispagestyle{empty}',
                            r'\vskip 40pt',  r'\normalfont\Huge\bfseries'),
        (r'\vskip 3.5ex',   r'\vskip 2.3ex', r'\normalfont\Large\bfseries'),
        (r'\vskip 3.25ex',  r'\vskip 1.5ex', r'\normalfont\large\bfseries'),
        (r'\vskip 3.25ex',  r'\vskip 1.5ex', r'\normalfont\normalsize\bfseries'),
        (r'\vskip 3.25ex',  r'\vskip 1.5ex', r'\normalfont\normalsize\bfseries'),
        (r'\vskip 3.25ex',  r'\vskip 1.5ex', r'\normalfont\normalsize\bfseries'),
        )

    # environments that need special treatment, defined in XETEX_PREAMBLE
    page_environments = """
    coverpage frontispiece titlepage verso dedication plainpage
    """.split ()

    # more environments that don't get special treatment
    # but might be useful in post-processing the TeX file
    special_environments = """
    contents foreword preface introduction prologue epilogue glossary
    bibliography index colophon pgfooter pgheader appendix
    """.split ()


    def __init__ (self, document):
        writers.Translator.__init__ (self, document)

        self.forbidden = '' # temporary hold for statements that are forbidden
                            # in environments. eg. footnotes inside tables.

        self.base_dir = os.path.dirname (document.settings.base_url)
        self.last_output_char = '\n'
        self.indent_p = False
        self.used_languages = set (('english', ))
        self.in_float = 0 # are we in a float? (latex doesn't allow nested floats)


    def register_classes (self):
        """ Register classes. """

        # register classes in the order you want them applied!

        # outside block classes

        # mayor structural building blocks
        for i in self.page_environments + self.special_environments:
            self.register_class  ('compound simple', i, '\\begin{%s_env}\n' % i, '\\end{%s_env}\n' % i)

        # simple classes
        # are blocks that contain only inlines

        self.register_class ('simple', 'noindent',     '\\noindent\n',     '')
        self.register_class ('simple', 'left',         '{\\raggedright\n', '\\endgraf}\n')
        self.register_class ('simple', 'center',       '{\\centering\n',   '\\endgraf}\n')
        self.register_class ('simple', 'right',        '{\\raggedleft\n',  '\\endgraf}\n')
        self.register_class ('simple', 'centerleft',   '{\\centerleft{',   '}}\n')

        # inline classes
        # be careful not to insert spurious spaces here

        self.register_class ('inline', 'superscript', r'\textsuperscript{', r'}')
        self.register_class ('inline', 'subscript',   r'\textsubscript{',   r'}')
        self.register_class ('inline', 'italics',     r'{\itshape{',        r'}}')
        self.register_class ('inline', 'bold',        r'{\bfseries{',       r'}}')
        self.register_class ('inline', 'monospaced',  r'{\ttfamily{',       r'}}')
        self.register_class ('inline', 'small-caps',  r'{\scshape{',        r'}}')
        self.register_class ('inline', 'normal',      r'{\upshape{',        r'}}')
        self.register_class ('inline', 'antiqua',     r'{\upshape{',        r'}}')
        self.register_class ('inline', 'gesperrt',    r'{\addfontfeature{LetterSpace=20.0}{',  r'}}')
        self.register_class ('inline', 'larger',      r'{\addfontfeature{Scale=1.2}{',         r'}}')
        self.register_class ('inline', 'smaller',     r'{\addfontfeature{Scale=0.8}{',         r'}}')

        self.register_class ('inline', 'dropspan',    r'{', r'}')

        # The height of a TeX box is just the height of the character,
        # while the height of an HTML line box is the height of the
        # character + internal leading.  Adding \strut is a sorry fix
        # for the problem of paragraphs with different font sizes.  It
        # will work only for spans of text not longer than 2 lines.  A
        # real fix must insert \strut before and/or after every word
        # in the bigger text.  A fix involving \baselineskip or
        # \lineskip and \lineskiplimit will not work because those
        # values will be reset before the paragraph builder gets
        # exercised.

        self.register_class ('inline', 'xx-large',    r'{\Huge\strut{',         r'}}')
        self.register_class ('inline', 'x-large',     r'{\LARGE\strut{',        r'}}')
        self.register_class ('inline', 'large',       r'{\Large\strut{',        r'}}')
        self.register_class ('inline', 'medium',      r'{\normalsize{ ',   r'}}')
        self.register_class ('inline', 'small',       r'{\footnotesize{', r'}}')
        self.register_class ('inline', 'x-small',     r'{\scriptsize{',   r'}}')
        self.register_class ('inline', 'xx-small',    r'{\tiny{',         r'}}')

        self.register_class ('inline', 'red',         r'{\addfontfeature{Color=FF0000}{',      r'}}')
        self.register_class ('inline', 'green',       r'{\addfontfeature{Color=00FF00}{',      r'}}')
        self.register_class ('inline', 'blue',        r'{\addfontfeature{Color=0000FF}{',      r'}}')
        self.register_class ('inline', 'yellow',      r'{\addfontfeature{Color=FFFF00}{',      r'}}')
        self.register_class ('inline', 'white',       r'{\addfontfeature{Color=FFFFFF}{',      r'}}')
        self.register_class ('inline', 'gray',        r'{\addfontfeature{Color=808080}{',      r'}}')
        self.register_class ('inline', 'black',       r'{\addfontfeature{Color=000000}{',      r'}}')


    def cmd (self, cmds):
        """ Output tex commands. """

        if isinstance (cmds, six.string_types):
            cmds = [cmds]

        for c in cmds:
            if c:
                self.context.append (c)
                self.last_output_char = c[-1]

    def text (self, text):
        """ Output text. """

        if text:
            # self.output_noindent ()
            self.context.append (text)
            self.last_output_char = text[-1]


    def comment (self, text):
        """ Output tex comment. """
        self.context.append ('%% %s\n' % text)
        self.last_output_char = '\n'
        self.src_sp ()

    def nl (self):
        if self.last_output_char != '\n':
            self.context.append ('\n')
            self.last_output_char = '\n'

    def noindent (self, b = True):
        """ Don't indent following text. """
        self.indent_p = not b

    def output_sp (self):
        """ Output spacing. """
        if self.vspace == 1999: # magic number to eat all space
            self.vspace = 0
        if self.vspace:
            self.nl ()
            self.cmd ('\\vs{%d}\n' % self.vspace)
            self.vspace = 0
            self.noindent ()

    def output_src_sp (self):
        """ Output source spacing. """
        if self.src_vspace == 1999: # magic number to eat all space
            self.src_vspace = 0
        if self.src_vspace:
            self.nl ()
            self.context.append ('\n' * self.src_vspace)
            self.src_vspace = 0

    def output_noindent (self):
        if not self.indent_p:
            self.context.append ('{\\noindent}\n')
            self.indent_p = True

    def ta (self, indent, text):
        """ Tabulate text to indent position. """
        self.cmd (r'\hspace{%dem}\=\kill\+' % indent)
        self.text (text)

    def push (self):
        """ Push environment. """
        self.context.append ('{')
        self.last_output_char = '{'

    def pop (self):
        """ Pop environment. """
        self.context.append ('}')
        self.last_output_char = '}'

    def begin (self, name, param = None):
        """ Push environment. """
        self.output_src_sp ()
        self.environments.append (name)
        self.cmd ('\\begin{%s}%s\n' % (name, param or ''))

    def end (self):
        """ Pop environment. """
        name = self.environments.pop ()
        self.nl ()
        self.cmd ('\\end{%s}\n' % name)

    def filter_title (self, node):
        """ Return a copy of a title, with references, images, etc. removed."""
        visitor = ContentsFilter (self.document)
        node.walkabout (visitor)
        return visitor.get_tree_copy ()

    def make_relative (self, uri):
        # Use relative paths in the TeX file because we copied the
        # image files to a local disk. (TeX cannot pull files from the
        # network.)

        # print ("make_relative: %s from %s" % (uri, self.base_dir))
        uri = os.path.relpath (uri, self.base_dir)
        # print ("made_relative: %s" % uri)

        return uri

    def get_align (self, node):
        return node.colspecs[0].get ('align', 'justify')[0] # .upper ()

    def indent (self, by = 1):
        """ Indent text. """
        self.cmd (r'\advance\leftskip\parindentamount{}') #  % by)

    def rindent (self, by = 1):
        """ Indent text on the right side. """
        self.cmd (r'\advance\rightskip\parindentamount{}') #  % by)

    def bq (self, by = 1):
        self.indent (by)
        self.rindent (by)
        self.noindent ()

    # pylint: disable=C0111
    # pylint: disable=W0613

    translate_map = {
        ord ('#'):  r'\#',
        ord ('$'):  r'\$',
        ord ('%'):  r'\%',
        ord ('&'):  r'\&',
        ord ('~'):  r'\textasciitilde{}',
        ord ('_'):  r'\_',
        ord ('^'):  r'\textasciicircum{}',
        ord ('\\'): r'\textbackslash{}',
        ord ('{'):  r'\{',
        ord ('}'):  r'\}',
        ord ('['):  r'{[}',
        ord (']'):  r'{]}',
        0x00ad:     r'\-', # soft hyphen
    }

    translate_map_literal = {}
    translate_map_literal.update (translate_map)
    translate_map_literal.update ({
        0x0d:       '\\\\n',
    })

    def preamble (self):
        """ Inserts xetex preamble. """

        hs = ['\\hypersetup{pdfcreator={Ebookmaker %s}}' % VERSION]
        if hasattr (self.document, 'meta_block'):
            for name, values in self.document.meta_block.items ():
                if name.lower () == 'dc.title':
                    content = values[0]
                    hs.append ('\\hypersetup{pdftitle={%s}}' % self.encode (content))
                elif name.lower () == 'dc.creator':
                    content = DublinCore.DublinCore.strunk (values)
                    hs.append ('\\hypersetup{pdfauthor={%s}}' % self.encode (content))
                elif name.lower () == 'dc.subject':
                    content = DublinCore.DublinCore.strunk (values)
                    hs.append ('\\hypersetup{pdfsubject={%s}}' % self.encode (content))

        envs = []
        for i in self.page_environments:
            envs.append (r'\newenvironment{%s_env}{\startenv}{\endenv}' % i)
        for i in self.special_environments:
            envs.append (r'\newenvironment{%s_env}{}{}' % i)

        preamble = XETEX_PREAMBLE
        preamble = preamble.replace ('<environments>', '\n'.join (envs))
        preamble = preamble.replace ('<otherlanguages>', ','.join (self.used_languages))
        return preamble.replace ('<hypersetup>', '\n'.join (hs))

    def postamble (self):
        """ Inserts xetex postamble. """
        return XETEX_POSTAMBLE

    def write_labels (self, node):
        """ Write labels for all ids and the refid of `node` """

        ids = node['ids']
        refid = node.get ('refid')
        if refid is not None:
            ids.append (refid)

        for id_ in ids:
            self.cmd ('\\label{%s}%%\n' % id_)
            self.cmd ('\\hypertarget{%s}{}%%\n' % id_)

    def write_pdf_bookmark (self, title, action_option, level = None):
        if level is None:
            level = self.section_level
        options = [ 'level=%d' % level, action_option ]
        self.cmd ('\\bookmark[%s]{%s}\n' % (','.join (options), self.encode (title)))

    def latex_units (self, length_str, reference_length = ''):
        """ Convert rst units to LaTeX units. """

        if length_str == 'image':
            return reference_length

        match = re.match (r'(\d*\.?\d*)\s*(\S*)', length_str)
        if not match:
            return length_str

        value, unit = match.groups ()
        # no unit or "DTP" points (called 'bp' in TeX):
        if unit in ('', 'pt'):
            length_str = '%sbp' % value

        # percentage: relate to current line width
        elif unit == '%':
            length_str = '%.3f%s' % (float (value) / 100.0, reference_length)

        return length_str

    def latex_floats (self, values):
        if 'none' in values:
            # 'H' must be only option, as per float package doc
            return 'H'
        lf = ''
        for v in values:
            lf += { 'here': 'h!', 'top': 't', 'bottom': 'b', 'page': 'p' }[v]
        if lf == 'h!':
            lf = 'h!t'
        return lf

    def begin_float (self, node, type_):
        """ Potentially open a latex floating environment. """

        ltxfl = self.latex_floats (node['float'])

        # latex doesn't support nested floating environments
        node.do_float = (ltxfl != 'H') and (self.in_float == 0)

        if node.do_float:
            # if we float we must save the accumulated space and remove it
            # or it will show up at the top inside the float
            node.saved_vspace = self.vspace
            self.vspace = 0

            # if we float away, make the next paragraph indent
            # note: we don't indent paras after figures any more
            #for para in node.traverse (nodes.paragraph, include_self = False, siblings = True):
            #    classes = para['classes']
            #    classes.append ('pnext')
            #    if 'pfirst' in classes:
            #        classes.remove ('pfirst')

            self.in_float += 1
            self.begin (type_, '[%s]' % ltxfl)
        else:
            self.begin ('container')

    def end_float (self, node):
        self.end ()
        if node.do_float:
            self.in_float -= 1
            # FIXME: floats insert their own breaks. Do we still needs this?
            self.vspace = node.saved_vspace
            # self.vspace = 0

    def encode (self, text):
        return text.translate (self.translate_map)

    def latex_language (self, node):
        """ language hack """

        for c in node['classes']:
            if c.startswith ('language-'):
                language = c[9:]
                language = DublinCore.DublinCore.language_map.get (
                    language, default='en').lower ()
                self.used_languages.add (language)
                return language
        return None

    # begin visitor functions

    def visit_outer (self, node):
        # self.comment ("visit_outer: %s" % node.__class__.__name__)

        if node.type in ('compound', 'simple'):
            if not isinstance (node, (nodes.footnote, nodes.label)):
                # often footnotes are moved inside of inline text
                # a newline in the source would then insert a spurious space
                self.output_src_sp ()

            language = self.latex_language (node)
            if language:
                self.begin (language)

        # transition and image
        if node.type == 'empty':
            if 'margin' in node['classes']:
                self.sp ()
            self.output_sp ()

    def visit_inner (self, node):
        # self.comment ("visit_inner: %s" % node.__class__.__name__)

        # must be here because it belongs inside a potential float
        if node.type != 'text' and 'margin' in node['classes']:
            self.sp ()

        # There can be only inline nodes inside a simple node, and
        # inline nodes have no margins, so we can safely output
        # vertical space here.
        if node.type == 'simple':
            self.output_sp ()
            self.output_noindent ()

        if node.type == 'inline':
            language = self.latex_language (node)
            if language:
                self.cmd (r'\text%s{' % language)
            self.cmd (self.get_prefix (node.type, node['classes']))

        elif node.type != 'text':
            prefix = self.get_prefix (node.type, node['classes'])
            if prefix:
                self.nl ()
                self.cmd (prefix)

    def depart_inner (self, node):
        if node.type == 'inline':
            self.cmd (self.get_suffix (node.type, node['classes']))
            if self.latex_language (node):
                self.cmd (r'}')
        elif node.type != 'text':
            suffix = self.get_suffix (node.type, node['classes'])
            if suffix:
                self.nl ()
                self.cmd (suffix)
        if node.type != 'text' and 'margin' in node['classes']:
            self.sp ()

        # self.comment ("departed_inner: %s" % node.__class__.__name__)

    def depart_outer (self, node):
        if node.type == 'empty':
            if 'margin' in node['classes']:
                self.sp ()

        if node.type in ('compound', 'simple'):
            if self.latex_language (node):
                self.end ()
            self.src_sp ()

        # self.comment ("departed_outer: %s" % node.__class__.__name__)


    def visit_Text (self, node):
        text = node.astext ()
        if self.in_literal:
            text = text.translate (self.translate_map_literal)
        else:
            text = text.translate (self.translate_map)

        if hasattr (node, 'attributes') and 'white-space-pre-line' in node.attributes['classes']:
            for line in text.splitlines (True):
                self.text (line)
                if '\n' in line:
                    self.cmd (' \\\\\n')
        else:
            self.text (text)

    def depart_Text (self, node):
        pass

    def visit_inline (self, node):
        if 'toc-pageref' in node['classes']:
            self.cmd (r'\leaders\hbox to 1em{\hss.\hss}\hfill{}')
        if 'dropcap' in node['classes']:
            self.lettrine (node)

    def depart_inline (self, node):
        if 'dropcap' in node['classes']:
            self.cmd (r'}')

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
        self.push ()
        self.indent (2)

    def depart_field_list (self, node):
        self.pop ()

    # start admonitions

    def visit_admonition (self, node, name = None):
        self.sp ()
        self.push ()
        self.bq ()
        if name:
            self.output_sp ()
            self.cmd ('\\textbf{')
            self.text (name)
            self.cmd ('}\\par\\nopagebreak\n\n')

    def depart_admonition (self, node):
        self.pop ()
        self.sp ()

    def visit_admonition_title (self, node):
        pass

    def depart_admonition_title (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        self.sp ()

    # start definition lists

    def visit_definition_list (self, node):
        self.begin ('description')

    def depart_definition_list (self, node):
        self.end ()

    def visit_definition_list_item (self, node):
        pass

    def depart_definition_list_item (self, node):
        pass

    def visit_term (self, node):
        self.cmd ('\\item[')

    def depart_term (self, node):
        self.cmd ('] ')

    def visit_classifier (self, node):
        pass

    def depart_classifier (self, node):
        pass

    def visit_definition (self, node):
        pass

    def depart_definition (self, node):
        pass

    # start option lists

    def visit_option_list (self, node):
        pass

    def depart_option_list (self, node):
        pass

    def visit_option_list_item (self, node):
        pass

    def depart_option_list_item (self, node):
        pass

    def visit_option_group (self, node):
        pass

    def depart_option_group (self, node):
        pass

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

    def depart_option_argument (self, node):
        pass

    def visit_description (self, node):
        pass

    def depart_description (self, node):
        pass

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
        self.begin ('itemize')
        self.list_enumerator_stack.append (writers.ListEnumerator (node, 'utf-8'))

    def list_end (self, node):
        self.list_enumerator_stack.pop ()
        self.end ()

    def visit_list_item (self, node):
        if 'toc-entry' in node['classes']:
            self.cmd (r'\item[] ')
        else:
            self.cmd (r'\item[%s] ' % self.list_enumerator_stack[-1].get_next ())

    def depart_list_item (self, node):
        pass

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
        self.push ()
        self.bq ()

    def depart_block_quote (self, node):
        self.pop ()
        self.sp ()

    def visit_comment (self, node):
        for line in node.astext ().splitlines ():
            self.comment (line)
        raise nodes.SkipNode

    def visit_container (self, node):
        self.begin ('container')

    def depart_container (self, node):
        self.end ()
        self.noindent ()

    def lettrine (self, node):
        # node is inline or image

        options = []
        if 'lines' in node:
            options.append ('lines=%d' % node['lines'])
        if 'indents' in node:
            indents = node['indents'].split ()
            if len (indents) < 2:
                indents.append ('0.5em')
            self.cmd (r'\dimen0=%s\dimen1=%s\advance\dimen1-\dimen0'
                      % (indents[0], indents[1]))
            options.append (r'findent=\dimen0')
            options.append (r'nindent=\dimen1')
        if 'raise' in node:
            options.append ('lraise=%f' % node['raise'])

        uri = None
        if isinstance (node, nodes.image):
            uri = node.get ('image', '')
        if uri:
            options.append ('image')
            self.cmd (r'\clubpenalty\@M\lettrine[%s]{%s}' %
                      (','.join (options), self.make_relative (uri)))
        else:
            self.cmd (r'\clubpenalty\@M\lettrine[%s]{' % ','.join (options))

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
        # extract bookmarks from the various 'contents' sections
        for container in node.traverse (nodes.container):
            if set (('contents', 'lof', 'lot')).intersection (container['classes']):
                if isinstance (container.parent[0], nodes.title):
                    title = self.filter_title (container.parent[0]).astext ()
                else:
                    title = 'Section'
                self.cmd ('\\bookmark[level=1,page=1]{%s}\n' % self.encode (title))

                for item in container.traverse (nodes.list_item):
                    text = self.filter_title (item).astext ()
                    self.write_pdf_bookmark (text, 'dest=%s' % item['refid'], item['level'])

        # bookmarks from original page numbers
        page_targets = [target for target in node.traverse (nodes.target)
                        if 'pageno' in target['classes']]
        if page_targets:
            self.cmd ('\\bookmark[level=1,page=1]{Pages In the Original}\n')
            for target in page_targets:
                title = target['html_attributes']['title']
                self.write_pdf_bookmark (title, 'dest=%s' % target['ids'][0], 2)

        # bookmarks need to land on a page
        self.cmd ('\\hbox{}')


    def visit_footer (self, node):
        self.document.reporter.warning (
            'footer not supported', base_node = node)

    def depart_footer (self, node):
        pass

    # footnotes, citations, labels

    def visit_label (self, node):
        # footnote and citation
        self.cmd ('\\footnotetext[')

    def depart_label (self, node):
        self.cmd (']')
        self.push ()
        self.sp (0)
        self.src_sp (0)

    def visit_footnote (self, node):
        pass

    def depart_footnote (self, node):
        self.nl ()
        self.pop ()

    def visit_footnote_reference (self, node):
        # we use \footnotemark in combination with \footnotetext to
        # permit footnotes even in forbidden modes
        self.cmd ('%\n\\footnotemark[')

    def depart_footnote_reference (self, node):
        self.cmd (']')

    def visit_citation (self, node):
        self.visit_footnote (node)

    def depart_citation (self, node):
        self.depart_footnote (node)

    def visit_citation_reference (self, node):
        self.cmd (r'\cite{')

    def depart_citation_reference (self, node):
        self.cmd (r'}')

    # end footnotes

    # references and targets

    def visit_reference (self, node):
        # we don't support extrnal refs
        if 'refuri' in node:
            href = None
        # internal reference
        elif 'refid' in node:
            href = node['refid']
        elif 'refname' in node:
            href = self.document.nameids[node['refname']]
        else:
            raise AssertionError ('Unknown reference.')
        if href:
            self.cmd ('\\hyperlink{%s}' % href)
        self.push ()

    def depart_reference (self, node):
        self.pop ()

    def visit_target (self, node):
        if 'pageno' in node['classes'] or 'lineno' in node['classes']:
            # self.output_noindent ()
            what = 'page' if 'pageno' in node['classes'] else 'line'
            if 'invisible' not in node['classes']:
                pageno = node['html_attributes']['title']
                cmd  = '\\pg%sno{%s}%%\n' % (what, pageno)
                if 'figure' in self.environments:
                    self.forbidden += cmd
                else:
                    self.cmd (cmd)
            # self.output_sp ()
            self.cmd (r'\raisebox{\ht\strutbox}')
            self.push ()

        refid = node.get ('refid')
        if refid is not None:
            # id has been moved to next_node
            # by PropagateTargets Transform in transforms/references.py

            # titles, figures, tables are handled in their visit_* method
            next_node = self.document.ids[refid]
            if not isinstance (next_node, (nodes.section, nodes.figure, nodes.table)):
                self.write_labels (node)
        else:
            self.write_labels (node)

        self.push ()

    def depart_target(self, node):
        if 'pageno' in node['classes'] or 'lineno' in node['classes']:
            self.pop ()
        self.pop ()

    # end references and targets

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
        self.forbidden = ''
        self.begin_float (node, 'figure')
        self.write_labels (node)

        if node.attributes.get ('align') in ('center', 'right'):
            self.cmd ('\\noindent\\hfill{}')

        if 'width' in node: # figwidth
            self.begin ('minipage', '{%s}' % self.latex_units (node['width'], '\\textwidth'))

    def depart_figure (self, node):
        if 'width' in node: # figwidth
            self.end ()

        if node.attributes.get ('align') == 'center':
            self.cmd ('\\hfill{}')

        self.end_float (node)
        self.cmd (self.forbidden)
        self.forbidden = ''

    image_align_codes = {
        # for inline images: by default latex aligns the bottom.
        'bottom': r'%s',
        'middle': r'\raisebox{-0.5\height}{%s}',
        'top':    r'\raisebox{-\height}{%s}',
        # block images:
        'center': r'{\hbox to \hsize{\hfill%s\hfill}}',
        'left':   r'{\hbox to \hsize{%s\hfill}}',
        'right':  r'{\hbox to \hsize{\hfill%s}}',
        }

    def visit_image (self, node):
        if 'dropcap' in node['classes']:
            self.lettrine (node)
            return

        options = []
        if 'height' in node:
            options.append ('height=%s' % self.latex_units (node['height']))
        if 'scale' in node:
            options.append ('scale=%f'  % (node['scale'] / 100.0))
        if 'width' in node:
            options.append ('width=%s'  % self.latex_units (node['width'], '\\textwidth'))

        options = (options and '[%s,keepaspectratio=true]' % (','.join (options))) or ''

        command = '\\includegraphics%s{%s}' % (options, self.make_relative (node['uri']))

        align = node.attributes.get ('align')
        if align in self.image_align_codes:
            command = self.image_align_codes[align] % command

        self.cmd (command)

    def depart_image (self, node):
        pass

    def visit_caption (self, node):
        # figure caption
        pass

    def depart_caption (self, node):
        pass

    def visit_legend (self, node):
        # figure legend
        pass

    def depart_legend (self, node):
        pass

    def visit_line_block (self, node):
        if not isinstance (node.parent, nodes.line_block):
            # outermost line block
            self.sp ()
            self.output_sp ()
            self.begin ('verse')
        else:
            self.push ()
            self.indent ()

    def depart_line_block (self, node):
        if not isinstance (node.parent, nodes.line_block):
            # outermost line block
            self.end ()
            self.sp ()
        else:
            self.pop ()

    def visit_line (self, node):
        if len (node.astext ()) == 0:
            # empty lines must use \vspace or latex
            # will complain about no line to end
            self.sp ()
            self.output_sp ()
        else:
            self.push ()
            self.cmd (r'\vl ')

    def depart_line (self, node):
        if len (node.astext ()) != 0:
            self.cmd ('\\par')
            self.pop ()
            self.nl ()

        if node is not node.parent[-1]: # not last
            self.src_sp (0)

    def visit_literal_block (self, node):
        self.sp ()
        self.output_sp () # vspace inside of tt block inserts a spurious newline
        self.begin ('alltt')
        self.in_literal += 1

    def depart_literal_block (self, node):
        self.in_literal -= 1
        self.end ()
        self.sp ()

    #
    #
    #

    def visit_paragraph (self, node):
        pass
        # self.output_sp ()
        # self.output_src_sp ()

    def depart_paragraph (self, node):
        # The LaTeX `\footnote` macro appends a strut to the footnote
        # text to ensure correct spacing if the last line of the
        # footnote text has no descenders. If we end the footnote with
        # a \par the strut will be inserted after the \par and will
        # yield an empty line.  The same is true for table cells.
        if isinstance (node.parent, (nodes.footnote, nodes.entry)):
            if not node.next_node (descend = 0, siblings = 1):
                return
        self.cmd (r'\par')
        self.src_sp ()
        if 'white-space-pre-line' in node['classes']:
            self.output_src_sp ()
            self.cmd ('\\vspace{1em}')
            self.src_sp ()

    def visit_raw (self, node):
        if 'tex' in node.get ('format', '').split():
            self.cmd (node.astext ())

        # ignore other raw formats
        raise nodes.SkipNode

    def visit_substitution_definition (self, node):
        """Internal only."""
        raise nodes.SkipNode

    def visit_substitution_reference (self, node):
        self.document.reporter.warning ('"substitution_reference" not supported',
                base_node=node)

    def visit_system_message (self, node):
        self.sp ()
        self.push ()
        self.bq ()
        line = ', line %s' % node['line'] if 'line' in node else ''
        self.text ('"System Message: %s/%s (%s:%s)"'
                  % (node['type'], node['level'], node['source'], line))

    def depart_system_message (self, node):
        self.pop ()
        self.sp ()

    # tables

    def begin_tabular (self, table):
        """ Begin longtable environment, add columns spec. """

        if self.header_sent:
            return

        colspec = ''
        if 'colspec' in table:
            colspec = table['colspec']
        else:
            colspecs = table.traverse (nodes.colspec)
            colspec = 'l' * len (colspecs)
            ## for c in colspecs:
            ##     colspec += { 'top'    : 'p' ,
            ##                  'middle' : 'm' ,
            ##                  'bottom' : 'b' }[c.get ('valign', 'middle')]
            ##     colspec += r'{%.03f\tablewidth}' % c['relative_width']


        self.cmd (r'\setlength{\tablewidth}{%s - \tabcolsep * 2 * %d}' % (
            self.latex_units (table.get ('width', '100%'), '\\linewidth'), len (colspecs)))

        self.src_sp ()
        self.begin ('longtable', r'{%s}' % (colspec))

        self.header_sent = True

    def visit_table (self, node):
        pass_1 = writers.TablePass1 (self.document)
        node.walk (pass_1)
        rows = pass_1.rows ()
        cols = pass_1.cols ()

        self.header_sent = False

        self.begin_float (node, 'table')
        self.write_labels (node)
        self.cmd ('\\footnotesize\n')

    def depart_table (self, node):
        self.end_float (node)

    def visit_table_title (self, node):
        self.sp ()

    def depart_table_title (self, node):
        self.cmd ('\\par\n')
        self.cmd ('\\penalty300\n')
        self.src_sp ()
        self.sp ()

    def visit_tgroup (self, node):
        pass

    def depart_tgroup (self, node):
        pass

    def visit_colspec (self, node):
        pass

    def depart_colspec (self, node):
        pass

    def visit_thead (self, node):
        table = node.parent.parent
        self.begin_tabular (table)
        self.set_first_last (node) # mark first row of head
        if 'table' in table['hrules']:
            self.cmd ('\\toprule\n')

    def depart_thead (self, node):
        pass

    def visit_tbody (self, node):
        table = node.parent.parent
        self.begin_tabular (table)
        self.set_first_last (node) # mark first row of body
        if 'table' in table['hrules']:
            self.cmd ('\\otoprule\n')

    def depart_tbody (self, node):
        table = node.parent.parent
        if 'table' in table['hrules']:
            self.cmd ('\\bottomrule\n')
        self.end ()

    def visit_row (self, node):
        table = node.parent.parent.parent
        self.set_first_last (node) # mark first and last cell
        if 'first' not in node['classes']:
            if 'rows' in table['hrules']:
                make_rules = MakeTableRules (self.document, self)
                node.walk (make_rules)
                self.cmd ('\n')

    def depart_row (self, node):
        self.cmd ('\\tabularnewline\n')

    def visit_entry (self, node):

        if 'vspan' in node:
            self.cmd (' & ' )
            raise nodes.SkipNode

        self.sp (0)

        sum_width = sum (map (operator.itemgetter ('relative_width'), node.colspecs))

        cols = node.get ('morecols', 0)
        if cols:
            self.cmd (r'\setlength{\dimen0}{%.03f\tablewidth + \tabcolsep * %d * 2}' % (sum_width, cols))
        else:
            self.cmd (r'\setlength{\dimen0}{%.03f\tablewidth}' % sum_width)

        parboxoptions =  { 'top'    : '[t]',
                           'middle' : '',
                           'bottom' : '[b]',
                           }[node.colspecs[0].get ('valign', 'middle')]

        rows = node.get ('morerows', 0) + 1
        if rows > 1:
            self.cmd (r'\setlength{\dimen1}{\ht\@arstrutbox * %d}' % rows)
            self.cmd (r'\addtolength{\dimen1}{\dp\@arstrutbox * %d}' % (rows - 1))
            if 'rows' in node.parent.parent.parent.parent['hrules']:
                self.cmd (r'\addtolength{\dimen1}{(\aboverulesep + \belowrulesep) * %d}' % (rows - 1))

            parboxoptions = { 'top'    : r'[t][\dimen1][t]',
                              'middle' : r'[c][\dimen1][c]',
                              'bottom' : r'[b][\dimen1][b]',
                              }[node.colspecs[0].get ('valign', 'middle')]

        self.cmd (r'\setbox0\vbox')
        self.push ()

        self.cmd (r'\hsize\dimen0')

        ## self.cmd (r'\fbox')
        ## self.push ()
        self.cmd (r'\parbox%s{\dimen0}' % parboxoptions)
        self.push ()

        self.cmd ({ 'left'   : '\\raggedright',
                    'right'  : '\\raggedleft',
                    'center' : '\\centering',
                    'justify': '' }[node.colspecs[0].get ('align', 'justify')])

        if isinstance (node.parent.parent, nodes.thead):
            self.cmd ('\\bfseries')

        self.cmd (r'\setlength{\parskip}{1em}\noindent')
        ## self.cmd (r'\fontspec[Numbers=Lining]{Linux Libertine O}')
        self.cmd ('\\@arstrut\n')

    def depart_entry (self, node):
        self.cmd (r'\@arstrut')

        self.pop () # parbox
        ## self.pop () # fbox
        self.pop () # setbox0

        cols = node.get ('morecols', 0)
        if cols:
            self.cmd (r'\setlength{\dimen0}{%.03f\tablewidth}' % node.colspecs[0]['relative_width'])
            self.cmd (r'\wd0\dimen0')

        rows = node.get ('morerows', 0) + 1
        if rows > 1:
            self.cmd (r'\ht0\ht\@arstrutbox\dp0 0pt')

        self.cmd (r'\box0')

        self.cmd (' &' * node.get ('morecols', 0))
        if 'last' not in node['classes']:  # not last cell in row
            self.cmd (' & ')


    # end tables

    # Structural Elements and Titles

    def visit_document_title (self, node):
        pass

    def depart_document_title (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        if 'with-subtitle' not in node['classes']:
            self.sp (2)

    def visit_document_subtitle (self, node):
        self.sp (1)

    def depart_document_subtitle (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        self.sp (2)

    def visit_section (self, node):
        self.section_level += 1

    def depart_section (self, node):
        self.section_level -= 1

    def visit_section_title (self, node):
        node.eff_level = min (self.section_level, 6) - 1 # 0-based
        beforeskip, afterskip, font = self.section_params [node.eff_level]
        section = node.parent

        self.output_sp ()
        # prefer a page break *before* hyperlink labels
        # avoids that the link goes to the previous page
        self.cmd ('\\penalty-300%\n')
        self.write_labels (section)

        self.cmd ('%s\n{\\noindent\\interlinepenalty \\@M%s%%\n' % (beforeskip, font))


    def depart_section_title (self, node):
        beforeskip, afterskip, fontsize = self.section_params [node.eff_level]
        self.cmd ('}\n\n\\unskip%s\\nobreak\n' % afterskip)
        self.noindent ()

    def visit_section_subtitle (self, node):
        self.sp (1)

    def depart_section_subtitle (self, node):
        self.cmd (r'\par\nobreak')
        self.src_sp ()
        self.sp (2)
        self.noindent ()

    def visit_rubric (self, node):
        self.sp ()

    def depart_rubric (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        self.sp ()

    def visit_topic (self, node):
        self.begin_float (node, 'topic')

    def depart_topic (self, node):
        self.end_float (node)

    def visit_topic_title (self, node):
        pass

    def depart_topic_title (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        self.sp ()

    def visit_sidebar (self, node):
        self.begin_float (node, 'sidebar')

    def depart_sidebar (self, node):
        self.end_float (node)

    def visit_sidebar_title (self, node):
        pass

    def depart_sidebar_title (self, node):
        self.cmd (r'\par')
        self.src_sp ()
        self.sp ()

    # Stuff

    def visit_page (self, node):
        self.output_src_sp ()
        self.src_sp ()
        if 'vspace' in node['classes']:
            self.sp (node['length'])
        elif 'clearpage' in node['classes']:
            self.cmd ('\\clearpage\n\n')
        elif 'cleardoublepage' in node['classes']:
            # output a completely blank page
            self.cmd ('\\clearpage{\\pagestyle{empty}\\cleardoublepage}\n\n')
        elif 'vfill' in node['classes']:
            self.cmd ('\\vspace*{\\fill}\n')
        else:
            for matter in ('frontmatter', 'mainmatter', 'backmatter'):
                if matter in node['classes']:
                    self.cmd ('%%\n\\%s\n%%\n\n' % matter)

        raise nodes.SkipNode # empty


    def visit_newline (self, node):
        self.cmd (' \\\\\n')

    def depart_newline (self, node):
        pass


    def visit_attribution (self, node):
        self.cmd (r'\nopagebreak')

    def depart_attribution (self, node):
        self.cmd (r'\par')


    def visit_transition (self, node):
        self.sp ()

    def depart_transition (self, node):
        self.src_sp ()


    def visit_problematic (self, node):
        pass

    def depart_problematic (self, node):
        pass

    def unimplemented_visit (self, node):
        raise NotImplementedError ('visiting unimplemented node type: %s'
                                  % node.__class__.__name__)
