""" Middleware that transforms images."""

import os

import PIL # to get useful exception if missing
import Image

from StringIO import StringIO

class ImageTransformationMiddleware(object):
    def __init__(self, app, global_conf=None):
        self.app = app

    def process(self, data, size, mimetype):
        image = Image.open(data)
        if size != image.size:
            image.thumbnail(size)

        return image

    def __call__(self, environ, start_response):
        catch_response = []
        
        def replace_start_response(status, headers, exc_info=None):
            catch_response.extend([status, headers, exc_info])

        app_iter = self.app(environ, replace_start_response)

        status, headers, exc_info = catch_response
        for name, value in headers:
            if name == 'content-type':
                content_type = value
                break
        else:
            # response does not set content type
            start_response(*catch_response)
            return app_iter
            
        if content_type and content_type.startswith('image/'):
            mimetype = environ.get('mimetype')
            width = environ.get('width')
            height = environ.get('height')

            try:
                size = (int(width), int(height))
            except ValueError:
                raise ValueError("Width and height parameters must be integers.")

            if not hasattr(app_iter, 'read'):
                app_iter = StringIO("".join(app_iter))
                
            image = self.process(app_iter, size, mimetype)
            body = image.tostring()
            start_response('200 OK', [
                ('content-type', 'image/%s' % image.format.lower()),
                ('content-length', str(len(body))),
                exc_info])
            
            return (body,)

        start_response(*catch_response)
        return app_iter

def make_bitblt_middleware(app, global_conf):
    return ImageTransformationMiddleware(app, global_conf)
