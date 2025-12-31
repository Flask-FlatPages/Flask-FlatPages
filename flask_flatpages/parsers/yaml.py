"""Module for YAML metadata parser."""

from __future__ import annotations

import operator
from io import StringIO
from itertools import takewhile
from typing import Any

from yaml import (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    DocumentEndToken,
    DocumentStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
    KeyToken,
    safe_load_all,
    SafeLoader,
    ScalarToken,
)

from ..utils import NamedStringIO


START_TOKENS = (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    DocumentStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
    KeyToken,
)


def _check_continue_parsing_tokens(token):
    return not (
        isinstance(token, (DocumentStartToken, DocumentEndToken))
        or token is None
    )


def _check_newline_token(token):
    return (
        isinstance(token, ScalarToken)
        and token.style is None
        and "\n" in token.value
    )


def load_meta(meta_yaml: str, path: str) -> dict[str, Any]:
    """Store a dict of metadata parsed from the YAML header of the file."""
    meta = {}
    for doc in safe_load_all(StringIO(meta_yaml)):
        if doc is not None:
            meta.update(doc)
    # YAML documents can be any type but we want a dict
    # eg. yaml.safe_load('') -> None
    #     yaml.safe_load('- 1\n- a') -> [1, 'a']
    if not meta:
        return {}
    if not isinstance(meta, dict):
        raise ValueError(
            "Expected a dict in metadata for '{0}', got {1}".format(
                path, type(meta).__name__
            )
        )
    return meta


def legacy_parser(content, path):
    """Legacy YAML parser."""
    lines = iter(content.split("\n"))

    # Read lines until an empty line is encountered.
    meta_yaml = "\n".join(takewhile(operator.methodcaller("strip"), lines))
    meta = load_meta(meta_yaml, path)
    # The rest is the content. `lines` is an iterator so it continues
    # where `itertools.takewhile` left it.
    content = "\n".join(lines)
    return meta, content


def libyaml_parser(content, path):
    """YAML parser."""
    yaml_loader = SafeLoader(NamedStringIO(content, path))
    yaml_loader.get_token()  # Get stream start token
    token = yaml_loader.get_token()
    if not isinstance(token, START_TOKENS):
        meta = ""
        content = content.lstrip("\n")
    else:
        lines = content.split("\n")
        if isinstance(token, DocumentStartToken):
            token = yaml_loader.get_token()
        newline_token = None
        while _check_continue_parsing_tokens(token):
            try:
                token = yaml_loader.get_token()
                if _check_newline_token(token) and newline_token is None:
                    newline_token = token
            except Exception:
                break
        if token is None and newline_token is None:
            meta = content
            content = ""
        else:
            if token is not None:
                meta_end_line = token.end_mark.line + 1
            else:
                meta_end_line = newline_token.start_mark.line
                meta_end_line += lines[meta_end_line:].index("")
            meta = "\n".join(lines[:meta_end_line])
            content = "\n".join(lines[meta_end_line:]).lstrip("\n")
    meta_dict = load_meta(meta, path)
    return meta_dict, content
