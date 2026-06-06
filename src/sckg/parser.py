"""AST-based source code parser for symbol and edge extraction.

Re-exports SymbolNode and Edge from sckg.parsers.base for backward
compatibility, and re-exports parse_file and parse_directory from the
multi-language dispatcher in sckg.parsers.

Docs: parser.doc.md
"""

from sckg.parsers.base import Edge, SymbolNode
from sckg.parsers import parse_directory, parse_file

__all__ = ["Edge", "SymbolNode", "parse_directory", "parse_file"]
