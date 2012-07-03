# coding: utf8
"""
    flas_flatpages
    ~~~~~~~~~~~~~~~~~~

    Flask-FlatPages provides a collections of pages to your Flask application.
    Pages are built from “flat” text files as opposed to a relational database.

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import os.path
import itertools

import yaml
import markdown
import werkzeug
import flask


def pygmented_markdown(text):
    """Render Markdown text to HTML. Uses the `Codehilite`_ extension
    if `Pygments`_ is available.

    .. _Codehilite: http://www.freewisdom.org/projects/python-markdown/CodeHilite
    .. _Pygments: http://pygments.org/
    """
    try:
        import pygments
    except ImportError:
        extensions = []
    else:
        extensions = ['codehilite']
    return markdown.markdown(text, extensions)


def pygments_style_defs(style='default'):
    """:return: the CSS definitions for the `Codehilite`_ Markdown plugin.

    :param style: The Pygments `style`_ to use.

    Only available if `Pygments`_ is.

    .. _Codehilite: http://www.freewisdom.org/projects/python-markdown/CodeHilite
    .. _Pygments: http://pygments.org/
    .. _style: http://pygments.org/docs/styles/
    """
    import pygments.formatters
    formater = pygments.formatters.HtmlFormatter(style=style)
    return formater.get_style_defs('.codehilite')


class Page(object):
    def __init__(self, path, meta_yaml, body, html_renderer):
        #: Path this pages was obtained from, as in ``pages.get(path)``.
        self.path = path
        #: Content of the pages.
        self.body = body
        self._meta_yaml = meta_yaml
        self.html_renderer = html_renderer

    def __repr__(self):
        return '<Page %r>' % self.path

    @werkzeug.cached_property
    def html(self):
        """The content of the page, rendered as HTML by the configured renderer.
        """
        return self.html_renderer(self.body)

    def __html__(self):
        """In a template, ``{{ page }}`` is equivalent to
        ``{{ page.html|safe }}``.
        """
        return self.html

    @werkzeug.cached_property
    def meta(self):
        """A dict of metadata parsed as YAML from the header of the file."""
        meta = yaml.safe_load(self._meta_yaml)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        assert isinstance(meta, dict)
        return meta

    def __getitem__(self, name):
        """Shortcut for accessing metadata.

        ``page['title']`` or, in a template, ``{{ page.title }}`` are
        equivalent to ``page.meta['title']``.
        """
        return self.meta[name]


class FlatPages(object):
    """
    A collections of :class:`Page` objects.

    :param app: your application. Can be omited if you call
                :meth:`init_app` later.
    :type app: Flask instance

    """
    def __init__(self, app=None):

        #: dict of filename: (page object, mtime when loaded)
        self._file_cache = {}

        if app:
            self.init_app(app)


    def init_app(self, app):
        """ Used to initialize an application, useful for
        passing an app later and app factory patterns.

        :param app: your application
        :type app: Flask instance

        """

        app.config.setdefault('FLATPAGES_ROOT', 'pages')
        app.config.setdefault('FLATPAGES_EXTENSION', '.html')
        app.config.setdefault('FLATPAGES_ENCODING', 'utf8')
        app.config.setdefault('FLATPAGES_HTML_RENDERER', pygmented_markdown)
        app.config.setdefault('FLATPAGES_AUTO_RELOAD', 'if debug')

        self.app = app

        app.before_request(self._conditional_auto_reset)

    def _conditional_auto_reset(self):
        """Reset if configured to do so on new requests."""
        auto = self.app.config['FLATPAGES_AUTO_RELOAD']
        if auto == 'if debug':
            auto = self.app.debug
        if auto:
            self.reload()

    def reload(self):
        """Forget all pages.
        All pages will be reloaded next time they're accessed"""
        try:
            # This will "unshadow" the cached_property.
            # The property will be re-executed on next access.
            del self.__dict__['_pages']
        except KeyError:
            pass

    def __iter__(self):
        """Iterate on all :class:`Page` objects."""
        return self._pages.itervalues()

    def get(self, path, default=None):
        """
        :Return: the :class:`Page` object at ``path``, or ``default``
                 if there is none.

        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            return pages[path]
        except KeyError:
            return default

    def get_or_404(self, path):
        """:Return: the :class:`Page` object at ``path``.
        :raises: :class:`NotFound` if the pages does not exist.
                 This is caught by Flask and triggers a 404 error.

        """
        page = self.get(path)
        if not page:
            flask.abort(404)
        return page

    @property
    def root(self):
        """Full path to the directory where pages are looked for.

        It is the `FLATPAGES_ROOT` config value, interpreted as relative to
        the app root directory.
        """
        return os.path.join(self.app.root_path,
                            self.app.config['FLATPAGES_ROOT'])

    @werkzeug.cached_property
    def _pages(self):
        """Walk the page root directory an return a dict of
        unicode path: page object.
        """
        def _walk(directory, path_prefix=()):
            for name in os.listdir(directory):
                full_name = os.path.join(directory, name)
                if os.path.isdir(full_name):
                    _walk(full_name, path_prefix + (name,))
                elif name.endswith(extension):
                    name_without_extension = name[:-len(extension)]
                    path = u'/'.join(path_prefix + (name_without_extension,))
                    pages[path] = self._load_file(path, full_name)

        extension = self.app.config['FLATPAGES_EXTENSION']
        pages = {}
        _walk(self.root)
        return pages

    def _load_file(self, path, filename):
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)
        if cached and cached[1] == mtime:
            # cached == (page, old_mtime)
            page = cached[0]
        else:
            with open(filename) as fd:
                content = fd.read().decode(
                    self.app.config['FLATPAGES_ENCODING'])
            page = self._parse(content, path)
            self._file_cache[filename] = page, mtime
        return page

    def _parse(self, string, path):
        lines = iter(string.split(u'\n'))
        # Read lines until an empty line is encountered.
        meta = u'\n'.join(itertools.takewhile(unicode.strip, lines))
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = u'\n'.join(lines)

        html_renderer = self.app.config['FLATPAGES_HTML_RENDERER']
        if not callable(html_renderer):
            html_renderer = werkzeug.import_string(html_renderer)
        return Page(path, meta, content, html_renderer)
