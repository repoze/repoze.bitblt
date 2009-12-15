import lxml.html
import urlparse

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

def compute_signature(width, height, key):
    return sha1("%s:%s:%s" % (width, height, key)).hexdigest()

def verify_signature(width, height, key, signature):
    return signature == compute_signature(width, height, key)

def rewrite_image_tags(body, key, app_url=None, try_xhtml=False):
    isxml = False
    if try_xhtml:
        try:
            parser = lxml.html.XHTMLParser(resolve_entities=False, strip_cdata=False)
            root = lxml.html.document_fromstring(body, parser=parser)
            isxml = True
        except lxml.etree.XMLSyntaxError, e:
            root = lxml.html.document_fromstring(body)
    else:
        root = lxml.html.document_fromstring(body)
    nsmap = {'x':lxml.html.XHTML_NAMESPACE}
    for img in root.xpath('.//img|.//x:img', namespaces=nsmap):
        width = img.attrib.get('width')
        height = img.attrib.get('height')
        src = img.attrib.get('src')

        if (width or height) and src:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(src)
            if app_url is not None and not src.startswith(app_url):
                if netloc != '':
                    continue
            if height and height.endswith('px'):
                height = height[:-2]
            if width and width.endswith('px'):
                width = width[:-2]
            if (height and not height.isdigit()) or (width and not width.isdigit()):
                continue
            signature = compute_signature(width, height, key)

            parts = path.split('/')
            parts.insert(-1, 'bitblt-%sx%s-%s' % (width, height, signature))

            path = '/'.join(parts)

            img.attrib['src'] = urlparse.urlunparse(
                (scheme, netloc, path, params, query, fragment))

    if isxml:
        return lxml.etree.tostring(root, encoding=unicode)
    return lxml.html.tostring(root, encoding=unicode)
