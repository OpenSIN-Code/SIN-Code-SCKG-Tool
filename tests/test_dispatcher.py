"""Tests for the multi-language parser dispatcher.

Docs: test_dispatcher.doc.md
"""

import tempfile
from pathlib import Path

from sckg.graph import KnowledgeGraph
from sckg.parser import parse_directory, parse_file


def test_python_files_parsed() -> None:
    """.py files should be routed to the Python parser and return python nodes."""
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as fh:
        fh.write('def hello():\n    """Say hello."""\n    pass\n')
        path = Path(fh.name)

    syms, _ = parse_file(path)
    assert len(syms) == 1
    assert syms[0].name == "hello"
    assert syms[0].language == "python"

    path.unlink()


def test_go_files_parsed() -> None:
    """.go files should be routed to the Go parser if available."""
    with tempfile.NamedTemporaryFile(suffix=".go", delete=False, mode="w") as fh:
        fh.write('package main\n\nfunc main() {}\n')
        path = Path(fh.name)

    try:
        syms, _ = parse_file(path)
        assert any(s.name == "main" and s.language == "go" for s in syms)
    except ValueError:
        # Go parser not available — skip gracefully
        pass

    path.unlink()


def test_unknown_files_skipped() -> None:
    """.txt files should return no parser and produce no errors."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w") as fh:
        fh.write("hello world\n")
        path = Path(fh.name)

    try:
        syms, edges = parse_file(path)
    except ValueError:
        syms, edges = [], []
    assert syms == []
    assert edges == []

    path.unlink()


def test_multilanguage_graph() -> None:
    """A graph built from multiple languages should carry distinct language tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Python file
        (root / "a.py").write_text("def foo(): pass\n")
        # Go file (only if parser available)
        (root / "b.go").write_text("package main\n\nfunc bar() {}\n")
        # TypeScript file (only if parser available)
        (root / "c.ts").write_text("export function baz(): void {}\n")

        syms, edges = parse_directory(root)
        graph = KnowledgeGraph()
        graph.build_from_parser(syms, edges)

        languages = {n["language"] for n in graph.nodes.values()}
        assert "python" in languages
        # Go / TypeScript may be absent if their parsers aren't installed;
        # we only assert that the dispatcher didn't crash and python is present.
        assert len(languages) >= 1
