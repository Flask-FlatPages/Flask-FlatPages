"""
=====================
flask_flatpages.utils
=====================

Utility functions to render Markdown text to HTML.

"""

import markdown
from markdown.extensions import codehilite

from . import compat
from .imports import PygmentsHtmlFormatter


def force_unicode(value, encoding='utf-8', errors='strict'):
    """Convert bytes or any other Python instance to string."""
    if isinstance(value, compat.text_type):
        return value
    return value.decode(encoding, errors)


def pygmented_markdown(text, flatpages=None):
    """Render Markdown text to HTML.

    Uses the `CodeHilite`_ extension only if `Pygments`_ is available. If
    `Pygments`_ is not available, "codehilite" is removed from list of
    extensions.

    If you need other extensions, set them up using the
    ``FLATPAGES_MARKDOWN_EXTENSIONS`` setting, which should be a sequence
    of strings or Markdown Extension objects.
    Extensions specified with entrypoint strings should be configured using
    ``FLATPAGES_EXTENSION_CONFIGS``.

    .. _CodeHilite:
       http://www.freewisdom.org/projects/python-markdown/CodeHilite
    .. _Pygments: http://pygments.org/
    """
    if flatpages:
        extensions = flatpages.config('markdown_extensions')
        extension_configs = flatpages.config('extension_configs')
    else:
        extensions = []
        extension_configs = {}
    if PygmentsHtmlFormatter is None:
        original_extensions = extensions
        original_config = extension_configs
        extensions = []
        extension_configs = {}

        for extension in original_extensions:
            if (
                isinstance(extension, compat.string_types) and
                'codehilite' in extension
            ):
                continue
            elif isinstance(
                extension,
                codehilite.CodeHiliteExtension
            ):
                continue
            extensions.append(extension)
            if isinstance(extension, compat.string_types):
                extension_configs[extension] = original_config[extension]
    elif not extensions:
        extensions = ['codehilite']
    return markdown.markdown(text, extensions=extensions,
                             extension_configs=extension_configs)


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
