# coding: utf8
"""
Tests for Flask-FlatPages
~~~~~~~~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010 by Simon Sapin.
:license: BSD, see LICENSE for more details.
"""

from __future__ import annotations
import datetime
import operator
import os
import shutil
import sys
import unicodedata
import flask


import yaml
import pytest
from flask import Flask
from flask_flatpages import FlatPages, pygments_style_defs
from flask_flatpages.imports import PygmentsHtmlFormatter
from werkzeug.exceptions import NotFound


utc = datetime.timezone.utc
from unittest.mock import patch


@pytest.fixture
def default_paths():
    return set(
        [
            "codehilite",
            "extra",
            "foo",
            "foo/bar",
            "foo/lorem/ipsum",
            "headerid",
            "hello",
            "meta_styles/closing_block_only",
            "meta_styles/yaml_style",
            "meta_styles/jekyll_style",
            "meta_styles/multi_line",
            "meta_styles/no_meta",
            "toc",
        ]
    )


@pytest.fixture
def all_paths(default_paths):
    return default_paths | {"foo/42/not_a_page", "not_a_page"}


@pytest.fixture
def paths_excluding(all_paths):
    def filtered_paths(*args):
        paths = all_paths
        for arg in args:
            paths = paths.remove(arg)
        return paths

    return filtered_paths


def _check_auto_reset(pages: FlatPages, should_reset: bool):
    bar = pages.get("foo/bar")
    assert bar.body == ""

    filename = os.path.join(pages.root, "foo", "bar.html")
    with open(filename, "w") as fd:
        fd.write("\nrewritten")

    # simulate a request (before_request functions are called)
    # pages.reload() is not call explicitly
    with flask.current_app.test_request_context():
        flask.current_app.preprocess_request()

    bar2 = pages.get("foo/bar")
    if should_reset:
        assert bar2.body == "rewritten"
        assert bar2 is not bar
    else:
        assert bar2.body == ""
        assert bar2 is bar


