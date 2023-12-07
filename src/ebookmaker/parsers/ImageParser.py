#!/usr/bin/env python
#  -*- mode: python; indent-tabs-mode: nil; -*- coding: UTF8 -*-

"""

ImageParser.py

Copyright 2009 by Marcello Perathoner

Distributable under the GNU General Public License Version 3 or newer.

Parse an url of type image/*.

"""

import copy

import six
from PIL import Image, ImageFile


from pkg_resources import resource_stream # pylint: disable=E0611

from libgutenberg.Logger import debug, error
from libgutenberg.MediaTypes import mediatypes as mt
from ebookmaker.parsers import ParserBase
from ebookmaker.ParserFactory import ParserFactory
from . import ParserAttributes

# works around problems with bad checksums in a small number of png files
ImageFile.LOAD_TRUNCATED_IMAGES = True

mediatypes = (mt.jpeg, mt.png, mt.gif, mt.svg)



class Parser(ParserBase):
    """Parse an image.

    And maybe resize it for ePub packaging.

    """

    def __init__(self, attribs=None):
        ParserBase.__init__(self, attribs)
        self.image_data = None
        self.dimen = None


    def resize_image(self, max_size, max_dimen, output_format=None):
        """ Create a new parser with a resized image. """

        def scale_image(image, scale):
            was = ''
            if scale < 1.0:
                dimen = (int(image.size[0] * scale), int(image.size[1] * scale))
                was = "(was %d x %d scale=%.2f) " % (image.size[0], image.size[1], scale)
                image = image.resize(dimen, Image.LANCZOS)
            return was, image

        def get_image_data(image, format_, quality='keep'):
            """ Format is the output format, not necessarily the input format """
            buf = six.BytesIO()
            if image.format != 'JPEG' and quality == 'keep':
                quality = 90
            if format_ == 'png':
                image.save(buf, 'png', optimize=True)
            else:
                try:
                    image.save(buf, 'jpeg', quality=quality)
                except ValueError as e:
                    if quality == 'keep' and 'quantization' in str(e):
                        image.save(buf, 'jpeg', quality=90)
                    else:
                        raise e
            return buf.getvalue()
        
        # can't do anything with SVG files
        if self.attribs.url.endswith('.svg'):
            return self

        new_parser = Parser()

        try:
            unsized_image = Image.open(six.BytesIO(self.image_data))

            format_ = unsized_image.format.lower()
            if output_format:
                format_ = output_format
            if format_ == 'gif':
                format_ = 'png'
                self.attribs.url +=  '.png'
                self.attribs.orig_mediatype = self.attribs.mediatype
                self.attribs.mediatype = ParserAttributes.HeaderElement(mt.png)
            if format_ == 'jpeg' and unsized_image.mode.lower() not in ('rgb', 'l'):
                unsized_image = unsized_image.convert('RGB')

            if 'dpi' in unsized_image.info:
                del unsized_image.info['dpi']

            # maybe resize image

            # find scaling factor
            scale = 1.0
            scale = min(scale, max_dimen[0] / float(unsized_image.size[0]))
            scale = min(scale, max_dimen[1] / float(unsized_image.size[1]))

            was, image = scale_image(unsized_image, scale)
            data = get_image_data(image, format_)

            if format_ == 'png':
                # scale it till it fits into max_size
                while len(data) > max_size and scale > 0.01:
                    scale = scale * 0.8
                    was, image = scale_image(unsized_image, scale)
                    data = get_image_data(image, format_)
            else:
                # find best quality that fits into max_size
                if len(data) > max_size:
                    for quality in (90, 85, 80, 70, 60, 50, 40, 30, 20, 10):
                        data = get_image_data(image, format_, quality=quality)
                        if len(data) <= max_size:
                            break

                    was += 'q=%d' % quality
            comment = "Image: %d x %d size=%d %s" % (
                image.size[0], image.size[1], len(data), was
            )
            debug(comment)

            new_parser.image_data = data
            new_parser.dimen = tuple(image.size)

            new_parser.attribs = copy.copy(self.attribs)
            new_parser.attribs.comment = comment
            new_parser.fp = self.fp

        except IOError as what:
            error("Could not resize image: %s; message %s", self.attribs.url, what)
            new_parser.attribs = copy.copy(self.attribs)
            fp = resource_stream('ebookmaker.parsers', 'broken.png')
            new_parser.image_data = fp.read()
            fp.close()

        return new_parser


    def get_image_dimen(self):
        if self.dimen is None:
            if self.image_data:
                try:
                    image = Image.open(six.BytesIO(self.image_data))
                    self.dimen = image.size
                except IOError as what:
                    error("Could not resize image (probably broken): %s", self.attribs.url)
                    self.dimen = (0, 0)  # broken image
            else:
                self.dimen = (0, 0)  # broken image
        return self.dimen


    def pre_parse(self):
        if self.image_data is None:
            self.image_data = self.bytes_content()

    def parse(self):
        pass

    def serialize(self):
        """ Serialize the image. """
        return self.image_data
