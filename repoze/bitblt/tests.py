import unittest
import base64
import webob
import urllib
import transform
from StringIO import StringIO

try:
    # webob >= 1.0
    from webob.headers import ResponseHeaders
except ImportError:
    # webob < 1.0
    from webob.headerdict import HeaderDict as ResponseHeaders

try:
    import PIL.Image as Image
except ImportError:
    import Image

class TestProfileMiddleware(unittest.TestCase):
    def _makeOne(self, *arg, **kw):
        from repoze.bitblt.processor import ImageTransformationMiddleware
        return ImageTransformationMiddleware(secret='secret', *arg, **kw)

    def test_rewrite_html_ns(self):
        body = '''\
        <html xmlns="http://www.w3.org/1999/xhtml"
              xmlns:esi="http://www.edge-delivery.org/esi/1.0">
          <body>
            <img src="foo.png" width="640" height="480" />
            <esi:include src="somehwere" />
          </body>
        </html>'''
        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app, try_xhtml=True)
        result = middleware(request.environ, start_response)
        width = "640"
        height = "480"
        signature = transform.compute_signature(width, height, middleware.secret)
        directive = "bitblt-%sx%s-%s" % (width, height, signature)
        body = "".join(result)
        self.failUnless("%s/foo.png" % directive in body)
        self.failUnless('<esi:include src="somehwere"' in body)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(body)))]])

    def test_proper_xhtml_handling(self):
        body = '''\
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
          <body>
            <img src="foo.png" />
            <br/>
            <span>&nbsp;</span>
          </body>
        </html>'''
        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app, try_xhtml=True)
        result = middleware(request.environ, start_response)
        body = "".join(result)
        self.failUnless('<!DOCTYPE' in body)
        self.failUnless('<img src="foo.png" />' in body)
        self.failIf('</img>' in body)
        self.failUnless('<br/>' in body)
        self.failIf('<br>' in body)
        self.failIf('</br>' in body)
        self.failUnless('<span>&nbsp;</span>' in body)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(body)))]])

    def test_rewrite_html(self):
        body = '''<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN" "http://www.w3.org/TR/REC-html40/loose.dtd">
        <html>
          <body>
            <img src="foo.png" width="640" height="480" />
            <img src="/fob.png" width="640" height="480" />
            <img src="path/foc.png" width="640" height="480" />
            <img src="/path/fod.png" width="640" height="480" />
            <img src="http://host/bar.png" width="640" height="480" />
            <img src="http://host/path/hat.png" width="640" height="480" />
            <img src="blubb.png" />
            <img src="blah.png" width="640" />

            Images with % sizes should not be rewritten, only the browser knows
            how big the images should be. They are based on available space, not
            original image dimensions.
            See http://www.w3.org/TR/html4/types.html#h-6.6.
                <img src="percentage.png" width="100%" />
                <img src="percentage.png" width="50%" height="50%"/>
                <img src="percentage.png" height="20%" />

            Image tags with px are used in the real world, we should rewrite them:
                <img src="pixels.png" width="640px" height="480px"/>
                <img src="pixels.png" width="640px" />
          </body>
        </html>'''

        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app)
        result = middleware(request.environ, start_response)
        width = "640"
        height = "480"
        signature = transform.compute_signature(width, height, middleware.secret)
        directive = "bitblt-%sx%s-%s" % (width, height, signature)
        body = "".join(result)
        self.failUnless(body.startswith('<!DOCTYPE'))
        self.failUnless('src="%s/foo.png"' % directive in body)
        self.failUnless('src="/%s/fob.png"' % directive in body)
        self.failUnless('src="path/%s/foc.png"' % directive in body)
        self.failUnless('src="/path/%s/fod.png"' % directive in body)
        self.failUnless('src="http://host/%s/bar.png"' % directive in body)
        self.failUnless('src="http://host/path/%s/hat.png"' % directive in body)
        self.failUnless('src="blubb.png" />' in body)
        self.failUnless('src="percentage.png" width="100%"' in body)
        self.failUnless('src="percentage.png" width="50%" height="50%"' in body)
        self.failUnless('src="percentage.png" height="20%"' in body)
        self.failUnless('src="%s/pixels.png" width="640px" height="480px"' % directive in body)
        height = None
        signature = transform.compute_signature(width, height, middleware.secret)
        directive = "bitblt-%sx%s-%s" % (width, height, signature)
        self.failUnless("%s/blah.png" % directive in body)
        self.failUnless('src="%s/pixels.png" width="640px"' % directive in body)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(body)))]])

    def test_rewrite_html_limited_to_application_url(self):
        body = '''\
        <html>
          <body>
            <img src="foo.png" width="640" height="480" />
            <img src="http://host/bar.png" width="640" height="480" />
            <img src="http://host/path/hat.png" width="640" height="480" />
            <img src="blubb.png" />
            <img src="blah.png" width="640" />
          </body>
        </html>'''

        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app, limit_to_application_url=True)
        result = middleware(request.environ, start_response)
        width = "640"
        height = "480"
        signature = transform.compute_signature(width, height, middleware.secret)
        directive = "bitblt-%sx%s-%s" % (width, height, signature)
        body = "".join(result)
        self.failUnless('DOCTYPE' not in body, body)
        self.failUnless("%s/foo.png" % directive in body)
        self.failUnless("http://host/bar.png" in body)
        self.failUnless("http://host/path/hat.png" in body)
        self.failUnless('<img src="blubb.png" />' in body)
        height = None
        signature = transform.compute_signature(width, height, middleware.secret)
        directive = "bitblt-%sx%s-%s" % (width, height, signature)
        self.failUnless("%s/blah.png" % directive in body)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(body)))]])

    def test_scaling(self):
        middleware = self._makeOne(None)
        f = middleware.process(StringIO(jpeg_image_data), (32, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.size, (32, 32))
        f = middleware.process(StringIO(jpeg_image_data), (32, None))
        image = Image.open(StringIO(f))
        self.assertEqual(image.size, (32, 32))
        f = middleware.process(StringIO(jpeg_image_data), (None, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.size, (32, 32))

    def test_keep_gif_transparency(self):
        middleware = self._makeOne(None)
        # resize non-transparent gif
        f = middleware.process(StringIO(gif_image_data), (32, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.size, (32, 32))
        self.assertEqual(image.info.get('transparency'), None)
        # resize transparent gif
        f = middleware.process(StringIO(transparent_gif_image_data), (32, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.size, (32, 32))
        self.assertEqual(image.info.get('transparency'), 156)

    def test_keep_icc_profile(self):
        middleware = self._makeOne(None)
        orig = Image.open(StringIO(jpeg_image_data))
        orig_icc = orig.info.get('icc_profile')
        self.assertNotEqual(orig_icc, None, 'Keeping ICC profiles requires PIL 1.1.7 or greater')
        orig_size = Image.open(StringIO(jpeg_image_data)).size
        # icc profiles are maintained in original images
        f = middleware.process(StringIO(jpeg_image_data), orig_size)
        image = Image.open(StringIO(f))
        self.assertEqual(image.info.get('icc_profile'), orig_icc)
        # and resized ones
        f = middleware.process(StringIO(jpeg_image_data), (32, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.info.get('icc_profile'), orig_icc)
        # images without icc_profiles don't magically get them
        no_icc = StringIO()
        orig.save(no_icc, 'JPEG')
        no_icc.seek(0)
        f = middleware.process(no_icc, (32, 32))
        image = Image.open(StringIO(f))
        self.assertEqual(image.info.get('icc_profile'), None)

    def test_non_utf8_url_non_image(self):
        body = "Hi"
        request = webob.Request.blank("not-utf-8-\xfe")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/plain')
            response(environ, start_response)
            return [response.body]

        def start_response(*args):
            pass

        middleware = self._makeOne(mock_app)
        result = middleware(request.environ, start_response)
        self.assertEqual(result, [body])

    def test_non_utf8_url_image(self):
        response = []

        def mock_start_response(status, headers, exc_info=None):
            response.extend((status, headers))

        def mock_app(environ, start_response):
            self.failIf('bitblt' in environ.get('PATH_INFO'))
            response = webob.Response(jpeg_image_data, content_type='image/jpeg')
            response(environ, start_response)
            return (response.body,)

        middleware = self._makeOne(mock_app)

        width = height = "32"
        signature = transform.compute_signature(width, height, middleware.secret)

        request = webob.Request.blank('not-utf-8-\xfe/bitblt-%sx%s-%s/foo.jpg' % (
            width, height, signature))

        result = middleware(request.environ, mock_start_response)
        status, headers = response

        self.assertEqual(status, '200 OK')
        self.assertNotEqual(''.join(result), jpeg_image_data)

    def test_call_content_type_not_image(self):
        body = "<html><body>Hello, world!</body></html>"
        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app)
        result = middleware(request.environ, start_response)
        self.assertEqual(result, [body])
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'), ('Content-Length', '39')]])

    def test_call_content_type_is_image(self):
        response = []

        def mock_start_response(status, headers, exc_info=None):
            response.extend((status, headers))

        def mock_app(environ, start_response):
            self.failIf('bitblt' in environ.get('PATH_INFO'))
            response = webob.Response(jpeg_image_data, content_type='image/jpeg')
            response(environ, start_response)
            return (response.body,)

        middleware = self._makeOne(mock_app)

        width = height = "32"
        signature = transform.compute_signature(width, height, middleware.secret)

        request = webob.Request.blank('bitblt-%sx%s-%s/foo.jpg' % (
            width, height, signature))

        result = middleware(request.environ, mock_start_response)
        response_length = len("".join(result))
        status, headers = response

        headers = ResponseHeaders(headers)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers['content-type'], 'image/jpeg')
        self.assertEqual(headers['content-length'], str(response_length))

    def test_call_is_untransformed_image(self):
        response = []

        def mock_start_response(status, headers, exc_info=None):
            response.extend((status, headers))

        def mock_app(environ, start_response):
            self.failIf('bitblt' in environ.get('PATH_INFO'))
            response = webob.Response(jpeg_image_data, content_type='image/jpeg')
            response(environ, start_response)
            return (response.body,)

        middleware = self._makeOne(mock_app)
        request = webob.Request.blank('foo.jpg')

        result = middleware(request.environ, mock_start_response)
        status, headers = response
        headers = ResponseHeaders(headers)
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers['content-type'], 'image/jpeg')
        self.assertEqual(headers['content-length'], str(len(jpeg_image_data)))

    def test_empty_body(self):
        # empty bodies can occure in redirects
        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response('', content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app)
        result = middleware(request.environ, start_response)

    def test_encoding(self):
        body = '''\
        <html>
          <body>
            <img src="foo.png" width="640" height="480" />
            <p>UTF-8 encoded chinese: \xe6\xb1\x89\xe8\xaf\xad\xe6\xbc\xa2\xe8\xaa\x9e</p>
          </body>
        </html>'''

        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html', charset='UTF-8')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app)
        result = middleware(request.environ, start_response)
        body = "".join(result)
        self.failUnless("UTF-8 encoded chinese: \xe6\xb1\x89\xe8\xaf\xad\xe6\xbc\xa2\xe8\xaa\x9e" in body, body)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(body)))]])

    def test_quality(self):
        ## Mimic Paste Deploy's behaviour, which pass parameters as
        ## strings
        middleware = self._makeOne(None, quality='10')
        f = middleware.process(StringIO(jpeg_image_data), (32, 32))

    def test_javascript_cdata(self):
        """Test that CDATA escaped javascript arrives unmolested when processing as XHTML."""
        body = '''\
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
          <head>
            <script type="text/javascript">
              <![CDATA[
              x = '<&>'
              ]]>
            </script>
          </head>
          <body>
            <img src="foo.png" width="640" height="480" />
          </body>
        </html>'''

        request = webob.Request.blank("")

        def mock_app(environ, start_response):
            response = webob.Response(body, content_type='text/html')
            response(environ, start_response)
            return (response.body,)

        response = []
        def start_response(*args):
            response.extend(args)

        middleware = self._makeOne(mock_app, try_xhtml=True)
        result = middleware(request.environ, start_response)
        result = "".join(result)
        self.failUnless("<![CDATA[" in result, result)
        self.failUnless("x = '<&>'" in result, result)
        self.assertEqual(response, [
            '200 OK', [('Content-Type', 'text/html; charset=UTF-8'),
                       ('Content-Length', str(len(result)))]])


    def test_cache(self):
        response = []
        def mock_start_response(status, headers, exc_info=None):
            response.extend((status, headers))

        def mock_app(environ, start_response):
            response = webob.Response(
                jpeg_image_data, content_type='image/jpeg')
            response(environ, start_response)
            return (response.body, )

        def make_request(secret):
            width = height = 100
            signature = transform.compute_signature(
                width, height, secret)
            return webob.Request.blank('bitblt-%sx%s-%s/foo.jpg' % (
                    width, height, signature))

        def process_with_counter(self, *args, **kwargs):
            self.processed = getattr(self, 'processed', 0) + 1
            return self._orig_process(*args, **kwargs)

        import os
        import os.path
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(),
                                'repoze.bitblt-tests-%s' % os.getpid())
        os.mkdir(temp_dir)
        try:
            from repoze.bitblt.processor import ImageTransformationMiddleware

            ImageTransformationMiddleware._orig_process = ImageTransformationMiddleware.process
            ImageTransformationMiddleware.process = process_with_counter
            middleware = self._makeOne(mock_app, cache=temp_dir)
            request = make_request(middleware.secret)
            result = middleware(request.environ, mock_start_response)
            self.assertEqual(middleware.processed, 1)

            ## Second pass, test that we did not process the image
            middleware = self._makeOne(mock_app, cache=temp_dir)
            request = make_request(middleware.secret)
            cached_result = middleware(request.environ, mock_start_response)
            self.assertEqual(getattr(middleware, 'processed', 0), 0)
            self.assertEqual(result, cached_result)

            ## Third pass, no cache
            middleware = self._makeOne(mock_app, cache=None)
            request = make_request(middleware.secret)
            middleware(request.environ, mock_start_response)
            self.assertEqual(middleware.processed, 1)
        finally:
            for path in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, path))
            os.rmdir(temp_dir)
            ImageTransformationMiddleware.process = ImageTransformationMiddleware._orig_process


