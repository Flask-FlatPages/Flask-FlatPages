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
import unicodedata
import unittest
from contextlib import contextmanager


import six
import yaml
import pytest
from flask import Flask
from flask_flatpages import FlatPages, pygments_style_defs
from flask_flatpages.imports import PygmentsHtmlFormatter
from werkzeug.exceptions import NotFound

from .test_temp_directory import temp_directory

if six.PY3:
    utc = datetime.timezone.utc
    from unittest.mock import patch
else:
    import pytz
    utc = pytz.utc
    from mock import patch


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


class TestFlatPages(unittest.TestCase):

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

    def assert_unicode(self, pages):
        hello = pages.get('hello')
        self.assertEqual(hello.meta, {'title': u'世界',
                                      'template': 'article.html'})
        self.assertEqual(hello['title'], u'世界')
        self.assertEqual(hello.body, u'Hello, *世界*!\n')
        # Markdown
        self.assertEqual(hello.html, u'<p>Hello, <em>世界</em>!</p>')

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

    def test_configured_auto_reset(self):
        app = Flask(__name__)
        app.config['FLATPAGES_AUTO_RELOAD'] = True
        with temp_pages(app) as pages:
            self.assert_auto_reset(pages)

    def test_configured_no_auto_reset(self):
        app = Flask(__name__)
        app.debug = True
        app.config['FLATPAGES_AUTO_RELOAD'] = False
        with temp_pages(app) as pages:
            self.assert_no_auto_reset(pages)

    def test_consistency(self):
        pages = FlatPages(Flask(__name__))
        for page in pages:
            assert pages.get(page.path) is page

    def test_debug_auto_reset(self):
        app = Flask(__name__)
        app.debug = True
        with temp_pages(app) as pages:
            self.assert_auto_reset(pages)

    def test_default_no_auto_reset(self):
        with temp_pages() as pages:
            self.assert_no_auto_reset(pages)

    def test_extension_comma(self):
        self.test_extension_sequence('.html,.txt')

    def test_extension_sequence(self, extension=None):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = extension or ['.html', '.txt']
        pages = FlatPages(app)
        self.assertEqual(
            set(page.path for page in pages),
            set(['codehilite',
                 'extra',
                 'foo',
                 'foo/42/not_a_page',
                 'foo/bar',
                 'foo/lorem/ipsum',
                 'headerid',
                 'hello',
                 'meta_styles/closing_block_only',
                 'meta_styles/yaml_style',
                 'meta_styles/jekyll_style',
                 'meta_styles/multi_line',
                 'meta_styles/no_meta',
                 'not_a_page',
                 'toc'])
        )

    def test_extension_set(self):
        self.test_extension_sequence(set(['.html', '.txt']))

    def test_extension_tuple(self):
        self.test_extension_sequence(('.html', '.txt'))

    def test_catch_conflicting_paths(self):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = ['.html', '.txt']
        with temp_pages(app) as pages:
            original_file = os.path.join(pages.root, 'hello.html')
            target_file = os.path.join(pages.root, 'hello.txt')
            shutil.copyfile(original_file, target_file)
            pages.reload()
            self.assertRaises(ValueError, pages.get, 'hello')

    def test_case_insensitive(self):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = ['.html', '.txt']
        app.config['FLATPAGES_CASE_INSENSITIVE'] = True
        with temp_pages(app) as pages:
            original_file = os.path.join(pages.root, 'hello.html')
            upper_file = os.path.join(pages.root, 'Hello.html')
            txt_file = os.path.join(pages.root, 'hello.txt')
            shutil.move(original_file, upper_file)
            pages.reload()
            self.assertEqual(
                set(page.path for page in pages),
                set(['codehilite',
                     'extra',
                     'foo',
                     'foo/42/not_a_page',
                     'foo/bar',
                     'foo/lorem/ipsum',
                     'headerid',
                     'hello',
                     'meta_styles/closing_block_only',
                     'meta_styles/yaml_style',
                     'meta_styles/jekyll_style',
                     'meta_styles/multi_line',
                     'meta_styles/no_meta',
                     'not_a_page',
                     'toc'])
            )
            shutil.copyfile(upper_file, txt_file)
            pages.reload()
            self.assertRaises(ValueError, pages.get, 'hello')

    def test_get(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(pages.get('foo/bar').path, 'foo/bar')
        self.assertEqual(pages.get('nonexistent'), None)
        self.assertEqual(pages.get('nonexistent', 42), 42)

    def test_get_or_404(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(pages.get_or_404('foo/bar').path, 'foo/bar')
        self.assertRaises(NotFound, pages.get_or_404, 'nonexistent')

    def test_iter(self):
        pages = FlatPages(Flask(__name__))
        self.assertEqual(
            set(page.path for page in pages),
            set(['codehilite',
                 'extra',
                 'foo',
                 'foo/bar',
                 'foo/lorem/ipsum',
                 'headerid',
                 'hello',
                 'meta_styles/closing_block_only',
                 'meta_styles/yaml_style',
                 'meta_styles/jekyll_style',
                 'meta_styles/multi_line',
                 'meta_styles/no_meta',
                 'toc'])
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

    def test_markdown(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEqual(foo.body, 'Foo *bar*\n')
        self.assertEqual(foo.html, '<p>Foo <em>bar</em></p>')

    def test_instance_relative(self):
        with temp_directory() as temp:
            source = os.path.join(os.path.dirname(__file__), 'pages')
            dest = os.path.join(temp, 'instance', 'pages')
            shutil.copytree(source, dest)
            app = Flask(__name__, instance_path=os.path.join(temp, 'instance'))
            app.config['FLATPAGES_INSTANCE_RELATIVE'] = True
            pages = FlatPages(app)
            bar = pages.get('foo/bar')
            self.assertTrue(bar is not None)

    def test_multiple_instance(self):
        """
        This does a very basic test to see if two instances of FlatPages,
        one default instance and one with a name, do pick up the different
        config settings.
        """
        app = Flask(__name__)
        app.debug = True
        app.config['FLATPAGES_DUMMY'] = True
        app.config['FLATPAGES_FUBAR_DUMMY'] = False
        with temp_pages(app) as pages:
            self.assertEqual(pages.config('DUMMY'),
                             app.config['FLATPAGES_DUMMY'])
        with temp_pages(app, 'fubar') as pages:
            self.assertEqual(pages.config('DUMMY'),
                             app.config['FLATPAGES_FUBAR_DUMMY'])

    @patch('flask_flatpages.parsers.yaml.legacy_parser',
           return_value=(dict(), 'Foo')
    )
    @patch('flask_flatpages.parsers.yaml.libyaml_parser',
           side_effect=ValueError('Cannot happen')
    )
    def test_legacy_parser(self, libyaml_mock, legacy_mock):
        app = Flask(__name__)
        app.config['FLATPAGES_LEGACY_META_PARSER'] = True
        
        pages = FlatPages(app)
        self.assertEqual(
            set(page.path for page in pages),
            set(['codehilite',
                 'extra',
                 'foo',
                 'foo/bar',
                 'foo/lorem/ipsum',
                 'headerid',
                 'hello',
                 'meta_styles/closing_block_only',
                 'meta_styles/yaml_style',
                 'meta_styles/jekyll_style',
                 'meta_styles/multi_line',
                 'meta_styles/no_meta',
                 'toc'])
        )
        libyaml_mock.assert_not_called()
        assert legacy_mock.call_count == len(list(pages))

    def test_other_encoding(self):
        app = Flask(__name__)
        app.config['FLATPAGES_ENCODING'] = 'shift_jis'
        app.config['FLATPAGES_ROOT'] = 'pages_shift_jis'
        pages = FlatPages(app)
        self.assert_unicode(pages)

    def test_other_extension(self):
        app = Flask(__name__)
        app.config['FLATPAGES_EXTENSION'] = '.txt'
        pages = FlatPages(app)
        self.assertEqual(
            set(page.path for page in pages),
            set(['not_a_page', 'foo/42/not_a_page'])
        )

    def test_other_html_renderer(self):
        def body_renderer(body):
            return body.upper()

        def page_renderer(body, pages, page):
            return page.body.upper()

        def pages_renderer(body, pages):
            return pages.get('hello').body.upper()

        renderers = filter(None, (
            operator.methodcaller('upper'),
            'string.upper' if not six.PY3 else None,
            body_renderer,
            page_renderer,
            pages_renderer
        ))

        for renderer in (renderers):
            pages = FlatPages(Flask(__name__))
            pages.app.config['FLATPAGES_HTML_RENDERER'] = renderer
            hello = pages.get('hello')
            self.assertEqual(hello.body, u'Hello, *世界*!\n')
            # Upper-case, markdown not interpreted
            self.assertEqual(hello.html, u'HELLO, *世界*!\n')

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_pygments_style_defs(self):
        styles = pygments_style_defs()
        self.assertTrue('.codehilite' in styles)

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

            # Reloading twice does not trigger an exception
            pages.reload()
            pages.reload()

    def test_unicode(self):
        pages = FlatPages(Flask(__name__))
        self.assert_unicode(pages)

    def test_unicode_filenames(self):
        def safe_unicode(sequence):
            if sys.platform != 'darwin':
                return sequence
            return map(lambda item: unicodedata.normalize('NFC', item),
                       sequence)

        app = Flask(__name__)
        with temp_pages(app) as pages:
            self.assertEqual(
                set(page.path for page in pages),
                set(['codehilite',
                     'extra',
                     'foo',
                     'foo/bar',
                     'foo/lorem/ipsum',
                     'headerid',
                     'hello',
                     'meta_styles/closing_block_only',
                     'meta_styles/yaml_style',
                     'meta_styles/jekyll_style',
                     'meta_styles/multi_line',
                     'meta_styles/no_meta',
                     'toc'])
            )

            os.remove(os.path.join(pages.root, 'foo', 'lorem', 'ipsum.html'))
            open(os.path.join(pages.root, u'Unïcôdé.html'), 'w').close()
            pages.reload()

            self.assertEqual(
                set(safe_unicode(page.path for page in pages)),
                set(['codehilite',
                     'extra',
                     'foo',
                     'foo/bar',
                     'headerid',
                     'hello',
                     'meta_styles/closing_block_only',
                     'meta_styles/yaml_style',
                     'meta_styles/jekyll_style',
                     'meta_styles/multi_line',
                     'meta_styles/no_meta',
                     'toc',
                     u'Unïcôdé']))

    def test_yaml_meta(self):
        pages = FlatPages(Flask(__name__))
        foo = pages.get('foo')
        self.assertEqual(foo.meta, {
            'title': 'Foo > bar',
            'created': datetime.date(2010, 12, 11),
            'updated': datetime.datetime(2015, 2, 9, 10, 59, 0),
            'updated_iso': datetime.datetime(2015, 2, 9, 10, 59, 0,
                                             tzinfo=utc),
            'versions': [3.14, 42],
        })
        self.assertEqual(foo['title'], 'Foo > bar')
        self.assertEqual(foo['created'], datetime.date(2010, 12, 11))
        self.assertEqual(foo['updated'],
                         datetime.datetime(2015, 2, 9, 10, 59, 0))
        self.assertEqual(foo['updated_iso'],
                         datetime.datetime(2015, 2, 9, 10, 59, 0,
                                           tzinfo=utc))
        self.assertEqual(foo['versions'], [3.14, 42])
        self.assertRaises(KeyError, lambda: foo['nonexistent'])

    def test_no_meta(self):
        app = Flask(__name__)
        with temp_pages(app) as pages:
            no_meta = pages.get('meta_styles/no_meta')
            self.assertEqual(no_meta.meta, {})
            filename = os.path.join(pages.root, 'meta_styles', 'no_meta.html')
            with open(filename, 'w') as f_:
                f_.write("\n Hello, there's no metadata here.")
            pages.reload()
            no_meta = pages.get('meta_styles/no_meta')
            self.assertEqual(no_meta.meta, {})
            with open(filename, 'w') as f_:
                f_.write("---\n---\nHello, there's no metadata here.")
            pages.reload()
            no_meta = pages.get('meta_styles/no_meta')
            self.assertEqual(no_meta.meta, {})
            with open(filename, 'w') as f_:
                f_.write("---\n...\nHello, there's no metadata here.")
            pages.reload()
            no_meta = pages.get('meta_styles/no_meta')
            self.assertEqual(no_meta.meta, {})
            with open(filename, 'w') as f_:
                f_.write("#Hello, there's no metadata here.")
            pages.reload()
            no_meta = pages.get('meta_styles/no_meta')
            self.assertEqual(no_meta.meta, {})

    def test_meta_closing_only(self):
        app = Flask(__name__)
        with temp_pages(app) as pages:
            page = pages.get('meta_styles/closing_block_only')
            self.assertEqual(page.meta, {'hello': 'world'})
            filename = os.path.join(pages.root, 'meta_styles', 'closing_block_only.html')
            with open(filename, 'w') as f:
                f.write('hello: world\n...\nFoo')
            pages.reload()
            page = pages.get('meta_styles/closing_block_only')
            self.assertEqual(page.meta, {'hello': 'world'})


    def test_jekyll_style_meta(self):
        app = Flask(__name__)
        with temp_pages(app) as pages:
            jekyll_style = pages.get('meta_styles/jekyll_style')
            self.assertEqual(jekyll_style.meta, {'hello': 'world'})
            self.assertEqual(jekyll_style.body, 'Foo')
            filename = os.path.join(pages.root, 'meta_styles', 'jekyll_style.html')
            with open(filename, 'r') as f_:
                lines = f_.readlines()
            with open(filename, 'w') as f_:
                f_.write('\n'.join(lines[1:]))
            pages.reload()
            jekyll_style = pages.get('meta_styles/jekyll_style')
            self.assertEqual(jekyll_style.meta, {'hello': 'world'})
            self.assertEqual(jekyll_style.body, 'Foo')

    def test_yaml_style_meta(self):
        app = Flask(__name__)
        with temp_pages(app) as pages:
            yaml_style = pages.get('meta_styles/yaml_style')
            self.assertEqual(yaml_style.meta, {'hello': 'world'})
            self.assertEqual(yaml_style.body, 'Foo')
            filename = os.path.join(pages.root, 'meta_styles', 'yaml_style.html')
            with open(filename, 'r') as f_:
                lines = f_.readlines()
            with open(filename, 'w') as f_:
                f_.write('\n'.join(lines[1:]))
            pages.reload()
            yaml_style = pages.get('meta_styles/yaml_style')
            self.assertEqual(yaml_style.meta, {'hello': 'world'})
            self.assertEqual(yaml_style.body, 'Foo')

    def test_multi_line(self):
        pages = FlatPages(Flask(__name__))
        multi_line = pages.get('meta_styles/multi_line')
        self.assertEqual(multi_line.body, 'Foo')
        self.assertIn('multi_line_string', multi_line.meta)
        self.assertIn('\n', multi_line.meta['multi_line_string'])
    
    def test_parser_error(self):
        app = Flask(__name__)
        with temp_pages(app) as pages:
            with open(os.path.join(pages.root, 'bad_file_test.html'), 'w') as f:
                if six.PY3:
                    f.write("Hello World \u000B")
                else:
                    f.write("\x0b".decode('utf-8'))
            with pytest.raises(yaml.reader.ReaderError, match=r".*bad_file_test.*") as excinfo:
                pages.get('bad_file_test')

