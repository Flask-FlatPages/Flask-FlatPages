"""
===============
flask_flatpages
===============

Flask-FlatPages provides a collections of pages to your Flask application.
Pages are built from "flat" text files as opposed to a relational database.

:copyright: (c) 2010-2014 by Simon Sapin, 2013-2014 by Igor Davydenko.
:license: BSD, see LICENSE for more details.
"""

from .flatpages import FlatPages  # noqa
from .page import Page  # noqa
from .utils import pygmented_markdown, pygments_style_defs  # noqa


__author__ = 'Simon Sapin'
__license__ = 'BSD License'
__version__ = '0.6-dev'
