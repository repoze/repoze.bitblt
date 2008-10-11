Overview
========

This package provides a WSGI middleware component which transforms and
converts image streams using PIL.


Usage
-----

The middleware works by looking for a "traversing directive"::

  <img src="http://host/path/bitblt-640x480/image.jpg" />

When a request comes in that matches the directive, the image is
transformed and the directive is removed from the request.

However, by specifying ``width`` and ``height`` attributes in
<img>-tags in served HTML documents, the middleware will do this
rewriting itself.

As such, the middleware is transparent: adding it to the pipeline
merely makes pages load more effectively, since images will be scaled
to desired size.


Credits
-------

Malthe Borch <mborch@gmail.com>
Stefan Eletzhofer <stefan.eletzhofer@inquant.de>
Jeroen Vloothuis <jeroen.vloothuis@xs4all.nl>


