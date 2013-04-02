# coding: utf8
"""
    flask_flatpages
    ~~~~~~~~~~~~~~~

    Flask-FlatPages provides a collections of pages to your Flask application.
    Pages are built from “flat” text files as opposed to a relational database.

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import inspect
import itertools
import os

import flask
import markdown
import yaml
import werkzeug

try:
    from pygments.formatters import HtmlFormatter as PygmentsHtmlFormatter
except ImportError:
    PygmentsHtmlFormatter = None


VERSION = '0.5'


def pygmented_markdown(text, flatpages=None):
    """Render Markdown text to HTML.

    Uses the `CodeHilite`_ extension only if `Pygments`_ is available. But if
    `Pygments`_ no available removes "codehilite" from list of possible
    extensions.

    If you need other extensions to use setup them to
    ``FLATPAGES_MARKDOWN_EXTENSIONS`` list setting. Later whole
    :class:`FlatPages` instance would be passed to your
    ``FLATPAGES_HTML_RENDERER`` function as second argument.

    .. _CodeHilite:
       http://www.freewisdom.org/projects/python-markdown/CodeHilite
    .. _Pygments: http://pygments.org/
    """
    extensions = flatpages.config('markdown_extensions') if flatpages else []

    if PygmentsHtmlFormatter is None:
        original_extensions = extensions
        extensions = []

        for extension in original_extensions:
            if extension.startswith('codehilite'):
                continue
            extensions.append(extension)
    elif not extensions:
        extensions = ['codehilite']

    return markdown.markdown(text, extensions)


def pygments_style_defs(style='default'):
    """:return: the CSS definitions for the `CodeHilite`_ Markdown plugin.

    :param style: The Pygments `style`_ to use.

    Only available if `Pygments`_ is.

    .. _CodeHilite:
       http://www.freewisdom.org/projects/python-markdown/CodeHilite
    .. _Pygments: http://pygments.org/
    .. _style: http://pygments.org/docs/styles/
    """
    formatter = PygmentsHtmlFormatter(style=style)
    return formatter.get_style_defs('.codehilite')


class Page(object):
    """Simple class to store all necessary information about flatpage.

    Main purpose to render pages content with ``html_renderer`` function.
    """
    def __init__(self, path, meta_yaml, body, html_renderer):
        """
        Initialize Page instance.

        :param path: Page path.
        :param meta_yaml: Page meta data in YAML format.
        :param body: Page body.
        :param html_renderer: HTML renderer function.
        """
        #: Path this pages was obtained from, as in ``pages.get(path)``.
        self.path = path
        #: Content of the pages.
        self._meta_yaml = meta_yaml
        self.body = body
        self.html_renderer = html_renderer

    def __getitem__(self, name):
        """Shortcut for accessing metadata.

        ``page['title']`` or, in a template, ``{{ page.title }}`` are
        equivalent to ``page.meta['title']``.
        """
        return self.meta[name]

    def __html__(self):
        """In a template, ``{{ page }}`` is equivalent to
        ``{{ page.html|safe }}``.
        """
        return self.html

    def __repr__(self):
        """Machine representation of :class:`Page` instance.
        """
        return '<Page %r>' % self.path

    @werkzeug.cached_property
    def html(self):
        """The content of the page, rendered as HTML by the configured
        renderer.
        """
        return self.html_renderer(self.body)

    @werkzeug.cached_property
    def meta(self):
        """A dict of metadata parsed as YAML from the header of the file.
        """
        meta = yaml.safe_load(self._meta_yaml)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        if not isinstance(meta, dict):
            raise ValueError(
                "Excpected a dict in metadata for '%s', got %s" %
                (self.path, type(meta).__name__)
            )
        return meta


class FlatPages(object):
    """A collections of :class:`Page` objects.
    """
    #: Default configuration for FlatPages extension
    default_config = (
        ('root', 'pages'),
        ('extension', '.html'),
        ('encoding', 'utf-8'),
        ('html_renderer', pygmented_markdown),
        ('markdown_extensions', ['codehilite']),
        ('auto_reload', 'if debug'),
    )

    def __init__(self, app=None):
        """Initialize FlatPages extension.

        :param app: your application. Can be omited if you call
                    :meth:`init_app` later.
        :type app: Flask instance
        """
        #: dict of filename: (page object, mtime when loaded)
        self._file_cache = {}

        if app:
            self.init_app(app)

    def __iter__(self):
        """Iterate on all :class:`Page` objects.
        """
        return self._pages.itervalues()

    def init_app(self, app):
        """Used to initialize an application, useful for passing an app later
        and app factory patterns.

        :param app: your application
        :type app: Flask instance
        """
        # Store default config to application
        for key, value in self.default_config:
            config_key = 'FLATPAGES_%s' % key.upper()
            app.config.setdefault(config_key, value)

        # Register function to forget all pages if necessary
        app.before_request(self._conditional_auto_reset)

        # And finally store application to current instance
        self.app = app

    def config(self, key):
        """Read actual configuration from Flask application config.

        :param key: Lowercase config key from :attr:`default_config` tuple
        """
        return self.app.config['FLATPAGES_%s' % key.upper()]

    def get(self, path, default=None):
        """Returns the :class:`Page` object at ``path``, or ``default`` if
        there is no such page.
        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            return pages[path]
        except KeyError:
            return default

    def get_or_404(self, path):
        """Returns the :class:`Page` object at ``path``, or raise Flask's
        404 error if there is no such page.
        """
        page = self.get(path)
        if not page:
            flask.abort(404)
        return page

    def reload(self):
        """Forget all pages.

        All pages will be reloaded next time they're accessed.
        """
        try:
            # This will "unshadow" the cached_property.
            # The property will be re-executed on next access.
            del self.__dict__['_pages']
        except KeyError:
            pass

    @property
    def root(self):
        """Full path to the directory where pages are looked for.

        It is the `FLATPAGES_ROOT` config value, interpreted as relative to
        the app root directory.
        """
        return os.path.join(self.app.root_path, self.config('root'))

    def _conditional_auto_reset(self):
        """Reset if configured to do so on new requests.
        """
        auto = self.config('auto_reload')
        if auto == 'if debug':
            auto = self.app.debug
        if auto:
            self.reload()

    def _load_file(self, path, filename):
        """Load file from file system and put it to cached dict as
        :class:`Path` and `mtime` tuple.
        """
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)
        if cached and cached[1] == mtime:
            page = cached[0]
        else:
            with open(filename) as fd:
                content = fd.read().decode(self.config('encoding'))
            page = self._parse(content, path)
            self._file_cache[filename] = page, mtime
        return page

    @werkzeug.cached_property
    def _pages(self):
        """Walk the page root directory an return a dict of unicode path:
        page object.
        """
        def _walk(directory, path_prefix=()):
            """Walk over directory and find all possible flatpages, files which
            ended with ``FLATPAGES_EXTENSION`` value.
            """
            for name in os.listdir(directory):
                full_name = os.path.join(directory, name)

                if os.path.isdir(full_name):
                    _walk(full_name, path_prefix + (name,))
                elif name.endswith(extension):
                    name_without_extension = name[:-len(extension)]
                    path = u'/'.join(path_prefix + (name_without_extension, ))
                    pages[path] = self._load_file(path, full_name)

        extension = self.config('extension')
        pages = {}

        # Fail if the root is a non-ASCII byte string. Use Unicode.
        _walk(unicode(self.root))

        return pages

    def _parse(self, string, path):
        """Parse flatpage file with reading meta data and body from it.

        :return: initialized :class:`Page` instance.
        """
        lines = iter(string.split(u'\n'))
        # Read lines until an empty line is encountered.
        meta = u'\n'.join(itertools.takewhile(unicode.strip, lines))
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = u'\n'.join(lines)

        html_renderer = self.config('html_renderer')

        if not callable(html_renderer):
            html_renderer = werkzeug.import_string(html_renderer)

        html_renderer = self._smart_html_renderer(html_renderer)
        return Page(path, meta, content, html_renderer)

    def _smart_html_renderer(self, html_renderer):
        """As of 0.4 version we support passing :class:`FlatPages` instance to
        HTML renderer function.

        So we need to inspect function args spec and if it supports two
        arguments, pass ``self`` instance there.

        .. versionadded:: 0.4
        """
        def wrapper(body):
            """Simple wrapper to inspect HTML renderer function and if it has
            two arguments and second argument named ``extensions``, pass
            ``FLATPAGES_MARKDOWN_EXTENSIONS`` as second argument to function.
            """
            try:
                spec = inspect.getargspec(html_renderer)
            except TypeError:
                return html_renderer(body)

            # Named tuple available only in Python 2.6+, before raw tuple used
            spec_args = spec[0] if not hasattr(spec, 'args') else spec.args

            if len(spec_args) == 1:
                return html_renderer(body)
            elif len(spec_args) == 2:
                return html_renderer(body, self)

            raise ValueError(
                'HTML renderer function {!r} not supported by Flask-FlatPages,'
                ' wrong number of arguments.'.format(html_renderer)
            )
        return wrapper
