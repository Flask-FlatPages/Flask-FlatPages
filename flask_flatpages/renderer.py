from inspect import getargspec
from werkzeug.utils import import_string

def smart_html_renderer(html_renderer, extensions=[]):
    if not callable(html_renderer):
        html_renderer = import_string(html_renderer)

    def wrapper(page):
        body = page.body

        try:
            args_length = len(getargspec(html_renderer).args)
        except TypeError:
            return html_renderer(body)

        if args_length == 1:
            return html_renderer(body)
        elif args_length == 2:
            return html_renderer(body, extensions)
        elif args_length == 3:
            return html_renderer(body, extensions, page)

        raise ValueError(
            'HTML renderer function {0!r} not supported by '
            'Flask-FlatPages, wrong number of arguments: {1}.'.
            format(html_renderer, args_length)
        )
        return wrapper
    return wrapper