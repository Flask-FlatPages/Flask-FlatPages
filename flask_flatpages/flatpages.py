"""Flatpages extension."""

from __future__ import annotations
import os
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterator
from functools import cached_property
from inspect import getfullargspec
from pathlib import Path
from typing import Any

from flask import abort, current_app, Flask
from werkzeug.utils import import_string

from .page import Page
from .parsers import legacy_parser, libyaml_parser
from .utils import (
    WrappedRenderer,
    force_unicode,
    pygmented_markdown,
)


class FlatPagesBase(ABC):
    default_config: tuple[tuple[str, Any], ...]

    def __init__(self, app: Flask | None = None, name: str | None = None):
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
            self.config_prefix = "FLATPAGES"
        else:
            self.config_prefix = "_".join(("FLATPAGES", name.upper()))

        self._root = None

        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """
        Use to initialize an application.

        Ueful for passing an app later and app factory patterns.

        :param app: your application
        :type app: a :class:`~flask.Flask` instance
        """
        # Store default config to application
        for key, value in self.default_config:
            config_key = "_".join((self.config_prefix, key.upper()))
            app.config.setdefault(config_key, value)

        # Register function to forget all pages if necessary
        app.before_request(self._conditional_auto_reset)

        # And finally store application to current instance and current
        # instance to application
        if "flatpages" not in app.extensions:
            app.extensions["flatpages"] = {}
        app.extensions["flatpages"][self.name] = self

    def config(self, key: str):
        """Read actual configuration from Flask application config.

        :param key: Lowercase config key from :attr:`default_config` tuple
        """
        return current_app.config["_".join((self.config_prefix, key.upper()))]

    def _conditional_auto_reset(self):
        """Reset if configured to do so on new requests."""
        auto = self.config("auto_reload")
        if auto == "if debug":
            auto = current_app.debug
        if auto:
            self.reload()

    @property
    def app(self) -> Flask:
        """
        The Flask Application associated with this extension.

        Accessing the application instance this way is not advised. This
        property exists to ensure backwards compatability, but is merely
        a convenience wrapper around ``current_app``.
        """
        return current_app

    @app.setter
    def app(self, app_instance: Flask):
        raise AttributeError(
            "Storing an app instance directly on an Extension is not permitted. "
            "Please see the Flask Extension Guidelines for more details."
        )

    @abstractmethod
    def _walk_pages(self) -> Generator[tuple[str, Any], None, None]: ...

    @abstractmethod
    def _load_page(self, page_path: str, page_id: Any) -> Page: ...

    @cached_property
    def _pages(self) -> dict[str, tuple[Any, Page]]:
        return {
            path: (id, self._load_page(path))
            for path, id in self._walk_pages()
        }

    def __iter__(self) -> Iterator[Page]:
        """Iterate on all :class:`Page` objects."""
        for page_path, page_data in self._pages.items():
            yield self._load_page(page_path, page_data[0])

    def reload(self):
        """Forget all pages.

        All pages will be reloaded next time they're accessed.
        """
        try:
            # This will "unshadow" the cached_property.
            # The property will be re-executed on next access.
            del self.__dict__["_pages"]
        except KeyError:
            pass

    def get(
        self, path: str, default: Page | None = None, *, reload: bool = False
    ) -> Page | None:
        """
        Return the :class:`Page` object at ``path``.

        Returns ``default`` if there is no such page.
        """
        # This may trigger the property. Do it outside of the try block.
        pages = self._pages
        try:
            page_id, page = pages[path]
            if reload:
                return self._load_page(path, page_id)
            return page
        except KeyError:
            return default

    def get_or_404(self, path: str) -> Page:
        """
        Return the :class:`Page` object at ``path``.

        Raise Flask's 404 error if there is no such page.
        """
        page = self.get(path)
        if not page:
            abort(404)
        return page

    def register_page(self, page_id: Any, path: str):
        self._pages[path] = (page_id, self._load_page(path, page_id))

    def reload_page(self, path: str) -> Page:
        page_id, _ = self._pages[path]
        page = self._load_page(path, page_id)
        self._pages[path] = (page_id, page)
        return page

    def _smart_html_renderer(self, html_renderer) -> WrappedRenderer[Page]:
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

        def wrapper(page: Page) -> str:
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
                "HTML renderer function {0!r} not supported by "
                "Flask-FlatPages, wrong number of arguments: {1}.".format(
                    html_renderer, args_length
                )
            )

        return wrapper


