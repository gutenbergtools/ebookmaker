From Tapio:

> After 27 years' co-operation with PG at all levels and over 3 500 submitted Finnish e-books, I don't want to leave any unfinished issues behind me. One nagging problem has been ebookmaker txt > html > epub conversion producing low-quality files or crap (poetry mostly rewraps into prose!). Al knows more about this.
> Attached you'll find my latest and last tested fixes, they affect one file only, so no side effects are expected. As I rarely do any programming with AI nowadays, I have no GitHub account. Please take care that your people will hand this Pull Request and commit to them to handle. I also hope you'll very soon apply the fix to your ebm 0.14.4 online version, which is critical for text conversion users. 


# Fix line-break handling for hand-formatted blocks in plain text sources

Five related fixes to `GutenbergTextParser`, all concerning blocks whose line
breaks were put there deliberately by the transcriber. Each is independent and
can be reverted on its own.

---

## 1. Verse in languages that do not capitalize every line

### Problem

Whether a paragraph is verse or prose is decided by a fuzzy score. One of the
strongest inputs is how many lines begin with a capital letter:

```python
c = count(self.metrics.titles)
self.scores.verse *= 1.2 ** (min(c - len(self.lines), 50) / 2.0)
```

Since `c <= len(self.lines)`, the exponent is never positive: the term is a
pure penalty, and it grows with the length of the paragraph.

| lines in stanza | multiplier when no line is capitalized |
|---|---|
| 4 | 0.69 |
| 8 | 0.48 |
| 12 | 0.33 |
| 20 | 0.16 |

The threshold is `scores.verse > 1.0`, so a stanza whose lines are not
capitalized loses — and the longer the stanza, the more certainly it loses. It
is then rendered as a reflowed block quote and the browser rewraps the verse
at whatever width the reader's window happens to be.

Capitalizing every verse line is an English convention. Finnish, Swedish,
German and many other languages do not follow it, so poems embedded in novels
in those languages are reflowed essentially every time. Single-line verse is
affected too: it never reaches `white-space: pre`, so its indentation is
dropped and the line moves flush left.

Transcribers have been working around this by hand. For a six-line stanza,
adding one extra space to lines 2 and 6 makes the block pass a different test:

```python
if some(not_(self.flush_left_lines()[1:])):
    self.scores.verse *= 20.0  # strong indicator
```

`some()` requires 25%, the first line is excluded, so 2 of the remaining 5
lines (40%) is enough while 1 of 5 (20%) is not. Needing to know that in order
to typeset a poem is not reasonable.

### Fix

If *every* line of a paragraph starts with at least `VERSE_INDENT` (default 4)
spaces, the transcriber indented and broke those lines deliberately.
`Par.analyze()` sets `par.force_verse`, unless `p_smells()` matches, and the
style pass honours the flag.

`EBOOKMAKER_VERSE_INDENT=0` restores the previous behaviour exactly.

### Why a flag and not a score

Boosting `scores.verse` instead leaks into neighbouring paragraphs through the
`follows verse` / `precedes verse` rules in `analyze_multi()`. In testing, a
three-space prose block quote next to a poem was promoted to `white-space: pre`
because its score was nudged from 0.833 to 1.0000000000000002. A flag
consulted only in the style pass leaves all existing scores untouched.

---

## 2. Numbered lists behave differently from roman-numbered ones

`_istitle` looks at the first word character of a line and asks `isupper()`.
`I.` is a letter and passes; `1.` is a digit and fails. A table of contents
numbered with roman numerals keeps its line breaks, while the same table
numbered `1. 2. ... 10.` is reflowed into one paragraph.

A new metric `numbers` records which lines start with a digit. When *most*
lines are numbered, they count as titles:

```python
if most(self.numbers):
    self.titles = or_(self.titles, self.numbers)
```

The `most()` guard matters. Counting digits per line unconditionally breaks
prose whose continuation line happens to start with a number — this occurs in
the existing test book 69030:

```
Promptly at nine that morning, as usual, Karl called up Apartment
60.
```

At 75%, one numbered line out of two does not qualify, while five out of five
in a table of contents does.

---

## 3. Block indentation as hard spaces

`preformat()` converts leading spaces to `&#xa0;`, so a preformatted block
starts with hard spaces that cannot adapt to the reader's screen. A title page
line centered in the source with 22 spaces becomes 22 hard spaces.

The block's common minimum indentation is now stripped and expressed as
`margin-left` instead. Indentation *relative* to that minimum is preserved,
which is what actually carries meaning inside a stanza.

Note in passing that `centered_lines()` and `flush_right_lines()` exist and
`scores.center` / `scores.right` are read in the style pass, but nothing ever
raises those scores, so `text-align` is effectively never emitted. Hard spaces
are currently the only positioning mechanism these blocks have.

---

## 4. Hand-broken blocks that are not indented

