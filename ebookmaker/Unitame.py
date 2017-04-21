#  -*- mode: python; indent-tabs-mode: nil; -*- coding: utf-8 -*-

"""
Unitame.py

Copyright 2010 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Module to implement the totally superfluous PG plain text conversion
into long extinct encodings.

We have to unitame-translate before feeding to nroff because nroff
does some irreversible (and wrong) translations of its own, like ä ->
a. Also, some unitame-translations change the number of characters,
thus throwing already-justified text off.

We cannot do the translations before feeding the source to docutils
because if we change the length of titles, we get the warning: Title
underline too short.

Translation does some dangerous things, like converting quotes to
apostrophes, which are command escapes in nroff. We have to escape
apostrophes in the source text but not apostroph-commands inserted by
the converter.

We also have to translate some important non-ascii characters, like
nbsp and shy, into command sequences before they reach unitame because
unitame would convert them into the semantically different space and
hyhpen.

All this makes translation inside the docutils converter the best
choice. Implemented as a docutils translator that visits all text
nodes.

Smart quote translation should also go into a docutils
translator. Likewise a translator for text-transform: upper.

"""

from __future__ import unicode_literals

import codecs
import unicodedata as ud

# UnitameData is generated from unitame.dat
from ebookmaker.UnitameData import unicode_to_iso_8859_1, iso_8859_1_to_ascii

# tweak dicts for translate ()
u2i = dict ( [ (ord (o), s) for o, s in unicode_to_iso_8859_1.items () ] )
i2a = dict ( [ (ord (o), s) for o, s in iso_8859_1_to_ascii.items () ] )

u2i.update ( {
    0x2000:     ' ',    # en quad
    0x2001:     '  ',   # em quad
    0x2002:     ' ',    # en space
    0x2003:     '  ',   # em space
    0x2004:     ' ',    # 3/em space
    0x2005:     '',     # 4/em
    0x2006:     '',     # 6/em
    0x2007:     ' ',    # figure space
    0x2008:     '',     # punctuation space
    0x2009:     '',     # thin space
    0x200a:     '',     # hair space
    0x200b:     '',     # zero space
    0x200c:     '',     # zwnj
    0x200d:     '',     # zwj
    0x2010:     '-',    # hyphen
    0x2011:     '-',    # non-breaking hyphen
    0x2012:     '-',    # figure-dash
    0x2013:     '-',    # en dash
    0x2014:     '--',   # em dash
    0x2015:     '-',    # horizontal bar
    0x2026:     '...',  # horizontal ellipsis
    ord ('™'): '(tm)',
    ord ('‹'): '<',
    ord ('›'): '>',
    ord ('†'): '+',
    ord ('‡'): '++',
    ord ('⁑'): '**',
    ord ('⁂'): '***',
    ord ('•'): '-',
    ord ('′'): '´',
    ord ('″'): '´´',
    ord ('‴'): '´´´',
    ord ('⁗'): '´´´´',
    ord ('⁓'): '~',
    ord ('‰'): '%o',
    ord ('‱'): '%oo',
    ord ('⚹'): '*',    # U+26b9 sextile
    ord ('⁰'): '^0',
    ord ('⁴'): '^4',
    ord ('⁵'): '^5',
    ord ('⁶'): '^6',
    ord ('⁷'): '^7',
    ord ('⁸'): '^8',
    ord ('⁹'): '^9',
    } )

# somehow cram these into ascii, so the ppers stop whining about not
# having nbsp in ascii, then fix it later by replacing them with nroff
# commands.

i2a.update ( {
    ord ('¹'): '^1',
    ord ('²'): '^2',
    ord ('³'): '^3',
    0x00a0:     '\u0011',       # nbsp => DC1
    0x00ad:     '\u0012',       # shy  => DC2
} )

unhandled_chars = []

def strip_accents (text):
    """ Strip accents from string.

    If the accented character doesn't fit into the encoding,
    remove the accent and try again.

    """
    return ud.normalize (
        'NFKC',
        ''.join ([c for c in ud.normalize ('NFKD', text) if ud.category (c) != 'Mn'])
    )


def unitame (exc):
    """
    Encoding error handler.

    The encoder handles all compatible characters itself.  It calls
    this function whenever it encounters a character it cannot encode.
    This function searches the unitame database for a replacement.


    """

    l = []
    for cc in exc.object[exc.start:exc.end]:
        c = cc
        if exc.encoding == 'latin-1': # python name for iso-8859-1
            c = c.translate (u2i)
            c = strip_accents (c)
            if c and ord (max (c)) < 256:
                l.append (c)
                c = None
        elif exc.encoding == 'ascii': # python name for us-ascii
            # "1¼" -> "1 1/4"
            if cc in '¼½¾':
                if exc.start > 0 and exc.object[exc.start - 1] in '0123456789':
                    l.append (' ')
            c = c.translate (u2i)
            c = c.translate (i2a)
            c = strip_accents (c)
            if c and ord (max (c)) < 128:
                l.append (c)
                c = None

        if c:
            l.append ('{~%s U+%04x~}' % (ud.name (cc), ord (cc)))
            unhandled_chars.extend (l)

    return (''.join (l), exc.end)


codecs.register_error ('unitame', unitame)
