"""
====================
flask_flatpages.renderer
====================

Define a html renderer for pages.

"""

from inspect import getargspec

from werkzeug.utils import import_string


def smart_html_renderer(html_renderer, flatpages):
    """
    Wrap the rendering function in order to allow the use of rendering
    functions with differing signatures.
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
    if not callable(html_renderer):
        html_renderer = import_string(html_renderer)

    def wrapper(page):
        """
        Simple wrapper to inspect the HTML renderer function and pass
        arguments to it based on the number of arguments.
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
            return html_renderer(body, flatpages)
        elif args_length == 3:
            return html_renderer(body, flatpages, page)

        raise ValueError(
            'HTML renderer function {0!r} not supported by '
            'Flask-FlatPages, wrong number of arguments: {1}.'.
            format(html_renderer, args_length)
        )
        return wrapper
    return wrapper
