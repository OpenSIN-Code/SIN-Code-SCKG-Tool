"""Tests for language-aware community detection.

Docs: test_communities.doc.md
"""

from pathlib import Path

from sckg.communities import (
    detect_language_communities,
    detect_mixed_communities,
    resolve_cross_language_edges,
)
from sckg.graph import Community, KnowledgeGraph
from sckg.parser import Edge, SymbolNode, parse_directory

FIXTURES = Path(__file__).with_name("fixtures")


def _make_symbol(name: str, kind: str, filepath: str, language: str = "python") -> SymbolNode:
    return SymbolNode(name=name, kind=kind, filepath=filepath, language=language)


# ── Test 1: isolated Python community ───────────────────────────────────────


def test_python_community_isolated() -> None:
    """A Python-only repo should yield exactly one Python community."""
    g = KnowledgeGraph()
    syms = [
        _make_symbol("foo", "function", "/src/a.py", "python"),
        _make_symbol("bar", "function", "/src/a.py", "python"),
    ]
    edges = [Edge("/src/a.py::foo", "/src/a.py::bar", "calls")]
    g.build_from_parser(syms, edges)

    lang_comms = detect_language_communities(g)
    assert "python" in lang_comms
    assert len(lang_comms) == 1
    assert len(lang_comms["python"]) == 1
    assert lang_comms["python"][0].dominant_language == "python"
    assert lang_comms["python"][0].size == 2


# ── Test 2: isolated Go community ───────────────────────────────────────────


def test_go_community_isolated() -> None:
    """A Go-only repo should yield exactly one Go community."""
    g = KnowledgeGraph()
    syms = [
        _make_symbol("main", "function", "/cmd/main.go", "go"),
        _make_symbol("Server", "struct", "/cmd/main.go", "go"),
    ]
    edges = [Edge("/cmd/main.go::main", "/cmd/main.go::Server", "calls")]
    g.build_from_parser(syms, edges)

    lang_comms = detect_language_communities(g)
    assert "go" in lang_comms
    assert len(lang_comms) == 1
    assert len(lang_comms["go"]) == 1
    assert lang_comms["go"][0].dominant_language == "go"
    assert lang_comms["go"][0].size == 2


# ── Test 3: mixed repo detects multiple communities ─────────────────────────


def test_mixed_repo_detects_multiple_communities() -> None:
    """A repo with Python, Go, and TypeScript should yield at least 3 communities."""
    repo = FIXTURES / "mixed_repo"
    symbols, edges = parse_directory(repo)
    g = KnowledgeGraph()
    g.build_from_parser(symbols, edges)
    resolve_cross_language_edges(g)

    lang_comms = detect_language_communities(g)
    # Should have communities for python, go, and typescript
    total = sum(len(c_list) for c_list in lang_comms.values())
    assert total >= 3, f"Expected >= 3 communities, got {total}"
    assert "python" in lang_comms or "go" in lang_comms or "typescript" in lang_comms


# ── Test 4: mixed community detected via cross-language edge ───────────────


def test_mixed_community_detected() -> None:
    """A cross-language edge (Python → Go) should create a mixed community."""
    g = KnowledgeGraph()
    syms = [
        _make_symbol("run_go", "function", "/app.py", "python"),
        _make_symbol("main", "function", "/go_binary.go", "go"),
    ]
    edges = [
        Edge("/app.py::run_go", "go_binary.go::main", "cross-language"),
    ]
    g.build_from_parser(syms, edges)

    communities = detect_mixed_communities(g)
    mixed = [c for c in communities if c.dominant_language == "mixed"]
    assert len(mixed) >= 1, f"Expected at least 1 mixed community, got {len(mixed)}"
    assert mixed[0].languages == {"python": 1, "go": 1}


# ── Test 5: community density calculation ───────────────────────────────────


def test_community_density_calculation() -> None:
    """A complete directed graph with 3 nodes should have density = 1.0."""
    g = KnowledgeGraph()
    syms = [
        _make_symbol("a", "function", "/x.py", "python"),
        _make_symbol("b", "function", "/x.py", "python"),
        _make_symbol("c", "function", "/x.py", "python"),
    ]
    # All possible directed edges among 3 nodes: 3*2 = 6
    edges = [
        Edge("/x.py::a", "/x.py::b", "calls"),
        Edge("/x.py::a", "/x.py::c", "calls"),
        Edge("/x.py::b", "/x.py::a", "calls"),
        Edge("/x.py::b", "/x.py::c", "calls"),
        Edge("/x.py::c", "/x.py::a", "calls"),
        Edge("/x.py::c", "/x.py::b", "calls"),
    ]
    g.build_from_parser(syms, edges)

    comms = detect_language_communities(g)
    python_comms = comms.get("python", [])
    assert len(python_comms) == 1
    assert python_comms[0].size == 3
    assert python_comms[0].density == 1.0
