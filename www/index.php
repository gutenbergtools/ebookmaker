<?php

###==========================================================###
### DEPRECATION NOTE: This file is no longer used in the     ###
### production environment and is no longer maintained here. ###
### The new web front end is now located in a new repo at:   ###
### https://github.com/gutenbergtools/ebookmaker-web/        ###
###==========================================================###

#
# Run ebookmaker on a project.  Allow the user to specify a few options
#

# Written by Greg Newby for Project Gutenberg and Distributed Proofreaders
# September 2011
# This PHP program is granted to the public domain

# Change history:
# 2011-09-25: First version for internal review
# 2011-10-06: First public release
# 2012-05-06: documentation updates, default eBook #
# 2014-10-10: Marcello: switch to ebookmaker/python3
# 2017-03-04: gbn: Update links to ebookmaker source
# 2019-11-10: gbn: moved to dante.pglaf.org with new ebookmaker & pipenv

# TODO: add escapes etc. to title,author,ebook,encoding

include ("pglaf.phh"); // Marcello's functions with additions/customizations
ini_set('default_charset', 'UTF-8');

$myname ="index.php";
$mybaseurl = "https://ebookmaker2.pglaf.org";
$prog = "export LC_ALL=C.UTF-8; export LANG=C.UTF-8; cd /opt/ebookmaker; /var/www/.local/bin/pipenv run ebo
okmaker";
$pbase = "ebookmaker"; # do not show users the whole prog line.
$tmpdir = "/htdocs/ebookmaker/cache"; # this overrides pglaf.phh

$myhead="Project Gutenberg Online Ebookmaker";

?>
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN"
   "http://www.w3.org/TR/1998/REC-html40-19980424/loose.dtd">

<html lang="en">
<head>
   <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=utf-8">
   <title>
<?php echo $myhead ?>
   </title>
</head>

<body>

  <h1>
<?php echo $myhead ?>
  </h1>

<?php

  print "<h2>Quick Start</h2>\n";

  print "<p>Please upload a <strong>single file</strong>.  ";
  print "If your submission has more than ";
  print "one file, upload a .zip of all the needed files.  ";
  print "Any images should be in a subdirectory (i.e., folder) ";
  print "named \"images\", and cannot be omitted if they are referenced by the source.  ";

print "<blockquote><form enctype=\"multipart/form-data\" method=\"POST\" accept-charset=\"UTF-8\" action=\"
index.php\">\n";
  print "<input type=\"file\" name=\"upfile1\"> Your file (any of: zip/rst/txt/htm/html)\n";

  print "<br><input type=\"text\" size=\"50\" name=\"mytitle\" value=\"UnknownTitle\"> EBook title";
  print "<br><input type=\"text\" size=\"50\" name=\"myauthor\" value=\"UnknownAuthor\"> EBook author";
  print "<br><input type=\"text\" size=\"20\" name=\"myencoding\" value=\"\"> File encoding (us-ascii, iso-
8859-1, utf8, etc.; mandatory for plain text files)";
  print "<br><input type=\"text\" size=\"10\" name=\"myebook\" value=\"10001\"> EBook number (must be an in
teger)";

  print "<br><input type=\"submit\" value=\"Make it!\" name=\"make\">\n";
  print "</form></blockquote>\n\n";

  print "<p>Ebookmaker will try to identify author, title, encoding and ";
  print "eBook number from your file, IF it includes the standard Project ";
  print "Gutenberg metadata as found in the published collection.  Otherwise, ";
  print "you can provide values.  Missing values are not usually a problem (but you must provide an encodin
g if you upload a plain text file).  Please only use Latin1 characters for author/title names.  </p>";

  print "<p>Note: After your file has transferred, processing can take as long a few minutes for large file
s. Send an email if the Web server seems to time out (so that run-time limits can be adjusted).</p>";