class FlatPages(FlatPagesBase):
    """A collection of :class:`Page` objects."""

    #: Default configuration for FlatPages extension
    default_config = (
        ("root", "pages"),
        ("extension", ".html"),
        ("encoding", "utf-8"),
        ("html_renderer", pygmented_markdown),
        ("markdown_extensions", ["codehilite"]),
        ("extension_configs", {}),
        ("auto_reload", "if debug"),
        ("case_insensitive", False),
        ("instance_relative", False),
        ("legacy_meta_parser", False),
    )

    def __init__(self, app: Flask | None = None, name: str | None = None):
        super().__init__(app, name)
        self._file_cache: dict[str, tuple[Page, float]] = {}

    @property
    def root(self) -> Path:
        """Full path to the directory where pages are looked for.

        This corresponds to the `FLATPAGES_%(name)s_ROOT` config value,
        interpreted as relative to the app's root directory, or as relative
        to the app's instance folder if `FLATPAGES_%(name)s_INSTANCE_RELATIVE`
        is set to `True`.

        """
        if self.config("instance_relative"):
            root_dir = os.path.join(
                current_app.instance_path, self.config("root")
            )
        else:
            root_dir = os.path.join(current_app.root_path, self.config("root"))
        return Path(force_unicode(root_dir))

    @cached_property
    def extensions(self) -> tuple[str]:
        extension = self.config("extension")

        # Support for multiple extensions
        if isinstance(extension, str):
            if "," in extension:
                extension = tuple(extension.split(","))
            else:
                extension = (extension,)
        elif isinstance(extension, (list, set)):
            extension = tuple(extension)

        # FlatPage extension should be a string or a sequence
        if not isinstance(extension, tuple):
            raise ValueError(
                "Invalid value for FlatPages extension. Should be a string or "
                "a sequence, got {0} instead: {1}".format(
                    type(extension).__name__, extension
                )
            )
        return extension

    @cached_property
    def _pages(self) -> dict[str, tuple[Any, Page]]:
        """
        Walk the page root directory and return a dict of pages.

        Returns a dictionary of pages keyed by their path.
        """
        pages = {}
        for path, id in self._walk_pages():
            if path in pages:
                raise ValueError(
                    "Multiple pages found which correspond to the same path. "
                    "This error can arise when using multiple extensions."
                )
            pages[path] = (id, self._load_page(path, id))
        return pages

    def _walk_pages(self) -> Generator[tuple[str, str], None, None]:
        for cur_path, _, filenames in os.walk(self.root):
            path_prefix = (self.root / cur_path).relative_to(self.root).parts

            for name in filenames:
                if not name.endswith(self.extensions):
                    continue
                name_without_extension = [
                    name[: -len(item)]
                    for item in self.extensions
                    if name.endswith(item)
                ][0]
                path = "/".join(path_prefix + (name_without_extension,))
                if self.config("case_insensitive"):
                    path = path.lower()
                yield path, str(self.root / cur_path / name)

    def _load_page(self, page_path: str, page_id: str) -> Page:
        """
        Load file from file system and cache it.

        We store the result as a tuple of :class:`Path` and the file `mtime`.
        """
        filename = page_id
        mtime = os.path.getmtime(filename)
        cached = self._file_cache.get(filename)

        if cached and cached[1] == mtime:
            page = cached[0]
        else:
            encoding = self.config("encoding")

            with open(filename, encoding=encoding) as handler:
                content = handler.read()

            page = self._parse(content, page_path)
            self._file_cache[filename] = (page, mtime)

        return page

    def _parse(self, content: str, path: str) -> Page:
        """Parse a flatpage file, i.e. read and parse its meta data and body.

        :return: initialized :class:`Page` instance.
        """
        if self.config("legacy_meta_parser"):
            meta, content = legacy_parser(content, path)
        else:
            meta, content = libyaml_parser(content, path)

        # Now we ready to get HTML renderer function
        html_renderer = self.config("html_renderer")

        # If function is not callable yet, import it
        if not callable(html_renderer):
            html_renderer = import_string(html_renderer)

        # Make able to pass custom arguments to renderer function
        html_renderer = self._smart_html_renderer(html_renderer)

        # Assign the relative path (to root) for use in the page object
        try:
            folder, _ = path.rsplit("/", maxsplit=1)
        except ValueError:
            folder = ""

        # Initialize and return Page instance
        return Page(path, meta, content, html_renderer, folder)
