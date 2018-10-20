"""
===============
flask_flatpages
===============

Flask-FlatPages provides a collection of pages to your Flask application.
Pages are built from "flat" text files as opposed to a relational database.

:copyright: (c) 2010-2015 by Simon Sapin, 2013-2015 by Igor Davydenko.
:license: BSD, see LICENSE for more details.
"""

from .flatpages import FlatPages  # noqa
from .page import Page  # noqa
from .utils import pygmented_markdown, pygments_style_defs  # noqa


__author__ = 'Simon Sapin, Igor Davydenko, Padraic Calpin'
__license__ = 'BSD License'
__version__ = '0.6.1'
