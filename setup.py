#
# ebookmaker distribution
#

from setuptools import setup

VERSION = '0.11.16'

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
        'chardet',
        'cherrypy',
        'cssutils',
        'docutils>=0.14',
        'lxml',
        'roman',
        'requests',
        'six>=1.4.1',
        'libgutenberg[covers]>=0.8.11',
    ],
    
    package_data = {
        'ebookmaker.parsers': ['broken.png', 'tidy.conf', 'txt2all.css'],
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
        "Programming Language :: Python :: 3.6",
    ],

    platforms = 'OS-independent'
)
