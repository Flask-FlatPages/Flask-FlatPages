Flask-FlatPages
===============

Flask-FlatPages provides a collections of pages to your `Flask`_ application.
Pages are built from “flat” text files as opposed to a relational database.

.. _Flask: http://flask.pocoo.org/

Installation
------------

Install the extension with one of the following commands::

    $ easy_install Flask-FlatPages

or alternatively if you have pip installed::

    $ pip install Flask-FlatPages

or you can get the `source code from github
<https://github.com/SimonSapin/Flask-FlatPages>`_.

Configuration
-------------

To get started all you need to do is to instantiate a :class:`FlatPages` object
after configuring the application::

    from flask import Flask
    from flaskext.flatpages import FlatPages
    
    app = Flask(__name__)
    app.config.from_pyfile('mysettings.cfg')
    pages = FlatPages(app)

Flask-FlatPages accepts the following configuration values. All of them
are optional.

``FLATPAGES_ROOT``
    Path to the directory where to look for page files. If relative,
    interpreted as relative to the application root, next to the ``static`` and
    ``templates`` directories. Defaults to ``pages``.

``FLATPAGES_EXTENSION``
    Filename extension for pages. Files in the ``FLATPAGES_ROOT`` directory
    without this suffix are ignored. Defaults to ``.html``.

``FLATPAGES_ENCODING``
    Encoding of the pages files. Defaults to ``utf8``.

``FLATPAGES_HTML_RENDERER``
    Callable or import string for a callable that takes the unicode body of a
    page, and return its HTML rendering as a unicode string. Defaults to
    :func:`~.pygmented_markdown`.

``FLATPAGES_AUTO_RELOAD``
    Wether to reload pages at each request. See :ref:`laziness-and-caching`
    for more details.  The default is to reload in ``DEBUG`` mode only.

How it works
------------

When first needed (see :ref:`laziness-and-caching` for more about this),
the extension loads all pages from the filesystem: a :class:`Page` object is
created for all files in ``FLATPAGES_ROOT`` whose name ends with
``FLATPAGES_EXTENSION``.

Each of these objects is associated to a path:
the slash-separated (whatever the OS) name of the file it was loaded from,
relative to the pages root, and excluding the extension. For example, for
an app in ``C:\myapp`` with the default configuration, the path for the
``C:\myapp\pages\lorem\ipsum.html`` is ``lorem/ipsum``.

Each file is made of a `YAML`_ mapping of metadata, a blank line, and the
page body::

    title: Hello
    published: 2010-12-22
    
    Hello, *World*!
    
    Lorem ipsum dolor sit amet, …

The body format defaults to `Markdown`_ with `Pygments`_ baked in if available,
but depends on the ``FLATPAGES_HTML_RENDERER`` configuration value.

.. _YAML: http://www.yaml.org/
.. _Markdown: http://daringfireball.net/projects/markdown/
.. _Pygments: http://pygments.org/

To use Pygments, you need to include the style declarations separately.
You can get them with :func:`.pygments_style_defs`::

    @app.route('/pygments.css')
    def pygments_css():
        return pygments_style_defs('tango'), 200, {'Content-Type': 'text/css'}

and in templates:

.. code-block:: html+jinja

    <link rel="stylesheet" href="{{ url_for('pygments_css') }}">


.. _laziness-and-caching:

Laziness and caching
--------------------

:class:`.FlatPages` does not hit the filesystem until needed but when it does,
it reads all pages from the disk at once.

Then, pages are not loaded again unless you explicitly ask for it with
:meth:`.FlatPages.reload`, or on new requests depending on the configuration.
(See ``FLATPAGES_AUTO_RELOAD``.)

This design was decided with `Flask-Static`_ in mind but should work even if
you don’t use it: you already restart your production server on code changes,
you just have to do it on page content change too. This can make sense if
the pages are deployed alongside the code in version control.

.. _Flask-Static: http://packages.python.org/Flask-Static/

If you have many pages and loading takes a long time, you can force it at
initialization time so that it’s done by the time the first request is served::

    pages = FlatPages(app)
    pages.get('foo') # Force loading now. foo.html may not even exist.

Loading everything every time may seem wasteful, but the impact is mitigated
by caching: if a file’s modification time hasn’t changed, it is not read again
and the previous :class:`.Page` object is re-used.

Likewise, the YAML and Markdown parsing is both lazy and cached: not done
until needed, and not done again if the file did not change.

API
---

.. module:: flaskext.flatpages

.. autoclass:: FlatPages
    :members: get, get_or_404, __iter__, reload

    Example usage::

        pages = FlatPages(app)
        
        @app.route('/')
        def index():
            # Articles are pages with a publication date
            articles = (p for p in pages if 'published' in p.meta)
            # Show the 10 most recent articles, most recent first.
            latest = sorted(articles, reverse=True,
                            key=lambda p: p.meta['published'])
            return render_template('articles.html', articles=latest[:10])

        @app.route('/<path:path>/')
        def page(path):
            page = pages.get_or_404(path)
            template = page.meta.get('template', 'flatpage.html')
            return render_template(template, page=page)

.. autoclass:: Page()
    :members:

    With the ``hello.html`` page defined earlier::

        # hello.html
        title: Hello
        published: 2010-12-22
        
        Hello, *World*!
        
        Lorem ipsum dolor sit amet, …
        
    ::
    
        >>> page = pages.get('hello')
        >>> page.meta # PyYAML converts YYYY-MM-DD to a date object
        {'title': u'Hello', 'published': datetime.date(2010, 12, 22)}
        >>> page['title']
        u'Hello'
        >>> page.body
        u'Hello, *World*!\n\nLorem ipsum dolor sit amet, \u2026'
        >>> page.html
        u'<p>Hello, <em>World</em>!</p>\n<p>Lorem ipsum dolor sit amet, \u2026</p>'

    .. automethod:: __getitem__
    .. automethod:: __html__
    
.. autofunction:: pygmented_markdown

.. autofunction:: pygments_style_defs

Changelog
---------

Version 0.2, released on 2011-06-02
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bugfix and cosmetic release. Tests are now installed alongside the code.

Version 0.1, released on 2011-02-06
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

First public release.

