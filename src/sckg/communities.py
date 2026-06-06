"""Language-aware community detection for SCKG knowledge graphs.

Docs: communities.doc.md
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path
from typing import Any

from sckg.graph import Community, KnowledgeGraph
from sckg.parsers.base import Edge, SymbolNode


# ── Language-aware detection ───────────────────────────────────────────


def detect_language_communities(graph: KnowledgeGraph) -> dict[str, list[Community]]:
    """Split graph by language, then run community detection within each language.

    Returns a dict mapping language → list of Community objects.  Each
    community is guaranteed to contain nodes of a single language (or
    ``"unknown"``).
    """
    # 1. Partition nodes by language
    nodes_by_lang: dict[str, list[str]] = defaultdict(list)
    for nid, node in graph.nodes.items():
        lang = node.get("language", "unknown")
        nodes_by_lang[lang].append(nid)

    result: dict[str, list[Community]] = {}
    for lang, node_ids in nodes_by_lang.items():
        if not node_ids:
            continue

        # 2. Build a subgraph for this language
        subgraph = KnowledgeGraph()
        for nid in node_ids:
            subgraph.nodes[nid] = graph.nodes[nid]

        # Only include edges whose both endpoints are in the subgraph
        for edge in graph.edges:
            if edge["source"] in subgraph.nodes and edge["target"] in subgraph.nodes:
                subgraph.add_edge(Edge(edge["source"], edge["target"], edge["relation"]))

        # 3. Run generic community detection on the subgraph
        raw_comms = subgraph.detect_communities()

        # 4. Convert to Community dataclass instances
        communities = _build_communities(subgraph, raw_comms, default_lang=lang)
        result[lang] = communities

    return result


# ── Mixed-language detection ───────────────────────────────────────────────


def detect_mixed_communities(graph: KnowledgeGraph) -> list[Community]:
    """Detect communities across *all* languages, labelling mixed ones.

    A community is **mixed** if it contains nodes from more than one
    language (e.g. Python calling Go via ``subprocess``).  Mixed
    communities are tagged with ``dominant_language="mixed"``.
    """
    raw_comms = graph.detect_communities()
    communities = _build_communities(graph, raw_comms, default_lang="unknown")

    for comm in communities:
        if len(comm.languages) > 1:
            comm.dominant_language = "mixed"

    return communities


# ── Helpers ───────────────────────────────────────────────────────────────


def _build_communities(
    graph: KnowledgeGraph,
    comms_dict: dict[str, str],
    default_lang: str,
) -> list[Community]:
    """Turn a raw community mapping into a list of :class:`Community` objects."""
    # Group node IDs by community label
    by_label: dict[str, list[str]] = defaultdict(list)
    for nid, label in comms_dict.items():
        by_label[label].append(nid)

    communities: list[Community] = []
    for idx, (label, nids) in enumerate(by_label.items(), start=1):
        nodes = [graph.nodes[nid] for nid in nids if nid in graph.nodes]

        # Count languages
        languages: dict[str, int] = defaultdict(int)
        for nid in nids:
            lang = graph.nodes[nid].get("language", "unknown")
            languages[lang] += 1

        # Dominant language (or "mixed" if more than one)
        dominant = max(languages, key=languages.get) if languages else default_lang
        if len(languages) > 1:
            dominant = "mixed"

        # Density = directed edges / possible directed edges
        size = len(nids)
        possible = size * (size - 1) if size > 1 else 1
        actual = 0
        for edge in graph.edges:
            if edge["source"] in nids and edge["target"] in nids:
                actual += 1
        density = actual / possible if possible else 0.0

        communities.append(
            Community(
                id=idx,
                nodes=nodes,
                dominant_language=dominant,
                languages=dict(languages),
                size=size,
                density=density,
            )
        )

    return communities


# ── Cross-language edge resolution ───────────────────────────────────────


def resolve_cross_language_edges(graph: KnowledgeGraph) -> None:
    """Post-process a graph to resolve cross-language edges (e.g. ``subprocess``).

    Scans Python nodes for ``subprocess`` calls that reference a binary
    name, then creates an explicit edge to the matching Go / TypeScript
    entry-point if one exists in the graph.
    """
    # Build a lookup: binary stem → node IDs for Go / TypeScript / etc.
    binary_nodes: dict[str, list[str]] = defaultdict(list)
    for nid, node in graph.nodes.items():
        lang = node.get("language", "unknown")
        if lang in ("go", "typescript", "javascript"):
            fp = Path(node.get("filepath", ""))
            stem = fp.stem
            binary_nodes[stem].append(nid)
            # Also index by function name if it's a main / default entry point
            if node.get("name") in ("main", "default", "start", "index"):
                binary_nodes[node["name"]].append(nid)

    # Scan Python edges for subprocess calls and rewrite to binary nodes
    new_edges: list[dict[str, Any]] = []
    for edge in graph.edges:
        if edge["relation"] == "subprocess" and edge["target"] in binary_nodes:
            targets = binary_nodes[edge["target"]]
            for tgt in targets:
                new_edges.append(
                    {
                        "source": edge["source"],
                        "target": tgt,
                        "relation": "cross-language",
                        "line": edge.get("line", 0),
                    }
                )
        else:
            new_edges.append(edge)

    graph.edges = new_edges
    # Rebuild adjacency
    graph._adjacency = defaultdict(set)
    for e in graph.edges:
        graph._adjacency[e["source"]].add(e["target"])
