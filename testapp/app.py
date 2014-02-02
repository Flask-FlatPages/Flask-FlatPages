"""
===========
testapp.app
===========

Simple Flask application that shows how to use Flask-FlatPages.

"""

from flask import Flask
from flask.ext.flatpages import FlatPages


def create_app(**options):
    """
    Initialize Flask application and FlatPages extension.
    """
    app = Flask(__name__)
    app.config.update(options)

    pages = FlatPages(app)
    return (app, pages)


(app, pages) = create_app()
