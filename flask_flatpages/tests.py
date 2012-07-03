# coding: utf8
"""
    Tests for Flask-FlatPages
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import unittest
import tempfile
import shutil
import os.path
import datetime
from contextlib import contextmanager

import jinja2
from werkzeug.exceptions import NotFound
from flask import Flask
from flask_flatpages import FlatPages


@contextmanager
def temp_directory():
    """This context manager gives the path to a new temporary directory that
    is deleted (with all it's content) at the end of the with block.
    """
    directory = tempfile.mkdtemp()
    try:
        yield directory
    finally:
        shutil.rmtree(directory)

@contextmanager
def temp_pages(app=None):
    """This context manager gives a FlatPages object configured
    in a temporary directory with a copy of the test pages.

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
        app.config['FLATPAGES_ROOT'] = temp
        yield FlatPages(app)


class TestTempDirectory(unittest.TestCase):
    def test_removed(self):
        with temp_directory() as temp:
            assert os.path.isdir(temp)
        # should be removed now
        assert not os.path.exists(temp)

    def test_exception(self):
        try:
            with temp_directory() as temp:
                assert os.path.isdir(temp)
                1/0
        except ZeroDivisionError:
            pass
        else:
            assert False, 'Exception did not propagate'
        assert not os.path.exists(temp)

    def test_writing(self):
        with temp_directory() as temp:
            filename = os.path.join(temp, 'foo')
            with open(filename, 'w') as fd:
                fd.write('foo')
            assert os.path.isfile(filename)
        assert not os.path.exists(temp)
        assert not os.path.exists(filename)


class TestFlatPages(unittest.TestCase):
    def test_iter(self):
        pages = FlatPages(Flask(__name__))
        self.assertEquals(
            set(page.path for page in pages),
            set(['foo', 'foo/bar', 'foo/lorem/ipsum', 'hello'])
        )

    def test_get(self):
        pages = FlatPages(Flask(__name__))
        self.assertEquals(pages.get('foo/bar').path, 'foo/bar')
        self.assertEquals(pages.get('nonexistent'), None)
        self.assertEquals(pages.get('nonexistent', 42), 42)

    def test_get_or_404(self):
        pages = FlatPages(Flask(__name__))
        self.assertEquals(pages.get_or_404('foo/bar').path, 'foo/bar')
        self.assertRaises(NotFound, pages.get_or_404, 'nonexistent')

    def test_consistency(self):
        pages = FlatPages(Flask(__name__))
        for page in pages:
            assert pages.get(page.path) is page

    def test_yaml_meta(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEquals(foo.meta, {
            'title': 'Foo > bar',
            'created': datetime.date(2010, 12, 11),
            'versions': [3.14, 42]
        })
        self.assertEquals(foo['title'], 'Foo > bar')
        self.assertEquals(foo['created'], datetime.date(2010, 12, 11))
        self.assertEquals(foo['versions'], [3.14, 42])
        self.assertRaises(KeyError, lambda: foo['nonexistent'])

    def test_markdown(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEquals(foo.body, 'Foo *bar*\n')
        self.assertEquals(foo.html, '<p>Foo <em>bar</em></p>')

    def _unicode(self, pages):
        hello = pages.get('hello')
        self.assertEquals(hello.meta, {'title': u'世界',
                                       'template': 'article.html'})
        self.assertEquals(hello['title'], u'世界')
        self.assertEquals(hello.body, u'Hello, *世界*!\n')
        # Markdow
        self.assertEquals(hello.html, u'<p>Hello, <em>世界</em>!</p>')

    def test_unicode(self):
        pages = FlatPages(Flask(__name__))
        self._unicode(pages)

    def test_other_encoding(self):
        app = Flask(__name__)
        app.config['FLATPAGES_ENCODING'] = 'shift_jis'
        app.config['FLATPAGES_ROOT'] = 'pages_shift_jis'
        pages = FlatPages(app)
        self._unicode(pages)

    def test_other_html_renderer(self):
        for renderer in (unicode.upper, 'string.upper'):
            pages = FlatPages(Flask(__name__))
            pages.app.config['FLATPAGES_HTML_RENDERER'] = renderer
            hello = pages.get('hello')
            self.assertEquals(hello.body, u'Hello, *世界*!\n')
            # Upper-case, markdown not interpreted
            self.assertEquals(hello.html, u'HELLO, *世界*!\n')

    def test_other_extension(self):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = '.txt'
        pages = FlatPages(app)
        self.assertEquals(
            set(page.path for page in pages),
            set(['not_a_page', 'foo/42/not_a_page'])
        )

    def test_lazy_loading(self):
        with temp_pages() as pages:
            bar = pages.get('foo/bar')
            # bar.html is normally empty
            self.assertEquals(bar.meta, {})
            self.assertEquals(bar.body, '')

        with temp_pages() as pages:
            filename = os.path.join(pages.root, 'foo', 'bar.html')
            # write as pages is already constructed
            with open(filename, 'a') as fd:
                fd.write('a: b\n\nc')
            bar = pages.get('foo/bar')
            # bar was just loaded from the disk
            self.assertEquals(bar.meta, {'a': 'b'})
            self.assertEquals(bar.body, 'c')

    def test_reloading(self):
        with temp_pages() as pages:
            bar = pages.get('foo/bar')
            # bar.html is normally empty
            self.assertEquals(bar.meta, {})
            self.assertEquals(bar.body, '')

            filename = os.path.join(pages.root, 'foo', 'bar.html')
            # rewrite already loaded page
            with open(filename, 'w') as fd:
                # The newline is a separator between the (empty) metadata
                # and the source 'first'
                fd.write('\nfirst rewrite')

            bar2 = pages.get('foo/bar')
            # the disk is not hit again until requested
            self.assertEquals(bar2.meta, {})
            self.assertEquals(bar2.body, '')
            self.assert_(bar2 is bar)

            # request reloading
            pages.reload()

            # write again
            with open(filename, 'w') as fd:
                fd.write('\nsecond rewrite')

            # get another page
            pages.get('hello')

            # write again
            with open(filename, 'w') as fd:
                fd.write('\nthird rewrite')

            # All pages are read at once when any is used
            bar3 = pages.get('foo/bar')
            self.assertEquals(bar3.meta, {})
            self.assertEquals(bar3.body, 'second rewrite') # not third
            # Page objects are not reused when a file is re-read.
            self.assert_(bar3 is not bar2)

            # Removing does not trigger reloading either
            os.remove(filename)

            bar4 = pages.get('foo/bar')
            self.assertEquals(bar4.meta, {})
            self.assertEquals(bar4.body, 'second rewrite')
            self.assert_(bar4 is bar3)

            pages.reload()

            bar5 = pages.get('foo/bar')
            self.assert_(bar5 is None)

    def test_caching(self):
        with temp_pages() as pages:
            foo = pages.get('foo')
            bar = pages.get('foo/bar')

            filename = os.path.join(pages.root, 'foo', 'bar.html')
            with open(filename, 'w') as fd:
                fd.write('\nrewritten')

            pages.reload()

            foo2 = pages.get('foo')
            bar2 = pages.get('foo/bar')

            # Page objects are cached and unmodified files (according to the
            # modification date) are not parsed again.
            self.assert_(foo2 is foo)
            self.assert_(bar2 is not bar)
            self.assert_(bar2.body != bar.body)

    def assert_no_auto_reset(self, pages):
        bar = pages.get('foo/bar')
        self.assertEquals(bar.body, '')

        filename = os.path.join(pages.root, 'foo', 'bar.html')
        with open(filename, 'w') as fd:
            fd.write('\nrewritten')

        # simulate a request (before_request functions are called)
        with pages.app.test_request_context():
            pages.app.preprocess_request()

        # not updated
        bar2 = pages.get('foo/bar')
        self.assertEquals(bar2.body, '')
        self.assert_(bar2 is bar)

    def assert_auto_reset(self, pages):
        bar = pages.get('foo/bar')
        self.assertEquals(bar.body, '')

        filename = os.path.join(pages.root, 'foo', 'bar.html')
        with open(filename, 'w') as fd:
            fd.write('\nrewritten')

        # simulate a request (before_request functions are called)
        # pages.reload() is not call explicitly
        with pages.app.test_request_context():
            pages.app.preprocess_request()

        # updated
        bar2 = pages.get('foo/bar')
        self.assertEquals(bar2.body, 'rewritten')
        self.assert_(bar2 is not bar)

    def test_default_no_auto_reset(self):
        with temp_pages() as pages:
            self.assert_no_auto_reset(pages)

    def test_debug_auto_reset(self):
        app = Flask(__name__)
        app.debug = True
        with temp_pages(app) as pages:
            self.assert_auto_reset(pages)

    def test_configured_no_auto_reset(self):
        app = Flask(__name__)
        app.debug = True
        app.config['FLATPAGES_AUTO_RELOAD'] = False
        with temp_pages(app) as pages:
            self.assert_no_auto_reset(pages)

    def test_configured_auto_reset(self):
        app = Flask(__name__)
        app.config['FLATPAGES_AUTO_RELOAD'] = True
        with temp_pages(app) as pages:
            self.assert_auto_reset(pages)


if __name__ == '__main__':
    unittest.main()
