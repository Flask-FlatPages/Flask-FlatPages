"""Flatpages extension."""
import operator
import os
from itertools import takewhile


import six
from flask import abort
from werkzeug.utils import cached_property, import_string
from yaml import (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    DocumentEndToken,
    DocumentStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
    KeyToken,
    SafeLoader,
    ScalarToken
)


from .page import Page
from .utils import force_unicode, pygmented_markdown


if six.PY3:
    from inspect import getfullargspec
    from io import StringIO
else:
    from inspect import getargspec as getfullargspec
    from StringIO import StringIO


START_TOKENS = (BlockMappingStartToken, BlockSequenceStartToken,
                DocumentStartToken, FlowMappingStartToken,
                FlowSequenceStartToken, KeyToken)


def _check_newline_token(token):
    return (
        isinstance(token, ScalarToken) and
        token.style is None and
        '\n' in token.value
    )


def _check_continue_parsing_tokens(token):
    return not (
        isinstance(
            token,
            (DocumentStartToken, DocumentEndToken)
        ) or token is None
    )


class FlatPages(object):
    """A collection of :class:`Page` objects."""

    #: Default configuration for FlatPages extension
    default_config = (
        ('root', 'pages'),
        ('extension', '.html'),
        ('encoding', 'utf-8'),
        ('html_renderer', pygmented_markdown),
        ('markdown_extensions', ['codehilite']),
        ('extension_configs', {}),
        ('auto_reload', 'if debug'),
        ('case_insensitive', False),
        ('instance_relative', False),
        ('legacy_meta_parser', False),
    )

    def __init__(self, app=None, name=None):
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

        if app:
            self.init_app(app)

    def __iter__(self):
        """Iterate on all :class:`Page` objects."""
        return six.itervalues(self._pages)

    def config(self, key):
        """Read actual configuration from Flask application config.

        :param key: Lowercase config key from :attr:`default_config` tuple
        """
        return self.app.config['_'.join((self.config_prefix, key.upper()))]

    def get(self, path, default=None):
        """
        Return the :class:`Page` object at ``path``.

        Returns ``default`` if there is no such page.
        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            return pages[path]
        except KeyError:
            return default

    def get_or_404(self, path):
        """
        Return the :class:`Page` object at ``path``.

        Raise Flask's 404 error if there is no such page.
        """
        page = self.get(path)
        if not page:
            abort(404)
        return page

    def init_app(self, app):
        """
        Use to initialize an application.

        Ueful for passing an app later and app factory patterns.

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

        This corresponds to the `FLATPAGES_%(name)s_ROOT` config value,
        interpreted as relative to the app's root directory, or as relative
        to the app's instance folder if `FLATPAGES_%(name)s_INSTANCE_RELATIVE`
        is set to `True`.

        """
        if self.config('instance_relative'):
            root_dir = os.path.join(self.app.instance_path,
                                    self.config('root'))
        else:
            root_dir = os.path.join(self.app.root_path, self.config('root'))
        return force_unicode(root_dir)

    def _conditional_auto_reset(self):
        """Reset if configured to do so on new requests."""
        auto = self.config('auto_reload')
        if auto == 'if debug':
            auto = self.app.debug
        if auto:
            self.reload()

    def _load_file(self, path, filename, rel_path):
        """
        Load file from file system and cache it.

        We store the result as a tuple of :class:`Path` and the file `mtime`.
        """
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)

        if cached and cached[1] == mtime:
            page = cached[0]
        else:
            encoding = self.config('encoding')

            if six.PY3:
                with open(filename, encoding=encoding) as handler:
                    content = handler.read()
            else:
                with open(filename) as handler:
                    content = handler.read().decode(encoding)

            page = self._parse(content, path, rel_path)
            self._file_cache[filename] = (page, mtime)

        return page

    @cached_property
    def _pages(self):
        """
        Walk the page root directory and return a dict of pages.

        Returns a dictionary of pages keyed by their path.
        """
        def _walker():
            """
            Walk over directory and find all possible flatpages.

            Returns files which end with the string or sequence given by
            ``FLATPAGES_%(name)s_EXTENSION``.
            """
            for cur_path, _, filenames in os.walk(self.root):
                rel_path = cur_path.replace(self.root, '').lstrip(os.sep)
                path_prefix = tuple(rel_path.split(os.sep)) if rel_path else ()

                for name in filenames:
                    if not name.endswith(extension):
                        continue

                    full_name = os.path.join(cur_path, name)
                    name_without_extension = [name[:-len(item)]
                                              for item in extension
                                              if name.endswith(item)][0]
                    path = u'/'.join(path_prefix + (name_without_extension, ))
                    if self.config('case_insensitive'):
                        path = path.lower()
                    yield (path, full_name, rel_path)

        # Read extension from config
        extension = self.config('extension')

        # Support for multiple extensions
        if isinstance(extension, six.string_types):
            if ',' in extension:
                extension = tuple(extension.split(','))
            else:
                extension = (extension, )
        elif isinstance(extension, (list, set)):
            extension = tuple(extension)

        # FlatPage extension should be a string or a sequence
        if not isinstance(extension, tuple):
            raise ValueError(
                'Invalid value for FlatPages extension. Should be a string or '
                'a sequence, got {0} instead: {1}'.
                format(type(extension).__name__, extension)
            )
        pages = {}
        for path, full_name, rel_path in _walker():
            if path in pages:
                raise ValueError(
                    'Multiple pages found which correspond to the same path. '
                    'This error can arise when using multiple extensions.')
            pages[path] = self._load_file(path, full_name, rel_path)
        return pages

    def _libyaml_parser(self, content):
        if not six.PY3:
            content = force_unicode(content)
        yaml_loader = SafeLoader(StringIO(content))
        yaml_loader.get_token()  # Get stream start token
        token = yaml_loader.get_token()
        if not isinstance(token, START_TOKENS):
            meta = ''
            content = content.lstrip('\n')
        else:
            lines = content.split('\n')
            if isinstance(token, DocumentStartToken):
                token = yaml_loader.get_token()
            newline_token = None
            while _check_continue_parsing_tokens(token):
                try:
                    token = yaml_loader.get_token()
                    if (
                        _check_newline_token(token) and
                        newline_token is None
                    ):
                        newline_token = token
                except Exception:
                    break
            if token is None and newline_token is None:
                meta = content
                content = ''
            else:
                if token is not None:
                    meta_end_line = token.end_mark.line + 1
                else:
                    meta_end_line = newline_token.start_mark.line
                    meta_end_line += lines[meta_end_line:].index('')
                meta = '\n'.join(lines[:meta_end_line])
                content = '\n'.join(lines[meta_end_line:]).lstrip('\n')
        if not six.PY3:
            return force_unicode(meta), force_unicode(content)
        return meta, content

    def _legacy_parser(self, content):
        lines = iter(content.split('\n'))

        # Read lines until an empty line is encountered.
        meta = '\n'.join(takewhile(operator.methodcaller('strip'), lines))
        # The rest is the content. `lines` is an iterator so it continues
        # where `itertools.takewhile` left it.
        content = '\n'.join(lines)
        return meta, content

    def _parse(self, content, path, rel_path):
        """Parse a flatpage file, i.e. read and parse its meta data and body.

        :return: initialized :class:`Page` instance.
        """
        if self.config('legacy_meta_parser'):
            meta, content = self._legacy_parser(content)
        else:
            meta, content = self._libyaml_parser(content)

        # Now we ready to get HTML renderer function
        html_renderer = self.config('html_renderer')

        # If function is not callable yet, import it
        if not callable(html_renderer):
            html_renderer = import_string(html_renderer)

        # Make able to pass custom arguments to renderer function
        html_renderer = self._smart_html_renderer(html_renderer)

        # Assign the relative path (to root) for use in the page object
        folder = rel_path

        # Initialize and return Page instance
        return Page(path, meta, content, html_renderer, folder)

    def _smart_html_renderer(self, html_renderer):
        """
        Wrappper to enable  rendering functions with differing signatures.

        We stay backwards compatible by using reflection, i.e. we inspect the
        given rendering function's signature in order to find out how many
        arguments the function takes.

        .. versionchanged:: 0.6

           Support for HTML renderer functions with signature
           ``f(body, flatpages, page)``, where ``page`` is an instance of
           :class:`Page`.

        .. versionchanged:: 0.5

           Support for HTML renderer functions with signature
           ``f(body, flatpages)``, where ``flatpages`` is an instance of
           :class:`FlatPages`.

        """
        def wrapper(page):
            """Wrap HTML renderer function.

            Pass arguments to the renderer based on the number of arguments.

            * 1 argument -> page body
            * 2 arguments -> page body, flatpages instance
            * 3 arguments -> page body, flatpages instance, page instance
            """
            body = page.body

            try:
                args_length = len(getfullargspec(html_renderer).args)
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
