"""
====================
flask_flatpages.page
====================

Define page instance.

"""

import operator

from itertools import takewhile

import yaml

from werkzeug.utils import cached_property

from .compat import StringIO


class Page(object):

    """Simple class to store all necessary information about a flatpage.

    Main purpose is to render the page's content with a ``html_renderer``
    function.
    """

    def __init__(self, name, location=None, html_renderer=None, meta='',
                 body=None):
        """
        Initialize Page instance.
        :param name: Page name.
        :param location: Page location in the respective cache (File/DB/...).
        :param meta: Page meta data in YAML format.
        :param body: Page body.
        :param html_renderer: HTML renderer function.
        """
        self.name = name
        self.location = location
        self._meta = meta
        self.body = body
        self.html_renderer = html_renderer

    @property
    def path(self):
        """Support backwards compability to flatpages versions prior 0.8.0."""
        return self.name

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
        return u'<Page %r %r>' % (self.name, self.location)

    def load_content(self, content):
        """Add the given context to the current page and extract meta data."""
        lines = iter(content.split(u'\n'))

        meta = u'\n'.join(takewhile(operator.methodcaller('strip'), lines))

        content = u'\n'.join(lines)
        self._meta = meta
        self.body = content

    def as_buffer(self):
        """Return the page content as StringIO buffer."""
        stream = StringIO()
        if self.meta:
            yaml.dump(self.meta, stream)
            stream.write(u'\n')

        stream.write(self.body)

        return stream

    @cached_property
    def html(self):
        """Content of the page, rendered as HTML by the configured renderer."""
        return self.html_renderer(self)

    @cached_property
    def meta(self):
        """A dict of metadata parsed as YAML from the header of the file."""
        meta = yaml.safe_load(self._meta)
        # YAML documents can be any type but we want a dict
        # eg. yaml.safe_load('') -> None
        #     yaml.safe_load('- 1\n- a') -> [1, 'a']
        if not meta:
            return {}
        if not isinstance(meta, dict):
            raise ValueError(u"Excpected dict in metadata for '{0}', got {1}".
                             format(self.name, type(meta).__name__))
        return meta
