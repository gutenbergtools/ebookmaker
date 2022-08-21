# Ebookmaker


Ebookmaker is the tool used for format conversion at Project Gutenberg.
It builds HTML5, EPUB2, EPUB3 and Kindle files (including KF8) from HTML.
It builds builds thes formats and PDF files from reST sources.

If you are preparing HTML for use with Ebookmaker, the [Usage Notes](USAGE.md) may be of interest.


## Prerequisites

* Python3 >= 3.7

### Needed only for Kindle generation

* Calibre (https://calibre-ebook.com/) (needed to make  Kindle files)
    * may need to install Calibre's ebook-convert command line tool https://manual.calibre-ebook.com/generated/en/cli-index.html

### Needed only for validation

* EpubCheck (for EPUB vaidalition) To use EPUBCheck validation, first download and install EPUBCheck from https://www.w3.org/publishing/epubcheck/. If the command to invoke it is  `java -jar /Applications/epubcheck-4.2.6/epubcheck.jar`, then add this line to ~/.ebookmaker or /etc/ebookmaker.conf: `epub_validator: java -jar /Applications/epubcheck-4.2.6/epubcheck.jar` then turn on validation by adding `--validate` to Ebookmaker's command line invocation or by setting validate to true in ~/.ebookmaker
* the W3C "Nu" validator (for HTML5 validation) https://validator.github.io/validator/ add this line to ~/.ebookmaker or /etc/ebookmaker.conf: `html_validator: [something for your install]/vnu-runtime-image/bin/vnu` then turn on validation by adding `--validate` to Ebookmaker's command line invocation or by setting validate to true in ~/.ebookmaker
* on MacOS, you may need to create security exceptions. On my system, I had to do `sudo xattr -r -d com.apple.quarantine /Users/eric/vnu-runtime-image/lib`

### Needed only for cover generation

* Cairo https://www.cairographics.org/download/
* Noto Sans and Noto Sans CJK:
    * CentOS or RedHat: `yum install google-noto-sans-cjk-fonts; yum install google-noto-sans-fonts`
    * Ubuntu: `apt-get install fonts-noto-cjk fonts-noto`

### Needed only for conversion from RST

* Libertinus Serif and Libertinus Sans https://github.com/alerque/libertinus
    * For Linux, 
        * Download the latest release https://github.com/alerque/libertinus/releases/latest
        * unzip, put .otf files into ~/.fonts 
        * update font catalog `fc-cache -f -v`
* DejaVu Sans Mono https://dejavu-fonts.github.io/
* TexLive (to build PDF from TeX and rst)

Tested with Python 3.8

## Install

(master branch, editable install)
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


## new to pipenv?

Install pipenv  (might be `pip install --user pipenv`, depending on your default python)

`$ pip3 install --user pipenv`

The default install location is `${HOME}/.local/bin`, so add this to your login shell's ${PATH} if needed.

Change directories to where you want to have your ebookmaker environment. Then, to initialize a python 3 virtual environment, do

`$ pipenv --three`

Whenever you want to enter this environment, move to this directory and do:

`$ pipenv shell`
 
Install the gutenberg modules:

`$ pipenv install ebookmaker`

Check your install:

`$ ebookmaker --version`
`EbookMaker 0.12.0`

Since you're in the shell, you can navigate to a book's directory and convert it:

`$ ebookmaker -v -v --make=epub.images --ebook 10001 --title "The Luck of the Kid" --author "Ridgwell Cullum" luck-kid.html`

## Update

`$ cd ebookmaker` to wherever you ran `$ pipenv install ebookmaker`

then:

`$ pipenv update ebookmaker`

## Test

Install, as above.

`$ cd ebookmaker` to wherever you ran `$ pip install ebookmaker`

then:

`$ git checkout master`

`$ pipenv install -e .`

`$ python setup.py test`

Travis-CI will run tests on branches committed in the gutenbergtools org

## Notes running Ebookmaker on Windows Machine (adapted from @windymilla)

1. Install Python 3.7+ from python.org. Install Kindlegen. Add it to the path. 
2. Add system environment variable: Right-click "My Computer", then Properties, then Advanced, then Environment variables, then New. Call the variable PYTHON_HOME, and set it to the Python folder.
3. Edit the Path variable and add to the end of it `;%PYTHON_HOME%\;%PYTHON_HOME%\Scripts\`
4. Check by starting a new command window and typing `python`. It should run your version of Python. Quit python with `^Z` & Enter.
5. In command window, type `pip3 install --user pipenv`. Script may warn it has put scripts into a folder such as `C:\Users\myname\AppData\Roaming\Python\Python37\Scripts`, and to add this to the Path environment variable. Do this – don't forget the semicolon before the new folder name! (Possibly might work instead to just copy the newly installed files from where they were installed into your main python scripts folder, i.e. `%PYTHON_HOME%\Scripts` ?)
6. Close old command window and start a new (to get the new path)
7. Create a folder for ebookmaker, e.g. `C:\DP\ebookmaker`
8. In command window, go to the new folder
9. Type `pipenv install ebookmaker` – takes a while to install. It will also create a "virtual environment", with a new folder, something like `C:\Users\myname\.virtualenvs\ebookmaker-cgaQuYhi`
10. (Optional - only if you need ebookmaker to create a book cover for you because you are not providing one)
    Download GTK+ to get Cairo. Precompiled Win32 binaries are here: http://ftp.gnome.org/pub/gnome/binaries ... _win32.zip
    Unzip this to a folder, e.g. `C:\DP\gtk` and add `C:\DP\gtk\bin` to the Path environment variable.
    Exit command window and start a new one to get new path
    Go to the ebookmaker folder, `C:\DP\ebookmaker`
11. Type `pipenv run python ebookmaker --version` to check ebookmaker version. If this doesn't work (it should, but didn't work for us) try:
    - Look in `C:\Users\myname\.virtualenvs\` and find the name of your virtualenv - it should be something like `ebookmaker-cgaQuYhi`
    - Type `pipenv run python C:\Users\myname\.virtualenvs\<name of virtualenv>\Scripts\ebookmaker --version` to check ebookmaker version. 
12. (Should not happen now Cairo is optional) If there's error like like no "cairo" or "cairo-2" found, check if your libcairo and libcairo-2 path exist. If they do, edit dlopen in  _init_.py in cairocffi package. Return the path found by ctypes.util.find_library directly instead of calling ffi.dlopen(path).
13. If folder/file name contains space, pathnames muse be enclosed in `"`, like `--output-dir="C:\your foldername"`. If pathname is quoted, it MUST NOT end with trailing `\` or error will be raised. If running bat file from within Guiguts, this means you should use `$d.` rather than `$d` (i.e. a dot after $d so quoted pathname will end in `\."` rather than `\"`) when passing it as a value for the output-dir argument.
14. Example run_ebookmaker.bat file for use with Guiguts:
      cd C:\DP\ebookmaker
      pipenv run python C:\Users\myname\.virtualenvs\ebookmaker-cgaQuYhi\Scripts\ebookmaker -v --make=epub.images --make=kindle.images --output-dir=%1 --title=%2 %3
15. Corresponding "external program" setup within Guiguts:
      `c:\dp\ebookmaker\run_ebookmaker.bat $d. $f $d$f$e`
