"""Python package for metadata parsers."""

from .yaml import legacy_parser, libyaml_parser

__all__ = ["legacy_parser", "libyaml_parser"]