class TestImgMatch(unittest.TestCase):

    def assertMatch(self, tag, result, app_url=None):
        r = self.match(tag, app_url=app_url)
        self.assertEquals(r, result)

    def match(self, tag, app_url=None):
        match = transform.re_img.match(tag)
        if match is None:
            return None
        result = transform.parse_regex_match(match, app_url=app_url)
        if result is None:
            return None
        src, height, width, scheme, netloc, path, params, query, fragment = result
        return src, height, width

    def test_no_match(self):
        self.assertMatch('<img />', None)
        self.assertMatch('<img src="foo.png"/>', None)
        self.assertMatch('<img width="640"/>', None)
        self.assertMatch('<img height="480"/>', None)
        self.assertMatch('<img height="480%" width="640%"/>', None)
        self.assertMatch('<img height="480" width="640"/>', None)
        self.assertMatch(
            "<img src='http://example.com/foo.png' width='640' height='480' />",
            None,
            app_url="http://example.example.com/")

    def test_matches(self):
        # ' quoting attributes
        self.assertMatch(
            "<img src='foo.png' width='640' fb:name='bobo' height='480' />",
            ('foo.png', '480', '640'))
        # weird whitespace in tag
        self.assertMatch(
            '<img\nsrc="foo.png"\r\nwidth="640"\theight="480"\n/>',
            ('foo.png', '480', '640'))
        # namespaced attributes
        self.assertMatch(
            '<img src="foo.png" width="640" fb:name="bobo" height="480" />',
            ('foo.png', '480', '640'))
        # px
        self.assertMatch(
            '<img src="foo.png" width="640px" height="480px" />',
            ('foo.png', '480', '640'))
        # full url, no app_url
        self.assertMatch(
            "<img src='http://example.com/foo.png' width='640' height='480' />",
            ('http://example.com/foo.png', '480', '640'))
        # full url matching app_url
        self.assertMatch(
            "<img src='http://example.com/foo.png' width='640' height='480' />",
            ('http://example.com/foo.png', '480', '640'),
            app_url="http://example.com/")
        # no / in close (HTML 4)
        self.assertMatch(
            "<img src='foo.png' width='640' height='480' >",
            ('foo.png', '480', '640'))

    def test_evil_matches(self):
        # evil stuff we actually find
        self.assertMatch(
            '<img src=foo.png width=640 fb:name=bobo height=480 />',
            ('foo.png', '480', '640'))


