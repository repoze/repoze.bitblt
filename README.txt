Overview
========

This package provides a WSGI middleware component which automatically
scales images according to the ``width`` and ``height`` property in
the <img> tag.

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

This effectively means that application developers needn't worry about
image scaling; simply put the desired size in the HTML document.

Note that this middleware is protected from DoS attacks (which is
important for any middleware that does significant processing) by
signing all URLs with an SHA digest signature.

Credits
-------

Malthe Borch <mborch@gmail.com>
Stefan Eletzhofer <stefan.eletzhofer@inquant.de>
Jeroen Vloothuis <jeroen.vloothuis@xs4all.nl>


