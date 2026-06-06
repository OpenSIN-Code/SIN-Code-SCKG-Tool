"""Tests for the AST parser module.

Docs: test_parser.doc.md
"""

from pathlib import Path

from sckg.parser import Edge, SymbolNode, parse_directory, parse_file


FIXTURES = Path(__file__).with_name("fixtures") / "sample_project"


def test_parse_file_extracts_function() -> None:
    """Parser should extract a function with its signature and docstring."""
    syms, _ = parse_file(FIXTURES / "utils.py")
    funcs = [s for s in syms if s.kind == "function" and s.name == "helper"]
    assert len(funcs) == 1
    h = funcs[0]
    assert h.name == "helper"
    assert h.line == 7
    assert "Print a greeting" in h.docstring
    assert "def helper(name: str)" in h.signature


def test_parse_file_extracts_class() -> None:
    """Parser should extract a class with its docstring."""
    syms, _ = parse_file(FIXTURES / "utils.py")
    classes = [s for s in syms if s.kind == "class" and s.name == "UtilityClass"]
    assert len(classes) == 1
    c = classes[0]
    assert c.name == "UtilityClass"
    assert c.line == 12
    assert "helper class" in c.docstring.lower()


def test_parse_file_finds_imports() -> None:
    """Parser should record import edges."""
    _, edges = parse_file(FIXTURES / "main.py")
    imports = [e for e in edges if e.relation == "imports"]
    assert len(imports) >= 2  # helper and UtilityClass
    targets = {e.target for e in imports}
    assert "utils.helper" in targets
    assert "utils.UtilityClass" in targets


def test_parse_file_finds_calls() -> None:
    """Parser should record call edges inside function bodies."""
    _, edges = parse_file(FIXTURES / "main.py")
    calls = [e for e in edges if e.relation == "calls"]
    targets = {e.target for e in calls}
    assert "helper" in targets
    assert "UtilityClass" in targets or "inst.do_something" in targets


def test_parse_directory_finds_all_files() -> None:
    """Directory parser should return symbols from all Python files."""
    syms, edges = parse_directory(FIXTURES)
    names = {s.name for s in syms}
    assert "helper" in names
    assert "UtilityClass" in names
    assert "MainClass" in names
    assert "main" in names
    assert len(syms) >= 4
    assert len(edges) >= 3
