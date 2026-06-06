"""Tests for similarity module."""

from __future__ import annotations

from sckg.similarity import (
    find_similar,
    extract_call_signature,
    extract_control_flow_features,
    extract_type_signature,
    jaccard_similarity,
    cosine_similarity,
)
from sckg.graph import KnowledgeGraph


def _make_graph():
    g = KnowledgeGraph()
    g.nodes = {
        "n1": {"id": "n1", "name": "parse_json", "kind": "function", "language": "python",
               "filepath": "parser.py", "line": 1, "docstring": "Parses JSON data",
               "signature": "parse_json(data: str) -> dict"},
        "n2": {"id": "n2", "name": "parse_xml", "kind": "function", "language": "python",
               "filepath": "parser.py", "line": 20, "docstring": "Parses XML data",
               "signature": "parse_xml(data: str) -> dict"},
        "n3": {"id": "n3", "name": "handle_error", "kind": "function", "language": "python",
               "filepath": "errors.py", "line": 5, "docstring": "Handles errors",
               "signature": "handle_error(err: Exception) -> None"},
        "n4": {"id": "n4", "name": "process_data", "kind": "function", "language": "python",
               "filepath": "processor.py", "line": 10, "docstring": "Processes data with if/else",
               "signature": "process_data(items: list) -> list"},
    }
    g.edges = [
        {"source": "n1", "target": "n3", "relation": "calls"},
        {"source": "n2", "target": "n3", "relation": "calls"},
        {"source": "n4", "target": "n1", "relation": "calls"},
    ]
    return g


def test_jaccard_similarity():
    """Jaccard similarity computes correctly."""
    assert jaccard_similarity({"a", "b"}, {"b", "c"}) == 1/3
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0
    assert jaccard_similarity(set(), set()) == 1.0
    assert jaccard_similarity({"a"}, set()) == 0.0


def test_cosine_similarity():
    """Cosine similarity computes correctly."""
    assert abs(cosine_similarity({"a": 1, "b": 1}, {"a": 1, "b": 1}) - 1.0) < 1e-10
    assert cosine_similarity({"a": 1}, {"b": 1}) == 0.0
    assert cosine_similarity({}, {}) == 1.0


def test_extract_call_signature():
    """Extract call signature from graph edges."""
    g = _make_graph()
    node = g.nodes["n1"]
    calls = extract_call_signature(node, g)
    assert "handle_error" in calls


def test_extract_control_flow_features():
    """Extract control flow features from signature/docstring."""
    node = {"signature": "def foo(items: list) -> list:", "docstring": "Processes with if and for loops"}
    features = extract_control_flow_features(node)
    assert features.get("if", 0) > 0
    assert features.get("for", 0) > 0


def test_extract_type_signature():
    """Extract type signature features."""
    node = {"signature": "def foo(data: str, count: int) -> dict:"}
    features = extract_type_signature(node)
    assert features.get("str", 0) > 0
    assert features.get("int", 0) > 0
    assert features.get("dict", 0) > 0


def test_find_similar_jaccard():
    """Find similar using Jaccard on call signatures."""
    g = _make_graph()
    # parse_json and parse_xml both call handle_error
    results = find_similar("n1", g, top_k=5, method="jaccard")
    names = [r.node["name"] for r in results]
    assert "parse_xml" in names


def test_find_similar_cosine():
    """Find similar using cosine on control flow + types."""
    g = _make_graph()
    results = find_similar("n1", g, top_k=5, method="cosine")
    # parse_xml should be similar (same signature pattern)
    names = [r.node["name"] for r in results]
    assert "parse_xml" in names


def test_find_similar_ast():
    """Find similar using full AST structural similarity."""
    g = _make_graph()
    results = find_similar("n1", g, top_k=5, method="ast")
    names = [r.node["name"] for r in results]
    assert "parse_xml" in names
    assert len(results) <= 5