Flask-FlatPages
===============

Flask-FlatPages provides a collection of pages to your `Flask`_ application.
Pages are built from “flat” text files as opposed to a relational database.

* Works on Python 2.6, 2.7 and 3.3+
* BSD licensed
* Latest documentation `on Read the Docs`_
* Source, issues and pull requests `on Github`_
* Releases `on PyPI`_

.. _Flask: http://flask.pocoo.org/
.. _on Read the Docs: http://flask-flatpages.readthedocs.org/
.. _on Github: https://github.com/SimonSapin/Flask-FlatPages/
.. _on PyPI: http://pypi.python.org/pypi/Flask-FlatPages


Installation
------------

Install the extension with `pip <http://pip.pypa.org/>`_::

    $ pip install Flask-FlatPages

or you can get the `source code from github
<https://github.com/SimonSapin/Flask-FlatPages>`_.

Configuration
-------------

To get started all you need to do is to instantiate a :class:`FlatPages` object
after configuring the application::

    from flask import Flask
    from flask_flatpages import FlatPages

    app = Flask(__name__)
    app.config.from_pyfile('mysettings.cfg')
    pages = FlatPages(app)

you can also pass the Flask application object later, by calling
:meth:`~.FlatPages.init_app`::

    pages = FlatPages()

    def create_app(config='mysettings.cfg'):
        app = Flask(__name__)
        app.config.from_pyfile(config)
        pages.init_app(app)
        return app


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
    Callable or import string for a callable that takes at least the unicode
    body of a page, and return its HTML rendering as a unicode string. Defaults
    to :func:`~.pygmented_markdown`.

    .. versionchanged:: 0.6

       Support for passing the :class:`~.Page` instance as third argument.

    .. versionchanged:: 0.5

       Support for passing the :class:`~.FlatPages` instance as second
       argument.

    Renderer functions need to have at least one argument, the unicode body.
    The use of either :class:`~FlatPages` as second argument or
    :class:`~FlatPages` and :class:`Page` as second respective third argument
    is optional, and allows for more advanced renderers.


``FLATPAGES_MARKDOWN_EXTENSIONS``
    .. versionadded:: 0.4

    List of Markdown extensions to use with default HTML renderer. Defaults to
    ``['codehilite']``.

    For passing additional arguments to Markdown extension, e.g. in case of
    using footnotes extension, use next syntax:
    ``['footnotes(UNIQUE_IDS=True)']``

``FLATPAGES_AUTO_RELOAD``
    Wether to reload pages at each request. See :ref:`laziness-and-caching`
    for more details.  The default is to reload in ``DEBUG`` mode only.

Please note that multiple FlatPages instances can be configured by using a
name for the FlatPages instance at initializaton time:

.. code-block:: python

   flatpages = FlatPages(name="blog")

To configure this instance, you must use modified configuration keys, by adding
the uppercase name to the configuration variable names: ``FLATPAGES_BLOG_*``

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

Using custom Markdown extensions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.4

By default, Flask-FlatPages renders flatpage body using `Markdown`_ with
`Pygments`_ format. This means passing ``['codehilite']`` extensions list to
``markdown.markdown`` function.

But sometimes you need to customize things, like using another extension or
disable default approach, this possible by passing special config.

For example, using another extension::

    FLATPAGES_MARKDOWN_EXTENSIONS = ['codehilite', 'headerid']

Or disabling default approach::

    FLATPAGES_MARKDOWN_EXTENSIONS = []

.. _laziness-and-caching:

Laziness and caching
--------------------

:class:`.FlatPages` does not hit the filesystem until needed but when it does,
it reads all pages from the disk at once.

Then, pages are not loaded again unless you explicitly ask for it with
:meth:`.FlatPages.reload`, or on new requests depending on the configuration.
(See ``FLATPAGES_AUTO_RELOAD``.)

This design was decided with `Frozen-Flask`_ in mind but should work even if
you don’t use it: you already restart your production server on code changes,
you just have to do it on page content change too. This can make sense if
the pages are deployed alongside the code in version control.

.. _Frozen-Flask: http://packages.python.org/Frozen-Flask/

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

.. module:: flask_flatpages

.. autoclass:: FlatPages
    :members: init_app, get, get_or_404, __iter__, reload

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

Version 0.6
~~~~~~~~~~~

* Python 3 support.
* The renderer function now optionally takes a third argument, namely
  the :class:`Page` instance.
* It is now possible to instantiate multiple instances of :class:`FlatPages`
  with different configurations. This is done by specifying an additional
  parameter ``name`` to the initializer and adding the same name in uppercase
  to the respective Flask configuration settings.


Version 0.5
~~~~~~~~~~~

Released on 2013-04-02

* Change behavior of passing ``FLATPAGES_MARKDOWN_EXTENSIONS`` to renderer
  function, now the :class:`FlatPages` instance is optionally passed as second
  argument. This allows more robust renderer functions.


Version 0.4
~~~~~~~~~~~

Released on 2013-04-01

* Add ``FLATPAGES_MARKDOWN_EXTENSIONS`` config to setup list of Markdown
  extensions to use with default HTML renderer.
* Fix a bug with non-ASCII filenames.


Version 0.3
~~~~~~~~~~~

Released on 2012-07-03

* Add :meth:`.FlatPages.init_app`
* Do not use namespace packages anymore: rename the package from
  ``flaskext.flatpages`` to ``flask_flatpages``
* Add configuration files for testing with tox and Travis.


Version 0.2
~~~~~~~~~~~

Released on 2011-06-02

Bugfix and cosmetic release. Tests are now installed alongside the code.


Version 0.1
~~~~~~~~~~~

Released on 2011-02-06.

First public release.
