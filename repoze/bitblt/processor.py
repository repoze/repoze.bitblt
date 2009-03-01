""" Middleware that transforms images."""

import os
import re
import hashlib
import webob

try:
    import PIL.Image as Image
except ImportError:
    import PIL # to get useful exception if missing
    import Image

from cStringIO import StringIO

from transform import rewrite_image_tags
from transform import verify_signature

re_bitblt = re.compile(r'bitblt-(?P<width>\d+|None)x(?P<height>\d+|None)-(?P<signature>[a-z0-9]+)/')

class ImageTransformationMiddleware(object):
    def __init__(self, app, global_conf=None, quality=80,
                 secret=None, filter='antialias',
                 limit_to_application_url=False,
                 try_xhtml=False):
        if secret is None:
            raise ValueError("Must configure ``secret``.")

        self.quality = quality
        self.app = app
        self.secret = secret
        self.filter = {
            'nearest': Image.NEAREST,
            'bilinear': Image.BILINEAR,
            'bicubic': Image.BICUBIC,
            'antialias': Image.ANTIALIAS,
        }.get(filter.lower(), 'antialias')
        self.limit_to_application_url = limit_to_application_url
        self.try_xhtml = try_xhtml

    def process(self, data, size):
        image = Image.open(data)
        if size != image.size:
            if size[0] is None:
                size = (image.size[0], size[1])
            elif size[1] is None:
                size = (size[0], image.size[1])
            image.thumbnail(size, self.filter)

        f = StringIO()
        image.save(f, image.format.upper(), quality=self.quality)
        return f.getvalue()

    def __call__(self, environ, start_response):
        request = webob.Request(environ)

        m = re_bitblt.search(request.path_info)
        if m is not None:
            width = m.group('width')
            height = m.group('height')
            signature = m.group('signature')
            verified = verify_signature(width, height, self.secret, signature)

            # remove bitblt part in path info
            request.path_info = re_bitblt.sub("", request.path_info)
        else:
            verified = width = height = None
            
        response = request.get_response(self.app)

        if response.content_type and response.content_type.startswith('text/html'):
            if not len(response.body):
                return response(environ, start_response)
            if self.limit_to_application_url:
                app_url = request.application_url
            else:
                app_url = None
            response.body = rewrite_image_tags(response.body, self.secret,
                                               app_url=app_url,
                                               try_xhtml=self.try_xhtml)
        
        if response.content_type and response.content_type.startswith('image/'):
            if verified and (width or height):
                try:
                    if width == 'None':
                        width = None
                    else:
                        width = int(width)
                    if height == 'None':
                        height = None
                    else:
                        height = int(height)
                    size = (width, height)
                except (ValueError, TypeError):
                    raise ValueError(
                        "Width and height parameters must be integers.")

                app_iter = response.app_iter
                if not hasattr(app_iter, 'read'):
                    app_iter = StringIO("".join(app_iter))

                body = self.process(app_iter, size)
                response.body = body
            
        return response(environ, start_response)

def make_bitblt_middleware(app, global_conf, **kwargs):
    return ImageTransformationMiddleware(app, global_conf, **kwargs)
