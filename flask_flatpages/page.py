"""Define flatpage instance."""

from __future__ import annotations
from functools import cached_property
from io import StringIO
from typing import Any

import yaml

from .utils import WrappedRenderer


class Page:
    """Simple class to store all necessary information about a flatpage.

    Main purpose is to render the page's content with a ``html_renderer``
    function.
    """

    def __init__(
        self,
        path: str,
        meta: str,
        body: str,
        html_renderer: WrappedRenderer["Page"],
        folder: str,
    ):
        """Initialize Page instance.

        :param path: Page path.
        :param meta: Page meta data in YAML format.
        :param body: Page body.
        :param html_renderer: HTML renderer function.
        :param folder: The folder the page is contained in.
        """
        #: Path this page was obtained from, as in ``pages.get(path)``
        self.path = path
        #: Content of the page
        self._meta = meta
        self.body = body
        #: Renderer function
        self.html_renderer = html_renderer
        #: The name of the folder the page is contained in.
        self.folder = folder

    def __getitem__(self, name: str):
        """Shortcut for accessing metadata.

        ``page['title']`` or, in a template, ``{{ page.title }}`` are
        equivalent to ``page.meta['title']``.
        """
        return self.meta[name]

    def __html__(self) -> str:
        """
        Return HTML for use in Jinja templates.

        In a template, ``{{ page }}`` is equivalent to
        ``{{ page.html|safe }}``.
        """
        return self.html

    def __repr__(self) -> str:
        """Machine representation of :class:`Page` instance."""
        return f"<Page {self.path}>"

    @cached_property
    def html(self) -> str:
        """Content of the page, rendered as HTML by the configured renderer."""
        return self.html_renderer(self)

    @cached_property
    def meta(self) -> dict[str, Any]:
        """Store a dict of metadata parsed from the YAML header of the file."""
        meta = {}
        for doc in yaml.safe_load_all(StringIO(self._meta)):
            if doc is not None:
                meta.update(doc)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        if not isinstance(meta, dict):
            raise ValueError(
                "Expected a dict in metadata for '{0}', got {1}".format(
                    self.path, type(meta).__name__
                )
            )
        return meta
