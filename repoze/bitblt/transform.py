import lxml.html
import urlparse
import hashlib

def compute_signature(width, height, key):
    return hashlib.sha1("%s:%s:%s" % (width, height, key)).hexdigest()

def verify_signature(width, height, key, signature):
    return signature == compute_signature(width, height, key)

def rewrite_image_tags(body, key):
    root = lxml.html.document_fromstring(body)
    for img in root.findall('.//img'):
        width = img.attrib.get('width')
        height = img.attrib.get('height')
        src = img.attrib.get('src')
        
        if width and height and src:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(src)
            signature = compute_signature(width, height, key)
            
            parts = path.split('/')
            parts.insert(-1, 'bitblt-%sx%s-%s' % (width, height, signature))
                
            path = '/'.join(filter(None, parts))

            img.attrib['src'] = urlparse.urlunparse(
                (scheme, netloc, path, params, query, fragment))

    return lxml.html.tostring(root)
                              

            

             
