"""TypeScript / TSX / JavaScript / JSX parser for SCKG.

Supports tree-sitter (preferred) and a lightweight regex fallback.
Docs: parsers/typescript_parser.doc.md
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode

# ── tree-sitter bootstrap ──────────────────────────────────────────────────────

try:
    from tree_sitter import Language, Parser
    from tree_sitter_typescript import language_tsx

    _TSX_LANGUAGE = Language(language_tsx())
    _PARSER = Parser(language=_TSX_LANGUAGE)
    _TREE_SITTER_OK = True
except Exception:  # noqa: BLE001
    _TREE_SITTER_OK = False
    _PARSER = None


# ── Regex fallback patterns ────────────────────────────────────────────────────

_RE_FUNCTION = re.compile(r"(?:export\s+(?:default\s+)?)?function\s+(\w+)")
_RE_ARROW = re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=[^=]*=>")
_RE_CLASS = re.compile(r"(?:export\s+)?class\s+(\w+)")
_RE_INTERFACE = re.compile(r"(?:export\s+)?interface\s+(\w+)")
_RE_IMPORT = re.compile(r"import\s+(?:(?:\{[^}]+\}|\w+)\s+from\s+)?['\"]([^'\"]+)['\"];?")
_RE_EXPORT = re.compile(r"export\s+(?:default\s+)?(?:class|function|interface|const|let|var)?\s*(\w+)?")
_RE_CALL = re.compile(r"(\w+)\s*\(")
_RE_JSX = re.compile(r"<([A-Z]\w*)(?:\s|/>|>)")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _node_text(node: Any) -> str:
    """Safely extract text from a tree-sitter node, decoding bytes if needed."""
    text = node.text
    if isinstance(text, bytes):
        return text.decode("utf-8", errors="replace")
    if isinstance(text, str):
        return text
    return str(text)


# ── Public API ─────────────────────────────────────────────────────────────────

def parse_file(filepath: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Parse a single TS/TSX/JS/JSX file and return symbols + edges."""
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    if _TREE_SITTER_OK:
        return _parse_with_tree_sitter(str(path), source)
    return _parse_with_regex(str(path), source)


# ── tree-sitter implementation ───────────────────────────────────────────────

def _parse_with_tree_sitter(filepath: str, source: str) -> tuple[list[SymbolNode], list[Edge]]:
    assert _PARSER is not None
    tree = _PARSER.parse(source.encode("utf-8"))
    root = tree.root_node

    symbols: list[SymbolNode] = []
    edges: list[Edge] = []
    imports: dict[str, str] = {}  # alias → source module

    # First pass: collect imports
    for node in root.children:
        if node.type == "import_statement":
            _process_import(node, filepath, edges, imports)

    # Second pass: collect symbols and calls
    for node in root.children:
        if node.type == "export_statement":
            _process_export(node, filepath, symbols, edges, imports)
        elif node.type == "function_declaration":
            _process_function(node, filepath, symbols, edges, imports)
        elif node.type == "class_declaration":
            _process_class(node, filepath, symbols, edges, imports)
        elif node.type == "interface_declaration":
            _process_interface(node, filepath, symbols, edges, imports)
        elif node.type == "lexical_declaration":
            _process_lexical(node, filepath, symbols, edges, imports)
        elif node.type == "expression_statement":
            _scan_calls(node, filepath, edges, None, imports)

    return symbols, edges


def _process_import(
    node: Any,
    filepath: str,
    edges: list[Edge],
    imports: dict[str, str],
) -> None:
    """Extract import edges and alias map."""
    source = None
    for child in node.children:
        if child.type == "string":
            source = _node_text(child)[1:-1]  # strip quotes
            break
    if not source:
        return

    for child in node.children:
        if child.type == "import_clause":
            # default import: identifier
            for sub in child.children:
                if sub.type == "identifier":
                    imports[_node_text(sub)] = source
                    edges.append(Edge(filepath, source, "imports", sub.start_point[0] + 1))
                elif sub.type == "named_imports":
                    for spec in sub.children:
                        if spec.type == "import_specifier":
                            names = [_node_text(c) for c in spec.children if c.type == "identifier"]
                            alias = names[-1] if names else _node_text(spec)
                            imports[alias] = source
                            edges.append(Edge(filepath, f"{source}::{alias}", "imports", spec.start_point[0] + 1))


def _process_export(
    node: Any,
    filepath: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
) -> None:
    """Handle export statements: export function/class/const/default."""
    exported_name = None
    is_default = False
    for child in node.children:
        if child.type == "default":
            is_default = True
        elif child.type in ("function_declaration", "class_declaration", "interface_declaration"):
            if child.type == "function_declaration":
                _process_function(child, filepath, symbols, edges, imports, is_export=True, is_default=is_default)
            elif child.type == "class_declaration":
                _process_class(child, filepath, symbols, edges, imports, is_export=True, is_default=is_default)
            elif child.type == "interface_declaration":
                _process_interface(child, filepath, symbols, edges, imports, is_export=True)
            return
        elif child.type == "lexical_declaration":
            _process_lexical(child, filepath, symbols, edges, imports, is_export=True, is_default=is_default)
            return

    # Bare export (e.g., export { foo })
    if is_default:
        edges.append(Edge(filepath, "default", "exports", node.start_point[0] + 1))
    else:
        edges.append(Edge(filepath, "*", "exports", node.start_point[0] + 1))


