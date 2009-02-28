import lxml.html
import urlparse
import hashlib

def compute_signature(width, height, key):
    return hashlib.sha1("%s:%s:%s" % (width, height, key)).hexdigest()

def verify_signature(width, height, key, signature):
    return signature == compute_signature(width, height, key)

def rewrite_image_tags(body, key, app_url=None, try_xhtml=False):
    if try_xhtml:
        try:
            root = lxml.etree.fromstring(body)
        except lxml.etree.XMLSyntaxError as e:
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
            signature = compute_signature(width, height, key)
            
            parts = path.split('/')
            parts.insert(-1, 'bitblt-%sx%s-%s' % (width, height, signature))
                
            path = '/'.join(filter(None, parts))

            img.attrib['src'] = urlparse.urlunparse(
                (scheme, netloc, path, params, query, fragment))

    return lxml.html.tostring(root)
                              

            

             
