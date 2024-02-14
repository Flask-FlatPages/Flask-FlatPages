"""
==============================
tests.test_markdown_extensions
==============================

Test proper work of various Markdown extensions.

"""

import sys


import markdown
import pytest
from flask_flatpages import FlatPages
from flask_flatpages.imports import PygmentsHtmlFormatter
from markdown.extensions.toc import TocExtension


def check_toc_page(pages: FlatPages):
    toc = pages.get("toc")
    fixture = markdown.markdown(
        toc.body,
        extensions=[TocExtension()],
    )
    assert fixture == toc.html


def check_default_codehilite_page(pages: FlatPages):
    codehilite = pages.get("codehilite")
    body = codehilite.body
    fixture = markdown.markdown(
        body,
        extensions=["codehilite"],
    )
    assert codehilite.html == fixture


def check_codehilite_with_linenums(pages: FlatPages):
    codehilite = pages.get("codehilite")
    body = codehilite.body
    fixture = markdown.markdown(
        body,
        extensions=["codehilite"],
        extension_configs={"codehilite": {"linenums": True}},
    )
    assert codehilite.html == fixture


def check_extra(pages: FlatPages):
    extra_sep = "\n" if sys.version_info[:2] > (2, 6) else "\n\n"
    fixture = (
        "<p>This is <em>true</em> markdown text.</p>\n"
        "<div>{0}"
        "<p>This is <em>true</em> markdown text.</p>\n"
        "</div>".format(extra_sep)
    )
    extra = pages.get("extra")
    assert extra.html == fixture


HELLO_HTML = "<h1>Page Header</h1>\n<h2>Paragraph Header</h2>\n<p>Text</p>"
HELLO_ID_HTML = (
    """<h1 id="page-header">Page Header</h1>\n"""
    """<h2 id="paragraph-header">Paragraph Header</h2>\n"""
    """<p>Text</p>"""
)


def test_default_markdown(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    hello = pages.get("headerid")
    assert hello.html == HELLO_HTML
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = []
    pages.reload()
    pages._file_cache = {}

    hello = pages.get("headerid")
    assert hello.html == HELLO_HTML
    if PygmentsHtmlFormatter is not None:
        check_default_codehilite_page(pages)


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_codehilite_linenums_disabled(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    # Test explicity disabled
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = ["codehilite"]
    check_default_codehilite_page(pages)
    # Test explicity disabled
    app_with_context.config["FLATPAGES_EXTENSION_CONFIGS"] = {
        "codehilite": {"linenums": "False"}
    }
    pages.reload()
    pages._file_cache = {}
    check_default_codehilite_page(pages)


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_codehilite_linenums_enabled(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = ["codehilite"]
    app_with_context.config["FLATPAGES_EXTENSION_CONFIGS"] = {
        "codehilite": {"linenums": "True"}
    }

    check_codehilite_with_linenums(pages)


def test_extra(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = ["extra"]
    check_extra(pages)


def test_toc(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = ["toc"]
    check_toc_page(pages)


def test_headerid_with_toc(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = [
        "codehilite",
        "toc",  # headerid is deprecated in Markdown 3.0
    ]
    pages.reload()
    pages._file_cache = {}

    hello = pages.get("headerid")
    assert hello.html == HELLO_ID_HTML
    if PygmentsHtmlFormatter is not None:
        check_default_codehilite_page(pages)  # test codehilite also loaded


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_extension_importpath(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = [
        "markdown.extensions.codehilite:CodeHiliteExtension"
    ]
    check_default_codehilite_page(pages)
    app_with_context.config[
        "FLATPAGES_EXTENSION_CONFIGS"
    ] = {  # Markdown 3 style config
        "markdown.extensions.codehilite:CodeHiliteExtension": {
            "linenums": True
        }
    }
    pages.reload()
    pages._file_cache = {}
    check_codehilite_with_linenums(pages)


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_extension_object(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    from markdown.extensions.codehilite import CodeHiliteExtension

    codehilite = CodeHiliteExtension()
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = [codehilite]
    check_default_codehilite_page(pages)
    codehilite = CodeHiliteExtension(linenums="True")  # Check config applies
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = [codehilite]
    pages.reload()
    pages._file_cache = {}
    check_codehilite_with_linenums(pages)


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_mixed_extension_types(app_with_context, flatpages_factory):
    from markdown.extensions.toc import TocExtension

    pages = flatpages_factory(app_with_context)

    toc = TocExtension()
    app_with_context.config["FLATPAGES_MARKDOWN_EXTENSIONS"] = [
        toc,
        "codehilite",
        "markdown.extensions.extra:ExtraExtension",
    ]
    check_toc_page(pages)
    check_default_codehilite_page(pages)
    check_extra(pages)
    app_with_context.config["FLATPAGES_EXTENSION_CONFIGS"] = {
        "codehilite": {"linenums": "True"}
    }
    pages.reload()
    pages._file_cache = {}
    check_toc_page(pages)
    check_extra(pages)
    check_codehilite_with_linenums(pages)
