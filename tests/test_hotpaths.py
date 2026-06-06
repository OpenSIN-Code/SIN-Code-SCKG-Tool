"""Tests for hotpaths module."""

from __future__ import annotations

from sckg.hotpaths import compute_hot_paths
from sckg.graph import KnowledgeGraph


def _make_graph():
    """Create a small graph with clear hot paths."""
    g = KnowledgeGraph()
    # Nodes
    g.nodes = {
        "n1": {"id": "n1", "name": "main", "kind": "function", "language": "python", "filepath": "main.py", "line": 1},
        "n2": {"id": "n2", "name": "helper", "kind": "function", "language": "python", "filepath": "utils.py", "line": 10},
        "n3": {"id": "n3", "name": "parse_json", "kind": "function", "language": "python", "filepath": "parser.py", "line": 5},
        "n4": {"id": "n4", "name": "unused", "kind": "function", "language": "python", "filepath": "dead.py", "line": 1},
        "n5": {"id": "n5", "name": "bridge", "kind": "function", "language": "python", "filepath": "bridge.py", "line": 1},
    }
    # Edges: main -> helper, main -> parse_json, helper -> parse_json, helper2 -> parse_json, bridge -> main
    # parse_json has 3 incoming (from main, helper, helper2) - unique max
    g.edges = [
        {"source": "n1", "target": "n2", "relation": "calls"},
        {"source": "n1", "target": "n3", "relation": "calls"},
        {"source": "n2", "target": "n3", "relation": "calls"},
        # Add another caller for parse_json to make it unique top
        {"source": "n4", "target": "n3", "relation": "calls"},
        {"source": "n5", "target": "n1", "relation": "calls"},
    ]
    return g


def test_in_degree_hotpaths():
    """parse_json has 3 incoming calls (from main, helper, unused) -> rank 1."""
    g = _make_graph()
    report = compute_hot_paths(g, top_n=5, weight="in_degree")
    assert report.hot_nodes[0].node["name"] == "parse_json"
    assert report.hot_nodes[0].in_degree == 3
    assert report.hot_nodes[0].rank == 1


def test_out_degree_hotpaths():
    """main calls 2 functions (helper, parse_json) -> rank 1."""
    g = _make_graph()
    report = compute_hot_paths(g, top_n=5, weight="out_degree")
    assert report.hot_nodes[0].node["name"] == "main"
    assert report.hot_nodes[0].out_degree == 2
    assert report.hot_nodes[0].rank == 1


def test_pagerank_hotpaths():
    """parse_json is sink with most incoming -> highest pagerank."""
    g = _make_graph()
    report = compute_hot_paths(g, top_n=5, weight="pagerank")
    # parse_json is the ultimate sink with 3 incoming -> highest pagerank
    assert report.hot_nodes[0].node["name"] == "parse_json"
    # All 5 nodes should be in the report
    assert len(report.hot_nodes) == 5


def test_top_n_limit():
    """--top 2 returns exactly 2."""
    g = _make_graph()
    report = compute_hot_paths(g, top_n=2, weight="in_degree")
    assert len(report.hot_nodes) == 2


def test_empty_graph():
    """Empty graph returns empty report."""
    g = KnowledgeGraph()
    g.nodes = {}
    g.edges = []
    report = compute_hot_paths(g, top_n=10, weight="in_degree")
    assert report.hot_nodes == []
    assert report.total_nodes == 0