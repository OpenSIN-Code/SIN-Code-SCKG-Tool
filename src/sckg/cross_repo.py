"""Cross-repository edge detection for SCKG.

Detects CLI-to-CLI calls (subprocess, os.system) and cross-repo Python imports
when multiple repositories are indexed together. Creates synthetic edges with
relation type ``cross_repo_call`` or ``cross_repo_import`` that the HTML
generator renders as purple dashed lines.

Docs: cross_repo.doc.md
"""

from __future__ import annotations

import ast
import shlex
from pathlib import Path
from typing import Any

from sckg.graph import KnowledgeGraph
from sckg.parser import parse_directory
from sckg.parsers.base import Edge, SymbolNode

# ── Known SIN-Code tools ───────────────────────────────────────────────────
# Hardcoded for v0.3.0; can be auto-detected later by scanning sibling repos.

KNOWN_TOOLS: dict[str, str] = {
    "ibd": "SIN-Code-IBD-Tool",
    "poc": "SIN-Code-PoC-Tool",
    "sckg": "SIN-Code-SCKG-Tool",
    "adw": "SIN-Code-ADW-Tool",
    "oracle": "SIN-Code-Oracle-Tool",
    "efm": "SIN-Code-EFM-Tool",
    "sin": "SIN-Code-Bundle",  # sin CLI calls others
    "discover": "SIN-Code-Discover-Tool",
    "execute": "SIN-Code-Execute-Tool",
    "map": "SIN-Code-Map-Tool",
    "grasp": "SIN-Code-Grasp-Tool",
    "scout": "SIN-Code-Scout-Tool",
    "harvest": "SIN-Code-Harvest-Tool",
    "orchestrate": "SIN-Code-Orchestrate-Tool",
}


# ── Helpers ────────────────────────────────────────────────────────────────


