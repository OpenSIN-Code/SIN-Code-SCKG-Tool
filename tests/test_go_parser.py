"""Tests for the Go tree-sitter parser module.

Docs: test_go_parser.doc.md
"""

from pathlib import Path

from sckg.parsers.go_parser import parse_file


FIXTURES = Path(__file__).with_name("fixtures") / "go_sample"


def test_extract_functions() -> None:
    """Parser should find top-level functions (main, helper)."""
    syms, _ = parse_file(FIXTURES / "main.go")
    funcs = {s.name for s in syms if s.kind == "function"}
    assert "main" in funcs
    assert "helper" in funcs


def test_extract_structs() -> None:
    """Parser should find struct type declarations (Server)."""
    syms, _ = parse_file(FIXTURES / "main.go")
    structs = {s.name for s in syms if s.kind == "struct"}
    assert "Server" in structs


def test_extract_methods() -> None:
    """Parser should find receiver methods (Start on *Server)."""
    syms, _ = parse_file(FIXTURES / "main.go")
    methods = {s.name for s in syms if s.kind == "method"}
    assert "Start" in methods

    # Verify parent (receiver type without pointer)
    start = [s for s in syms if s.name == "Start" and s.kind == "method"][0]
    assert start.parent == "Server"
    assert "*Server" in start.signature


def test_extract_imports() -> None:
    """Parser should record import edges (fmt)."""
    _, edges = parse_file(FIXTURES / "main.go")
    imports = [e for e in edges if e.relation == "imports"]
    targets = {e.target for e in imports}
    assert "fmt" in targets


def test_extract_calls() -> None:
    """Parser should record call edges inside function bodies (fmt.Println)."""
    _, edges = parse_file(FIXTURES / "main.go")
    calls = [e for e in edges if e.relation == "calls"]
    targets = {e.target for e in calls}
    assert "fmt.Println" in targets
    assert "helper" in targets
    assert "s.Start" in targets
