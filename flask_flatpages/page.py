"""
====================
flask_flatpages.page
====================

Define flatpage instance.

"""

import operator

from itertools import takewhile

import yaml

from werkzeug.utils import cached_property


class Page(object):
    """Simple class to store all necessary information about a flatpage.

    Main purpose is to render the page's content with a ``html_renderer``
    function.
    """

    def __init__(self, name, location, html_renderer, meta='', body=None):
        """
        Initialize Page instance.

        :param path: Page path.
        :param meta: Page meta data in YAML format.
        :param body: Page body.
        :param html_renderer: HTML renderer function.
        """
        self.name = name
        self.location = location
        self._meta = meta
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
        return '<Page %r %r>' % (self.name, self.location)

    def load_content(self, content):

        lines = iter(content.split('\n'))

        meta = '\n'.join(takewhile(operator.methodcaller('strip'), lines))

        content = '\n'.join(lines)
        self._meta = meta
        self.body = content


    @cached_property
    def html(self):
        """The content of the page, rendered as HTML by the configured
        renderer.
        """
        return self.html_renderer(self)

    @cached_property
    def meta(self):
        """A dict of metadata parsed as YAML from the header of the file.
        """
        meta = yaml.safe_load(self._meta)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        if not isinstance(meta, dict):
            raise ValueError("Excpected a dict in metadata for '{0}', got {1}".
                             format(self.path, type(meta).__name__))
        return meta
