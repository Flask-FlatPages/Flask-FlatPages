"""
==============================
tests.test_markdown_extensions
==============================

Test proper work of various Markdown extensions.

"""

import sys
import unittest
from collections.abc import Generator

import markdown
import pytest
from flask import Flask
from flask_flatpages import FlatPages
from flask_flatpages.imports import PygmentsHtmlFormatter
from markdown.extensions.toc import TocExtension
from six import PY3



class TestMarkdownExtensions(unittest.TestCase):

    def setUp(self):
        self.app =Flask(__name__)
        self._app_context = self.app.app_context()
        self._app_context.push()
        self.pages = FlatPages(self.app)
    

    def tearDown(self) -> None:
        self._app_context.push()

    def check_toc_page(self):
        toc = self.pages.get('toc')
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
    def check_default_codehilite_page(self):
        codehilite = self.pages.get('codehilite')
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
    def check_codehilite_with_linenums(self):
        codehilite = self.pages.get('codehilite')
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

    def check_extra(self):
        extra_sep = '\n' if sys.version_info[:2] > (2, 6) else '\n\n'

        extra = self.pages.get('extra')
        self.assertEqual(
            extra.html,
            '<p>This is <em>true</em> markdown text.</p>\n'
            '<div>{0}'
            '<p>This is <em>true</em> markdown text.</p>\n'
            '</div>'.format(extra_sep)
        )

    def test_basic(self):

        hello = self.pages.get('headerid')
        self.assertEqual(
            hello.html,
            u'<h1>Page Header</h1>\n<h2>Paragraph Header</h2>\n<p>Text</p>'
        )

        self.pages.app.config['FLATflatpages_MARKDOWN_EXTENSIONS'] = []
        self.pages.reload()
        self.pages._file_cache = {}

        hello = self.pages.get('headerid')
        self.assertEqual(
            hello.html,
            u'<h1>Page Header</h1>\n<h2>Paragraph Header</h2>\n<p>Text</p>'
        )
        if PygmentsHtmlFormatter is not None:
            self.check_default_codehilite_page()

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_codehilite_linenums_disabled(self):
        #Test explicity disabled
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['codehilite']
        self.check_default_codehilite_page()
        #Test explicity disabled
        self.pages.app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'False'
            }
        }
        self.pages.reload()
        self.pages._file_cache = {}
        self.check_default_codehilite_page()

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_codehilite_linenums_enabled(self):
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['codehilite']
        self.app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'True'
            }
        }

        self.check_codehilite_with_linenums()

    def test_extra(self):
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['extra']
        self.check_extra()

    def test_toc(self):
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['toc']
        self.check_toc_page()

    def test_headerid_with_toc(self):
        self.pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite', 'toc' #headerid is deprecated in Markdown 3.0
        ]
        self.pages.reload()
        self.pages._file_cache = {}

        hello = self.pages.get('headerid')
        self.assertEqual(
            hello.html,
            '<h1 id="page-header">Page Header</h1>\n'
            '<h2 id="paragraph-header">Paragraph Header</h2>\n'
            '<p>Text</p>'
        )
        if PygmentsHtmlFormatter is not None:
            self.check_default_codehilite_page() #test codehilite also loaded

    
    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_extension_importpath(self):
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'markdown.extensions.codehilite:CodeHiliteExtension'
        ]
        self.check_default_codehilite_page()
        self.app.config['FLATPAGES_EXTENSION_CONFIGS'] = { #Markdown 3 style config
            'markdown.extensions.codehilite:CodeHiliteExtension': {
                'linenums': True
            }
        }
        self.pages.reload()
        self.pages._file_cache = {}
        self.check_codehilite_with_linenums()

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_extension_object(self):
        from markdown.extensions.codehilite import CodeHiliteExtension
        codehilite = CodeHiliteExtension()
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [codehilite]
        self.check_default_codehilite_page()
        codehilite = CodeHiliteExtension(linenums='True') #Check config applies
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [codehilite]
        self.pages.reload()
        self.pages._file_cache = {}
        self.check_codehilite_with_linenums()

    @pytest.mark.skipif(PygmentsHtmlFormatter is None,
                        reason='Pygments not installed')
    def test_mixed_extension_types(self):
        from markdown.extensions.toc import TocExtension
        toc = TocExtension()
        self.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            toc,
            'codehilite',
            'markdown.extensions.extra:ExtraExtension'
        ]
        self.check_toc_page()
        self.check_default_codehilite_page()
        self.check_extra()
        self.app.config['FLATPAGES_EXTENSION_CONFIGS'] = {
            'codehilite': {
                'linenums': 'True'
            }
        }
        self.pages.reload()
        self.pages._file_cache = {}
        self.check_toc_page()
        self.check_extra()
        self.check_codehilite_with_linenums()