def test_caching(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    foo = pages.get("foo")
    bar = pages.get("foo/bar")

    filename = os.path.join(pages.root, "foo", "bar.html")
    with open(filename, "w") as fd:
        fd.write("\nrewritten")

    pages.reload()

    foo2 = pages.get("foo")
    bar2 = pages.get("foo/bar")

    # Page objects are cached and unmodified files (according to the
    # modification date) are not parsed again.
    assert foo2 is foo
    assert bar2 is not bar
    assert bar2.body != bar.body


def test_configured_auto_reset(app_with_context, temp_pages):
    app_with_context.config["FLATPAGES_AUTO_RELOAD"] = True
    pages = temp_pages(app_with_context)
    _check_auto_reset(pages, True)


def test_configured_no_auto_reset(app_with_context, temp_pages):
    app_with_context.debug = True
    app_with_context.config["FLATPAGES_AUTO_RELOAD"] = False
    pages = temp_pages(app_with_context)
    _check_auto_reset(pages, should_reset=False)


def test_consistency(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    for page in pages:
        assert pages.get(page.path) is page


def test_debug_auto_reset(app_with_context, temp_pages):
    app_with_context.debug = True
    pages = temp_pages(app_with_context)
    _check_auto_reset(pages, should_reset=True)


def test_default_no_auto_reset(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    _check_auto_reset(pages, should_reset=False)


@pytest.fixture
def pages_with_extension(app_with_context, flatpages_factory):
    def _initialised_pages(extensions):
        app_with_context.config["FLATPAGES_EXTENSION"] = extensions
        flatpages = flatpages_factory(app_with_context)
        return set(page.path for page in flatpages)

    yield _initialised_pages


def test_extension_sequence(all_paths, pages_with_extension):
    assert all_paths == pages_with_extension([".html", ".txt"])


def test_extension_comma(all_paths, pages_with_extension):
    assert all_paths == pages_with_extension(".html,.txt")


def test_extension_set(all_paths, pages_with_extension):
    assert all_paths == pages_with_extension(set([".html", ".txt"]))


def test_extension_tuple(all_paths, pages_with_extension):
    assert all_paths == pages_with_extension((".html", ".txt"))


def test_catch_conflicting_paths(app_with_context, temp_pages):
    app_with_context.config["FLATPAGES_EXTENSION"] = [".html", ".txt"]
    pages = temp_pages(app_with_context)
    original_file = os.path.join(pages.root, "hello.html")
    target_file = os.path.join(pages.root, "hello.txt")
    shutil.copyfile(original_file, target_file)
    pages.reload()
    with pytest.raises(ValueError):
        pages.get("hello")


def test_case_insensitive(app_with_context, temp_pages, all_paths):
    app_with_context.config["FLATPAGES_EXTENSION"] = [".html", ".txt"]
    app_with_context.config["FLATPAGES_CASE_INSENSITIVE"] = True
    pages = temp_pages(app_with_context)
    original_file = os.path.join(pages.root, "hello.html")
    upper_file = os.path.join(pages.root, "Hello.html")
    txt_file = os.path.join(pages.root, "hello.txt")
    shutil.move(original_file, upper_file)
    pages.reload()
    assert all_paths == set(p.path for p in pages)
    shutil.copyfile(upper_file, txt_file)
    pages.reload()
    with pytest.raises(ValueError):
        pages.get("hello")


def test_get(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    assert pages.get("foo/bar").path == "foo/bar"
    assert pages.get("nonexistent") == None
    assert pages.get("nonexistent", 42) == 42


def test_get_or_404(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    assert pages.get_or_404("foo/bar").path == "foo/bar"
    with pytest.raises(NotFound):
        pages.get_or_404("nonexistant")


def test_iter(app_with_context, flatpages_factory, default_paths):
    pages = flatpages_factory(app_with_context)
    assert set(p.path for p in pages) == default_paths


def test_lazy_loading(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    bar = pages.get("foo/bar")
    # bar.html is normally empty
    assert bar.meta == {}
    assert bar.body == ""
    filename = os.path.join(pages.root, "foo", "bar.html")
    # write as pages is already constructed
    with open(filename, "a") as fd:
        fd.write("a: b\n\nc")
    bar = pages.get("foo/bar")
    assert bar.meta == {}
    assert bar.body == ""
    pages.reload()
    bar = pages.get("foo/bar")
    # bar was just loaded from the disk
    assert bar.meta == {"a": "b"}
    assert bar.body == "c"


def test_markdown(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    foo = pages.get("foo")
    assert foo.body == "Foo *bar*\n"
    assert foo.html == "<p>Foo <em>bar</em></p>"


def test_instance_relative(tmpdir):
    source = os.path.join(os.path.dirname(__file__), "pages")
    dest = os.path.join(tmpdir, "instance", "pages")
    shutil.copytree(source, dest)
    app = Flask(__name__, instance_path=os.path.join(tmpdir, "instance"))
    app.config["FLATPAGES_INSTANCE_RELATIVE"] = True
    pages = FlatPages(app)
    with app.app_context():
        bar = pages.get("foo/bar")
        assert bar is not None


def test_multiple_instance(app_with_context, temp_pages):
    """
    This does a very basic test to see if two instances of FlatPages,
    one default instance and one with a name, do pick up the different
    config settings.
    """
    app_with_context.debug = True
    app_with_context.config["FLATPAGES_DUMMY"] = True
    app_with_context.config["FLATPAGES_FUBAR_DUMMY"] = False
    p1 = temp_pages(app_with_context)
    assert p1.config("DUMMY") == app_with_context.config["FLATPAGES_DUMMY"]
    p2 = temp_pages(app_with_context, "fubar")
    assert (
        p2.config("DUMMY") == app_with_context.config["FLATPAGES_FUBAR_DUMMY"]
    )


def _assert_unicode(pages: FlatPages):
    hello = pages.get("hello")
    assert hello.meta == {"title": "世界", "template": "article.html"}
    assert hello["title"] == "世界"
    assert hello.body == "Hello, *世界*!\n"
    # Markdown
    assert hello.html == "<p>Hello, <em>世界</em>!</p>"


def test_legacy_parser(
    app_with_context, flatpages_factory, default_paths, mocker
):
    app_with_context.config["FLATPAGES_LEGACY_META_PARSER"] = True
    yaml_mock = mocker.Mock(side_effect=ValueError("CannotHappen"))
    legacy_mock = mocker.Mock(return_value=(dict(), "Foo"))
    mocker.patch(
        "flask_flatpages.flatpages.legacy_parser", legacy_mock
    )
    mocker.patch(
        "flask_flatpages.flatpages.libyaml_parser", yaml_mock
    )
    pages = flatpages_factory(app_with_context)
    assert {page.path for page in pages} == default_paths
    yaml_mock.assert_not_called()
    assert legacy_mock.call_count == len(list(pages))


def test_other_encoding(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    app_with_context.config["FLATPAGES_ENCODING"] = "shift_jis"
    app_with_context.config["FLATPAGES_ROOT"] = "pages_shift_jis"
    _assert_unicode(pages)


def test_other_extension(
    app_with_context, flatpages_factory, all_paths, default_paths
):
    pages = flatpages_factory(app_with_context)
    txt_paths = all_paths - default_paths
    app_with_context.config["FLATPAGES_EXTENSION"] = ".txt"
    found_paths = {page.path for page in pages}
    assert found_paths == txt_paths
    assert found_paths.isdisjoint(default_paths)


def test_other_html_renderer():
    def body_renderer(body):
        return body.upper()

    def page_renderer(body, pages, page):
        return page.body.upper()

    def pages_renderer(body, pages):
        return pages.get("hello").body.upper()

    renderers = filter(
        None,
        (
            operator.methodcaller("upper"),
            None,
            body_renderer,
            page_renderer,
            pages_renderer,
        ),
    )

    for renderer in renderers:
        app = Flask(__name__)
        pages = FlatPages(app)
        with app.app_context():
            app.config["FLATPAGES_HTML_RENDERER"] = renderer
            hello = pages.get("hello")
            assert hello.body == "Hello, *世界*!\n"
            # Upper-case, markdown not interpreted
            assert hello.html == "HELLO, *世界*!\n"


@pytest.mark.skipif(
    PygmentsHtmlFormatter is None, reason="Pygments not installed"
)
def test_pygments_style_defs():
    styles = pygments_style_defs()
    assert ".codehilite" in styles


def test_reloading(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    bar = pages.get("foo/bar")
    # bar.html is normally empty
    assert bar.meta == {}
    assert bar.body == ""

    filename = os.path.join(pages.root, "foo", "bar.html")
    # rewrite already loaded page
    with open(filename, "w") as fd:
        # The newline is a separator between the (empty) metadata
        # and the source 'first'
        fd.write("\nfirst rewrite")

    bar2 = pages.get("foo/bar")
    # the disk is not hit again until requested
    assert bar2.meta == {}
    assert bar2.body == ""
    assert bar2 is bar

    # request reloading
    pages.reload()

    # write again
    with open(filename, "w") as fd:
        fd.write("\nsecond rewrite")

    # get another page
    pages.get("hello")

    # write again
    with open(filename, "w") as fd:
        fd.write("\nthird rewrite")

    # All pages are read at once when any is used
    bar3 = pages.get("foo/bar")
    assert bar3.meta == {}
    assert bar3.body == "second rewrite"  # not third
    # Page objects are not reused when a file is re-read.
    assert bar3 is not bar2

    # Removing does not trigger reloading either
    os.remove(filename)

    bar4 = pages.get("foo/bar")
    assert bar4.meta == {}
    assert bar4.body == "second rewrite"
    assert bar4 is bar3

    pages.reload()

    bar5 = pages.get("foo/bar")
    assert bar5 is None

    # Reloading twice does not trigger an exception
    pages.reload()
    pages.reload()


def test_unicode(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    _assert_unicode(pages)


def test_unicode_filenames(app_with_context, temp_pages, default_paths):
    def safe_unicode(sequence):
        if sys.platform != "darwin":
            return sequence
        return ''.join(unicodedata.normalize("NFC", item) for item in sequence)

    pages = temp_pages(app_with_context)
    assert {page.path for page in pages} == default_paths

    os.remove(os.path.join(pages.root, "foo", "lorem", "ipsum.html"))
    open(os.path.join(pages.root, "Unïcôdé.html"), "w").close()
    pages.reload()

    assert set(safe_unicode(page.path) for page in pages) == (
        (default_paths | {"Unïcôdé"}) - {"foo/lorem/ipsum"}
    )


def test_yaml_meta(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    foo = pages.get("foo")
    assert foo.meta == {
        "title": "Foo > bar",
        "created": datetime.date(2010, 12, 11),
        "updated": datetime.datetime(2015, 2, 9, 10, 59, 0),
        "updated_iso": datetime.datetime(2015, 2, 9, 10, 59, 0, tzinfo=utc),
        "versions": [3.14, 42],
    }
    assert foo["title"] == "Foo > bar"
    assert foo["created"] == datetime.date(2010, 12, 11)
    assert foo["updated"] == datetime.datetime(2015, 2, 9, 10, 59, 0)
    assert foo["updated_iso"] == datetime.datetime(
        2015, 2, 9, 10, 59, 0, tzinfo=utc
    )
    assert foo["versions"] == [3.14, 42]
    with pytest.raises(KeyError):
        foo["nonexistent"]


def test_no_meta(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    no_meta = pages.get("meta_styles/no_meta")
    assert no_meta.meta == {}
    filename = os.path.join(pages.root, "meta_styles", "no_meta.html")
    with open(filename, "w") as f_:
        f_.write("\n Hello, there's no metadata here.")
    pages.reload()
    no_meta = pages.get("meta_styles/no_meta")
    assert no_meta.meta == {}
    with open(filename, "w") as f_:
        f_.write("---\n---\nHello, there's no metadata here.")
    pages.reload()
    no_meta = pages.get("meta_styles/no_meta")
    assert no_meta.meta == {}
    with open(filename, "w") as f_:
        f_.write("---\n...\nHello, there's no metadata here.")
    pages.reload()
    no_meta = pages.get("meta_styles/no_meta")
    assert no_meta.meta == {}
    with open(filename, "w") as f_:
        f_.write("#Hello, there's no metadata here.")
    pages.reload()
    no_meta = pages.get("meta_styles/no_meta")
    assert no_meta.meta == {}


def test_meta_closing_only(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    page = pages.get("meta_styles/closing_block_only")
    assert page.meta == {"hello": "world"}
    filename = os.path.join(
        pages.root, "meta_styles", "closing_block_only.html"
    )
    with open(filename, "w") as f:
        f.write("hello: world\n...\nFoo")
    pages.reload()
    page = pages.get("meta_styles/closing_block_only")
    assert page.meta == {"hello": "world"}


def test_jekyll_style_meta(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    jekyll_style = pages.get("meta_styles/jekyll_style")
    assert jekyll_style.meta == {"hello": "world"}
    assert jekyll_style.body == "Foo"
    filename = os.path.join(pages.root, "meta_styles", "jekyll_style.html")
    with open(filename, "r") as f_:
        lines = f_.readlines()
    with open(filename, "w") as f_:
        f_.write("\n".join(lines[1:]))
    pages.reload()
    jekyll_style = pages.get("meta_styles/jekyll_style")
    assert jekyll_style.meta == {"hello": "world"}
    assert jekyll_style.body == "Foo"


def test_yaml_style_meta(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    yaml_style = pages.get("meta_styles/yaml_style")
    yaml_style.meta == {"hello": "world"}
    yaml_style.body == "Foo"
    filename = os.path.join(pages.root, "meta_styles", "yaml_style.html")
    with open(filename, "r") as f_:
        lines = f_.readlines()
    with open(filename, "w") as f_:
        f_.write("\n".join(lines[1:]))
    pages.reload()
    yaml_style = pages.get("meta_styles/yaml_style")
    yaml_style.meta == {"hello": "world"}
    yaml_style.body == "Foo"


def test_multi_line(app_with_context, flatpages_factory):
    pages = flatpages_factory(app_with_context)
    multi_line = pages.get("meta_styles/multi_line")
    assert multi_line.body == "Foo"
    assert "multi_line_string" in multi_line.meta
    assert "\n" in multi_line.meta["multi_line_string"]


def test_parser_error(app_with_context, temp_pages):
    pages = temp_pages(app_with_context)
    with open(os.path.join(pages.root, "bad_file_test.html"), "w") as f:
        f.write("Hello World \u000b")
    with pytest.raises(yaml.reader.ReaderError, match=r".*bad_file_test.*"):
        pages.get("bad_file_test")
