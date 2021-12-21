Flask-FlatPages
===============

Flask-FlatPages provides a collection of pages to your `Flask`_ application.
Pages are built from “flat” text files as opposed to a relational database.

* Works on Python 2.7 and 3.4+
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

``FLATPAGES_INSTANCE_RELATIVE``
    .. versionadded:: 0.7

    If `True`, Flask-Flatpages will interpret the root as relative to the
    application's 
    `instance folder <http://flask.pocoo.org/docs/1.0/config/#instance-folders>`_.
    Defaults to `False`.

``FLATPAGES_EXTENSION``
    Filename extension for pages. Files in the ``FLATPAGES_ROOT`` directory
    without this suffix are ignored. Defaults to ``.html``.

    .. versionchanged:: 0.6

       Support multiple file extensions via sequences, e.g.:
       ``['.htm', '.html']`` or via comma-separated strings: ``.htm,.html``.

``FLATPAGES_CASE_INSENSITIVE``
    .. versionadded:: 0.7

    If `True`, the path property of each :class:`Page` instance will be all
    lower case. Flask-Flatpages will throw a `ValueError` if multiple pages
    would correspond to the same path.

``FLATPAGES_ENCODING``
    Encoding of the pages files. Defaults to ``utf8``.

``FLATPAGES_HTML_RENDERER``
    Callable or import string for a callable that takes at least the unicode
    body of a page, and return its HTML rendering as a unicode string. Defaults
    to :func:`~.pygmented_markdown`.

    .. versionchanged:: 0.5

       Support for passing the :class:`~.FlatPages` instance as second
       argument.

    .. versionchanged:: 0.6

       Support for passing the :class:`~.Page` instance as third argument.

    Renderer functions need to have at least one argument, the unicode body.
    The use of either :class:`~FlatPages` as second argument or
    :class:`~FlatPages` and :class:`Page` as second respective third argument
    is optional, and allows for more advanced renderers.


``FLATPAGES_MARKDOWN_EXTENSIONS``
    .. versionadded:: 0.4

    List of Markdown extensions to use with default HTML renderer, given  as
    either 'entrypoint' strings or ``markdown.Extension`` objects. Defaults to
    ``['codehilite']``.

    .. versionchanged:: 0.7

    Markdown 2.5 changed the syntax for passing extensions, and for configuring
    extensions. 
    In particular, configuring an extension by passing keyword arguments along
    with the import string is now deprecated. Instead, these options need to be
    passed in a dict. For more information, see ``FLATPAGES_EXTENSION_CONFIGS``.

``FLATPAGES_EXTENSION_CONFIGS``
    .. versionadded:: 0.7

    Extension config dictionary for configuring extensions passed by their import
    string. For each extension, ``FLATPAGES_EXTENSION_CONFIGS`` contains a dict
    of configuration settings passed as strings.
    For example, to enable linenums in ``codehilite``:

    .. code-block:: python

        FLATPAGES_EXTENSION_CONFIGS = {
            'codehilite': {
                'linenums': 'True'
            }
        }

    `See the Markdown 3 documentation for more details <https://python-markdown.github.io/reference/#extension_configs>`_

``FLATPAGES_AUTO_RELOAD``
    Whether to reload pages at each request. See :ref:`laziness-and-caching`
    for more details.  The default is to reload in ``DEBUG`` mode only.

``FLATPAGES_LEGACY_META_PARSER``
    .. versionadded:: 0.8

    Controls whether to use the newer parser based on tokenising metadata
    with libyaml.

    Setting this to true reverts to the simpler method of parsing metadata
    used in versions <0.8, which requires the metadata block be terminated
    by a newline, or else if there's no metadata that a leading newline be
    present. Intended to provide a fallback in case of bugs with the newer
    parser.

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

Each file is made of a `YAML`_ mapping of metadata, and the
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

Delimiting YAML Metadata
~~~~~~~~~~~~~~~~~~~~~~~~

.. versionadded:: 0.8

In previous versions, YAML metadata was terminated by a newline. This meant it
was impossible to use multi-line strings in the metadata, or worse that if
your page had no metadata at all it needed to start with an empty line.

Starting with v0.8, YAML can now be delimited in 'Jekyll' style, by wrapping
it with ``---``::

    ---
    title: Hello World
    author: J.L Coolman
    ---
    Hello, world!

Or using YAML 'end document' specifiers like::

    ---
    title: Hello Again
    author: J.L Coolman
    ...
    Hello, world!

Or by terminating with a newline, in a backwards compatible way.

In all cases, the leading ``---`` is optional.

With this change, it's now possible to have pages with no-metadata
by starting them with::

    ---
    ---
    Hello, this is my page

Or::

    ---
    ...
    Hello, this is a page too

Or even just launching in to the body::
    
    Hello, this is also a page!

.. warning:: 
    If you want to use multiline strings in metadatia you **must** use
    a start and end delimiter, or else the parser may cut the metadata
    at the first blank line.


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

