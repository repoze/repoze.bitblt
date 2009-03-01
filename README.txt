Overview
========

This package provides a WSGI middleware component which automatically
scales images according to the ``width`` and ``height`` property in
the <img> tag.

To configure the middleware, pass in a string for ``secret``; this may
be any string internal to the system.

You can also set ``filter`` to select the scaling filter. The available
filters are ``nearest``, ``bilinear``, ``bicubic`` and ``antialias``. The
default is ``antialias``.

If you want to change the compression level for JPEG images, then you can set
the ``quality`` option to a value between 1 (worst) and 95 (best). The default
is 80.

By default all image URLs are rewritten. With ``limit_to_application_url``
you can limit the rewriting to relative URLs and absolute URLs below the
application URL.

If you want to use namespaces for tags in your content, then you need to
specify ``try_xhtml`` which uses an XML parser for the content and preserves
namespaces. This is useful if you use esi:include for example. Your content
needs to be well formed for this to work, that includes a proper doctype etc.

Usage
-----

The middleware operates in two phases, on HTML documents and images
respectively.

When processing HTML documents, it looks for image tags in the
document soup::

  <img src="some_image.png" width="640" height="480" />

In the case it finds such an image element, it rewrites the URL to
include scaling information which the middleware will read when the
image is served through it.

The image will be proportionally scaled, so it fits into the given size. If
you only set one of width or height, then the image will only be limited to
that, but still proportionally scaled.

This effectively means that application developers needn't worry about
image scaling; simply put the desired size in the HTML document.

Note that this middleware is protected from DoS attacks (which is
important for any middleware that does significant processing) by
signing all URLs with an SHA digest signature.

Credits
-------

* Malthe Borch <mborch@gmail.com>
* Stefan Eletzhofer <stefan.eletzhofer@inquant.de>
* Jeroen Vloothuis <jeroen.vloothuis@xs4all.nl>
* Florian Schulze <florian.schulze@gmx.net>
