""" Middleware that transforms images."""

import os
import webob

import PIL # to get useful exception if missing
import Image

from StringIO import StringIO

class ImageTransformationMiddleware(object):
    def __init__(self, app, global_conf=None, quality=80):
        self.quality = quality
        self.app = app

    def process(self, data, size, mimetype, quality):
        image = Image.open(data)
        if size != image.size:
            image.thumbnail(size)

        f = StringIO()
        
        image.save(f, mimetype.split('/')[-1].upper(), quality=quality)
        f.seek(0)

        return f

    def __call__(self, environ, start_response):
        request = webob.Request(environ)
        response = request.get_response(self.app)
        
        if response.content_type and response.content_type.startswith('image/'):
            mimetype = request.params.get('mimetype', response.content_type)
            quality = request.params.get('quality', self.quality)
            width = request.params.get('width')
            height = request.params.get('height')

            # we currently require both parameters to be present
            if width is not None and height is not None:
                try:
                    size = (int(width), int(height))
                except (ValueError, TypeError):
                    raise ValueError("Width and height parameters must be integers.")

                app_iter = response.app_iter
                if not hasattr(app_iter, 'read'):
                    app_iter = StringIO("".join(app_iter))

                f = self.process(app_iter, size, mimetype, quality)
                response.content_type = mimetype
                response.app_iter = f
                response.content_length = f.len
            
        return response(environ, start_response)

def make_bitblt_middleware(app, global_conf):
    return ImageTransformationMiddleware(app, global_conf)