jpeg_image_data = base64.decodestring("""\
/9j/4AAQSkZJRgABAQEASABIAAD/4gPwSUNDX1BST0ZJTEUAAQEAAAPgYXBwbAIAAABtbnRyUkdC
IFhZWiAH1gAFABcADwALAAthY3NwQVBQTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA9tYAAQAA
AADTLWFwcGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA5y
WFlaAAABLAAAABRnWFlaAAABQAAAABRiWFlaAAABVAAAABR3dHB0AAABaAAAABRjaGFkAAABfAAA
ACxyVFJDAAABqAAAAA5nVFJDAAABuAAAAA5iVFJDAAAByAAAAA52Y2d0AAAB2AAAADBuZGluAAAC
CAAAADhkZXNjAAACQAAAAGhkc2NtAAACqAAAAN5tbW9kAAADiAAAAChjcHJ0AAADsAAAAC1YWVog
AAAAAAAAfmkAAEC2AAABklhZWiAAAAAAAABU7AAApucAABbfWFlaIAAAAAAAACOBAAAYeQAAurZY
WVogAAAAAAAA89gAAQAAAAEWCHNmMzIAAAAAAAELtwAABZb///NXAAAHKQAA/df///u3///9pgAA
A9oAAMD2Y3VydgAAAAAAAAABAc0AAGN1cnYAAAAAAAAAAQHNAABjdXJ2AAAAAAAAAAEBzQAAdmNn
dAAAAAAAAAABAADRdAAAAAAAAQAAAADRdAAAAAAAAQAAAADRdAAAAAAAAQAAbmRpbgAAAAAAAAAw
AACmwAAAVgAAAEoAAACbwAAAJAAAABZAAABQQAAAVEAAAjMzAAIzMwACMzNkZXNjAAAAAAAAAA5W
QTIwMTJ3U0VSSUVTAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAG1sdWMAAAAAAAAADwAAAAxpdElUAAAA
GgAAAMRmckZSAAAAGgAAAMRlc0VTAAAAGgAAAMRmaUZJAAAAGgAAAMRwdFBUAAAAGgAAAMR6aFRX
AAAAGgAAAMRqYUpQAAAAGgAAAMRubE5MAAAAGgAAAMRkZURFAAAAGgAAAMRrb0tSAAAAGgAAAMRl
blVTAAAAGgAAAMRub05PAAAAGgAAAMRzdlNFAAAAGgAAAMRkYURLAAAAGgAAAMR6aENOAAAAGgAA
AMQAVgBBADIAMAAxADIAdwBTAEUAUgBJAEUAUwAAbW1vZAAAAAAAAFpjAABqHAAAAADAORUAAAAA
AAAAAAAAAAAAAAAAAHRleHQAAAAAQ29weXJpZ2h0IEFwcGxlIENvbXB1dGVyLCBJbmMuLCAyMDAz
AAAAAP/bAEMAAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB
AQEBAQEBAQEBAQEBAQEBAf/bAEMBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEB
AQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAf/AABEIADAAMAMBEQACEQEDEQH/xAAeAAACAAYD
AAAAAAAAAAAAAAAKCwEDBQYHCQACCP/EAC4QAAAGAQMDAwEJAQAAAAAAAAECAwQFBgcIERIJISIA
ChNBFBUjMTIzQlFSYf/EABQBAQAAAAAAAAAAAAAAAAAAAAD/xAAUEQEAAAAAAAAAAAAAAAAAAAAA
/9oADAMBAAIRAxEAPwA/UxylARMIAAAIiI9gAA/MRH6AG/c309BKMYFClEgibc3gJQ5F5fQ+3Yp0
yCPPluBeRSfz9AMZ1VvdB6PunJkmbwHjmky+rzUPT5QYjIdRplziaLjPGsizAAkqzdMsuq3dl18i
xKiqachTarTbEnAyScjA3ObqVhjFo1YMQdN73bWkTWdlyHwfqFxJNaLbvdZJlDY7tM/kqOylhuxz
TxdFo0rdhyEFSxvKY+sc26cppwJp6pvKU4M1ctpK5wz88U2mALTSAQ33DYo8eIgIjuACYCbD4gAC
mCZjJlTKQpjH8lPIfQT/AEGsPqXdUXEnTfqWMEJqg5Kz/qA1AWeQpOm/TJhOINO5RzFaotKP+8yR
jYjd6ZjXYZzNwLOalmsfOSyLyeim0PW5xyo5SagPR1HPcn6m9OGlvNWLs0dO/UN099aeUKQeJ0p2
S4WODy5ieVazDyJgr5fYfJ0TFUhoTIOJ63OmsUTXGcHdGcTdXNPJc/hZrIxskAI2UunP1DcfYkU1
MZZ0d6oaniB+mWdlss3nEd8joFqymZEiLKz2yblIdFzCxlgfyLJOPs1rTjY+eeSkb9gfvDSrAqwe
HEhIQRBYgbbl3DY3ISlMUxyj/wAMQDF8TJqFU4eZCAf0DQP20vW7oWojRc4wZrOz5Q6hnnS1JU3H
MbecxX6qUp1mPFtsKrFYjkgmbXKw42zIVedxjzGtqMiR9MSiUfQ7PYZKbtt5lX7kC6SGA4bhtt2/
L6bgBgD+hASiUew7egGB6zSOQ9FfUJ0C9ZNfEVvzvpn0z0PMeC9TkFj+NQm7zg2qZQiZ9hE54qUa
u7bFKm2Tuc5G2yacGi41vCwbapSszDlvLOeigF8nesljHqa+4H0Q5g1HGQoOgbB2dzVXANGyC8aN
oWmnfg+JS8v5SW5lgYOx3fM0bjO6ZCVXcKVeh1GCrNbmLDPQ9JdXCVDcppeoXW/x71jNVOVOolfb
m26W8Iw1PSmoh7mu/wBenNEMnphd1S9HxYzxhjaxzkzT4NumDGkyMujD12HutbpoXCNywso8slqh
LaC6i/K1Ra52pWitn7KlHsthNTmUqqovJtKopMvlq23kTqqKGF6lCqMU3JiqKFUWKdb5jnOfYLYb
GOQ4mSIBxAob8kvmAoCYoAIkEBLuY4lT4m8FPk+E/IihyHBvD7XvI2Vck9GTS8+yk8lZYlVkcr43
xvOTbt4+k5TFGPMlWOq01mo4fKqnCPpYRsljWus2opsYms0mGh2bZsjH/CQL69wloG1adR3QO609
aSchVar2RPJlZv17oNumJCsxecafTYufkI3GoWNqm6jWT4l8NT7hCsbM1b1x9YqvCPJKwV4kUR4q
ClrUnppzto9zLctPepPG05ijMNAcs21sps4pFSCrY0g0ayca+YzcG9l6/Yq/MRTlrIRM9XZiZgJZ
FQjyLfuWxyH9BCyapdSlyxZAYNuGoXOFqwlU045KqYcsuWcgz+Ka0SIAPuhOCx3MWB/UYlGLKJvu
9vHxbdNsp+j8Lw9Bgdc5Dm8NwKG4lAw9yAYeYpgUoFTApTmNt8aaZTGMc4EIQxSEDiRgKJhEBHbv
+YAAfTlx/mIb/p2/b57cR8yA2s9rbrig9W/S1xhjp+4iWuU9G5kdOd6ho1lHw5DU6AaHf4VtqURH
gUCMZrGykfXZCwvilfWy9Um8zb86zxyssqBIChRNxDbkHIOQCYSgAAYDAbsUQMJTFLsUQDf/AEBO
fMFtHulejrrcsWu7IevDCWGshagMJ5yq+NFbIbEdYk73ZMQ2rGeLIDHEtG2mkVhrJ2xrTnkBj6Pt
yN6RiXFTj301JQ8xJRDwkajKgF5NwM1XJFzDT0XIw0qyVO3eRsswdRb9mumYSqIuWT9Fu6bqJmKY
FCrIpmKP6vQUsyZi+IgXfbfschu24hvuUwhsPHkXv5J/i/tmKYQ7FIBP3eRB3Dt9eO4lOXjsOygA
PIpT8Q47778ybhvq9u51Q23TM171+YyLPrxOmfUG1jMPaghOZUYqtMHkkRSh5gdN03Lcqg4rs7kz
qYcC3fPGWNbFkhGHj3cs8Ztjg4H9BJVIKnEvcAEdjCBuJgLsIjsIeWxjAUpuJkzf0cO3oKDOVmDs
sS6g7NCxlihHyQtn8POMG83HvmyhBQUQes5MjpB2kqU6nyKOC8viNwP4cy+gC89yj0FNIhtImW9e
ulbF1Q075owQxjrpkCoYrho+pYqzDjo8zDQdmF/QIpuxq9RvtVZvTXaNuVLZxLi1It7PXrnD22Ym
4G1VUFuy5OAl7iYTchAeAFIYvMxQMnt48REo7fHyT/yfuYhAi3MUpgE3YOROQgURMBeXnw4qonMc
5BMmKXMpVCnOPMgkKcgf/9k=""")

