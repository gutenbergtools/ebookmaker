#
# ebookmaker distribution
#
#!/usr/bin/env python

from setuptools import setup

VERSION = '0.13.8'

if __name__ == "__main__":
 
    setup (
        name = 'ebookmaker',
        version = VERSION,

        packages = [
            'ebookmaker',
            'ebookmaker.parsers',
            'ebookmaker.writers',
            'ebookmaker.packagers',

            'ebookmaker.mydocutils',
            'ebookmaker.mydocutils.parsers',
            'ebookmaker.mydocutils.transforms',
            'ebookmaker.mydocutils.writers',

            'ebookmaker.mydocutils.gutenberg',
            'ebookmaker.mydocutils.gutenberg.parsers',
            'ebookmaker.mydocutils.gutenberg.transforms',
            'ebookmaker.mydocutils.gutenberg.writers',
        ],

        scripts = [
            'scripts/ebookmaker',
            'scripts/convert_unitame',
            'scripts/rhyme_compiler',
        ],

        install_requires = [
            'pillow>=8.3.2',
            'cssutils',
            'docutils>=0.18.1',
            'lxml',
            'roman',
            'requests',
            'six>=1.4.1',
            'libgutenberg[covers]>=0.10.22',
            'cchardet==2.2.0a2',
            'beautifulsoup4',
            'html5lib',
        ],
    
        package_data = {
            'ebookmaker.parsers': ['broken.png', 'txt2all.css'],
            'ebookmaker.writers': ['cover.jpg'],
            'ebookmaker.mydocutils.parsers': ['*.rst'],
            'ebookmaker.mydocutils.writers': ['*.css'],
            'ebookmaker.mydocutils.gutenberg.parsers': ['*.rst'],
        },

        data_files = [
            ('', ['CHANGES', 'README.md']),
        ],

        # metadata for upload to PyPI

        author = "Marcello Perathoner",
        maintainer = "Eric Hellman",
        maintainer_email = "eric@hellman.net",
        description = "The Project Gutenberg tool to generate EPUBs and other ebook formats.",
        long_description = open ('README.md', encoding='utf-8').read (),
        long_description_content_type = 'text/markdown',
        license = "GPL v3",
        keywords = "ebook epub kindle pdf rst reST reStructuredText project gutenberg format conversion",
        url = "https://github.com/gutenbergtools/ebookmaker/",

        classifiers = [
            "Topic :: Text Processing",
            "License :: OSI Approved :: GNU General Public License (GPL)",
            "Environment :: Console",
            "Operating System :: OS Independent",
            "Intended Audience :: Other Audience",
            "Programming Language :: Python",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
        ],

        platforms = 'OS-independent'
    )
