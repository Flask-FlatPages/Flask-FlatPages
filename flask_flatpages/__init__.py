"""

Flask-FlatPages provides a collection of pages to your Flask application.

Pages are built from "flat" text files as opposed to a relational database.

:copyright: (c) 2010-2015 by Simon Sapin, 2013-2015 by Igor Davydenko.
:license: BSD, see LICENSE for more details.
"""

from .flatpages import FlatPages
from .page import Page
from .utils import pygmented_markdown, pygments_style_defs
from . import parsers

__author__ = "Simon Sapin, Igor Davydenko, Padraic Calpin"
__license__ = "BSD License"
__version__ = "0.9.0"

__all__ = ["FlatPages", "Page", "parsers", "pygmented_markdown", "pygments_style_defs"]