if (! isset($_REQUEST['make'])) {

  print "<h2>Usage Details</h2>";

  print "<p>Here you can run ebookmaker on a file you upload.  The ebookmaker ";
  print "tools are what www.gutenberg.org uses to automatically create ";
  print "additional file formats for readers to enjoy.  The process is that ";
  print "a master format file (RST, HTML or plain text) is used to generate ";
  print "EPUB and other mobile-friendly formats, as well as HTML or text ";
  print "if they were not provided originally.</p>\n";
  print "\n<p>It is <font color=\"red\">strongly recommended</font> that ";
  print "this tool be utilized before new eBooks are submitted at <a href=";
  print "\"https://upload.pglaf.org/\">upload.pglaf.org</a>, in order to ";
  print "allow opportunity to improve the automated output by making changes ";
  print "to the submitted files.  In particular, the automated tools might ";
  print "do poorly when submissions utilize HTML for page layout, rather than ";
  print "only the content's structure.</p>\n";

  print "<p>Ebookmaker will be run against a single file ";
  print "type from among those you upload, whichever is found first: ";
  print "<tt>.rst .htm .html .txt</tt>, so probably you should just include ";
  print "one at a time.  Note, however, that the full processing chain ";
  print "is implemented for rst (ReStructured Text) only.  For HTML, you will ";
  print "get most output formats (including EPUB).  For plain text, you will ";
  print "only get a few output formats (again, including EPUB), and ";
  print "probably some errors from ebookmaker.</p>";


  print "<p>You can test how well mobile output looks (EPUB and MOBI/Kindle) ";
  print "without needing a mobile device.  Instead, try one of the many free ";
  print "browser plug-ins. </p>\n";

  print "<p>The file you upload should contain a nearly-finished ";
  print "eBook project, such as would be submitted via ";
  print "<a href=\"https://upload.pglaf.org/\">upload.pglaf.org</a>, although ";
  print "the directory/file structure is simpler. ";
  print "For HTML, it's best to run the <a href=\"https://validator.w3.org\">HTML validator</a> and other c
hecks ";
  print "found in the upload.pglaf.org 'preview' function." ;
  print "The output you will get is intended to help determine whether resulting ";
  print "automatically-generated files (epub and other formats) ";
  print "have any problems or shortcomings that could be addressed ";
  print "prior to submission.</p>\n";
?>

<p>
Information about ebookmaker best practices for Project Gutenberg is available at 
<a href="https://www.pgdp.net/wiki/The_Proofreader%27s_Guide_to_EPUB">https://www.pgdp.net/wiki/The_Proofre
ader%27s_Guide_to_EPUB</a>
</p>

<p>
You can <a href="https://github.com/gutenbergtools/ebookmaker/blob/dev/README.md">download the most recent 
ebookmaker source</a> if you would rather run it on your own system.

</p>

<p>
  Additional RST resources:
</p>

<ul>
  <li><a href="https://docutils.sourceforge.net/docs/ref/rst/directives.html">docutils.sourceforge.net/docs
/ref/rst/directives.html</a>: reStructuredText Directives</li>
  <li><a href="https://www.gutenberg.org/ebooks/181">PG RST manual</a>
</ul>

<?php
  print "<p>Currently, supported operations are the following.  Note that file TYPE is based on file NAME, 
so files should end in .rst, .htm or .txt (or .zip, including those three file types):  \n<ul>\n";
  print " <li>Input filetype <strong>RST</strong>: all supported output types (text, HTML, epub/mobi and va
riations)</li>";
  print " <li>Input filetype <strong>HTML</strong>: all supported output types, but with some problems or i
rregularities.  For best results, provide HTML that includes the standard Project Gutenberg boilerplate inf
ormation (header and footer), and do NOT provide author, title, etc. in the form below (just leave them bla
nk)</li>";
  print " <li>Input filetype <strong>text</strong> (any encoding): very limited, will only output other pla
in text variations, no HTML or epub/mobi</li>";
  print "</ul>";

  require('plaintail.inc');
  exit;
} 

// Did we get input?
if (strlen($_FILES['upfile1']['name']) == 0) {
  print "<p><font color=\"red\">Error: Ebookmaker was requested to process files, but no file ";
  print "was received.  Please try again, or send email for help.";
  print "</font></p>\n\n";

  require('plaintail.inc');
  exit;
}

// Rename uploaded file, create new output directory:
$upfile1_name = fix_filename($_FILES['upfile1']['name']);
$tmpsubdir = date ('YmdHis');
$dirname = $tmpdir . "/" . $tmpsubdir;
$newname = $dirname . "/" . $upfile1_name;
mkdir ($dirname); // where our output will go
rename( $_FILES['upfile1']['tmp_name'], $newname);// remove from php spool area
chmod ("$newname", 0644);

// We will redirect some messages to this file, for the user to read:
$outfile = $tmpdir . "/" . $tmpsubdir . "/output.txt";