gif_image_data = base64.decodestring("""\
R0lGODdhMAAwAIcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMAAGYAAJkAAMwA
AP8AAAAzADMzAGYzAJkzAMwzAP8zAABmADNmAGZmAJlmAMxmAP9mAACZADOZAGaZAJmZAMyZAP+Z
AADMADPMAGbMAJnMAMzMAP/MAAD/ADP/AGb/AJn/AMz/AP//AAAAMzMAM2YAM5kAM8wAM/8AMwAz
MzMzM2YzM5kzM8wzM/8zMwBmMzNmM2ZmM5lmM8xmM/9mMwCZMzOZM2aZM5mZM8yZM/+ZMwDMMzPM
M2bMM5nMM8zMM//MMwD/MzP/M2b/M5n/M8z/M///MwAAZjMAZmYAZpkAZswAZv8AZgAzZjMzZmYz
ZpkzZswzZv8zZgBmZjNmZmZmZplmZsxmZv9mZgCZZjOZZmaZZpmZZsyZZv+ZZgDMZjPMZmbMZpnM
ZszMZv/MZgD/ZjP/Zmb/Zpn/Zsz/Zv//ZgAAmTMAmWYAmZkAmcwAmf8AmQAzmTMzmWYzmZkzmcwz
mf8zmQBmmTNmmWZmmZlmmcxmmf9mmQCZmTOZmWaZmZmZmcyZmf+ZmQDMmTPMmWbMmZnMmczMmf/M
mQD/mTP/mWb/mZn/mcz/mf//mQAAzDMAzGYAzJkAzMwAzP8AzAAzzDMzzGYzzJkzzMwzzP8zzABm
zDNmzGZmzJlmzMxmzP9mzACZzDOZzGaZzJmZzMyZzP+ZzADMzDPMzGbMzJnMzMzMzP/MzAD/zDP/
zGb/zJn/zMz/zP//zAAA/zMA/2YA/5kA/8wA//8A/wAz/zMz/2Yz/5kz/8wz//8z/wBm/zNm/2Zm
/5lm/8xm//9m/wCZ/zOZ/2aZ/5mZ/8yZ//+Z/wDM/zPM/2bM/5nM/8zM///M/wD//zP//2b//5n/
/8z//////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACwAAAAAMAAwAEAI/wDDCRxI
sKDBgwgTKkwIBoDDhxAjLgpHsaLFixUJAQAQrqNHACBthRvZK1y4bV8AqFzJsqXKcDBjyowJoKbN
mwAWbetlCwyAnwBcABhKtGjRWuGSKl3KNByAp1CjSp1KdaqtcFizat3KVautRWAAiB1LtqxZseHS
ql3Llm0vMADiAnABJpzdu3jz6s27CAwAADXAhNMGoLDhw4gLuwDAOJzjx5Ajh+sFAACYcOEAaNZs
K9wiAKBBhwsHBoDp06hTmwYTrrXr12AAyJ4NYAGA27hzA4AAoLfv38ABLApHvLjx44sAKF/OvLnz
589thZtOvbr169Z7hdsWzhaA7+DDi///viCc+fPo06tfz769+/c1AMifTx/AmXD48+vfz79/foC9
AAwkWNBgwXAJFS5kqBAMAAALFi0CA8DiRQBgNALg2NHjR1vhRI4kSbIGADDhVIZbBMDlonC2AMwE
4CJcODAAdO7k2VNnOKBBhYYDA8Do0aPhlC4CsyhcuEUApE6lWnWqrXBZtWq1BcDrV7BhxY4lCybc
WbRp0W4LBwbAW7hx5c6lK9dWOLx59eoF0NfvX8CBBQu2Fc7wYcSIbdUA0NjxY8iRJUMGE87yZcyZ
NW8G0NnzZ9CdIQAAEM70adSpVYfrFc7163CLAMymXdv27HC5de/m3dv3b+DBhffuFc7/+HHkyZUv
Z66cEADo0aMvClfd+nXs2bVrrwHA+3fw38GEI1/e/Hn06csvAtDe/Xv47cPNp1/f/n384WoA4N/f
P0AAAgcOXBTuIMKEChGCAeDwYY0aACZSrGjxIphwGjdy7NgLAAAw4UaG6wXgJIBF4VauBAPgJcyY
MMGAAQAmHM6cOsOBAQAmHFCgYAAAABMu3CIAAFz0ChcOANSoUqdCrRHuKlasYAAACOcVHICwALaF
AwPg7Nle4cAAaOv2Ldy2i8LRrVsXDAAANWoA6Nt3UbhwEAAQXhQuHIDEihczVrwoHOTIksMtAmD5
suUa4TZztgXgM+jQoj8vABDuNOrU3uHAAGjt+jVs1y4A0K5t+zaAcLp38w63CADw4MKHC18A4Djy
5MqPh2vu/HnzXmAAUK9u/Tr27NhrhOvu/Tt4MADGky9v/jz68jXCsW/v3j2A+PLn069vvz6YcPr3
899fAyAAgQMJFjR40GCNcAsZNmS4CEBEiRMpVrRoMVxGjRs5hlsEpgYEFwBIljR5EmXKcCtZtnT5
0iUYADNp1rR5M1xOnTt59uQJLly4GgCIFjV6tGg4pUuZNnXKdFs4qeFqALB6FWtWq+G4dvX6FWxX
cOHIkl0EAO0CAGvZtmUbEAA7""")