def _process_function(
    node: Any,
    filepath: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
    is_export: bool = False,
    is_default: bool = False,
) -> None:
    """Extract a function declaration and calls inside it."""
    name_node = _child_by_type(node, "identifier")
    name = _node_text(name_node) if name_node else "anonymous"
    line = node.start_point[0] + 1

    sig = _signature_from_params(node)
    sym = SymbolNode(
        name=name,
        kind="function",
        filepath=filepath,
        line=line,
        docstring="",
        signature=sig,
        language="typescript",
    )
    symbols.append(sym)
    sym_id = sym._id()

    if is_export:
        edges.append(Edge(filepath, name, "exports", line))
    if is_default:
        edges.append(Edge(filepath, "default", "exports", line))

    body = _child_by_type(node, "statement_block")
    if body:
        _scan_calls(body, filepath, edges, sym_id, imports)


def _process_class(
    node: Any,
    filepath: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
    is_export: bool = False,
    is_default: bool = False,
) -> None:
    """Extract a class declaration, methods, and inheritance."""
    name_node = _child_by_type(node, "type_identifier")
    name = _node_text(name_node) if name_node else "Anonymous"
    line = node.start_point[0] + 1

    # Inheritance
    bases: list[str] = []
    for child in node.children:
        if child.type == "class_heritage":
            for sub in child.children:
                if sub.type == "extends_clause":
                    for ext in sub.children:
                        if ext.type in ("identifier", "type_identifier"):
                            bases.append(_node_text(ext))

    sig = f"({', '.join(bases)})" if bases else "()"
    sym = SymbolNode(
        name=name,
        kind="class",
        filepath=filepath,
        line=line,
        docstring="",
        signature=sig,
        language="typescript",
    )
    symbols.append(sym)
    class_id = sym._id()

    for base in bases:
        edges.append(Edge(class_id, base, "inherits", line))
    if is_export:
        edges.append(Edge(filepath, name, "exports", line))
    if is_default:
        edges.append(Edge(filepath, "default", "exports", line))

    body = _child_by_type(node, "class_body")
    if body:
        for child in body.children:
            if child.type in ("method_definition", "public_field_definition"):
                _process_method(child, filepath, name, symbols, edges, imports)
            else:
                _scan_calls(child, filepath, edges, class_id, imports)


def _process_method(
    node: Any,
    filepath: str,
    class_name: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
) -> None:
    """Extract a class method."""
    name_node = _child_by_type(node, "property_identifier")
    name = _node_text(name_node) if name_node else "anonymous"
    line = node.start_point[0] + 1

    sig = _signature_from_params(node)
    sym = SymbolNode(
        name=name,
        kind="function",
        filepath=filepath,
        line=line,
        docstring="",
        signature=sig,
        parent=class_name,
        language="typescript",
    )
    symbols.append(sym)
    sym_id = sym._id()

    body = _child_by_type(node, "statement_block")
    if body:
        _scan_calls(body, filepath, edges, sym_id, imports)


def _process_interface(
    node: Any,
    filepath: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
    is_export: bool = False,
) -> None:
    """Extract an interface declaration."""
    name_node = _child_by_type(node, "type_identifier")
    name = _node_text(name_node) if name_node else "Anonymous"
    line = node.start_point[0] + 1

    sym = SymbolNode(
        name=name,
        kind="interface",
        filepath=filepath,
        line=line,
        docstring="",
        signature="()",
        language="typescript",
    )
    symbols.append(sym)
    if is_export:
        edges.append(Edge(filepath, name, "exports", line))


def _process_lexical(
    node: Any,
    filepath: str,
    symbols: list[SymbolNode],
    edges: list[Edge],
    imports: dict[str, str],
    is_export: bool = False,
    is_default: bool = False,
) -> None:
    """Extract const/let declarations, including arrow functions."""
    for child in node.children:
        if child.type == "variable_declarator":
            name_node = _child_by_type(child, "identifier")
            name = _node_text(name_node) if name_node else "anonymous"
            line = child.start_point[0] + 1

            arrow = _child_by_type(child, "arrow_function")
            if arrow:
                sig = _signature_from_params(arrow)
                sym = SymbolNode(
                    name=name,
                    kind="function",
                    filepath=filepath,
                    line=line,
                    docstring="",
                    signature=sig,
                    language="typescript",
                )
                symbols.append(sym)
                sym_id = sym._id()
                body = _child_by_type(arrow, "statement_block")
                if body:
                    _scan_calls(body, filepath, edges, sym_id, imports)
            else:
                sym = SymbolNode(
                    name=name,
                    kind="variable",
                    filepath=filepath,
                    line=line,
                    docstring="",
                    signature="",
                    language="typescript",
                )
                symbols.append(sym)

            if is_export:
                edges.append(Edge(filepath, name, "exports", line))
            if is_default:
                edges.append(Edge(filepath, "default", "exports", line))


