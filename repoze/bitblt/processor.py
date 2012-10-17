""" Middleware that transforms images."""

from base64 import urlsafe_b64encode
import os.path
import re
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
                 try_xhtml=False, # BBB
                 cache=None):
        if secret is None:
            raise ValueError("Must configure ``secret``.")

        self.quality = int(quality)
        self.app = app
        self.secret = secret
        self.filter = {
            'nearest': Image.NEAREST,
            'bilinear': Image.BILINEAR,
            'bicubic': Image.BICUBIC,
            'antialias': Image.ANTIALIAS,
        }.get(filter.lower(), 'antialias')
        self.limit_to_application_url = limit_to_application_url
        self.cache = cache

    def process(self, data, size):
        image = Image.open(data)

        kw = {'quality': self.quality}
        transparency = image.info.get('transparency', None)
        if transparency is not None:
            kw['transparency'] = transparency

        # maintian icc_profile if we find it, requires PIL 1.1.7 or greater
        icc_profile = image.info.get('icc_profile', None)
        if icc_profile is not None:
            kw['icc_profile'] = icc_profile

        if size != image.size:
            if size[0] is None:
                size = (image.size[0], size[1])
            elif size[1] is None:
                size = (size[0], image.size[1])
            image.thumbnail(size, self.filter)

        f = StringIO()
        image.save(f, image.format.upper(), **kw)
        return f.getvalue()

    def __call__(self, environ, start_response):
        path_info = environ['PATH_INFO']
        m = re_bitblt.search(path_info)
        if m is not None:
            width = m.group('width')
            height = m.group('height')
            signature = m.group('signature')
            verified = verify_signature(width, height, self.secret, signature)

            # remove bitblt part in path info
            full_path_info = path_info
            environ['PATH_INFO'] = re_bitblt.sub("", path_info)
        else:
            verified = width = height = None

        request = webob.Request(environ)
        response = request.get_response(self.app)

        if response.content_type and \
               response.content_type.startswith('text/html') and \
               response.charset:
            if not len(response.body):
                return response(environ, start_response)
            if self.limit_to_application_url:
                app_url = request.application_url
            else:
                app_url = None

            response.unicode_body = rewrite_image_tags(
                response.unicode_body, self.secret,
                app_url=app_url)

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

                if self.cache:
                    cache_key = urlsafe_b64encode(full_path_info)
                    cache_file = os.path.join(self.cache, cache_key)
                    if os.path.exists(cache_file):
                        f = open(cache_file)
                        body = f.read()
                        f.close()
                    else:
                        body = self.process(app_iter, size)
                        f = open(cache_file, 'w+')
                        f.write(body)
                        f.close()
                else:
                    body = self.process(app_iter, size)
                response.body = body

        return response(environ, start_response)

def make_bitblt_middleware(app, global_conf, **kwargs):
    return ImageTransformationMiddleware(app, global_conf, **kwargs)
