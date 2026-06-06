"""Hot-paths detection for SCKG knowledge graphs.

Identifies the most frequently called functions (hot paths) using various
centrality measures. Helps understand architecture and find optimization targets.

Docs: hotpaths.doc.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx

from sckg.graph import KnowledgeGraph


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class HotNode:
    """A node ranked by hot-path score.

    Attributes:
        node: The original node dict from the knowledge graph.
        score: Centrality score used for ranking (higher = more important).
        rank: 1-based rank in the sorted hot-path list.
        in_degree: Number of incoming edges (how many call this).
        out_degree: Number of outgoing edges (how many this calls).
    """

    node: dict[str, Any]
    score: float
    rank: int
    in_degree: int
    out_degree: int


@dataclass
class HotPathReport:
    """Result of a hot-paths analysis pass.

    Attributes:
        hot_nodes: Nodes sorted by score descending (top N hot paths).
        weight_method: The centrality measure used (in_degree, out_degree, betweenness, pagerank).
        total_nodes: Total number of nodes in the graph.
    """

    hot_nodes: list[HotNode]
    weight_method: str
    total_nodes: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the report to a JSON-friendly dict."""
        return {
            "hot_nodes": [
                {
                    "node": hn.node,
                    "score": hn.score,
                    "rank": hn.rank,
                    "in_degree": hn.in_degree,
                    "out_degree": hn.out_degree,
                }
                for hn in self.hot_nodes
            ],
            "weight_method": self.weight_method,
            "total_nodes": self.total_nodes,
        }


def compute_hot_paths(
    graph: KnowledgeGraph,
    top_n: int = 20,
    weight: str = "in_degree",
) -> HotPathReport:
    """Compute the top N hot paths in the knowledge graph.

    Args:
        graph: The knowledge graph to analyze.
        top_n: Number of top hot paths to return (default: 20).
        weight: Centrality measure to use:
            - "in_degree": Number of incoming edges (most called functions).
            - "out_degree": Number of outgoing edges (most calling functions).
            - "betweenness": Betweenness centrality (bridges between clusters).
            - "pagerank": PageRank score (importance in graph).

    Returns:
        HotPathReport with ranked hot nodes, weight method, and total node count.

    Raises:
        ValueError: If weight method is not recognized.
    """
    if not graph.nodes:
        return HotPathReport(hot_nodes=[], weight_method=weight, total_nodes=0)

    # Build NetworkX graph from KnowledgeGraph
    nx_graph = nx.DiGraph()
    for nid, node in graph.nodes.items():
        nx_graph.add_node(nid, **node)

    for edge in graph.edges:
        source = edge.get("source", "")
        target = edge.get("target", "")
        if source in graph.nodes and target in graph.nodes:
            nx_graph.add_edge(source, target)

    # Compute degrees for all nodes (used for in/out degree metrics)
    in_degrees = dict(nx_graph.in_degree())
    out_degrees = dict(nx_graph.out_degree())

    # Compute scores based on weight method
    if weight == "in_degree":
        scores = in_degrees
    elif weight == "out_degree":
        scores = out_degrees
    elif weight == "betweenness":
        scores = nx.betweenness_centrality(nx_graph)
    elif weight == "pagerank":
        scores = nx.pagerank(nx_graph)
    else:
        raise ValueError(f"Unknown weight method: {weight}. Must be one of: in_degree, out_degree, betweenness, pagerank")

    # Sort nodes by score descending
    sorted_nodes = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=True,
    )

    # Build HotNode list for top N
    hot_nodes: list[HotNode] = []
    for rank, (nid, score) in enumerate(sorted_nodes[:top_n], 1):
        node = graph.nodes[nid]
        hot_nodes.append(
            HotNode(
                node=node,
                score=float(score),
                rank=rank,
                in_degree=in_degrees.get(nid, 0),
                out_degree=out_degrees.get(nid, 0),
            )
        )

    return HotPathReport(
        hot_nodes=hot_nodes,
        weight_method=weight,
        total_nodes=len(graph.nodes),
    )
