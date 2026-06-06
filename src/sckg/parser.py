"""AST-based source code parser for symbol and edge extraction.

Docs: parser.doc.md
"""

import ast
import os
from pathlib import Path
from typing import Any


# ── Data Structures ──────────────────────────────────────────────────────

class SymbolNode:
    """Represents a code symbol (function, class, variable, module)."""

    def __init__(
        self,
        name: str,
        kind: str,  # function | class | module | variable
        filepath: str,
        line: int = 0,
        docstring: str = "",
        signature: str = "",
        parent: str | None = None,
    ):
        self.name = name
        self.kind = kind
        self.filepath = filepath
        self.line = line
        self.docstring = docstring
        self.signature = signature
        self.parent = parent

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
        }

    def _id(self) -> str:
        # Unique ID: filepath::name (with parent for nested)
        if self.parent:
            return f"{self.filepath}::{self.parent}.{self.name}"
        return f"{self.filepath}::{self.name}"


class Edge:
    """Represents a relationship between two symbols."""

    def __init__(self, source: str, target: str, relation: str, line: int = 0):
        self.source = source
        self.target = target
        self.relation = relation
        self.line = line

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "line": self.line,
        }


# ── AST Visitors ───────────────────────────────────────────────────────────

class SymbolExtractor(ast.NodeVisitor):
    """Walk an AST and collect symbols + edges for a single file."""

    def __init__(self, filepath: str, source: str):
        self.filepath = filepath
        self.source = source
        self.symbols: list[SymbolNode] = []
        self.edges: list[Edge] = []
        self._imports: dict[str, str] = {}  # alias → fully qualified name
        self._current_class: str | None = None

    # ── Module-level ──────────────────────────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._handle_function(node, is_async=True)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool = False) -> None:
        docstring = ast.get_docstring(node) or ""
        sig = self._signature(node, is_async)
        parent = self._current_class
        sym = SymbolNode(
            name=node.name,
            kind="function",
            filepath=self.filepath,
            line=node.lineno,
            docstring=docstring,
            signature=sig,
            parent=parent,
        )
        self.symbols.append(sym)

        # Collect calls inside this function
        self._collect_calls(node, sym._id())
        # Collect nested definitions
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        docstring = ast.get_docstring(node) or ""
        bases = [self._name(base) for base in node.bases]
        sig = f"({', '.join(bases)})" if bases else "()"
        sym = SymbolNode(
            name=node.name,
            kind="class",
            filepath=self.filepath,
            line=node.lineno,
            docstring=docstring,
            signature=sig,
        )
        self.symbols.append(sym)
        class_id = sym._id()

        # Inheritance edges
        for base in bases:
            self.edges.append(Edge(class_id, base, "inherits", node.lineno))

        # Visit methods
        prev_class = self._current_class
        self._current_class = node.name
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._handle_function(child, is_async=isinstance(child, ast.AsyncFunctionDef))
        self._current_class = prev_class

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            name = alias.asname or alias.name
            self._imports[name] = alias.name
            self.edges.append(Edge(
                source=self.filepath,
                target=alias.name,
                relation="imports",
                line=node.lineno,
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        for alias in node.names:
            name = alias.asname or alias.name
            full = f"{module}.{alias.name}" if module else alias.name
            self._imports[name] = full
            self.edges.append(Edge(
                source=self.filepath,
                target=full,
                relation="imports",
                line=node.lineno,
            ))

    def _collect_calls(self, node: ast.AST, caller_id: str) -> None:
        """Recursively find all Call nodes inside a function/class body."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                callee = self._name(child.func)
                if callee:
                    self.edges.append(Edge(caller_id, callee, "calls", child.lineno))

    # ── Helpers ─────────────────────────────────────────────────────────

    def _signature(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> str:
        args = []
        # positional args
        for arg in node.args.args:
            args.append(self._arg_str(arg))
        # vararg
        if node.args.vararg:
            args.append(f"*{self._arg_str(node.args.vararg)}")
        # kwonly
        for arg in node.args.kwonlyargs:
            args.append(self._arg_str(arg))
        # kwarg
        if node.args.kwarg:
            args.append(f"**{self._arg_str(node.args.kwarg)}")
        prefix = "async def " if is_async else "def "
        return f"{prefix}{node.name}({', '.join(args)})"

    def _arg_str(self, arg: ast.arg) -> str:
        if arg.annotation:
            return f"{arg.arg}: {self._name(arg.annotation)}"
        return arg.arg

    def _name(self, node: ast.AST | None) -> str:
        """Best-effort string representation of an AST expression node."""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._name(node.value)}.{node.attr}"
        if isinstance(node, ast.Call):
            return self._name(node.func)
        if isinstance(node, ast.Subscript):
            return self._name(node.value)
        if isinstance(node, ast.Constant):
            return repr(node.value)
        return ""


# ── Public API ───────────────────────────────────────────────────────────

def parse_file(filepath: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Parse a single Python file and return symbols + edges."""
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    extractor = SymbolExtractor(str(path), source)
    extractor.visit(tree)
    return extractor.symbols, extractor.edges


def parse_directory(repo_path: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Recursively parse all .py files in a directory."""
    all_symbols: list[SymbolNode] = []
    all_edges: list[Edge] = []
    repo = Path(repo_path)

    for py_file in repo.rglob("*.py"):
        # Skip hidden directories and virtual envs
        parts = py_file.relative_to(repo).parts
        if any(p.startswith(".") or p in ("venv", ".venv", "__pycache__") for p in parts):
            continue
        try:
            syms, edges = parse_file(py_file)
            all_symbols.extend(syms)
            all_edges.extend(edges)
        except SyntaxError as exc:
            # Gracefully skip files with syntax errors
            print(f"[WARN] Skipping {py_file}: {exc}")
    return all_symbols, all_edges
