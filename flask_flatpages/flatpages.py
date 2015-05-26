"""
=========================
flask_flatpages.flatpages
=========================

Flatpages extension.

"""
import os

from flask import abort
from werkzeug.utils import cached_property

from . import compat
from .cache import FileCache, SQLiteCache
from .renderer import smart_html_renderer
from .utils import force_unicode, pygmented_markdown, validate_file_extension


class FlatPages(object):

    """A collection of :class:`Page` objects."""

    #: Default configuration for FlatPages extension
    default_config = (
        ('root', 'pages'),
        ('extension', '.html'),
        ('encoding', 'utf-8'),
        ('cachetype', 'file'),
        ('html_renderer', pygmented_markdown),
        ('markdown_extensions', ['codehilite']),
        ('auto_reload', 'if debug'),
    )

    def __init__(self, app=None, name=None, cache=None):
        """Initialize FlatPages extension.

        :param app: Your application. Can be omitted if you call
                    :meth:`init_app` later.
        :type app: A :class:`~flask.Flask` instance
        :param name: The name for this FlatPages instance. Used for looking
                    up config values using
                        'FLATPAGES_%s_%s' % (name.upper(), key)
                    By default, no name is used, so configuration is
                    done by specifying config values using
                        'FLATPAGES_%s' % (key)
                    Typically, you only need to set this parameter if you
                    want to use multiple :class:`FlatPages instances within the
                    same Flask application.
        :type name: string

        .. versionchanged:: 0.6

           New parameter `name` to support multiple FlatPages instances.
        """
        self.name = name

        if name is None:
            self.config_prefix = 'FLATPAGES'
        else:
            self.config_prefix = '_'.join(('FLATPAGES', name.upper()))

        #: dict of filename: (page object, mtime when loaded)
        self._file_cache = {}
        self._cache = cache
        self._html_renderer = None

        if app:
            self.init_app(app)

    def __iter__(self):
        """Iterate on all :class:`Page` objects."""
        return compat.itervalues(self._pages)

    def config(self, key):
        """Read actual configuration from Flask application config.

        :param key: Lowercase config key from :attr:`default_config` tuple
        """
        return self.app.config['_'.join((self.config_prefix, key.upper()))]

    def get(self, path, default=None):
        """
        Return the :class:`Page` object at ``path``, or ``default`` if there is
        no such page.
        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            return pages[path]
        except KeyError:
            return default

    def get_or_404(self, path):
        """
        Return the :class:`Page` object at ``path``, or raise Flask's 404 error
        if there is no such page.
        """
        page = self.get(path)
        if not page:
            abort(404)
        return page

    def init_app(self, app):
        """
        Used to initialize an application, useful for passing an app later and
        app factory patterns.

        :param app: your application
        :type app: a :class:`~flask.Flask` instance
        """
        # Store default config to application
        for key, value in self.default_config:
            config_key = '_'.join((self.config_prefix, key.upper()))
            app.config.setdefault(config_key, value)

        # Register function to forget all pages if necessary
        app.before_request(self._conditional_auto_reset)

        # And finally store application to current instance and current
        # instance to application
        if 'flatpages' not in app.extensions:
            app.extensions['flatpages'] = {}
        app.extensions['flatpages'][self.name] = self
        self.app = app

        self._init_cache()

    def _init_cache(self):
        """Used to initialize the backend cache.

        Right now there is the option to store and load all pages from the
        filesystem or a SQLite database.
        """
        if self._cache is None:
            cache_type = self.config('cachetype')
            encoding = self.config('encoding')
            if cache_type == 'file':
                ext = validate_file_extension(self.config('extension'))
                self._cache = FileCache(self.root, ext, encoding)
            elif cache_type == 'sqlite':
                self._cache = SQLiteCache(self.root, encoding)

    def store_page(self, page):
        """Store the given page.

        The page will be saved in the configured backend cache and the _pages
        dict will be refreshed.
        """
        success = self._cache.store_page(page)
        if success:
            self.reload()

    def delete_page(self, page):
        """Delete the page from the cache.

        The page will be removed from the filesystem or database and the _pages
        dict will be refreshed.
        """
        success = self._cache.delete_page(page)
        if success:
            self.reload()

    def reload(self, deep=False):
        """Forget all pages.

        All pages will be reloaded next time they're accessed.
        """
        try:
            # This will "unshadow" the cached_property.
            # The property will be re-executed on next access.
            del self.__dict__['_pages']
            if deep:
                self._cache.empty()
        except KeyError:
            pass

    @property
    def html_renderer(self):
        """Generate a html_renderer for all pages."""
        if True:
            html_renderer = self.config('html_renderer')
            self._html_renderer = smart_html_renderer(html_renderer, self)
        return self._html_renderer

    @property
    def root(self):
        """Full path to the directory where pages are looked for.

        This corresponds to the `FLATPAGES_%(name)s_ROOT` config value,
        interpreted as relative to the app's root directory.
        """
        # force a trailing slash by adding an empty element
        root_dir = os.path.join(self.app.root_path, self.config('root'), '')
        return force_unicode(root_dir)

    def _conditional_auto_reset(self):
        """Reset if configured to do so on new requests."""
        auto = self.config('auto_reload')
        if auto == 'if debug':
            auto = self.app.debug
        if auto:
            self.reload()

    @cached_property
    def _pages(self):
        """Load all pages from the backend and save them in memory."""
        if self._cache is not None:
            return self._cache.load_pages(self.html_renderer)
