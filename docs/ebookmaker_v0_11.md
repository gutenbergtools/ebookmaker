# New features in Ebookmaker v0.11

In addition to some small tweaks in its generated EPUBs, Ebookmaker version 0.11 also emits regularized HTML files for all types of input, including HTML source files. These "derived" files are now the preferred HTML presentation on the PG website.

The source HTML files are not modified, and are available (at the URLs they've always been at) via the "More files..." link on the website. Errata should be addressed in the source files, not the derived files, as whitespace and link structure are changed by ebookmaker in ways that may preclude reprocessing. Files are re-derived for the entire catalog monthly.

A major impetus for this change is to improve compatibility with browser plugins, mobile apps, proxy servers, accessibility tools and PG's own file processors. Much of our back file uses old versions of HTML that are poorly supported in modern browsers and other tools, and while there is ongoing work to update the back file, we are thousands of books away from being able to present uniformly coded HTML. This change is also a first step towards being able to use HTML5 for both source files and for presentation.

Here are the differences between HTML source files and the HTML files derived from them:

1. all HTML files are cleaned by HTML Tidy. Tidy does the following:
    i. HTML Tidy emits well-formed UTF8-encoded XHTML-compatible files. This will allow the PG web server to add the encoding to MIME headers, improving browser compatibility and accessibility.
    ii. LF is used as the newline character for all files (unix standard)
    iii. HTML entities such as `&rsquo;` `&Aacute;` etc. are converted to unicode characters. Together with webserver configuration changes, this will improve web browser compatibility.
    iv. Tidy corrects badly formed HTML, improving browser compatibility and standards conformance.
    v. A doctype declaration for XHTML+RDFa 1.1 is used for all files to allow better validation with included RDFa metadata.
    vi. Tags are now uniformly lower case
    vii. Some legacy presentational tags (`<i>`, `<b>`, `<center>` when enclosed within appropriate inline tags, and ) are replaced with CSS `<style>` tags and structural markup as appropriate.
    viii. Empty paragraphs are discarded.
    ix. Any text directly in the `<body>` element is wrapped in a `<p>` element.
    x. Self-closing tags are now closed with an end tag. So... `<a id="x" />` is changed to `<a id="x" ></a>`. This is needed because Chrome and Safari no longer support self-closing tags. The oddest looking change is `<br>` -> `<br></br>`. We need that because we're still using XHTML to support legacy content and EPUB2. We expect a lot of remediation work will be needed before we can switch to HTML5 and EPUB3.
    xi. Inline style attributes are moved to a generated inline stylesheet for better rendering performance. The same mechanism is used to separate CSS from text in our EPUB files.
    
2. Metadata is added to the `<head>` element. We include RDFa, Dublin Core, and schema.org metadata for better SEO and Facebook/Twitter unfurls. Changes in the metadata are now reflected in the HTML presentation.

3. Because the derived HTML is moved to a new directory, linked files also needed to be moved. Because the derived file has a different name, back-links needed to be changed.

There is one minor change to the EPUB generation process. `data-*` attributes are now removed because they were preventing EPUB2 validation.


Some versions of ebookmaker since our last production release did not run without access to the live PG database. Don't use them. 

This version on ebookmaker has not been tested on Windows, as I don't currently have access to a Windows box for development. If you run ebookmaker on Window, please let me know how it goes, and if there are problems, please comment here or create an issue on the Gihub repo: https://github.com/gutenbergtools/ebookmaker/issues

In the next major version of Ebookmaker, the boilerplate headers and footers will be inserted/replaced as part of the presentation HTML derivation process.