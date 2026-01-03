"""Module for TOML metadata parser."""

from __future__ import annotations
from typing import Any

try:
    # stdlib tomllib (Py3.11+)
    import tomllib as _toml
except ImportError:
    # Try tomli (Py3)
    import tomli as _toml


def toml_parser(content: str, path: str) -> tuple[dict[str, Any], str]:
    """TOML parser."""
    lines = content.split("\n")

    start = False
    end_idx = 0
    for idx, line in enumerate(lines, 1):
        if line == "+++":
            if start:
                end_idx = idx
                break
            start = True

    toml_str = "\n".join([line for line in lines[:end_idx] if line != "+++"])
    meta = _toml.loads(toml_str)
    text = "\n".join(
        [line for line in lines[end_idx:] if line != "+++"]
    ).lstrip("\n")
    return meta, text
