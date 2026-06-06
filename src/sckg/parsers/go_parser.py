"""Tree-sitter Go parser for symbol and edge extraction.

Docs: go_parser.doc.md
"""

from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode


def _node_text(node: Any, source: bytes) -> str:
    """Extract the UTF-8 text span covered by a tree-sitter node."""
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _find_child(node: Any, *types: str) -> Any | None:
    """Return the first direct child matching one of the given types."""
    for child in node.children:
        if child.type in types:
            return child
    return None


def _find_children(node: Any, *types: str) -> list[Any]:
    """Return all direct children matching one of the given types."""
    return [c for c in node.children if c.type in types]


def _func_name(node: Any, source: bytes) -> str:
    """Best-effort name string for a call-expression node."""
    # call_expression -> identifier  (local call)
    # call_expression -> selector_expression -> identifier . field_identifier
    # call_expression -> selector_expression -> selector_expression (nested)
    if node.type == "identifier":
        return _node_text(node, source)
    if node.type == "selector_expression":
        parts: list[str] = []
        current = node
        while current.type == "selector_expression":
            # selector_expression children: lhs, ".", rhs
            # Search for field_identifier first to avoid picking the lhs identifier
            rhs = _find_child(current, "field_identifier")
            if not rhs:
                rhs = _find_child(current, "identifier")
            lhs = current.children[0] if current.children else None
            if rhs:
                parts.append(_node_text(rhs, source))
            current = lhs
        if current and current.type in ("identifier", "selector_expression"):
            # If we stopped at identifier, prepend it
            if current.type == "identifier":
                parts.append(_node_text(current, source))
            elif current.type == "selector_expression":
                # Should not happen — continue flattening
                pass
        parts.reverse()
        return ".".join(parts)
    if node.type == "parenthesized_expression":
        # (pkg.Foo)(args) — unwrap one level
        inner = _find_child(node, "selector_expression", "identifier")
        if inner:
            return _func_name(inner, source)
    return ""