Using custom HTML renderers
~~~~~~~~~~~~~~~~~~~~~~~~~~~

As pointed above, by default Flask-FlatPages expects that flatpage body
contains `Markdown`_ markup, so uses ``markdown.markdown`` function to render
its content. But due to ``FLATPAGES_HTML_RENDERER`` setting you can specify
different approach for rendering flatpage body.

The most common necessity of using custom HTML renderer is modifyings default
Markdown approach (e.g. by pre-rendering Markdown flatpages with Jinja), or
using different markup for rendering flatpage body (e.g. ReStructuredText).
Examples below introduce how to use custom renderers for those needs.

Pre-rendering Markdown flatpages with Jinja
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

    from flask import Flask, render_template_string
    from flask_flatpages import FlatPages
    from flask_flatpages.utils import pygmented_markdown

    def my_renderer(text):
        prerendered_body = render_template_string(text)
        return pygmented_markdown(prerendered_body)
        # Or, if you wish to render using the markdown extensions
        # listed in FLATPAGES_MARKDOWN_EXTENSIONS:
        #return pygmented_markdown(prerendered_body, flatpages=pages)

    app = Flask(__name__)
    app.config['FLATPAGES_HTML_RENDERER'] = my_renderer
    pages = FlatPages(app)

ReStructuredText flatpages
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. note:: For rendering ReStructuredText you need to add `docutils
   <http://pypi.python.org/pypi/docutils>`_ to your project requirements.

::

    from docuitls.core import publish_parts
    from flask import Flask
    from flask_flatpages import FlatPages

    def rst_renderer(text):
        parts = publish_parts(source=text, writer_name='html')
        return parts['fragment']

    app = Flask(__name__)
    app.config['FLATPAGES_HTML_RENDERER'] = rst_renderer
    pages = FlatPages(app)

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
    pages.get('foo')  # Force loading now. foo.html may not even exist.

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

.. release-notes::

v0.7.2
~~~~~~~~~~~~~
Release Date: 2020-04-19

Bug Fixes
^^^^^^^^^

- Fixed a bug arising when the user overrides the default markdown extensions, but does not use Pygments. Apologies to anyone who didn't want codehiliting!
  (`#73 <https://github.com/Flask-FlatPages/Flask-FlatPages/issues/73>`_) 

Documentation Changes
^^^^^^^^^^^^^^^^^^^^^

- Update documentation to use the latest version of the Flask template.
   
- Add towncrier config for auto-generating release notes
   

Other Notes
^^^^^^^^^^^

- This project currently supports Python versions 2.7, and 3.4+.

  Some dependencies, particularly PyYAML, do not support Python 3.4 in the most recent versions. Thus, for security reasons,
  we strongly advise using Python 2.7 if no newer version of Python 3 is available.

  Support for Python 3.4 will be dropped in June 2020.


v0.7.1
~~~~~~~~~~~~~

* Small bump to dependency versions to resolve security alerts.

v0.7.0
~~~~~~~~~~~~~

* Update to Markdown 3.0 with new extension loading syntax. 
* Added `FLATPAGES_EXTENSION_CONFIGS` for configuring extensions specified by import string.
* Add support for loading pages from Flask instance folder
* Add a case insensitive loading option

v0.6.1
~~~~~~~~~~~~~

* Update dependencies to `Flask>=1.0` (as Flask 0.12.1 has known vulnerabilities).
* Pin `Markdown<=3.0` as the Markdown extension API has changed.

v0.6
~~~~~~~~~~~

Release Date: 2015-02-09

* Python 3 support.
* Allow multiple file extensions for FlatPages.
* The renderer function now optionally takes a third argument, namely
  the :class:`Page` instance.
* It is now possible to instantiate multiple instances of :class:`FlatPages`
  with different configurations. This is done by specifying an additional
  parameter ``name`` to the initializer and adding the same name in uppercase
  to the respective Flask configuration settings.


v0.5
~~~~~~~~~~~

Release Date: 2013-04-02

* Change behavior of passing ``FLATPAGES_MARKDOWN_EXTENSIONS`` to renderer
  function, now the :class:`FlatPages` instance is optionally passed as second
  argument. This allows more robust renderer functions.


v0.4
~~~~~~~~~~~

Release Date: 2013-04-01

* Add ``FLATPAGES_MARKDOWN_EXTENSIONS`` config to setup list of Markdown
  extensions to use with default HTML renderer.
* Fix a bug with non-ASCII filenames.


v0.3
~~~~~~~~~~~

Release Date: 2012-07-03

* Add :meth:`.FlatPages.init_app`
* Do not use namespace packages anymore: rename the package from
  ``flaskext.flatpages`` to ``flask_flatpages``
* Add configuration files for testing with tox and Travis.


v0.2
~~~~~~~~~~~

Release Date: 2011-06-02

Bugfix and cosmetic release. Tests are now installed alongside the code.


v0.1
~~~~~~~~~~~

Release Date: 2011-02-06.

First public release.
