"""Dead code detection for SCKG knowledge graphs.

Identifies isolated nodes (zero incoming edges) as dead-code candidates,
while respecting entry-point heuristics (main, __init__, CLI handlers,
public API, etc.). Also flags "suspicious" nodes with exactly one incoming
edge for manual review.

Docs: dead_code.doc.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sckg.graph import KnowledgeGraph


@dataclass
class DeadCodeReport:
    """Result of a dead-code analysis pass.

    Attributes:
        dead_nodes: Nodes with zero incoming edges that are not entry points.
        entry_points: Nodes identified as entry points (excluded from dead).
        suspicious_nodes: Nodes with exactly one incoming edge (low usage).
        coverage_pct: Percentage of non-dead nodes (0.0 – 1.0).
    """

    dead_nodes: list[dict[str, Any]] = field(default_factory=list)
    entry_points: list[dict[str, Any]] = field(default_factory=list)
    suspicious_nodes: list[dict[str, Any]] = field(default_factory=list)
    coverage_pct: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-friendly dict."""
        return {
            "dead_nodes": self.dead_nodes,
            "entry_points": self.entry_points,
            "suspicious_nodes": self.suspicious_nodes,
            "coverage_pct": self.coverage_pct,
        }


def _count_incoming_edges(graph: KnowledgeGraph) -> dict[str, int]:
    """Return a map from node id → number of incoming edges.

    We count an edge as incoming when its target matches either the full
    node id (``filepath::name``) or the bare symbol name. This compensates
    for the parser, which stores call targets as raw names (e.g. ``helper``)
    rather than fully qualified ids (e.g. ``utils.py::helper``).
    """
    incoming: dict[str, int] = {}
    for nid in graph.nodes:
        incoming[nid] = 0

    # Build a quick name → ids lookup for bare-name matching.
    name_to_ids: dict[str, list[str]] = {}
    for nid, node in graph.nodes.items():
        name = node.get("name", "")
        name_to_ids.setdefault(name, []).append(nid)

    for edge in graph.edges:
        target = edge.get("target", "")
        # Exact match on node id
        if target in incoming:
            incoming[target] += 1
        # Bare-name match (e.g. "helper" → "utils.py::helper")
        elif target in name_to_ids:
            for nid in name_to_ids[target]:
                incoming[nid] += 1

    return incoming


def _is_entry_point(node: dict[str, Any], explicit_ids: set[str]) -> bool:
    """Return True if the node is an entry point and should not be flagged dead.

    Heuristics (in order of priority):
    1. Explicitly listed in ``entry_points`` argument.
    2. Name is ``main`` and kind is ``function`` (CLI / script entry point).
    3. Name is ``__init__`` and kind is ``function`` (Python constructor).
    4. Name is ``__main__`` and kind is ``module`` (Python module entry point).
    """
    nid = node.get("id", "")
    if nid in explicit_ids:
        return True

    name = node.get("name", "")
    kind = node.get("kind", "")

    if name == "main" and kind == "function":
        return True
    if name == "__init__" and kind == "function":
        return True
    if name == "__main__" and kind == "module":
        return True

    return False


def find_dead_code(
    graph: KnowledgeGraph,
    entry_points: list[str] | None = None,
) -> DeadCodeReport:
    """Analyze ``graph`` and return a dead-code report.

    A node is considered **dead** when it has zero incoming edges and is
    not an entry point. Nodes with exactly one incoming edge are flagged as
    **suspicious** (low usage, worth reviewing). Entry points are excluded
    from the dead set regardless of their incoming edge count.

    Coverage is calculated as ``non_dead / total_nodes``. When the graph
    contains no nodes, coverage is defined as ``1.0`` (100%).
    """
    incoming = _count_incoming_edges(graph)
    explicit_ids = set(entry_points or [])

    dead: list[dict[str, Any]] = []
    entry: list[dict[str, Any]] = []
    suspicious: list[dict[str, Any]] = []

    total = len(graph.nodes)
    for nid, node in graph.nodes.items():
        count = incoming.get(nid, 0)
        is_ep = _is_entry_point(node, explicit_ids)

        if is_ep:
            entry.append(node)
        elif count == 0:
            dead.append(node)
        elif count == 1:
            suspicious.append(node)

    non_dead = total - len(dead)
    coverage_pct = non_dead / total if total else 1.0

    return DeadCodeReport(
        dead_nodes=dead,
        entry_points=entry,
        suspicious_nodes=suspicious,
        coverage_pct=coverage_pct,
    )
