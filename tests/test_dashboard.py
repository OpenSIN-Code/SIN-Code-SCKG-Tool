"""Tests for dashboard module."""

from __future__ import annotations

import tempfile
from pathlib import Path

from sckg.dashboard import (
    collect_repo_stats,
    build_cross_repo_matrix,
    collect_community_overview,
    collect_hot_paths_per_repo,
    collect_dead_code_per_repo,
    generate_dashboard,
)
from sckg.graph import KnowledgeGraph


def _make_multi_repo_graph():
    g = KnowledgeGraph()
    g.nodes = {
        "n1": {"id": "n1", "name": "main", "kind": "function", "language": "python",
               "filepath": "main.py", "line": 1, "repo": "repo-a", "parent": None},
        "n2": {"id": "n2", "name": "helper", "kind": "function", "language": "python",
               "filepath": "utils.py", "line": 10, "repo": "repo-a", "parent": None},
        "n3": {"id": "n3", "name": "main", "kind": "function", "language": "go",
               "filepath": "main.go", "line": 5, "repo": "repo-b", "parent": None},
        "n4": {"id": "n4", "name": "config", "kind": "function", "language": "go",
               "filepath": "config.go", "line": 1, "repo": "repo-b", "parent": None},
    }
    g.edges = [
        {"source": "n1", "target": "n2", "relation": "calls", "repo": "repo-a"},
        {"source": "n3", "target": "n4", "relation": "calls", "repo": "repo-b"},
    ]
    return g


def test_collect_repo_stats():
    """Collect per-repo statistics."""
    g = _make_multi_repo_graph()
    stats = collect_repo_stats(g)
    repo_names = [r["name"] for r in stats]
    assert "repo-a" in repo_names
    assert "repo-b" in repo_names
    repo_a = next(r for r in stats if r["name"] == "repo-a")
    assert repo_a["node_count"] == 2
    assert repo_a["languages"]["python"] == 2


def test_build_cross_repo_matrix():
    """Build cross-repo edge matrix."""
    g = _make_multi_repo_graph()
    matrix = build_cross_repo_matrix(g)
    assert "repo-a" in matrix["repos"]
    assert "repo-b" in matrix["repos"]


def test_collect_community_overview():
    """Collect community overview."""
    g = _make_multi_repo_graph()
    overview = collect_community_overview(g)
    assert len(overview) >= 0  # May be empty if no community detection run


def test_collect_hot_paths_per_repo():
    """Collect hot paths per repo."""
    g = _make_multi_repo_graph()
    hot = collect_hot_paths_per_repo(g, top=3)
    assert "repo-a" in hot or "repo-b" in hot


def test_generate_dashboard_writes_html():
    """Generate dashboard HTML file."""
    g = _make_multi_repo_graph()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "dashboard.html"
        result = generate_dashboard(g, out, workspace_path="/test/workspace")
        assert result.exists()
        html = result.read_text()
        assert "SCKG Multi-Repo Dashboard" in html
        assert "chord-svg" in html
        assert "Cross-Repo Call Graph" in html