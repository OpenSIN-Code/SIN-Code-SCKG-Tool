"""Tests for hybrid_search module."""

from __future__ import annotations

from sckg.hybrid_search import hybrid_search, normalize_scores
from sckg.search import build_ngram_index
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
        "n4": {"id": "n4", "name": "format_data", "kind": "function", "language": "python",
               "filepath": "utils.py", "line": 30, "docstring": "Formats JSON output",
               "signature": "format_data(data: dict) -> str"},
    }
    g.edges = [
        {"source": "n1", "target": "n3", "relation": "calls"},
        {"source": "n2", "target": "n3", "relation": "calls"},
        {"source": "n4", "target": "n1", "relation": "calls"},
    ]
    return g


def test_normalize_scores_basic():
    """Normalize scores to [0, 1] range."""
    scores = {"a": 10, "b": 5, "c": 0}
    norm = normalize_scores(scores)
    assert norm["a"] == 1.0
    assert norm["b"] == 0.5
    assert norm["c"] == 0.0


def test_normalize_scores_empty():
    """Normalize empty scores returns empty dict."""
    assert normalize_scores({}) == {}


def test_normalize_scores_single():
    """Normalize single score returns 1.0."""
    assert normalize_scores({"a": 5}) == {"a": 1.0}


def test_hybrid_search_combines_scores():
    """Hybrid search returns combined results."""
    g = _make_graph()
    index = build_ngram_index(g)
    results = hybrid_search("parse json", g, index, top_k=5, alpha=0.5)
    assert len(results) >= 1
    assert results[0].node["name"] in ["parse_json", "format_data"]


def test_hybrid_search_pure_ngram():
    """Hybrid with alpha=1.0 emphasizes n-gram (similarity still computed but lower weight)."""
    g = _make_graph()
    index = build_ngram_index(g)
    results = hybrid_search("parse json", g, index, top_k=5, alpha=1.0)
    assert len(results) >= 1
    # With alpha=1.0, ngram_score should dominate; combined score >= ngram_score * (1 - 0.0001)
    # (similarity contributes 0 weight but still listed in metadata)
    for r in results:
        # Combined score = alpha * ngram + (1-alpha) * sim = 1.0 * ngram + 0 * sim
        assert abs(r.score - r.ngram_score) < 1e-10


def test_hybrid_search_pure_similarity():
    """Hybrid with alpha=0.0 emphasizes similarity."""
    g = _make_graph()
    index = build_ngram_index(g)
    results = hybrid_search("parse json", g, index, top_k=5, alpha=0.0)
    # Should still return results (the anchor node from n-gram)
    assert len(results) >= 1


def test_hybrid_search_empty_graph():
    """Hybrid search on empty graph returns empty list."""
    g = KnowledgeGraph()
    g.nodes = {}
    g.edges = []
    results = hybrid_search("test", g, top_k=5, alpha=0.5)
    assert results == []