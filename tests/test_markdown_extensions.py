"""
==============================
tests.test_markdown_extensions
==============================

Test proper work of various Markdown extensions.

"""

import sys
import unittest


import markdown
import pytest
from flask import Flask
from flask_flatpages import FlatPages
from flask_flatpages.imports import PygmentsHtmlFormatter
from markdown.extensions.toc import TocExtension


class TestMarkdownExtensions(unittest.TestCase):

    def check_toc_page(self, pages):
        toc = pages.get('toc')
        self.assertEqual(
            toc.html,
            '<div class="toc">\n<ul>\n<li><a href="#page-header">Page '
            'Header</a><ul>\n<li><a href="#paragraph-header">Paragraph '
            'Header</a></li>\n</ul>\n</li>\n</ul>\n</div>\n'
            '<h1 id="page-header">Page Header</h1>\n'
            '<h2 id="paragraph-header">Paragraph Header</h2>\n'
            '<p>Text</p>'
        )

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def check_default_codehilite_page(self, pages):
        codehilite = pages.get('codehilite')
        body = codehilite.body
        fixture = markdown.markdown(
            body,
            extensions=['codehilite'],
        )
        self.assertEqual(
            codehilite.html,
            fixture
        )

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def check_codehilite_with_linenums(self, pages):
        codehilite = pages.get('codehilite')
        body = codehilite.body
        fixture = markdown.markdown(
            body,
            extensions=['codehilite'],
            extension_configs={
                'codehilite': {
                    'linenums': True
                }
            }
        )
        self.assertEqual(
            codehilite.html,
            fixture
        )

    def check_extra(self, pages):
        extra_sep = '\n' if sys.version_info[:2] > (2, 6) else '\n\n'

        extra = pages.get('extra')
        self.assertEqual(
            extra.html,
            '<p>This is <em>true</em> markdown text.</p>\n'
            '<div>{0}'
            '<p>This is <em>true</em> markdown text.</p>\n'
            '</div>'.format(extra_sep)
        )

    def test_basic(self):
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
        if PygmentsHtmlFormatter is not None:
            self.check_default_codehilite_page(pages)

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_codehilite_linenums_disabled(self):
        #Test explicity disabled
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['codehilite']
        pages = FlatPages(app)
        self.check_default_codehilite_page(pages)
        #Test explicity disabled
        pages.app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'False'
            }
        }
        pages.reload()
        pages._file_cache = {}
        self.check_default_codehilite_page(pages)

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_codehilite_linenums_enabled(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['codehilite']
        app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'True'
            }
        }
        pages = FlatPages(app)

        self.check_codehilite_with_linenums(pages)

    def test_extra(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['extra']
        pages = FlatPages(app)
        self.check_extra(pages)

    def test_toc(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['toc']
        pages = FlatPages(app)
        self.check_toc_page(pages)

    def test_headerid_with_toc(self):
        app = Flask(__name__)
        pages = FlatPages(app)
        pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite', 'toc' #headerid is deprecated in Markdown 3.0
        ]
        pages.reload()
        pages._file_cache = {}

        hello = pages.get('headerid')
        self.assertEqual(
            hello.html,
            '<h1 id="page-header">Page Header</h1>\n'
            '<h2 id="paragraph-header">Paragraph Header</h2>\n'
            '<p>Text</p>'
        )
        if PygmentsHtmlFormatter is not None:
            self.check_default_codehilite_page(pages) #test codehilite also loaded

    
    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_extension_importpath(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'markdown.extensions.codehilite:CodeHiliteExtension'
        ]
        pages = FlatPages(app)
        self.check_default_codehilite_page(pages)
        app.config['FLATPAGES_EXTENSION_CONFIGS'] = { #Markdown 3 style config
            'markdown.extensions.codehilite:CodeHiliteExtension': {
                'linenums': True
            }
        }
        pages.reload()
        pages._file_cache = {}
        self.check_codehilite_with_linenums(pages)

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_extension_object(self):
        app = Flask(__name__)
        from markdown.extensions.codehilite import CodeHiliteExtension
        codehilite = CodeHiliteExtension()
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [codehilite]
        pages = FlatPages(app)
        self.check_default_codehilite_page(pages)
        codehilite = CodeHiliteExtension(linenums='True') #Check config applies
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [codehilite]
        pages.reload()
        pages._file_cache = {}
        self.check_codehilite_with_linenums(pages)

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_mixed_extension_types(self):
        app = Flask(__name__)
        from markdown.extensions.toc import TocExtension
        toc = TocExtension()
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            toc,
            'codehilite',
            'markdown.extensions.extra:ExtraExtension'
        ]
        pages = FlatPages(app)
        self.check_toc_page(pages)
        self.check_default_codehilite_page(pages)
        self.check_extra(pages)
        app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'True'
            }
        }
        pages.reload()
        pages._file_cache = {}
        self.check_toc_page(pages)
        self.check_extra(pages)
        self.check_codehilite_with_linenums(pages)