class GoSymbolExtractor:
    """Walk a tree-sitter Go AST and collect symbols + edges for a single file."""

    def __init__(self, filepath: str, source: bytes, tree: Any):
        self.filepath = filepath
        self.source = source
        self.tree = tree
        self.symbols: list[SymbolNode] = []
        self.edges: list[Edge] = []
        self._imports: dict[str, str] = {}  # alias → import path
        self._current_struct: str | None = None

    def extract(self) -> tuple[list[SymbolNode], list[Edge]]:
        """Entry point: walk the tree and return (symbols, edges)."""
        self._walk(self.tree.root_node)
        return self.symbols, self.edges

    def _walk(self, node: Any) -> None:
        """Recursively visit interesting top-level nodes."""
        if node.type == "import_declaration":
            self._handle_import(node)
        elif node.type == "type_declaration":
            self._handle_type_declaration(node)
        elif node.type == "function_declaration":
            self._handle_function_declaration(node)
        elif node.type == "method_declaration":
            self._handle_method_declaration(node)
        else:
            for child in node.children:
                self._walk(child)

    # ── Import handling ──────────────────────────────────────────────────────────

    def _handle_import(self, node: Any) -> None:
        # import_declaration may contain import_spec or import_spec_list
        for child in node.children:
            if child.type == "import_spec":
                self._extract_import_spec(child)
            elif child.type == "import_spec_list":
                for spec in child.children:
                    if spec.type == "import_spec":
                        self._extract_import_spec(spec)

    def _extract_import_spec(self, spec: Any) -> None:
        path_node = _find_child(spec, "interpreted_string_literal", "raw_string_literal")
        if not path_node:
            return
        path_text = _node_text(path_node, self.source)
        # Remove surrounding quotes
        import_path = path_text.strip('"`')

        # Check for alias
        alias_node = _find_child(spec, "identifier", "_")
        if alias_node:
            alias = _node_text(alias_node, self.source)
            self._imports[alias] = import_path
        else:
            # Default alias is the last path segment
            alias = import_path.split("/")[-1]
            self._imports[alias] = import_path

        self.edges.append(
            Edge(
                source=self.filepath,
                target=import_path,
                relation="imports",
                line=path_node.start_point[0] + 1,
            )
        )

    # ── Type declarations (struct / interface) ───────────────────────────────────

    def _handle_type_declaration(self, node: Any) -> None:
        # type_declaration -> type_spec -> type_identifier + struct_type/interface_type
        type_spec = _find_child(node, "type_spec")
        if not type_spec:
            for child in node.children:
                self._walk(child)
            return

        name_node = _find_child(type_spec, "type_identifier")
        if not name_node:
            return
        name = _node_text(name_node, self.source)
        kind = "type"  # generic fallback

        struct_node = _find_child(type_spec, "struct_type")
        interface_node = _find_child(type_spec, "interface_type")
        if struct_node:
            kind = "struct"
        elif interface_node:
            kind = "interface"

        sym = SymbolNode(
            name=name,
            kind=kind,
            filepath=self.filepath,
            line=name_node.start_point[0] + 1,
            docstring="",
            signature="",
            parent=None,
            language="go",
        )
        self.symbols.append(sym)

        # If it's a struct, walk body for embedded fields (inheritance-like)
        if struct_node:
            prev_struct = self._current_struct
            self._current_struct = name
            field_list = _find_child(struct_node, "field_declaration_list")
            if field_list:
                for field in field_list.children:
                    if field.type == "field_declaration":
                        # embedded field has no field_identifier, just type_identifier
                        type_ids = _find_children(field, "type_identifier", "qualified_type")
                        if type_ids and not _find_child(field, "field_identifier"):
                            # This is an embedded type (inheritance edge)
                            for tid in type_ids:
                                self.edges.append(
                                    Edge(
                                        source=sym._id(),
                                        target=_node_text(tid, self.source),
                                        relation="inherits",
                                        line=tid.start_point[0] + 1,
                                    )
                                )
            self._current_struct = prev_struct

    # ── Function declarations ────────────────────────────────────────────────────

    def _handle_function_declaration(self, node: Any) -> None:
        name_node = _find_child(node, "identifier")
        if not name_node:
            return
        name = _node_text(name_node, self.source)
        line = name_node.start_point[0] + 1

        sig = self._signature(node, name)
        sym = SymbolNode(
            name=name,
            kind="function",
            filepath=self.filepath,
            line=line,
            docstring="",
            signature=sig,
            parent=None,
            language="go",
        )
        self.symbols.append(sym)
        self._collect_calls(node, sym._id())

    # ── Method declarations ──────────────────────────────────────────────────────

    def _handle_method_declaration(self, node: Any) -> None:
        # method_declaration -> receiver param list, name, param list, result?, block
        name_node = _find_child(node, "field_identifier")
        if not name_node:
            return
        name = _node_text(name_node, self.source)
        line = name_node.start_point[0] + 1

        receiver = self._receiver_type(node)
        sig = self._signature(node, name, receiver=receiver)
        parent = receiver.lstrip("*") if receiver else None

        sym = SymbolNode(
            name=name,
            kind="method",
            filepath=self.filepath,
            line=line,
            docstring="",
            signature=sig,
            parent=parent,
            language="go",
        )
        self.symbols.append(sym)
        self._collect_calls(node, sym._id())

    def _receiver_type(self, node: Any) -> str:
        """Extract the receiver type name from a method_declaration."""
        # The first parameter_list is the receiver
        param_lists = _find_children(node, "parameter_list")
        if not param_lists:
            return ""
        receiver_list = param_lists[0]
        # parameter_list -> parameter_declaration -> pointer_type / type_identifier
        param_decl = _find_child(receiver_list, "parameter_declaration")
        if not param_decl:
            return ""
        type_node = _find_child(param_decl, "pointer_type", "type_identifier", "qualified_type")
        if not type_node:
            return ""
        if type_node.type == "pointer_type":
            inner = _find_child(type_node, "type_identifier", "qualified_type")
            if inner:
                return "*" + _node_text(inner, self.source)
        return _node_text(type_node, self.source)

    # ── Signature builder ────────────────────────────────────────────────────────

    def _signature(
        self, node: Any, name: str, receiver: str | None = None
    ) -> str:
        """Build a Go-like signature string for display."""
        parts = ["func"]
        if receiver:
            parts.append(f"({receiver})")
        parts.append(name)

        # parameter lists: skip receiver (first) if method
        param_lists = _find_children(node, "parameter_list")
        if node.type == "method_declaration" and len(param_lists) > 1:
            param_lists = param_lists[1:]

        if param_lists:
            params_text = _node_text(param_lists[0], self.source)
            parts.append(params_text)

        # result type (single or multiple return)
        result_node = _find_child(node, "type_identifier", "qualified_type", "result")
        if result_node:
            if result_node.type == "result":
                parts.append(_node_text(result_node, self.source))
            else:
                parts.append(_node_text(result_node, self.source))

        return " ".join(parts)

    # ── Call collection ──────────────────────────────────────────────────────────

    def _collect_calls(self, node: Any, caller_id: str) -> None:
        """Recursively find all call_expression nodes inside a node."""
        # We can use a simple DFS because tree-sitter nodes are iterable
        stack = list(node.children)
        while stack:
            child = stack.pop()
            if child.type == "call_expression":
                func_node = _find_child(child, "identifier", "selector_expression", "parenthesized_expression")
                if func_node:
                    callee = _func_name(func_node, self.source)
                    if callee:
                        self.edges.append(
                            Edge(
                                caller_id,
                                callee,
                                "calls",
                                child.start_point[0] + 1,
                            )
                        )
                # Don't recurse into the call itself to avoid double-counting nested calls
                for arg in child.children:
                    if arg.type not in ("identifier", "selector_expression"):
                        stack.extend(arg.children)
            else:
                stack.extend(child.children)


def parse_file(filepath: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Parse a single Go file and return symbols + edges."""
    from tree_sitter import Language, Parser

    import tree_sitter_go

    path = Path(filepath)
    source_bytes = path.read_bytes()

    lang = Language(tree_sitter_go.language())
    parser = Parser(lang)
    tree = parser.parse(source_bytes)

    extractor = GoSymbolExtractor(str(path), source_bytes, tree)
    return extractor.extract()
