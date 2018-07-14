#
# ebookmaker distribution
#

from distutils.core import setup

VERSION = '0.4.0a5'

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
        'Pillow',
        'chardet',
        'cherrypy',
        'cssutils',
        'docutils>=0.14',
        'libgutenberg>=0.1.6',
        'lxml',
        'roman',
        'requests',
        'six>=1.4.1',
        'setuptools',
    ],

    package_data = {
        'ebookmaker.parsers': ['broken.png'],
        'ebookmaker.writers': ['cover.jpg'],
        'ebookmaker.mydocutils.parsers': ['*.rst'],
        'ebookmaker.mydocutils.writers': ['*.css'],
        'ebookmaker.mydocutils.gutenberg.parsers': ['*.rst'],
    },

    data_files = [
        ('', ['CHANGES', 'README']),
    ],

    # metadata for upload to PyPI

    author = "Marcello Perathoner",
    author_email = "webmaster@gutenberg.org",
    description = "The Project Gutenberg tool to generate EPUBs and other ebook formats.",
    long_description = open ('README').read (),
    license = "GPL v3",
    keywords = "ebook epub kindle pdf rst reST reStructuredText project gutenberg format conversion",
    url = "http://pypi.python.org/pypi/ebookmaker/",

    classifiers = [
        "Topic :: Text Processing",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Intended Audience :: Other Audience",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.3",
    ],

    platforms = 'OS-independent'
)
