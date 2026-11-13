"""Spoken heading labels affect EPUB3 navigation, not its visible caption/NCX."""
import copy
import pickle
import unittest

from lxml import etree

from ebookmaker import parsers, HTMLChunker
from ebookmaker.writers import Epub3Writer, EpubWriter

NS = {'h': 'http://www.w3.org/1999/xhtml', 'n': 'http://www.daisy.org/z3986/2005/ncx/'}


class TestTocLabels(unittest.TestCase):
    def toc(self, body):
        document = etree.fromstring((
            '<html xmlns="http://www.w3.org/1999/xhtml"><head><title>Book</title>'
            '</head><body>' + body + '</body></html>').encode('utf-8'))
        parser = parsers.HTMLParserBase()
        parser.attribs.url = 'file:///book.xhtml'
        return parser.make_toc(document)

    def links(self, toc):
        nav = Epub3Writer.Toc(None)._make_navmap(toc)
        return nav.xpath('.//h:a', namespaces=NS)

    def test_label_does_not_replace_visible_text(self):
        toc = self.toc('<h2 id="ch" aria-label="Chapter twelve">Ⅻ</h2>')
        link, = self.links(toc)
        self.assertEqual(link.get('aria-label'), 'Chapter twelve')
        self.assertEqual(link.text, 'Ⅻ')
        self.assertEqual(link.get('href'), 'file:///book.xhtml#ch')
        self.assertEqual(len(toc[0]), 3)
        self.assertIsInstance(toc[0][1], str)

    def test_nested_markup_and_escaped_label(self):
        toc = self.toc('<h2 aria-label="One &amp; two &quot;chapters&quot;">'
                       '<span>Ⅰ</span> <em>&amp; Ⅱ</em></h2>')
        link, = self.links(toc)
        self.assertEqual(link.get('aria-label'), 'One & two "chapters"')
        self.assertEqual(link.text, 'Ⅰ & Ⅱ')
        self.assertEqual(etree.fromstring(etree.tostring(link)).get('aria-label'),
                         'One & two "chapters"')

    def test_unlabelled_heading_remains_plain_text(self):
        toc = self.toc('<h2>Plain <em>heading</em></h2>')
        link, = self.links(toc)
        self.assertNotIn('aria-label', link.attrib)
        self.assertEqual(link.text, 'Plain heading')
        self.assertIs(type(toc[0][1]), str)

    def test_title_override_preserves_its_visible_caption(self):
        link, = self.links(self.toc('<h2 title="Short caption" aria-label="Spoken caption">'
                                   'Long visible <em>heading</em></h2>'))
        self.assertEqual((link.text, link.get('aria-label')), ('Short caption', 'Spoken caption'))

    def test_empty_label_is_preserved(self):
        link, = self.links(self.toc('<h2 aria-label="">Visible</h2>'))
        self.assertEqual(link.get('aria-label'), '')
        self.assertEqual(link.text, 'Visible')

    def test_standalone_whitespace_label_is_preserved(self):
        link, = self.links(self.toc('<h2 aria-label="   ">Visible</h2>'))
        self.assertEqual(link.get('aria-label'), '   ')
        self.assertEqual(link.text, 'Visible')

    def test_div_target_keeps_the_heading_label(self):
        toc = self.toc('<div id="section" aria-label="Container">\n'
                       '<h2 aria-label="Chapter one">Ⅰ</h2><p>Body</p></div>')
        link, = self.links(toc)
        self.assertEqual(link.get('href'), 'file:///book.xhtml#section')
        self.assertEqual(link.get('aria-label'), 'Chapter one')

    def test_ancestor_label_is_not_a_heading_label(self):
        link, = self.links(self.toc('<div aria-label="Container">\n<h2>Plain</h2></div>'))
        self.assertNotIn('aria-label', link.attrib)

    def test_combined_headings_keep_visible_and_spoken_sequences(self):
        for headings, visible, spoken in [
            ('<h2 aria-label="Chapter one">Ⅰ</h2><h2>Subtitle</h2>',
             'Ⅰ Subtitle', 'Chapter one Subtitle'),
            ('<h2>Chapter</h2><h2 aria-label="One">Ⅰ</h2>', 'Chapter Ⅰ', 'Chapter One'),
            ('<h2 aria-label="One">Ⅰ</h2><h2 aria-label="Two">Ⅱ</h2>', 'Ⅰ Ⅱ', 'One Two'),
        ]:
            with self.subTest(headings=headings):
                link, = self.links(self.toc(headings))
                self.assertEqual((link.text, link.get('aria-label')), (visible, spoken))

    def test_suppressed_headings_stay_suppressed(self):
        self.assertEqual(self.toc('<h2 title="" aria-label="Hidden">Heading</h2>'), [])
        self.assertEqual(self.toc('<h2 aria-label="Author">by Someone</h2>'), [])

    def test_combined_blank_segments_fall_back_to_visible_captions(self):
        for blank in ('', '   '):
            for headings, visible, spoken in [
                (f'<h2 aria-label="{blank}">Introduction</h2><h2>Background</h2>',
                 'Introduction Background', 'Introduction Background'),
                (f'<h2>Introduction</h2><h2 aria-label="{blank}">Background</h2>',
                 'Introduction Background', 'Introduction Background'),
                (f'<h2 aria-label="Part one">Ⅰ</h2><h2 aria-label="{blank}">Overview</h2>',
                 'Ⅰ Overview', 'Part one Overview'),
                (f'<h2 aria-label="Part one">Ⅰ</h2><h2>Overview</h2>'
                 f'<h2 aria-label="{blank}">Background</h2>',
                 'Ⅰ Overview Background', 'Part one Overview Background'),
                (f'<h2 aria-label="{blank}">Introduction</h2><h2>Background</h2>'
                 '<h2 aria-label="Part one">Ⅰ</h2>',
                 'Introduction Background Ⅰ', 'Introduction Background Part one'),
                (f'<h2 aria-label="{blank}">Introduction</h2>'
                 f'<h2 aria-label="{blank}">Background</h2>'
                 f'<h2 aria-label="{blank}">Overview</h2>',
                 'Introduction Background Overview', 'Introduction Background Overview'),
            ]:
                with self.subTest(blank=blank, headings=headings):
                    link, = self.links(self.toc(headings))
                    self.assertEqual((link.text, link.get('aria-label')), (visible, spoken))

    def test_page_list_does_not_copy_heading_labels(self):
        toc = self.toc('<h2 aria-label="Chapter">Ⅰ</h2>'
                       '<span class="pageno" aria-label="Page seven">7</span>')
        nav = Epub3Writer.Toc(None)
        link, = nav._make_pagelist(toc).xpath('.//h:a', namespaces=NS)
        self.assertEqual(link.text, '7')
        self.assertNotIn('aria-label', link.attrib)
        self.assertEqual(len(self.links(toc)), 1)

    def test_labels_survive_chunk_and_filename_rewrites(self):
        toc = self.toc('<h2 id="chapter" aria-label="One">Ⅰ</h2>')
        chunker = object.__new__(HTMLChunker.HTMLChunker)
        chunker.idmap = {'file:///book.xhtml#chapter': 'file:///book-1.xhtml#chapter'}
        chunker.rewrite_internal_links_toc(toc)
        nav = Epub3Writer.Toc(None)
        nav.toc = toc
        nav.rewrite_links(lambda url: url.replace('file:///', ''))
        link, = self.links(nav.toc)
        self.assertEqual((link.get('href'), link.get('aria-label')), ('book-1.xhtml#chapter', 'One'))

    def test_legacy_ncx_preserves_the_visible_caption(self):
        toc = self.toc('<h2 aria-label="Chapter one">Ⅰ <em>Title</em></h2>')
        ncx = EpubWriter.TocNCX(None)
        ncx.toc = copy.deepcopy(toc)
        ncx.normalize_toc()
        ncx.seen_urls = {toc[0][0]: '1'}
        text, = ncx._make_navmap(ncx.toc).xpath('.//n:navLabel/n:text', namespaces=NS)
        self.assertEqual(text.text, 'Ⅰ Title')
        self.assertFalse(text.getparent().getparent().xpath('.//*[@aria-label]'))

    def test_labelled_text_remains_copyable_and_serializable_as_text(self):
        text = self.toc('<h2 aria-label="Chapter one">Ⅰ</h2>')[0][1]
        for copied in (copy.deepcopy(text), pickle.loads(pickle.dumps(text))):
            self.assertEqual(copied, 'Ⅰ')
            self.assertEqual(getattr(copied, 'aria_label', None), 'Chapter one')

    def test_manual_three_field_entries_still_work(self):
        link, = self.links([['book.xhtml#one', 'One', 1]])
        self.assertEqual(link.text, 'One')
        self.assertNotIn('aria-label', link.attrib)


if __name__ == '__main__':
    unittest.main()