A publisher's imprint is reflowed into a single line:

```
Helsingissä                 →    Helsingissä Kustannusosakeyhtiö Otava 1912
Kustannusosakeyhtiö Otava
1912
```

The block is not indented, and only two of its three lines start with a
capital, which falls below the 75% that `most()` requires. The same happens to
casts of characters, addresses and signatures.

### Fix

A signal that does not depend on indentation at all: reflowed prose always
fills its lines nearly to the margin, so a block whose *longest* line does not
come close was typed one line at a time.

```python
lengths = sorted(len(line) for par in self.pars for line in par.lines)
fill_width = lengths[int(len(lengths) * 0.9)]
...
elif max(self.metrics.lengths) < self.fill_width * SHORT_BLOCK_RATIO:
    self.force_verse = True
```

The fill width is measured from the book itself rather than hard-coded, so the
rule works for transcriptions wrapped at 60, 70 or 80 columns. A high
percentile rather than the maximum, so one stray long line does not set the
standard for the whole book.

The rule does not apply to single-line paragraphs or to PG boilerplate.

---

## 5. Blocks start at a uniform level

Two adjustments, both about where a preformatted block begins.

**The margin is the same for every block** (`VERSE_MARGIN`, 5%). It used to be
derived from the source indentation, so a poem whose stanzas were indented by
4 and 6 spaces got 5% and 8% and drifted apart; a title page indented 23 spaces
got 31% and was pushed a third of the way across the screen.

**Extra indentation on the first line is removed.** A block never starts
indented relative to its own body — the blank line above it is what separates
it from the previous paragraph. Indentation on later lines is meaningful and
is kept:

```
      JONAS |                    JONAS |
    KLARA | aviopari.     →      KLARA | aviopari.
    MARIA, palvelija.            MARIA, palvelija.
```

---

## 6. First-line indent on hand-broken blocks

### Problem

The stylesheet gives every body-level paragraph a first-line indent
(`body > p { text-indent: 1em }`) and suppresses it only after a heading
(`h2 + p { text-indent: 0 }`). That is right for prose, but a hand-broken
block is not prose: its first line is a verse line, a publisher's town, or a
table-of-contents entry, and the transcription does not indent it.

The result was visible in every text with verse or front matter: the *first*
stanza of a poem started flush left because it follows the poem's heading,
while every stanza after it started one em in. The same stray indent appeared
on title pages and tables of contents.

```
KUKKIVA MAA.                    KUKKIVA MAA.

Maa kuohuu syreenien...         Maa kuohuu syreenien...
                          →
  Mita siita, etta kuolema        Mita siita, etta kuolema
```

### Fix

Any paragraph shipped as a hand-broken block (`force_verse`, or
`scores.quote > THRESHOLD`) gets an explicit `text-indent: 0`.

A single-line paragraph is ambiguous: in a novel it is a one-line prose
paragraph and must keep its indent. It is treated as front matter — and loses
the indent — only when neither neighbour is flowed prose, which is the case
for a byline, an imprint, a section title or a numbered subtitle sitting
between headings and blocks.

`Par.next` is now initialized in `__init__`; it was only ever assigned for
paragraphs that have a successor.

---

## Test plan

Verified with constructed Finnish samples and with the existing test book:

* Stanzas indented by 4+ spaces with no capitalized lines keep one `<br />`
  per line. Verified for 4-, 6- and 8-line stanzas and for a single-line
  stanza (previously flush left).
* A prose block quote indented by 3 spaces is still reflowed — the threshold
  is exactly 4.
* Stanzas that *are* capitalized behave as before.
* A table of contents numbered `1. 2. 3. 10. 11.` keeps its line breaks,
  matching the existing behaviour for `I. II. III. X. XI.`.
* Two-line prose ending in a line that starts with a number is still reflowed.
* A three-line publisher's imprint with no indentation keeps its line breaks.
* A stanza whose first line is indented deeper than its body has that first
  line aligned with the body; a deeper line further down keeps its indent.
* `tests/files/69030/69030-0.txt` differs from the pre-patch output in exactly
  two paragraphs out of 162, both on the title page, where hard spaces became
  a margin.
* Every hand-broken block in a Finnish verse collection (Katri Vala,
  *Kaukainen puutarha*) now carries `text-indent: 0`; the stanzas of a poem
  start at the same level, and so do the lines of the title page and the
  table of contents.
* Ordinary prose paragraphs in the constructed samples are unchanged: they
  keep the stylesheet's first-line indent.
* `tests/test_html.py` passes. `tests/test_txt.py` and `tests/test_job.py`
  fail identically before and after (missing dependencies in the test
  environment).

## Compatibility note

Texts that indent prose block quotes by 4 or more spaces will now have those
quotes preformatted as well. Transcribers who want such a quote reflowed can
indent it by 2–3 spaces, or lower `VERSE_INDENT` for that build.
