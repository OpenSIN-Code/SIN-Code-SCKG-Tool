"""Tests for the KnowledgeGraph module.

Docs: test_graph.doc.md
"""

import json
import tempfile
from pathlib import Path

from sckg.graph import KnowledgeGraph
from sckg.parser import Edge, SymbolNode


def _fixture_symbol(name: str, kind: str, filepath: str) -> SymbolNode:
    return SymbolNode(name=name, kind=kind, filepath=filepath)


def test_build_graph_adds_nodes_and_edges() -> None:
    """Graph should hold nodes and edges after building from parser output."""
    g = KnowledgeGraph()
    syms = [
        _fixture_symbol("foo", "function", "/a/b.py"),
        _fixture_symbol("Bar", "class", "/a/b.py"),
    ]
    edges = [Edge("/a/b.py::foo", "Bar", "calls")]
    g.build_from_parser(syms, edges)
    assert len(g.nodes) == 2
    assert len(g.edges) == 1
    assert g.edges[0]["relation"] == "calls"


def test_add_edge_updates_adjacency() -> None:
    """Adding an edge should update the adjacency list."""
    g = KnowledgeGraph()
    g.add_symbol(_fixture_symbol("a", "function", "/x.py"))
    g.add_edge(Edge("/x.py::a", "b", "calls"))
    assert "b" in g._adjacency["/x.py::a"]


def test_detect_communities_groups_by_directory() -> None:
    """Community detection should group symbols by shared directory."""
    g = KnowledgeGraph()
    syms = [
        _fixture_symbol("f1", "function", "/src/a.py"),
        _fixture_symbol("f2", "function", "/src/a.py"),
        _fixture_symbol("f3", "function", "/src/sub/b.py"),
    ]
    edges = [
        Edge("/src/a.py::f1", "os.path", "imports"),
        Edge("/src/a.py::f2", "os.path", "imports"),  # shared import with f1
    ]
    g.build_from_parser(syms, edges)
    comms = g.detect_communities()
    assert len(comms) == 3
    # f1 and f2 share directory, so should be in same community (or merged)
    assert comms["/src/a.py::f1"] == comms["/src/a.py::f2"]


def test_save_and_load_json() -> None:
    """Round-trip JSON serialization should preserve nodes and edges."""
    g = KnowledgeGraph()
    syms = [_fixture_symbol("foo", "function", "/a.py")]
    edges = [Edge("/a.py::foo", "bar", "calls")]
    g.build_from_parser(syms, edges)

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as fh:
        path = fh.name
    g.save_json(path)

    g2 = KnowledgeGraph()
    g2.load_json(path)
    assert len(g2.nodes) == 1
    assert len(g2.edges) == 1
    Path(path).unlink()


def test_find_symbol_ranking() -> None:
    """Query should rank functions whose name matches highest."""
    g = KnowledgeGraph()
    syms = [
        SymbolNode(name="helper", kind="function", filepath="/x.py", docstring="A helper"),
        SymbolNode(name="HelperClass", kind="class", filepath="/x.py", docstring="Helper class"),
    ]
    g.build_from_parser(syms, [])
    results = g.find_symbol("helper")
    assert results[0]["name"] == "helper"
    assert results[0]["kind"] == "function"
