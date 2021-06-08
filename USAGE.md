# Usage Notes

Ebookmaker has to reliably make EPUB and MOBI for over 60,000 different titles every month, so it includes a number of adaptations that may not be intuitive for HTML authors.

## Crawling

Ebookmaker starts with a document file path or URL, and then follows links and images to a depth determined by the `--max_depth` setting. It only follows links that are in the same directory or below; anything in the same directory linked by the starting page will be included in the ebook it tries to build. The `*.noimages` filetype builds (for example, `--make=epub.noimages`) exclude images. If you don't want the ebook to include a resource that your HTML links to, use the `rel='nofollow'` attribute of the `a` tag.

The crawl from the starting page determines the reading order for the ebook. If the starting page links to another html page, the content from that page will be placed after the starting page in the reading order. For this reason, it's simpler to put all the content on a single page. Multi-page HTML books should convert well if attention is paid to the reading order implied by the starting page.

## Floats and absolute positioning

Ebookmaker removes elements that float, because a large part of the PG backfile was produced before any ebook readers could handle floats. It also removes elements with absolute as it is not supported by EPUB2. HTML authors can prevent floating elements from being stripped by using a css selector that contains the `x-ebookmaker` class. Ebookmaker assumes that if the HTML designer uses the `x-ebookmaker` class, they've considered the impact of the float on the generated EPUB.

## Page numbers

Ebookmaker strips content from elements that it thinks are page numbers. HTML produced for PG often implements the original page numbers either with float or with absolute positioning. If these elements were left in, they would show up as numbers in the middle of the text.

To still keep links working, all page number contraptions are replaced with empty `a` tags with class `x-ebookmaker-pageno`.

The classes that make Ebookmaker think the element is a page number are: `pagenum pageno page pb folionum foliono`.

## Tables of Contents

Ebookmaker uses HTML heading elements to generate a table of contents. To play nicely with this process, HTML should not use heading elements for things that don't belong in the table of contents, and _should_ use heading elements for things that do!

## Hidden content

Content hidden by the `display:none` css directive can create havoc with ebook generation. For example, MOBI generation _will_ fail if the target of a link is hidden. Authors of HTML for Ebookmaker should refrain from using `display:none` and should check that all ebook formats convert as expected.

## Images and Covers

HTML authors can control the image that Ebookmaker uses for ebook files. If there is no suitable cover image, Ebookmaker will generate one. Images are scaled if they are "too big". It's a bit complicated, so there's [a separate page](docs/images.md) that tries to explain it all.


## Special classes

Ebookmaker recognizes a number of special classes that can be used to modify its HTML conversion. There are 4 "`x-ebookmaker`" classes:

 - Ebookmaker adds the class `x-ebookmaker` to the `body` element inside the EPUBs it builds. This can be then be used by css to make styles that are only active inside an ebook file. This class replaces a deprecated 'handheld' @media query.
 - The `x-ebookmaker-important` class on an image element tells ebookmaker not to remove the image, even in `*.noimages` builds.
 - The `x-ebookmaker-drop` class tells ebookmaker to remove an element and its descendents from ebook builds. Don't use this class to prevent a file from being crawled - use `rel='nofollow'` instead.
 - As described above, Ebookmaker adds the `x-ebookmaker-pageno` class to  elements whose content has been stripped because they use a class that indicates they represent page numbers.

