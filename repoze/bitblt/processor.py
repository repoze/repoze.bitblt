""" Middleware that transforms images."""

import os
import re
import hashlib
import webob

import PIL # to get useful exception if missing
import Image

from cStringIO import StringIO

from transform import rewrite_image_tags
from transform import verify_signature

re_bitblt = re.compile(r'bitblt-(?P<width>\d+)x(?P<height>\d+)-(?P<signature>[a-z0-9]+)/')

class ImageTransformationMiddleware(object):
    def __init__(self, app, global_conf=None, quality=80, key=None):
        self.quality = quality
        self.app = app

        if key is None:
            key = hashlib.sha1().hexdigest()
            
        self.key = key
        
    def process(self, data, size):
        image = Image.open(data)
        if size != image.size:
            image.thumbnail(size)

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
            verified = verify_signature(width, height, self.key, signature)

            # remove bitblt part in path info
            request.path_info = re_bitblt.sub("", request.path_info)
        else:
            width = height = None
            
        response = request.get_response(self.app)

        if response.content_type and response.content_type.startswith('text/html'):
            response.body = rewrite_image_tags(response.body, self.key)
        
        if response.content_type and response.content_type.startswith('image/'):
            if verified and width and height:
                try:
                    size = (int(width), int(height))
                except (ValueError, TypeError):
                    raise ValueError(
                        "Width and height parameters must be integers.")

                app_iter = response.app_iter
                if not hasattr(app_iter, 'read'):
                    app_iter = StringIO("".join(app_iter))

                body = self.process(app_iter, size)
                response.body = body
            
        return response(environ, start_response)

def make_bitblt_middleware(app, global_conf):
    return ImageTransformationMiddleware(app, global_conf)
