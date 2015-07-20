# coding: utf8
"""
    Tests for Flask-FlatPages
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

import datetime
import operator
import os
import shutil
import sys
import time
import unicodedata
import unittest

from contextlib import contextmanager

from pathlib import Path

from flask import Flask
from flask.ext.flatpages import FlatPages, Page, compat, pygments_style_defs
from werkzeug.exceptions import NotFound

from .test_temp_directory import temp_directory


@contextmanager
def temp_pages(app=None, name=None):
    """
    This context manager gives a FlatPages object configured in a temporary
    directory with a copy of the test pages.

    Using a temporary copy allows us to safely write and remove stuff without
    worrying about undoing our changes.
    """
    with temp_directory() as temp:
        source = os.path.join(os.path.dirname(__file__), 'pages')
        # Remove the destination dir as copytree wants it not to exist.
        # Doing so kind of defeats the purpose of tempfile as it introduces
        # a race condition, but should be good enough for our purpose.
        os.rmdir(temp)
        shutil.copytree(source, temp)
        app = app or Flask(__name__)
        if name is None:
            config_root = 'FLATPAGES_ROOT'
        else:
            config_root = 'FLATPAGES_%s_ROOT' % str(name).upper()
        app.config[config_root] = temp
        yield FlatPages(app, name)


class TestCaches(unittest.TestCase):
    def setUp(self):
        self.cache_types = ['file', 'sqlite']

    def tearDown(self):
        pass

    def test_cache_creation(self):
        with temp_directory() as temp:
            for cache_type in self.cache_types:
                app = Flask(__name__)
                app.config['FLATPAGES_ROOT'] = os.path.join(temp, 'tmpcache')
                app.config['FLATPAGES_CACHETYPE'] = cache_type

                pages = FlatPages(app)
                cache_path = pages._cache._root
                self.assertTrue(cache_path.exists())
                self.assertTrue('tmpcache' in cache_path.parts)

    def test_load_page(self):
        for cache_type in self.cache_types:
            app = Flask(__name__)
            app.config['FLATPAGES_CACHETYPE'] = cache_type
            with temp_pages(app=app) as pages:

                files_dir = Path(pages.root).absolute()
                for path in files_dir.glob('**/*.html'):
                    rel_path = path.relative_to(files_dir)
                    name = '/'.join(rel_path.parts)
                    name = name[:-len('.html')]
                    page = pages.get(name)
                    self.assertTrue(page is not None)


    def test_delete_page(self):
        for cache_type in self.cache_types:
            app = Flask(__name__)
            app.config['FLATPAGES_CACHETYPE'] = cache_type
            with temp_pages(app=app) as pages:

                files_dir = Path(pages.root).absolute()
                for path in files_dir.glob('**/*.html'):
                    rel_path = path.relative_to(files_dir)
                    name = '/'.join(rel_path.parts)
                    name = name[:-len('.html')]
                    page = pages.get(name)
                    self.assertTrue(page is not None)
                    pages.delete_page(page)
                    page = pages.get(name)
                    self.assertTrue(page is None)

    def test_store_simple_page(self):
        with temp_directory() as temp:
            for cache_type in self.cache_types:
                app = Flask(__name__)
                app.config['FLATPAGES_ROOT'] = os.path.join(temp, 'tmpcache')
                app.config['FLATPAGES_CACHETYPE'] = cache_type

                pages = FlatPages(app)

                path = u'my-new-page'
                page = Page(path, html_renderer=pages.html_renderer)

                content = 'foo: bar\n\n## TestPage\n lorem ipsum'

                page.load_content(content)
                pages.store_page(page)

                page = pages.get(u'my-new-page')
                self.assertTrue(page is not None)

    def test_store_overwrite_page(self):
        with temp_directory() as temp:
            for cache_type in self.cache_types:
                app = Flask(__name__)
                app.config['FLATPAGES_ROOT'] = os.path.join(temp, 'tmpcache')
                app.config['FLATPAGES_CACHETYPE'] = cache_type

                pages = FlatPages(app)

                path = u'overwrite'
                page = Page(path, html_renderer=pages.html_renderer)

                content = 'foo: bar\n\n## TestPage\n lorem ipsum'

                page.load_content(content)
                pages.store_page(page)

                p1 = pages.get(u'overwrite')

                time.sleep(1)
                content = ''
                page.load_content(content)
                pages.store_page(page)

                p2 = pages.get(u'overwrite')
                self.assertTrue(p1.body != p2.body)
                self.assertTrue(p2.body == content)

    def test_store_unicode_page(self):
        with temp_directory() as temp:
            for cache_type in self.cache_types:
                app = Flask(__name__)
                app.config['FLATPAGES_ROOT'] = os.path.join(temp, 'tmpcache')
                app.config['FLATPAGES_CACHETYPE'] = cache_type

                pages = FlatPages(app)
                path = u'Unïcôdé'
                page = Page(path, html_renderer=pages.html_renderer)

                content = u'foo: bar\n\n## TestPage\n lorem ipsum'

                page.load_content(content)
                pages.store_page(page)

                path = unicodedata.normalize('NFC', u'Unïcôdé')
                p1 = pages.get(path)

                self.assertTrue(p1 is not None)
                self.assertTrue(p1.body == '## TestPage\n lorem ipsum')
