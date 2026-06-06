"""Tests for cross-repository edge detection.

Docs: test_cross_repo.doc.md
"""

import json
import tempfile
from pathlib import Path

from sckg.cross_repo import (
    KNOWN_TOOLS,
    detect_imports,
    detect_subprocess_calls,
    build_cross_repo_graph,
    find_repos_in_workspace,
)
from sckg.parsers.base import Edge


def test_detect_subprocess_call() -> None:
    """Should find subprocess.run(["ibd", "diff", ...]) and create a cross_repo_call edge."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
        fh.write('import subprocess\n\nsubprocess.run(["ibd", "diff", "a.py", "b.py"])\n')
        path = Path(fh.name)

    edges = detect_subprocess_calls(path)
    path.unlink()

    assert len(edges) == 1
    assert edges[0].relation == "cross_repo_call"
    assert edges[0].target == "SIN-Code-IBD-Tool"
    assert edges[0].source == str(path)


def test_detect_os_system_call() -> None:
    """Should find os.system("poc verify ...") and create a cross_repo_call edge."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
        fh.write('import os\n\nos.system("poc verify --strict")\n')
        path = Path(fh.name)

    edges = detect_subprocess_calls(path)
    path.unlink()

    assert len(edges) == 1
    assert edges[0].relation == "cross_repo_call"
    assert edges[0].target == "SIN-Code-PoC-Tool"


def test_detect_import_cross_repo() -> None:
    """Should find import sin_codocs when sin-codocs is in the known_packages map."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
        fh.write("import sin_codocs\nfrom sin_codocs import checker\n")
        path = Path(fh.name)

    known = {"sin_codocs": "SIN-Code-CoDocs-Tool"}
    edges = detect_imports(path, known)
    path.unlink()

    assert len(edges) == 2
    targets = {e.target for e in edges}
    assert targets == {"SIN-Code-CoDocs-Tool"}
    for e in edges:
        assert e.relation == "cross_repo_import"


def test_ignore_unknown_binary() -> None:
    """Should NOT create an edge for subprocess.run(["ls", "-la"])."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as fh:
        fh.write('import subprocess\n\nsubprocess.run(["ls", "-la"])\n')
        path = Path(fh.name)

    edges = detect_subprocess_calls(path)
    path.unlink()

    assert len(edges) == 0


def test_build_workspace_graph() -> None:
    """Should index 2 repos and find cross-repo edges between them."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        repo1 = root / "repo1"
        repo2 = root / "repo2"
        repo1.mkdir()
        repo2.mkdir()

        # repo1 calls a tool from another repo via subprocess
        (repo1 / "main.py").write_text(
            'import subprocess\n\ndef run():\n    subprocess.run(["ibd", "diff", "a.py", "b.py"])\n'
        )
        # repo2 has a normal Python file
        (repo2 / "utils.py").write_text(
            'def helper():\n    """A helper."""\n    pass\n'
        )

        graph = build_cross_repo_graph([repo1, repo2])

        cross_edges = [e for e in graph.edges if e["relation"] == "cross_repo_call"]
        assert len(cross_edges) == 1
        assert cross_edges[0]["target"] == "SIN-Code-IBD-Tool"

        # Verify that both repos were indexed (nodes exist)
        names = {n["name"] for n in graph.nodes.values()}
        assert "helper" in names
        assert "run" in names

        # Verify synthetic repo node exists
        assert "SIN-Code-IBD-Tool" in graph.nodes


def test_find_repos_in_workspace() -> None:
    """Should discover repo directories by marker files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "repo_a").mkdir()
        (root / "repo_a" / "pyproject.toml").write_text("[project]\n")
        (root / "repo_b").mkdir()
        (root / "repo_b" / ".git").mkdir()
        (root / "not_a_repo").mkdir()
        (root / "not_a_repo" / "readme.txt").write_text("hello")

        repos = find_repos_in_workspace(root)
        names = {r.name for r in repos}
        assert "repo_a" in names
        assert "repo_b" in names
        assert "not_a_repo" not in names


def test_known_tools_map() -> None:
    """The KNOWN_TOOLS dict should map common SIN-Code binaries to repo names."""
    assert KNOWN_TOOLS["ibd"] == "SIN-Code-IBD-Tool"
    assert KNOWN_TOOLS["poc"] == "SIN-Code-PoC-Tool"
    assert KNOWN_TOOLS["sin"] == "SIN-Code-Bundle"