// Unzip the input file, if needed:
$whichmatch = preg_match("/\.zip$/", $newname);
if ($whichmatch != 0) {
  $retval = system ("/bin/echo unzipping $newname > $outfile");
  $retval = shell_exec ("/usr/bin/unzip -l $newname > $outfile > 2>&1");
  $retval = shell_exec ("USER=www-data;LOGNAME=www-data;HOME=$newname;/usr/bin/unzip -o -U $newname -d $dir
name");
}

// Options to ebookmaker:
$gopts=""; $basename="";
$gotdir=0; # only open one subdirectory

// Figure out which input file to feed ebookmaker:
if ($dh = opendir($dirname)) {

DIRECTORY_GOTO:  // Yes, a goto statement

  while (($file = readdir($dh)) !== false) {

    if ($file == '.' || $file == '..') { continue; };

    // Got a subdir?  ASSuME we should follow it if we checked all the
    // top-level files already
    if (is_dir ("$dirname/$file")) {
      if ($gotdir !== 0) {
	print "<p><font color=\"red\">More than one directory was included in the .zip, please only include
 one top-level subdirectory or folder.</font></p>\n";
	exit;
      }
      //      closedir($dh);
      //      $dirname = $dirname . "/" . $file;
      continue;
    }
    
    // Skip our output; filesystem directories
    if (preg_match("/output.txt/", $file)) { continue; }
    if (preg_match("/\.zip$/", $file)) { continue; }
    // Marcello commented it out because it breaks filenames with "0" in it
    // if (preg_match("/$gotdir/", $file)) { continue; }

    // rst:
    $whichmatch = preg_match("/\.rst$/", $file);
    if ($whichmatch != 0) {
      $gotdir = 0;
      $basename = basename($file);
      $gopts = $gopts . "--make=all ";
      $retval = system ("/bin/echo Input file: $basename >> $outfile");
      break;
    }

    // htm:
    $whichmatch = preg_match("/\.htm$/", $file);
    if ($whichmatch != 0) {
      $gotdir = 0;
      $basename = basename($file);
      $gopts = $gopts . "--make=epub --make=kindle --make=txt --make=html ";
      $retval = system ("/bin/echo Input file: $basename >> $outfile");
      break;
    }

    // html:
    $whichmatch = preg_match("/\.html$/", $file);
    if ($whichmatch != 0) {
      $gotdir = 0;
      $basename = basename($file);
      $gopts = $gopts . "--make=epub --make=kindle --make=txt --make=html ";
      $retval = system ("/bin/echo Input file: $basename >> $outfile");
      break;
    }

    // txt:
    $whichmatch = preg_match("/\.txt$/", $file);
    if ($whichmatch != 0) {
      $gotdir = 0;
      $basename = basename($file);
      $gopts = $gopts . "--make=epub --make=kindle --make=txt --make=html ";
      $retval = system ("/bin/echo Input file: $basename >> $outfile");
      break;
    }

  }
   closedir($dh);
} else {
  print "<p><font color=\"red\">Sorry, an error happened opening our temporary directory location $dirname,
 $?.  Please report this if it persists.</p>\n";
  exit;
}

// Loop back if there is a subdirectory:
if ($gotdir !== 0) {
  $dirname = $dirname . "/" . $gotdir;
  //  $gotdir = $file;
  if (! ($dh = opendir($dirname))) {
    print "<p><font color=\"red\">Sorry, an error happened opening our temporary directory location $dirnam
e, $?.  Please report this if it persists.</p>\n";
    exit;
  } 
  $gotdir = 0;
  goto DIRECTORY_GOTO;
}

// Make sure we found a file to operate on:
if ("$basename" == "") {
  print "<p>Sorry, but we could not identify a file ending in rst, txt, ";
  print "htm, or html.  Follow this link to see what was identified.  You ";
  print "might need to give a more Unix-friendly filename (no spaces, lower ";
  print "case, no special characters). Please try again, or send email if ";
  print "you need help or things seem amiss.</p>";
  print "<p><ul>\n  <li><a href=\"$mybaseurl/cache/$tmpsubdir\">$mybaseurl/cache/$tmpsubdir</a></li>\n</ul>
\n</p>";
  require('plaintail.inc');
  exit;
}

$basename = $dirname . "/" . $basename;

# print_r ($_REQUEST);
# TODO: add escapes etc. to title,author,ebook,encoding
$gopts = $gopts . "--max-depth=3 ";
$gopts = $gopts . "--output-dir=$tmpdir" . "/" . $tmpsubdir . " ";

if (strlen($_REQUEST['mytitle'])) {
  $gopts = $gopts . "--title=\"" . $_REQUEST['mytitle'] . "\" ";
}
if (strlen($_REQUEST['myauthor'])) {
  $gopts = $gopts . "--author=\"" . $_REQUEST['myauthor'] . "\" ";
}
if (strlen($_REQUEST['myencoding'])) {
  $gopts = $gopts . "--input-mediatype=\"text/plain;charset=" . $_REQUEST['myencoding'] . "\" ";
}
if (strlen($_REQUEST['myebook'])) {
  $gopts = $gopts . "--ebook=\"" . $_REQUEST['myebook'] . "\" ";
} else {
  $gopts = $gopts . "--ebook=10001 "; # Required
}


// Run ebookmaker
print "<p>Starting ebookmaker on " . $basename;
print " with this command: <br><tt>$pbase $gopts file://$basename\n</tt>\n";
$retval = system ("$prog --version >> $outfile"); 
$retval = system ("$prog $gopts file://$basename >> $outfile 2>&1");
print "</p>";

if ($retval == 0) {
  print "<p><font color=\"green\">Success</font>: ebookmaker ended with a successful exit code.  This does 
not mean all desired output was successfully generated.  The output.txt file provides detail on the process
ing that occurred, and any error or informational messages.  \n";
  print "Please follow this link to view the input file you uploaded ";
  print "(possibly it was renamed) and any output files.  This link ";
  print "will stay available for a day or two:";
  print "<ul>\n  <li><a href=\"$mybaseurl/cache/$tmpsubdir\">$mybaseurl/cache/$tmpsubdir</a></li>\n</ul>\n<
/p>";
} else {
  print "<p>Sorry, ebookmaker ended with an error code.  Send email if this seems to be an actual problem, 
not just a temporary glitch or a problem with your file.</p>\n";
}

print "<p><a href=\"$myname\">Submit another</a>\n";

require('plaintail.inc');
exit;

?>