def _scan_calls(
    node: Any,
    filepath: str,
    edges: list[Edge],
    caller_id: str | None,
    imports: dict[str, str],
) -> None:
    """Recursively find call expressions and JSX elements."""
    # Walk the whole subtree; node.walk() is available in tree-sitter 0.25
    # We iterate over the node and its descendants via a simple recursive helper
    _scan_calls_recursive(node, filepath, edges, caller_id, imports)


def _scan_calls_recursive(
    node: Any,
    filepath: str,
    edges: list[Edge],
    caller_id: str | None,
    imports: dict[str, str],
) -> None:
    for child in node.children:
        if child.type == "call_expression":
            callee = _call_name(child)
            if callee:
                edges.append(Edge(caller_id or filepath, callee, "calls", child.start_point[0] + 1))
        elif child.type in ("jsx_element", "jsx_self_closing_element"):
            comp = _jsx_component_name(child)
            if comp:
                edges.append(Edge(caller_id or filepath, comp, "calls", child.start_point[0] + 1))
        _scan_calls_recursive(child, filepath, edges, caller_id, imports)


def _call_name(node: Any) -> str | None:
    """Best-effort name extraction from a call_expression."""
    func = node.children[0] if node.children else None
    if func is None:
        return None
    if func.type in ("identifier", "type_identifier"):
        return _node_text(func)
    if func.type == "member_expression":
        parts = []
        for c in func.children:
            if c.type in ("identifier", "property_identifier"):
                parts.append(_node_text(c))
        return ".".join(parts) if parts else None
    return None


def _jsx_component_name(node: Any) -> str | None:
    """Extract component name from a JSX element."""
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "member_expression"):
            text = _node_text(child)
            # Only treat PascalCase identifiers as components
            if text and text[0].isupper():
                return text
        # For jsx_opening_element / jsx_self_closing_element inner structure
        if child.type in ("jsx_opening_element", "jsx_closing_element"):
            for sub in child.children:
                if sub.type in ("identifier", "type_identifier"):
                    sub_text = _node_text(sub)
                    if sub_text and sub_text[0].isupper():
                        return sub_text
    return None


def _signature_from_params(node: Any) -> str:
    """Build a rough signature string from formal_parameters."""
    params = _child_by_type(node, "formal_parameters")
    if not params:
        return "()"
    args: list[str] = []
    for child in params.children:
        if child.type == "identifier":
            args.append(_node_text(child))
        elif child.type == "required_parameter":
            # e.g., (a: number) → extract identifier
            for sub in child.children:
                if sub.type == "identifier":
                    args.append(_node_text(sub))
                    break
    return f"({', '.join(args)})"


def _child_by_type(node: Any, type_name: str) -> Any | None:
    for child in node.children:
        if child.type == type_name:
            return child
    return None


# ── Regex fallback implementation ──────────────────────────────────────────────

def _parse_with_regex(filepath: str, source: str) -> tuple[list[SymbolNode], list[Edge]]:
    symbols: list[SymbolNode] = []
    edges: list[Edge] = []
    lines = source.splitlines()

    for line_no, line in enumerate(lines, start=1):
        # Functions
        for m in _RE_FUNCTION.finditer(line):
            sym = SymbolNode(
                name=m.group(1),
                kind="function",
                filepath=filepath,
                line=line_no,
                docstring="",
                signature="()",
                language="typescript",
            )
            symbols.append(sym)

        # Arrow functions
        for m in _RE_ARROW.finditer(line):
            sym = SymbolNode(
                name=m.group(1),
                kind="function",
                filepath=filepath,
                line=line_no,
                docstring="",
                signature="()",
                language="typescript",
            )
            symbols.append(sym)

        # Classes
        for m in _RE_CLASS.finditer(line):
            sym = SymbolNode(
                name=m.group(1),
                kind="class",
                filepath=filepath,
                line=line_no,
                docstring="",
                signature="()",
                language="typescript",
            )
            symbols.append(sym)

        # Interfaces
        for m in _RE_INTERFACE.finditer(line):
            sym = SymbolNode(
                name=m.group(1),
                kind="interface",
                filepath=filepath,
                line=line_no,
                docstring="",
                signature="()",
                language="typescript",
            )
            symbols.append(sym)

        # Imports
        for m in _RE_IMPORT.finditer(line):
            edges.append(Edge(filepath, m.group(1), "imports", line_no))

        # Exports
        for m in _RE_EXPORT.finditer(line):
            name = m.group(1) or "*"
            edges.append(Edge(filepath, name, "exports", line_no))

        # Calls (generic function calls)
        for m in _RE_CALL.finditer(line):
            name = m.group(1)
            # Avoid keywords
            if name not in ("if", "while", "for", "switch", "catch", "return"):
                edges.append(Edge(filepath, name, "calls", line_no))

        # JSX components
        for m in _RE_JSX.finditer(line):
            edges.append(Edge(filepath, m.group(1), "calls", line_no))

    return symbols, edges
