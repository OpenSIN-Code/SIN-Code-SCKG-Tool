"""Base data structures shared across all language parsers.

Docs: parsers/base.doc.md
"""

from __future__ import annotations

from typing import Any


class SymbolNode:
    """Represents a code symbol (function, class, variable, module, etc.)."""

    def __init__(
        self,
        name: str,
        kind: str,  # function | class | module | variable | struct | interface | method | component
        filepath: str,
        line: int = 0,
        docstring: str = "",
        signature: str = "",
        parent: str | None = None,
        language: str = "python",
        repo: str = "",
    ):
        self.name = name
        self.kind = kind
        self.filepath = filepath
        self.line = line
        self.docstring = docstring
        self.signature = signature
        self.parent = parent
        self.language = language
        self.repo = repo

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self._id(),
            "name": self.name,
            "kind": self.kind,
            "filepath": self.filepath,
            "line": self.line,
            "docstring": self.docstring,
            "signature": self.signature,
            "parent": self.parent,
            "language": self.language,
            "repo": self.repo,
        }

    def _id(self) -> str:
        # Unique ID: filepath::name (with parent for nested)
        if self.parent:
            return f"{self.filepath}::{self.parent}.{self.name}"
        return f"{self.filepath}::{self.name}"


class Edge:
    """Represents a relationship between two symbols."""

    def __init__(self, source: str, target: str, relation: str, line: int = 0, repo: str = ""):
        self.source = source
        self.target = target
        self.relation = relation
        self.line = line
        self.repo = repo

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "line": self.line,
            "repo": self.repo,
        }
