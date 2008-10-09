Overview
========

This package provides a WSGI middleware component which transforms and
converts image streams using PIL.


Usage
-----

The middleware responds to the following URL parameters:

  @width      Width
  @height     Height
  @mimetype   MIME-type 
  @quality    Image quality (default is 80)
  
Example:

  http://host/path/to/images/foo.jpg?width=640&height=480&mimetype=image/png

Note that in a real-world setup, you'd want to put a caching proxy in
front of your application.


Future plans
------------

Support video transcoding.


Credits
-------

Malthe Borch <mborch@gmail.com> and Stefan Eletzhofer <stefan.eletzhofer@inquant.de>

