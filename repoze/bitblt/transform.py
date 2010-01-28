import re
from StringIO import StringIO
import urlparse

try:
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

re_img = re.compile(r'''<img'''
                    r'''(?:\s+(?:''' # whitespace at start of tag
                        r'''src=["']?(?P<src>[^"'\s]*)["']?''' # find src= 
                        r'''|width=["']?(?P<width>\d*)(?:px)?["']?''' # or find width=
                        r'''|height=["']?(?P<height>\d*)(?:px)?["']?''' # or find height=
                        r'''|[\w:]*=(?:'[^']*'|"[^"]*"|[^<>"'\s]*)''' # or match but ignore most other tags
                    r'''))+\s*/>''') # match whitespace at the end and the end tag

def compute_signature(width, height, key):
    return sha1("%s:%s:%s" % (width, height, key)).hexdigest()

def verify_signature(width, height, key, signature):
    return signature == compute_signature(width, height, key)

def rewrite_image_tags(body, key, app_url=None):
    mos =  re_img.finditer(body)
    index = 0
    new_body = []
    for mo in mos:
        # add section before current match to new body
        new_body.append(body[index:mo.start()])
        index = mo.end()
        # work on <img> tag
        d = dict(src=None, height=None, width=None)
        d.update(mo.groupdict())
        src, height, width = d['src'], d['height'], d['width']
        new_body.append(body[mo.start():mo.end()])
        # check conditions in which we should skip this tag
        if not src or not (width or height):
            continue
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(src)
        if app_url is not None and not src.startswith(app_url):
            if netloc != '':
                continue
        # calculate new src url 
        signature = compute_signature(width, height, key)
        parts = path.split('/')
        parts.insert(-1, 'bitblt-%sx%s-%s' % (width, height, signature))
        path = '/'.join(parts)
        src = urlparse.urlunparse((scheme, netloc, path, params, query, fragment))
        # replace last element (which is the unmodified img tag)
        new_body[-1:] = [body[mo.start():mo.start('src')], src, body[mo.end('src'):mo.end()]]
    # add section after last match to new body
    new_body.append(body[index:])
    return ''.join(new_body)
