# coding: utf8
"""
    Tests for Flask-FlatPages
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2010 by Simon Sapin.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import with_statement

import datetime
import os
import shutil
import sys
import tempfile
import unicodedata
import unittest



from contextlib import contextmanager

import jinja2

from flask import Flask
from flask_flatpages import FlatPages, pygments_style_defs
from werkzeug.exceptions import NotFound



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
    def test_pygments_style_defs(self):
        styles = pygments_style_defs()
        self.assertTrue(styles.startswith('.codehilite'))

    def test_iter(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(
            set(page.path for page in pages),
            set(['foo', 'foo/bar', 'foo/lorem/ipsum', 'headerid', 'hello'])
        )

    def test_get(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(pages.get('foo/bar').path, 'foo/bar')
        self.assertEqual(pages.get('nonexistent'), None)
        self.assertEqual(pages.get('nonexistent', 42), 42)

    def test_get_or_404(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(pages.get_or_404('foo/bar').path, 'foo/bar')
        self.assertRaises(NotFound, pages.get_or_404, 'nonexistent')

    def test_consistency(self):
        pages = FlatPages(Flask(__name__))
        for page in pages:
            assert pages.get(page.path) is page

    def test_yaml_meta(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEqual(foo.meta, {
            'title': 'Foo > bar',
            'created': datetime.date(2010, 12, 11),
            'versions': [3.14, 42]
        })
        self.assertEqual(foo['title'], 'Foo > bar')
        self.assertEqual(foo['created'], datetime.date(2010, 12, 11))
        self.assertEqual(foo['versions'], [3.14, 42])
        self.assertRaises(KeyError, lambda: foo['nonexistent'])

    def test_markdown(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEqual(foo.body, 'Foo *bar*\n')
        self.assertEqual(foo.html, '<p>Foo <em>bar</em></p>')

    def _unicode(self, pages):
        hello = pages.get('hello')
        self.assertEqual(hello.meta, {'title': u'世界',
                                       'template': 'article.html'})
        self.assertEqual(hello['title'], u'世界')
        self.assertEqual(hello.body, u'Hello, *世界*!\n')
        # Markdow
        self.assertEqual(hello.html, u'<p>Hello, <em>世界</em>!</p>')

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
        def hello_renderer(body, pages):
            return pages.get('hello').body.upper()

        if sys.version < '3':
            renderers = (unicode.upper, 'string.upper', hello_renderer)
        else:
            renderers = (str.upper, hello_renderer)
        
        for renderer in (renderers):
            pages = FlatPages(Flask(__name__))
            pages.app.config['FLATPAGES_HTML_RENDERER'] = renderer
            hello = pages.get('hello')
            self.assertEqual(hello.body, u'Hello, *世界*!\n')
            # Upper-case, markdown not interpreted
            self.assertEqual(hello.html, u'HELLO, *世界*!\n')
    
    def test_markdown_extensions(self):
        pages = FlatPages(Flask(__name__))

        hello = pages.get('headerid')
        self.assertEqual(
            hello.html,
            u'<h1>Page Header</h1>\n<h2>Paragraph Header</h2>\n<p>Text</p>'
        )

        pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = []
        pages.reload()
        pages._file_cache = {}

        hello = pages.get('headerid')
        self.assertEqual(
            hello.html,
            u'<h1>Page Header</h1>\n<h2>Paragraph Header</h2>\n<p>Text</p>'
        )

        pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite', 'headerid'
        ]
        pages.reload()
        pages._file_cache = {}

        hello = pages.get('headerid')
        self.assertEqual(
            hello.html,
            u'<h1 id="page-header">Page Header</h1>\n'
            u'<h2 id="paragraph-header">Paragraph Header</h2>\n'
            u'<p>Text</p>'
        )

    def test_other_extension(self):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = '.txt'
        pages = FlatPages(app)
        self.assertEqual(
            set(page.path for page in pages),
            set(['not_a_page', 'foo/42/not_a_page'])
        )

    def test_lazy_loading(self):
        with temp_pages() as pages:
            bar = pages.get('foo/bar')
            # bar.html is normally empty
            self.assertEqual(bar.meta, {})
            self.assertEqual(bar.body, '')

        with temp_pages() as pages:
            filename = os.path.join(pages.root, 'foo', 'bar.html')
            # write as pages is already constructed
            with open(filename, 'a') as fd:
                fd.write('a: b\n\nc')
            bar = pages.get('foo/bar')
            # bar was just loaded from the disk
            self.assertEqual(bar.meta, {'a': 'b'})
            self.assertEqual(bar.body, 'c')

    def test_reloading(self):
        with temp_pages() as pages:
            bar = pages.get('foo/bar')
            # bar.html is normally empty
            self.assertEqual(bar.meta, {})
            self.assertEqual(bar.body, '')

            filename = os.path.join(pages.root, 'foo', 'bar.html')
            # rewrite already loaded page
            with open(filename, 'w') as fd:
                # The newline is a separator between the (empty) metadata
                # and the source 'first'
                fd.write('\nfirst rewrite')

            bar2 = pages.get('foo/bar')
            # the disk is not hit again until requested
            self.assertEqual(bar2.meta, {})
            self.assertEqual(bar2.body, '')
            self.assertTrue(bar2 is bar)

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
            self.assertEqual(bar3.meta, {})
            self.assertEqual(bar3.body, 'second rewrite')  # not third
            # Page objects are not reused when a file is re-read.
            self.assertTrue(bar3 is not bar2)

            # Removing does not trigger reloading either
            os.remove(filename)

            bar4 = pages.get('foo/bar')
            self.assertEqual(bar4.meta, {})
            self.assertEqual(bar4.body, 'second rewrite')
            self.assertTrue(bar4 is bar3)

            pages.reload()

            bar5 = pages.get('foo/bar')
            self.assertTrue(bar5 is None)

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
            self.assertTrue(foo2 is foo)
            self.assertTrue(bar2 is not bar)
            self.assertTrue(bar2.body != bar.body)

    def assert_no_auto_reset(self, pages):
        bar = pages.get('foo/bar')
        self.assertEqual(bar.body, '')

        filename = os.path.join(pages.root, 'foo', 'bar.html')
        with open(filename, 'w') as fd:
            fd.write('\nrewritten')

        # simulate a request (before_request functions are called)
        with pages.app.test_request_context():
            pages.app.preprocess_request()

        # not updated
        bar2 = pages.get('foo/bar')
        self.assertEqual(bar2.body, '')
        self.assertTrue(bar2 is bar)

    def assert_auto_reset(self, pages):
        bar = pages.get('foo/bar')
        self.assertEqual(bar.body, '')

        filename = os.path.join(pages.root, 'foo', 'bar.html')
        with open(filename, 'w') as fd:
            fd.write('\nrewritten')

        # simulate a request (before_request functions are called)
        # pages.reload() is not call explicitly
        with pages.app.test_request_context():
            pages.app.preprocess_request()

        # updated
        bar2 = pages.get('foo/bar')
        self.assertEqual(bar2.body, 'rewritten')
        self.assertTrue(bar2 is not bar)

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

    def test_unicode_filenames(self):
        def safe_unicode(sequence):
            if sys.platform != 'darwin':
                return sequence
            return map(lambda item: unicodedata.normalize('NFC', item),
                       sequence)

        app = Flask(__name__)
        with temp_pages(app) as pages:
            self.assertEqual(
                set(p.path for p in pages),
                set(['foo/bar',
                     'foo/lorem/ipsum',
                     'foo',
                     'headerid',
                     'hello']))
            os.remove(os.path.join(pages.root, 'foo', 'lorem', 'ipsum.html'))
            open(os.path.join(pages.root, u'Unïcôdé.html'), 'w').close()
            pages.reload()
            self.assertEqual(
                set(safe_unicode(p.path for p in pages)),
                set(['foo/bar', 'foo', 'headerid', 'hello', u'Unïcôdé']))


if __name__ == '__main__':
    unittest.main()
