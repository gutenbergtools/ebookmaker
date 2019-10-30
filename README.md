# EbookMaker


EbookMaker is the tool used for format conversion at Project Gutenberg.
It builds EPUB2 and Kindle files from HTML.
Also it builds HTML4, EPUB2, Kindle, and PDF files from reST sources.


## Prerequisites

* Python2 >= 2.7 or Python3 >= 3.6
* HTMLTidy (http://binaries.html-tidy.org/),
* Kindlegen (https://www.amazon.com/gp/feature.html/?docId=1000765211),
* TexLive (to build from TeX), and
* groff (not sure when this is needed).

For cover generation

* Cairo https://www.cairographics.org/download/
* Noto Sans and Noto Sans CJK 
    * `yum install google-noto-sans-cjk-fonts`
    * `yum install google-noto-sans-fonts`

Tested with Python 3.6

## Install

(dev branch, editable install)
`pipenv install ebookmaker`

Use the ebookmaker.conf file to pass a path to your kindlegen, tex, and groff programs 
if they're not in your PATH. Edit the ebookmaker.conf and copy it to /etc/ebookmaker.conf to 
reset the paths.
Copy ebookmaker.conf to ~/.ebookmaker to override settings in /etc/ebookmaker.conf or to set default 
command line options.

## Sample invocation

(From the directory where you ran `pipenv install`)

`pipenv shell`
`ebookmaker -v -v --make=epub.images --output-dir=/Documents/pg /Documents/library/58669/58669-h/58669-h.htm`

or

`pipenv run ebookmaker -v -v --make=epub.images --output-dir=/Documents/pg /Documents/library/58669/58669-h/58669-h.htm`



## Test

Use `python setup.py test`

Travis-CI will run tests on branches committed in the gutenbergtools org

## new to pipenv?

Install pipenv  (might be `pip install --user pipenv`, depending on your default python)

`$ pip3 install --user pipenv`

Change directories to where you want to have your ebookmaker environment. Then, to initialize a python 3 virtual environment, do

`$ pipenv --three`

Whenever you want to enter this environment, move to this directory and do:

`$ pipenv shell`
 
Install the gutenberg modules:

`$ pipenv install ebookmaker`

Check your install:

`$ ebookmaker --version`
`EbookMaker 0.6.0`

Since you're in the shell, you can navigate to a book's directory and convert it:

`$ ebookmaker -v -v --make=epub.images --ebook 10001 --title "The Luck of the Kid" --author "Ridgwell Cullum" luck-kid.html`

