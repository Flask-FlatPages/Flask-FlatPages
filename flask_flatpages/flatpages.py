"""
=========================
flask_flatpages.flatpages
=========================

Flatpages extension.

"""

import operator
import os

from inspect import getargspec
from itertools import takewhile

from flask import abort
from werkzeug.utils import cached_property, import_string

from . import compat
from .page import Page
from .utils import force_unicode, pygmented_markdown


class FlatPages(object):
    """A collection of :class:`Page` objects.
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

        :param app: Your application. Can be omited if you call
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
        return compat.itervalues(self._pages)

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
            abort(404)
        return page

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

        # And finally store application to current instance and current
        # instance to application
        app.extensions['flatpages'] = self
        self.app = app

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
        root_dir = os.path.join(self.app.root_path, self.config('root'))
        return force_unicode(root_dir)

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
            encoding = self.config('encoding')

            if compat.IS_PY3:
                with open(filename, encoding=encoding) as handler:
                    content = handler.read()
            else:
                with open(filename) as handler:
                    content = handler.read().decode(encoding)

            page = self._parse(content, path)
            self._file_cache[filename] = (page, mtime)

        return page

    @cached_property
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

        _walk(self.root)
        return pages

    def _parse(self, content, path):
        """Parse flatpage file with reading meta data and body from it.

        :return: initialized :class:`Page` instance.
        """
        lines = iter(content.split('\n'))

        # Read lines until an empty line is encountered.
        meta = '\n'.join(takewhile(operator.methodcaller('strip'), lines))
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = '\n'.join(lines)

        # Now we ready to get HTML renderer function
        html_renderer = self.config('html_renderer')

        # If function is not callable yet, import it
        if not callable(html_renderer):
            html_renderer = import_string(html_renderer)

        # Make able to pass custom arguments to renderer function
        html_renderer = self._smart_html_renderer(html_renderer)

        # Initialize and return Page instance
        return Page(path, meta, content, html_renderer)

    def _smart_html_renderer(self, html_renderer):
        """As of 0.4 version we support passing :class:`FlatPages` instance to
        HTML renderer function.

        So we need to inspect function args spec and if it supports two
        arguments, pass ``self`` instance there.

        .. versionadded:: 0.4

        As of 0.6 version we support passing :class:`Page` instance to HTML
        renderer function too, to make more robust renderers.

        .. versionchanged:: 0.6
        """
        def wrapper(page):
            """Simple wrapper to inspect HTML renderer function and pass
            arguments to it due to args length.

            * 1 argument -> page body
            * 2 arguments -> page body, flatpages instance
            * 3 arguments -> page body, flatpages instance, page instance
            """
            body = page.body

            try:
                args_length = len(getargspec(html_renderer).args)
            except TypeError:
                return html_renderer(body)

            if args_length == 1:
                return html_renderer(body)
            elif args_length == 2:
                return html_renderer(body, self)
            elif args_length == 3:
                return html_renderer(body, self, page)

            raise ValueError(
                'HTML renderer function {0!r} not supported by '
                'Flask-FlatPages, wrong number of arguments: {1}.'.
                format(html_renderer, args_length)
            )
        return wrapper