transparent_gif_image_data = base64.decodestring("""\
R0lGODdhMAAwAIcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADMAAGYAAJkAAMwA
AP8AAAAzADMzAGYzAJkzAMwzAP8zAABmADNmAGZmAJlmAMxmAP9mAACZADOZAGaZAJmZAMyZAP+Z
AADMADPMAGbMAJnMAMzMAP/MAAD/ADP/AGb/AJn/AMz/AP//AAAAMzMAM2YAM5kAM8wAM/8AMwAz
MzMzM2YzM5kzM8wzM/8zMwBmMzNmM2ZmM5lmM8xmM/9mMwCZMzOZM2aZM5mZM8yZM/+ZMwDMMzPM
M2bMM5nMM8zMM//MMwD/MzP/M2b/M5n/M8z/M///MwAAZjMAZmYAZpkAZswAZv8AZgAzZjMzZmYz
ZpkzZswzZv8zZgBmZjNmZmZmZplmZsxmZv9mZgCZZjOZZmaZZpmZZsyZZv+ZZgDMZjPMZmbMZpnM
ZszMZv/MZgD/ZjP/Zmb/Zpn/Zsz/Zv//ZgAAmTMAmWYAmZkAmcwAmf8AmQAzmTMzmWYzmZkzmcwz
mf8zmQBmmTNmmWZmmZlmmcxmmf9mmQCZmTOZmWaZmZmZmcyZmf+ZmQDMmTPMmWbMmZnMmczMmf/M
mQD/mTP/mWb/mZn/mcz/mf//mQAAzDMAzGYAzJkAzMwAzP8AzAAzzDMzzGYzzJkzzMwzzP8zzABm
zDNmzGZmzJlmzMxmzP9mzACZzDOZzGaZzJmZzMyZzP+ZzADMzDPMzGbMzJnMzMzMzP/MzAD/zDP/
zGb/zJn/zMz/zP//zAAA/zMA/2YA/5kA/8wA//8A/wAz/zMz/2Yz/5kz/8wz//8z/wBm/zNm/2Zm
/5lm/8xm//9m/wCZ/zOZ/2aZ/5mZ/8yZ//+Z/wDM/zPM/2bM/5nM/8zM///M/wD//zP//2b//5n/
/8z//////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEAAJwALAAAAAAwADAA
QAj/AMMJHEiwoMGDCBMqTAgGgMOHECMuCkexosWLFQkBABCuo0cAIG2FG9krXLhtXwCoXMmypcpw
MGPKjAmgps2bABZt62ULDICfAFwAGEq0aNFa4ZIqXco0HICnUKNKnUp1qq1wWLNq3cpVq61FYACI
HUu2rFmx4dKqXcuWbS8wAOICcAEmnN27ePPqzbsIDAAANcCE0wagsOHDiAu7AMA4nOPHkCOH6wUA
AJhw4QBo1mwr3CIAoEGHCwcGgOnTqFObBhOutevXYADIng1gAYDbuHMDgACgt+/fwAEsCke8uPHj
iwAoX868ufPnz22Fm069uvXr1nuF2xbOFoDv4MOL//++IJz58+jTq1/Pvr379zUAyJ9PH8CZcPjz
69/Pv39+gL0ADCRY0GDBcAkVLmSoEAwAAAsWLQIDwOJFAGA0AuDY0eNHW+FEjiRJsgYAMOFUhlsE
wOWicLYAzATgIlw4MAB07uTZU2c4oEGFhgMDwOjRo+GULgKzKFy4RQCkTqVadaqtcFm1arUFwOtX
sGHFjiULJtxZtGnRbgsHBsBbuHHlzqUr11Y4vHn16gXQ1+9fwIEFC7YVzvBhxIht1QDQ2PFjyJEl
QwYTzvJlzJk1bwbQ2fNn0J0hAAAQzvRp1KlVh+sVzvXrcIsAzKZd2/bscLl17+bd2/dv4MGF9+4V
zv/4ceTJlS9nrpwQAOjRoy8KV936dezZtWuvAcD7d/DfwYQjX978efTpyy8C0N79e/jtw82nX9/+
ffzhagDg398/QAACBw5cFO4gwoQKEYIB4PBhjRoAJlKsaPEimHAaN3Ls2AsAADDhRobrBeAkgEXh
Vq4EA+AlzJgwwYABACYczpw6w4EBACYcUKBgAAAAEy7cIgAAXPQKFw4A1KhSp0KtEe4qVqxgAAAI
5xUcgLAAtoUDA+Ds2V7hwABo6/Yt3LaLwtGtWxcMAAA1agDo23dRuHAQABBeFC4cgMSKFzNWvCgc
5MiSwy0CYPmy5RrhNnO2BeAz6NCiPy8AEO406tTe4cAAaO36NWzXLgDQrm37NoBwunfzDrcIAPDg
wocLXwDgOPLkyo+Ha+78efNeYABQr279Ovbs2GuE6+79O3gwAMaTL2/+PPryNcKxb+/ePYD48ufT
r2+/Pphw+vfz318DIACBAwkWNHjQYI1wCxk2ZLgIQESJEylWtGgxXEaNGzmGWwSmBgQXAEiWNHkS
ZcpwK1m2dPnSJRgAM2nWtHkzXE6dO3n25AkuXLgaAIgWNXq0aDilS5k2dcp0Wzip4WoAsHoVa1ar
4bh29foVbFdw4ciSXQQA7QIAa9m2ZRsQADs=""")

def test_suite():
    import sys
    return unittest.findTestCases(sys.modules[__name__])
