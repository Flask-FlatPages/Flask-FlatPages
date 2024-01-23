"""Module for YAML metadata parser."""
import operator
from itertools import takewhile

import six
from yaml import (
    BlockMappingStartToken,
    BlockSequenceStartToken,
    DocumentEndToken,
    DocumentStartToken,
    FlowMappingStartToken,
    FlowSequenceStartToken,
    KeyToken,
    SafeLoader,
    ScalarToken,
)

from ..utils import force_unicode, NamedStringIO


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


def legacy_parser(content):
    """Legacy YAML parser."""
    lines = iter(content.split("\n"))

    # Read lines until an empty line is encountered.
    meta = "\n".join(takewhile(operator.methodcaller("strip"), lines))
    # The rest is the content. `lines` is an iterator so it continues
    # where `itertools.takewhile` left it.
    content = "\n".join(lines)
    return meta, content


def libyaml_parser(content, path):
    """YAML parser."""
    if not six.PY3:
        content = force_unicode(content)
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
    if not six.PY3:
        return force_unicode(meta), force_unicode(content)
    return meta, content
