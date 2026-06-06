"""Tests for search module."""

from __future__ import annotations

from sckg.search import build_ngram_index, search, search_pattern, split_identifier
from sckg.graph import KnowledgeGraph


def _make_graph():
    g = KnowledgeGraph()
    g.nodes = {
        "n1": {"id": "n1", "name": "parse_json_response", "kind": "function", "language": "python",
               "filepath": "parser.py", "line": 1, "docstring": "Parses a JSON response from the API",
               "signature": "parse_json_response(data: str) -> dict"},
        "n2": {"id": "n2", "name": "parse_xml", "kind": "function", "language": "python",
               "filepath": "parser.py", "line": 20, "docstring": "Parses XML data",
               "signature": "parse_xml(data: str) -> dict"},
        "n3": {"id": "n3", "name": "handle_error", "kind": "function", "language": "python",
               "filepath": "errors.py", "line": 5, "docstring": "Handles errors gracefully",
               "signature": "handle_error(err: Exception) -> None"},
        "n4": {"id": "n4", "name": "handle_request", "kind": "function", "language": "python",
               "filepath": "server.py", "line": 10, "docstring": "Handles incoming HTTP requests",
               "signature": "handle_request(req: Request) -> Response"},
    }
    g.edges = [
        {"source": "n1", "target": "n3", "relation": "calls"},  # parse_json_response calls handle_error
    ]
    return g


def test_ngram_extraction():
    """split_identifier splits camelCase and snake_case correctly."""
    assert split_identifier("parse_json_response") == ["parse", "json", "response"]
    # camelCase: regex splits on uppercase sequences
    assert "parse" in split_identifier("parseJSONResponse")
    assert "json" in split_identifier("parseJSONResponse")
    assert "response" in split_identifier("parseJSONResponse")
    assert "parse" in split_identifier("ParseJSONResponse")
    assert "json" in split_identifier("ParseJSONResponse")
    assert "response" in split_identifier("ParseJSONResponse")


def test_build_index():
    """Index has tokens mapped to node IDs with weights."""
    g = _make_graph()
    idx = build_ngram_index(g)
    # "parse json" bigram should be in index
    assert "parse json" in idx.index
    # Should map to n1 (parse_json_response)
    nids = [nid for nid, _ in idx.index["parse json"]]
    assert "n1" in nids


def test_search_ranking():
    """'parse json' finds parse_json_response before parse_xml."""
    g = _make_graph()
    idx = build_ngram_index(g)
    results = search("parse json", g, idx, top_k=5)
    assert len(results) >= 2
    assert results[0].node["name"] == "parse_json_response"
    assert results[1].node["name"] == "parse_xml"


def test_search_with_docstring_boost():
    """Function with 'json parsing' in docstring ranks high."""
    g = _make_graph()
    idx = build_ngram_index(g)
    results = search("json parsing", g, idx, top_k=5)
    assert len(results) >= 1
    # parse_json_response has "Parses a JSON response" in docstring
    assert results[0].node["name"] == "parse_json_response"


def test_pattern_search():
    """Pattern 'handle_*' finds handle_error and handle_request."""
    g = _make_graph()
    results = search_pattern("handle_*", g, top_k=10)
    names = {r.node["name"] for r in results}
    assert "handle_error" in names
    assert "handle_request" in names
    assert "parse_json_response" not in names