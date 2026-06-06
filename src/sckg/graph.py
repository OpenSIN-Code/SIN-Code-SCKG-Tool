"""Graph data structure with community detection for SCKG.

Docs: graph.doc.md
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode


@dataclass
class Community:
    """A detected community (cluster) of related code symbols."""

    id: int
    nodes: list[dict[str, Any]]
    dominant_language: str
    languages: dict[str, int]
    size: int
    density: float


class KnowledgeGraph:
    """In-memory adjacency-list graph of code symbols and relationships."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._communities: dict[str, str] | None = None
        self._community_objects: list[Community] | None = None

    # ── Building ───────────────────────────────────────────────────────────

    def add_symbol(self, symbol: SymbolNode) -> None:
        self.nodes[symbol._id()] = symbol.to_dict()

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge.to_dict())
        self._adjacency[edge.source].add(edge.target)

    def build_from_parser(self, symbols: list[SymbolNode], edges: list[Edge]) -> None:
        """Populate graph from parser output."""
        for sym in symbols:
            self.add_symbol(sym)
        for edge in edges:
            self.add_edge(edge)

    # ── Persistence ─────────────────────────────────────────────────────────

    def save_json(self, path: str | Path) -> None:
        """Serialize graph to JSON (adjacency list)."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "nodes": list(self.nodes.values()),
                    "edges": self.edges,
                    "communities": self._communities_dict(),
                },
                fh,
                indent=2,
                ensure_ascii=False,
            )

    def load_json(self, path: str | Path) -> None:
        """Load graph from JSON."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.nodes = {n["id"]: n for n in data["nodes"]}
        self.edges = data["edges"]
        self._adjacency = defaultdict(set)
        for e in self.edges:
            self._adjacency[e["source"]].add(e["target"])
        self._communities = None  # will be recomputed on demand
        self._community_objects = None

    # ── Querying ────────────────────────────────────────────────────────────

    def find_symbol(self, query: str) -> list[dict[str, Any]]:
        """Return nodes whose name or docstring matches the query."""
        query_lower = query.lower()
        results = []
        for node in self.nodes.values():
            score = 0
            if query_lower in node["name"].lower():
                score += 10
            if query_lower in node.get("docstring", "").lower():
                score += 3
            if query_lower in node.get("signature", "").lower():
                score += 2
            if node["kind"] == "function" and query_lower in node["name"].lower():
                score += 5  # boost functions
            if score > 0:
                results.append((score, node))
        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results]

    def related_symbols(self, node_id: str) -> list[dict[str, Any]]:
        """Return all nodes reachable from node_id via edges."""
        seen = set()
        stack = [node_id]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for target in self._adjacency.get(current, []):
                stack.append(target)
        return [self.nodes[nid] for nid in seen if nid in self.nodes and nid != node_id]

    # ── Community Detection ─────────────────────────────────────────────────

    def detect_communities(self) -> dict[str, str]:
        """Simple heuristic: group by directory path (shared imports)."""
        if self._communities is not None:
            return self._communities

        communities: dict[str, str] = {}
        community_map: dict[str, str] = {}  # dirpath → community_id

        # Heuristic 1: directory-based grouping
        for nid, node in self.nodes.items():
            fp = node.get("filepath", "")
            dirpath = str(Path(fp).parent)
            if dirpath not in community_map:
                community_map[dirpath] = f"community_{len(community_map)}"
            communities[nid] = community_map[dirpath]

        # Heuristic 2: merge communities that share many import targets
        import_targets: dict[str, set[str]] = defaultdict(set)
        for edge in self.edges:
            if edge["relation"] == "imports":
                import_targets[edge["source"]].add(edge["target"])

        # Find modules with high overlap of imports and merge
        # (simplified: if two files share >0 imports, merge communities)
        dir_imports: dict[str, set[str]] = defaultdict(set)
        for src, targets in import_targets.items():
            src_dir = str(Path(src).parent)
            dir_imports[src_dir].update(targets)

        for d1, t1 in dir_imports.items():
            for d2, t2 in dir_imports.items():
                if d1 != d2 and t1 & t2:
                    c1 = community_map.get(d1)
                    c2 = community_map.get(d2)
                    if c1 and c2 and c1 != c2:
                        # Merge c2 into c1
                        for nid, cid in communities.items():
                            if cid == c2:
                                communities[nid] = c1
                        community_map[d2] = c1

        self._communities = communities
        return communities

    def detect_communities_by_language(self) -> dict[str, list[Community]]:
        """Detect communities split by language, then cluster within each language.

        Returns a dict mapping language → list of Community objects.
        """
        from sckg.communities import detect_language_communities

        return detect_language_communities(self)

    def get_communities(self, mixed: bool = False) -> list[Community]:
        """Return Community objects for the graph.

        Args:
            mixed: If True, detect communities across all languages and mark
                mixed communities (those containing multiple languages).
                If False, group by language first, then cluster within each.
        """
        if mixed:
            from sckg.communities import detect_mixed_communities

            self._community_objects = detect_mixed_communities(self)
        else:
            from sckg.communities import detect_language_communities

            lang_communities = detect_language_communities(self)
            # Flatten into a single list with renumbered IDs
            communities: list[Community] = []
            for idx, comms in enumerate(lang_communities.values(), 1):
                for comm in comms:
                    comm.id = idx + len(communities) - 1
                    communities.append(comm)
            # Renumber IDs sequentially
            for i, comm in enumerate(communities, 1):
                comm.id = i
            self._community_objects = communities
        return self._community_objects

    def _communities_dict(self) -> dict[str, str]:
        if self._communities is None:
            self.detect_communities()
        return self._communities or {}

    # ── Repo Support ──────────────────────────────────────────────────────────

    def get_repos(self) -> list[str]:
        """Return list of unique repository names in the graph."""
        repos = set()
        for node in self.nodes.values():
            repo = node.get("repo", "")
            if repo:
                repos.add(repo)
        for edge in self.edges:
            repo = edge.get("repo", "")
            if repo:
                repos.add(repo)
        return sorted(repos)

    def filter_by_repo(self, repo_name: str) -> "KnowledgeGraph":
        """Return a subgraph containing only nodes/edges from the given repo."""
        subgraph = KnowledgeGraph()
        # Filter nodes
        node_ids = set()
        for nid, node in self.nodes.items():
            if node.get("repo", "") == repo_name:
                subgraph.nodes[nid] = node
                node_ids.add(nid)
        # Filter edges where both endpoints are in the subgraph
        for edge in self.edges:
            if edge.get("repo", "") == repo_name:
                if edge["source"] in node_ids and edge["target"] in node_ids:
                    subgraph.edges.append(edge)
                    subgraph._adjacency[edge["source"]].add(edge["target"])
        return subgraph

    def get_cross_repo_edges(self) -> list[dict[str, Any]]:
        """Return edges where source and target belong to different repos."""
        cross_edges = []
        for edge in self.edges:
            src_repo = self.nodes.get(edge["source"], {}).get("repo", "")
            tgt_repo = self.nodes.get(edge["target"], {}).get("repo", "")
            if src_repo and tgt_repo and src_repo != tgt_repo:
                cross_edges.append(edge)
        return cross_edges

    # ── Incremental Updates ──────────────────────────────────────────────────

    def remove_nodes_by_file(self, filepath: str) -> int:
        """Remove all nodes from a specific file. Returns count of removed nodes."""
        to_remove = [nid for nid, node in self.nodes.items() if node.get("filepath", "") == filepath]
        for nid in to_remove:
            del self.nodes[nid]
            # Remove from adjacency
            self._adjacency.pop(nid, None)
            for src in self._adjacency:
                self._adjacency[src].discard(nid)
        # Remove edges involving removed nodes
        self.edges = [e for e in self.edges if e["source"] not in to_remove and e["target"] not in to_remove]
        # Invalidate communities
        self._communities = None
        self._community_objects = None
        return len(to_remove)

    def upsert_file(self, filepath: str, symbols: list[SymbolNode], edges: list[Edge]) -> None:
        """Add or update nodes/edges from a specific file."""
        # First remove existing nodes from this file
        self.remove_nodes_by_file(filepath)
        # Add new symbols
        for sym in symbols:
            self.add_symbol(sym)
        # Add new edges
        for edge in edges:
            self.add_edge(edge)