def _extract_first_arg_string(node: ast.expr) -> str | None:
    """Best-effort extraction of the first argument from a Call node.

    Handles:
    - List literals:  ``subprocess.run(["ibd", ...])`` → ``"ibd"``
    - String literals:  ``os.system("poc verify")`` → ``"poc verify"``
    """
    if isinstance(node, ast.List) and node.elts:
        first = node.elts[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _first_word(text: str) -> str | None:
    """Return the first whitespace-delimited word of a shell command."""
    if not text:
        return None
    text = text.strip().strip('"').strip("'")
    try:
        parts = shlex.split(text)
    except ValueError:
        # Malformed shell string — fall back to naive split
        parts = text.split()
    return parts[0] if parts else None


def _callee_name(node: ast.expr | None) -> str | None:
    """Return the dotted name of a ``Call.func`` node (e.g. ``'subprocess.run'``)."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _callee_name(node.value)
        if prefix:
            return f"{prefix}.{node.attr}"
    return None


# ── Detection functions ────────────────────────────────────────────────────


def detect_subprocess_calls(file_path: Path) -> list[Edge]:
    """Parse a Python file and return edges for known CLI-to-CLI calls.

    Scans for:
    - ``subprocess.run`` / ``subprocess.call`` / ``subprocess.Popen`` with a
      list or string as the first positional argument.
    - ``os.system`` with a string argument.

    When the first argument resolves to a known SIN-Code binary, an edge with
    ``relation="cross_repo_call"`` is created whose ``target`` is the canonical
    repo name (e.g. ``"SIN-Code-IBD-Tool"``).
    """
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    edges: list[Edge] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        callee = _callee_name(node.func)
        if callee is None:
            continue

        binary: str | None = None
        line = getattr(node, "lineno", 0)

        # subprocess.run([...]), subprocess.call([...]), subprocess.Popen([...])
        if callee.startswith("subprocess.") and node.args:
            first_arg = _extract_first_arg_string(node.args[0])
            if first_arg:
                if isinstance(node.args[0], ast.List):
                    binary = first_arg
                else:
                    binary = _first_word(first_arg)

        # os.system("cmd ...")
        elif callee == "os.system" and node.args:
            first_arg = _extract_first_arg_string(node.args[0])
            if first_arg:
                binary = _first_word(first_arg)

        if binary and binary in KNOWN_TOOLS:
            edges.append(
                Edge(
                    source=str(file_path),
                    target=KNOWN_TOOLS[binary],
                    relation="cross_repo_call",
                    line=line,
                )
            )

    return edges


def detect_imports(file_path: Path, known_packages: dict[str, str]) -> list[Edge]:
    """Parse a Python file and return edges for cross-repo imports.

    Args:
        file_path: Path to the Python file to scan.
        known_packages: Mapping from top-level Python package name → repo name.
            Example: ``{"sin_codocs": "SIN-Code-CoDocs-Tool"}``.

    Returns:
        Edges with ``relation="cross_repo_import"`` where the imported module
        matches a known package.
    """
    source = file_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    edges: list[Edge] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level in known_packages:
                    edges.append(
                        Edge(
                            source=str(file_path),
                            target=known_packages[top_level],
                            relation="cross_repo_import",
                            line=node.lineno,
                        )
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top_level = module.split(".")[0]
            if top_level in known_packages:
                edges.append(
                    Edge(
                        source=str(file_path),
                        target=known_packages[top_level],
                        relation="cross_repo_import",
                        line=node.lineno,
                    )
                )

    return edges


# ── Workspace helpers ──────────────────────────────────────────────────────


def find_repos_in_workspace(workspace_dir: Path) -> list[Path]:
    """Return a list of repository roots inside a workspace directory.

    Heuristic: a directory is considered a repository if it contains one of the
    following markers:

    - ``.git`` (Git repository)
    - ``pyproject.toml`` / ``setup.py`` (Python project)
    - ``go.mod`` (Go module)
    - ``package.json`` (Node.js project)
    """
    workspace_dir = Path(workspace_dir).resolve()
    if not workspace_dir.is_dir():
        return []

    repos: list[Path] = []
    for child in workspace_dir.iterdir():
        if not child.is_dir():
            continue
        markers = (
            child / ".git",
            child / "pyproject.toml",
            child / "setup.py",
            child / "go.mod",
            child / "package.json",
        )
        if any(m.exists() for m in markers):
            repos.append(child)

    return repos


# ── Graph builder ──────────────────────────────────────────────────────────


def build_cross_repo_graph(
    repo_paths: list[Path],
    known_packages: dict[str, str] | None = None,
) -> KnowledgeGraph:
    """Index multiple repositories and add cross-repo edges.

    Steps:
    1. Parse each repository with :func:`parse_directory` and build a base
       :class:`KnowledgeGraph`.
    2. Collect every Python file across all repos.
    3. Scan each file for subprocess calls (:func:`detect_subprocess_calls`).
    4. Scan each file for cross-repo imports (:func:`detect_imports`).
    5. Add cross-repo edges and ensure synthetic repo nodes exist so the D3
       visualisation has targets to connect to.

    Args:
        repo_paths: List of repository root directories.
        known_packages: Optional mapping from package name → repo name. If
            omitted, only subprocess calls are detected.

    Returns:
        A :class:`KnowledgeGraph` containing intra-repo and cross-repo edges.
    """
    graph = KnowledgeGraph()
    all_python_files: list[Path] = []

    for repo_path in repo_paths:
        repo_path = Path(repo_path).resolve()
        if not repo_path.exists():
            continue

        # Index the repo (intra-repo symbols + edges)
        symbols, edges = parse_directory(repo_path)
        graph.build_from_parser(symbols, edges)

        # Collect Python files for cross-repo scanning (skip venv / cache)
        all_python_files.extend(
            p
            for p in repo_path.rglob("*.py")
            if not any(
                part.startswith(".")
                or part
                in (
                    "venv",
                    ".venv",
                    "__pycache__",
                    "node_modules",
                    "vendor",
                    "dist",
                    "build",
                    ".next",
                )
                for part in p.relative_to(repo_path).parts
            )
        )

    # Detect cross-repo subprocess calls
    for py_file in all_python_files:
        for edge in detect_subprocess_calls(py_file):
            graph.add_edge(edge)

    # Detect cross-repo imports
    if known_packages:
        for py_file in all_python_files:
            for edge in detect_imports(py_file, known_packages):
                graph.add_edge(edge)

    # Ensure synthetic nodes exist for cross-repo targets so D3 has something
    # to draw an edge to.
    for edge in graph.edges:
        if edge.get("relation") in ("cross_repo_call", "cross_repo_import"):
            target = edge["target"]
            if target not in graph.nodes:
                graph.nodes[target] = {
                    "id": target,
                    "name": target,
                    "kind": "repo",
                    "filepath": "",
                    "line": 0,
                    "docstring": "",
                    "signature": "",
                    "parent": None,
                    "language": "repo",
                }

    graph.detect_communities()
    return graph
