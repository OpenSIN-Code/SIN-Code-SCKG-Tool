"""Tests for performance module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from sckg.performance import save_json_fast, load_json_fast, IndexedGraph
from sckg.graph import KnowledgeGraph


def _make_graph():
    g = KnowledgeGraph()
    g.nodes = {
        "n1": {"id": "n1", "name": "main", "kind": "function", "language": "python",
               "filepath": "main.py", "line": 1, "repo": "repo-a"},
        "n2": {"id": "n2", "name": "helper", "kind": "function", "language": "python",
               "filepath": "utils.py", "line": 10, "repo": "repo-a"},
        "n3": {"id": "n3", "name": "main", "kind": "function", "language": "go",
               "filepath": "main.go", "line": 5, "repo": "repo-b"},
    }
    g.edges = [
        {"source": "n1", "target": "n2", "relation": "calls", "repo": "repo-a"},
    ]
    return g


def test_save_and_load_json_fast():
    """Save and load graph with fast JSON."""
    g = _make_graph()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "graph.json"
        save_json_fast(g, path)
        assert path.exists()
        loaded = load_json_fast(path)
        assert len(loaded.nodes) == 3
        assert len(loaded.edges) == 1
        assert "n1" in loaded.nodes


def test_indexed_graph_by_repo():
    """IndexedGraph returns nodes by repo."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    repo_a_nodes = indexed.get_by_repo("repo-a")
    assert len(repo_a_nodes) == 2
    repo_b_nodes = indexed.get_by_repo("repo-b")
    assert len(repo_b_nodes) == 1


def test_indexed_graph_by_language():
    """IndexedGraph returns nodes by language."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    py_nodes = indexed.get_by_language("python")
    assert len(py_nodes) == 2
    go_nodes = indexed.get_by_language("go")
    assert len(go_nodes) == 1


def test_indexed_graph_by_type():
    """IndexedGraph returns nodes by type."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    funcs = indexed.get_by_type("function")
    assert len(funcs) == 3


def test_indexed_graph_filter_combined():
    """IndexedGraph filter with multiple criteria."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    results = indexed.filter(language="python", type="function", limit=10)
    assert len(results) == 2
    repo_a_funcs = indexed.filter(repo="repo-a", type="function", limit=10)
    assert len(repo_a_funcs) == 2


def test_indexed_graph_invalidate():
    """IndexedGraph can invalidate indices."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    # First access builds indices
    _ = indexed.get_by_repo("repo-a")
    # Invalidate
    indexed.invalidate()
    # Access again
    nodes = indexed.get_by_repo("repo-a")
    assert len(nodes) == 2


def test_indexed_graph_index_size():
    """IndexedGraph tracks index size."""
    g = _make_graph()
    indexed = IndexedGraph(g)
    size = indexed.index_size
    assert size > 0  # Has 3 nodes across 4 indices