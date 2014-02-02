"""
=======================
flask_flatpages.imports
=======================

Conditional imports.

"""

try:
    from pygments.formatters import HtmlFormatter as PygmentsHtmlFormatter
except ImportError:
    PygmentsHtmlFormatter = None
