"""
==============================
tests.test_markdown_extensions
==============================

Test proper work of various Markdown extensions.

"""

import sys
import unittest

from flask import Flask
from flask_flatpages import FlatPages
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
        codehilite = pages.get('codehilite') #Test codehilite loaded by default
                                             #by pygmented_markdown
        self.assertEqual(
            codehilite.html,
            '<div class="codehilite"><pre><span></span><span class="k">print</span>'
            '<span class="p">(</span><span class="s1">&#39;Hello, world!&#39;'
            '</span><span class="p">)</span>\n</pre></div>'
        )
        pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite', 'headerid'
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
        codehilite = pages.get('codehilite') #Test codehilite also loaded
        self.assertEqual(
            codehilite.html,
            '<div class="codehilite"><pre><span></span><span class="k">print</span>'
            '<span class="p">(</span><span class="s1">&#39;Hello, world!&#39;'
            '</span><span class="p">)</span>\n</pre></div>'
        )

    def test_codehilite_linenums_disabled(self):
        #Test implicitly disabled
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['codehilite']
        pages = FlatPages(app)
        codehilite = pages.get('codehilite')
        self.assertEqual(
            codehilite.html,
            '<div class="codehilite"><pre><span></span><span class="k">print</span>'
            '<span class="p">(</span><span class="s1">&#39;Hello, world!&#39;'
            '</span><span class="p">)</span>\n</pre></div>'
        )
        #Test explicity disabled
        pages.app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite(linenums=False)'
        ]
        pages.reload()
        pages._file_cache = {}
        codehilite = pages.get('codehilite')
        self.assertEqual(
            codehilite.html,
            '<div class="codehilite"><pre><span></span><span class="k">print</span>'
            '<span class="p">(</span><span class="s1">&#39;Hello, world!&#39;'
            '</span><span class="p">)</span>\n</pre></div>'
        )

    def test_codehilite_linenums_enabled(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [
            'codehilite(linenums=True)'
        ]
        pages = FlatPages(app)

        codehilite = pages.get('codehilite')
        self.assertEqual(
            codehilite.html,
            '<table class="codehilitetable"><tr><td class="linenos">'
            '<div class="linenodiv"><pre>1</pre></div></td><td class="code">'
            '<div class="codehilite"><pre><span></span><span class="k">print</span>'
            '<span class="p">(</span><span class="s1">&#39;Hello, world!&#39;'
            '</span><span class="p">)</span>\n</pre></div>\n</td></tr></table>'
        )

    def test_extra(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['extra']
        pages = FlatPages(app)
        extra_sep = '\n' if sys.version_info[:2] > (2, 6) else '\n\n'

        extra = pages.get('extra')
        self.assertEqual(
            extra.html,
            '<p>This is <em>true</em> markdown text.</p>\n'
            '<div>{0}'
            '<p>This is <em>true</em> markdown text.</p>\n'
            '</div>'.format(extra_sep)
        )

    def test_toc(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = ['toc']
        pages = FlatPages(app)
        self.check_toc_page(pages)

    def test_toc_ext_object(self):
        app = Flask(__name__)
        app.config['FLATPAGES_MARKDOWN_EXTENSIONS'] = [TocExtension()]
        pages = FlatPages(app)
        self.check_toc_page(pages)
