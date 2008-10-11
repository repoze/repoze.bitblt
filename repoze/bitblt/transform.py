import lxml.html
import urlparse

def rewrite_image_tags(body):
    root = lxml.html.document_fromstring(body)
    for img in root.findall('.//img'):
        width = img.attrib.get('width')
        height = img.attrib.get('height')
        src = img.attrib.get('src')
        
        if width and height and src:
            scheme, netloc, path, params, query, fragment = urlparse.urlparse(src)

            parts = path.split('/')
            parts.insert(-1, 'bitblt-%sx%s' % (width, height))
                
            path = '/'.join(filter(None, parts))

            img.attrib['src'] = urlparse.urlunparse(
                (scheme, netloc, path, params, query, fragment))

    return lxml.html.tostring(root)
                              

            

             
