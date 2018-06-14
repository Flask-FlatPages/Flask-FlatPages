"""
====================
flask_flatpages.page
====================

Define flatpage instance.

"""

import yaml

from werkzeug.utils import cached_property


class Page(object):

    """Simple class to store all necessary information about a flatpage.

    Main purpose is to render the page's content with a ``html_renderer``
    function.
    """

    def __init__(self, path, meta, body, html_renderer):
        """Initialize Page instance.

        :param path: Page path.
        :param meta: Page meta data in YAML format.
        :param body: Page body.
        :param html_renderer: HTML renderer function.
        """
        #: Path this page was obtained from, as in ``pages.get(path)``
        self.path = path
        #: Content of the page
        self._meta = meta
        self.body = body
        #: Renderer function
        self.html_renderer = html_renderer

    def __getitem__(self, name):
        """Shortcut for accessing metadata.

        ``page['title']`` or, in a template, ``{{ page.title }}`` are
        equivalent to ``page.meta['title']``.
        """
        return self.meta[name]

    def __html__(self):
        """
        In a template, ``{{ page }}`` is equivalent to
        ``{{ page.html|safe }}``.
        """
        return self.html

    def __repr__(self):
        """Machine representation of :class:`Page` instance."""
        return '<Page %r>' % self.path

    @cached_property
    def html(self):
        """Content of the page, rendered as HTML by the configured renderer."""
        return self.html_renderer(self)

    @cached_property
    def meta(self):
        """A dict of metadata parsed as YAML from the header of the file."""
        meta = yaml.safe_load_all(self._meta)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']

        meta_list = list(meta)
        meta_dict = dict(meta_list[0])

        if not meta_dict:
            return {}
        if not isinstance(meta_dict, dict):
            raise ValueError("Expected a dict in metadata for '{0}', got {1}".
                             format(self.path, type(meta_dict).__name__))
        return meta_dict
