#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: iso-8859-1 -*-

"""

ImageParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Parse an url of type image/*.

"""

import copy

import six
from PIL import Image

from pkg_resources import resource_string # pylint: disable=E0611

from libgutenberg.Logger import debug, error
from libgutenberg.MediaTypes import mediatypes as mt
from ebookmaker import parsers
from ebookmaker.parsers import ParserBase

mediatypes = (mt.jpeg, mt.png, mt.gif)

class Parser (ParserBase):
    """Parse an image.

    And maybe resize it for ePub packaging.

    """

    def __init__ (self, attribs = None):
        ParserBase.__init__ (self, attribs)
        self.image_data = None
        self.dimen = None


    def resize_image (self, max_size, max_dimen, output_format = None):
        """ Create a new parser with a resized image. """

        new_parser = Parser ()

        try:
            image = Image.open (six.BytesIO (self.image_data))

            format_ = image.format
            if output_format:
                format_ = output_format
            if format_ == 'gif':
                format_ = 'png'
            if format_ == 'jpeg' and image.mode.lower () != 'rgb':
                image = image.convert ('RGB')

            if 'dpi' in image.info:
                del image.info['dpi']

            # maybe resize image

            # find scaling factor
            scale = 1.0
            scale = min (scale, max_dimen[0] / float (image.size[0]))
            scale = min (scale, max_dimen[1] / float (image.size[1]))

            was = ''
            if scale < 1.0:
                dimen = (int (image.size[0] * scale), int (image.size[1] * scale))
                was = "(was %d x %d scale=%.2f) " % (image.size[0], image.size[1], scale)
                image = image.resize (dimen, Image.ANTIALIAS)

            # find best quality that fits into max_size
            data = self.image_data
            if (scale < 1.0) or (len (self.image_data) > max_size):
                for quality in (90, 85, 80, 70, 60, 50, 40, 30, 20, 10):
                    buf = six.BytesIO ()
                    image.save (buf, format_, quality = quality)
                    data = buf.getvalue ()
                    if len (data) <= max_size:
                        was += 'q=%d' % quality
                        break

            comment = "Image: %d x %d size=%d %s" % (
                        image.size[0], image.size[1], len (data), was)
            debug (comment)

            new_parser.image_data = data
            new_parser.dimen = tuple (image.size)

            new_parser.attribs = copy.copy (self.attribs)
            new_parser.attribs.comment = comment
            new_parser.fp = self.fp

        except IOError as what:
            error ("Could not resize image: %s" % what)
            new_parser.broken_image ()

        return new_parser


    def get_image_dimen (self):
        if self.dimen is None:
            image = Image.open (six.BytesIO (self.image_data))
            self.dimen = image.size
        return self.dimen


    def broken_image (self):
        """ Insert broken image placeholder. """

        self.image_data = resource_string ('ebookmaker.parsers', 'broken.png')
        self.attribs.mediatype = parsers.ParserAttributes.HeaderElement ('image/png')
        self.attribs.rel.add ('important') # keep even in non-image build


    def pre_parse (self):
        if self.image_data is None:
            self.image_data = self.bytes_content ()
        if self.image_data is None:
            self.broken_image ()


    def parse (self):
        """ Parse the image. """
        pass


    def serialize (self):
        """ Serialize the image. """
        return self.image_data
