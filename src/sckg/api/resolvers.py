"""GraphQL resolvers for SCKG knowledge graph API.

Loads the knowledge graph and resolves GraphQL queries.

Docs: resolvers.doc.md
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import strawberry
from strawberry.types import Info

from sckg.communities import Community, detect_language_communities
from sckg.cross_repo import KNOWN_TOOLS
from sckg.dead_code import DeadCodeReport, find_dead_code
from sckg.graph import KnowledgeGraph
from sckg.hotpaths import HotNode, HotPathReport, compute_hot_paths
from sckg.search import NgramIndex, SearchResult, build_ngram_index, search


# ── Global state (loaded on first query) ──────────────────────────────────────

_graph: KnowledgeGraph | None = None
_index: NgramIndex | None = None
_graph_path: Path | None = None


def _ensure_graph(info: Info) -> KnowledgeGraph:
    """Load graph from context or global state."""
    global _graph, _index

    if _graph is not None:
        return _graph

    # Try to get from request context (set by server.py)
    context = info.context
    if hasattr(context, "graph") and context.graph is not None:
        _graph = context.graph
        _index = build_ngram_index(_graph)
        return _graph

    # Fallback: try to load from global path
    if _graph_path and _graph_path.exists():
        _graph = KnowledgeGraph()
        _graph.load_json(_graph_path)
        _index = build_ngram_index(_graph)
        return _graph

    raise RuntimeError("No graph loaded. Use `sckg serve --graph-path` or set context.")


def _node_to_gql(node: dict[str, Any]) -> "Node":
    """Convert KnowledgeGraph node dict to GraphQL Node type."""
    from sckg.api.schema import Node
    return Node(
        id=node.get("id", ""),
        name=node.get("name", ""),
        type=node.get("kind", ""),
        language=node.get("language", ""),
        file_path=node.get("filepath", ""),
        line_start=node.get("line", 0),
        line_end=node.get("line_end", node.get("line", 0)),
        docstring=node.get("docstring"),
        in_degree=node.get("in_degree", 0),
        out_degree=node.get("out_degree", 0),
        community_id=node.get("community_id"),
        is_hot=node.get("is_hot", False),
        is_dead=node.get("is_dead", False),
        is_entry_point=node.get("is_entry_point", False),
    )


# ── Resolvers ──────────────────────────────────────────────────────────────────

def resolve_nodes(
    info: Info,
    language: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = 100,
) -> list["Node"]:
    """Return nodes with optional filtering by language and type."""
    graph = _ensure_graph(info)
    from sckg.api.schema import Node

    nodes = []
    for node in graph.nodes.values():
        if language and node.get("language") != language:
            continue
        if type and node.get("kind") != type:
            continue
        nodes.append(_node_to_gql(node))
        if len(nodes) >= limit:
            break
    return nodes


def resolve_node(info: Info, id: str) -> Optional["Node"]:
    """Return a single node by its unique ID."""
    graph = _ensure_graph(info)
    from sckg.api.schema import Node

    node = graph.nodes.get(id)
    return _node_to_gql(node) if node else None


def resolve_edges(
    info: Info,
    source: Optional[str] = None,
    target: Optional[str] = None,
    type: Optional[str] = None,
) -> list["Edge"]:
    """Return edges with optional filtering by source, target, or type."""
    graph = _ensure_graph(info)
    from sckg.api.schema import Edge

    edges = []
    for edge in graph.edges:
        if source and edge.get("source") != source:
            continue
        if target and edge.get("target") != target:
            continue
        if type and edge.get("relation") != type:
            continue
        edges.append(Edge(
            id=edge.get("id", ""),
            source=edge.get("source", ""),
            target=edge.get("target", ""),
            type=edge.get("relation", ""),
            weight=edge.get("weight", 1.0),
        ))
    return edges


def resolve_communities(info: Info) -> list["Community"]:
    """Return all detected communities in the graph."""
    graph = _ensure_graph(info)
    from sckg.api.schema import Community, JSON

    # Use language-aware community detection
    lang_comms = detect_language_communities(graph)

    gql_comms = []
    for lang, comm_list in lang_comms.items():
        for comm in comm_list:
            gql_comms.append(Community(
                id=comm.id,
                dominant_language=comm.dominant_language,
                languages=JSON.from_dict(comm.languages),
                size=comm.size,
                density=comm.density,
                nodes=[_node_to_gql(n) for n in comm.nodes],
            ))
    return gql_comms


def resolve_hot_paths(
    info: Info,
    weight: str = "in_degree",
    top: int = 20,
) -> "HotPathReport":
    """Return hot paths (most connected/important nodes) using specified weight method."""
    graph = _ensure_graph(info)
    from sckg.api.schema import HotPathReport, HotNode

    report = compute_hot_paths(graph, top_n=top, weight=weight)

    hot_nodes = []
    for hn in report.hot_nodes:
        hot_nodes.append(HotNode(
            node=_node_to_gql(hn.node),
            score=hn.score,
            rank=hn.rank,
        ))

    return HotPathReport(
        hot_nodes=hot_nodes,
        weight_method=report.weight_method,
    )


def resolve_dead_code(info: Info) -> "DeadCodeReport":
    """Return dead code analysis report."""
    graph = _ensure_graph(info)
    from sckg.api.schema import DeadCodeReport

    report = find_dead_code(graph)

    return DeadCodeReport(
        dead_nodes=[_node_to_gql(n) for n in report.dead_nodes],
        entry_points=[_node_to_gql(n) for n in report.entry_points],
        suspicious_nodes=[_node_to_gql(n) for n in report.suspicious_nodes],
        coverage_pct=report.coverage_pct,
    )


def resolve_search(info: Info, query: str, top: int = 10) -> list["SearchResult"]:
    """Search the graph for symbols matching the query string."""
    global _index
    graph = _ensure_graph(info)

    if _index is None:
        _index = build_ngram_index(graph)

    from sckg.api.schema import SearchResult

    results = search(query, graph, _index, top_k=top)
    return [SearchResult(
        node=_node_to_gql(r.node),
        score=r.score,
        matched_ngrams=r.matched_ngrams,
        snippet=r.snippet,
    ) for r in results]


def resolve_stats(info: Info) -> "JSON":
    """Return graph statistics as JSON."""
    graph = _ensure_graph(info)

    lang_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    for node in graph.nodes.values():
        lang = node.get("language", "unknown")
        kind = node.get("kind", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
        type_counts[kind] = type_counts.get(kind, 0) + 1

    dead_report = find_dead_code(graph)

    stats = {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "languages": lang_counts,
        "types": type_counts,
        "community_count": len(set(graph._communities_dict().values())) if graph._communities_dict() else 0,
        "dead_code_count": len(dead_report.dead_nodes),
        "entry_point_count": len(dead_report.entry_points),
        "coverage_pct": dead_report.coverage_pct,
    }

    from sckg.api.schema import JSON
    return JSON.from_dict(stats)


# ── Graph loading helper ───────────────────────────────────────────────────────

def load_graph(graph_path: Path) -> KnowledgeGraph:
    """Load knowledge graph from JSON file."""
    graph = KnowledgeGraph()
    graph.load_json(graph_path)
    return graph