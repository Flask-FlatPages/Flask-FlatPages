# coding: utf8
from __future__ import annotations
import os

from flask_flatpages import FlatPages


def _make_pages(app, subdir="pages_toml"):
    root = os.path.join(os.path.dirname(__file__), subdir)
    app.config["FLATPAGES_ROOT"] = root
    # Prefer TOML meta parser for these tests
    app.config["FLATPAGES_META_PARSER"] = "toml"
    pages = FlatPages(app)
    return pages


def test_toml_hello_meta_and_rendering(app_with_context):
    pages = _make_pages(app_with_context)
    hello = pages.get("hello")
    assert hello is not None
    assert hello.meta == {"title": "世界", "template": "article.html"}
    assert hello.body.strip() == "Hello, *世界*!"
    # html rendering via markdown
    assert "Hello" in hello.html


def test_toml_jekyll_style_meta(app_with_context):
    pages = _make_pages(app_with_context)
    page = pages.get("meta_styles/jekyll_style")
    assert page is not None
    assert page.meta.get("hello") == "world"
    assert page.body.strip() == "Foo"
