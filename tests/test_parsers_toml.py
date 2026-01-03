from flask_flatpages.parsers.toml import toml_parser


def test_toml_parser():
    content = """+++
title = "Test Page"
author = "John Doe"
+++

# This is a test page
"""
    metadata, body = toml_parser(content, "test.md")
    assert metadata == {"title": "Test Page", "author": "John Doe"}
    assert body == "# This is a test page\n"


def test_toml_parser_no_metadata():
    content = """# This is a test page without metadata"""
    metadata, body = toml_parser(content, "test_no_meta.md")
    assert metadata == {}
    assert body == "# This is a test page without metadata"


def test_toml_parser_leading_blank_lines():
    content = """+++
title = "Test Page"
author = "John Doe"
+++

# This is a test page
"""
    metadata, body = toml_parser(content, "test.md")
    assert metadata == {"title": "Test Page", "author": "John Doe"}
    assert body == "# This is a test page\n"


def test_toml_parser_missing_closing_delimiter():
    content = """+++
title = "Test Page"
author = "John Doe"

# This is a test page
"""
    metadata, body = toml_parser(content, "test.md")
    assert metadata == {}
    assert body == content.replace("+++\n", "", 1)


def test_toml_parser_empty():
    content = """+++
+++
"""
    metadata, body = toml_parser(content, "test_empty_meta.md")
    assert metadata == {}
    assert body == ""


def test_toml_parser_yaml_style_delimiters_are_ignored():
    # If a file uses YAML-style delimiters (---) but no +++ TOML delimiters,
    # the TOML parser should not treat it as TOML metadata and should return
    # an empty metadata dict with the original content as the body.
    content = """---
title = "YAML Title"
---
# Body
"""
    metadata, body = toml_parser(content, "yaml_delim.md")
    assert metadata == {}
    assert body == content


def test_toml_parser_yaml_doc_end_marker_is_ignored():
    # Likewise, a YAML document ending with ... should not be parsed as TOML
    # front matter when +++ is absent.
    content = """---
title = "YAML Title"
...
# Body
"""
    metadata, body = toml_parser(content, "yaml_doc_end.md")
    assert metadata == {}
    assert body == content
