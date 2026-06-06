"""Graph data structure with community detection for SCKG.

Docs: graph.doc.md
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode


class KnowledgeGraph:
    """In-memory adjacency-list graph of code symbols and relationships."""

    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[dict[str, Any]] = []
        self._adjacency: dict[str, set[str]] = defaultdict(set)
        self._communities: dict[str, str] | None = None

    # ── Building ──────────────────────────────────────────────────────────

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

    # ── Persistence ───────────────────────────────────────────────────────

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

    # ── Querying ──────────────────────────────────────────────────────────

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

    # ── Community Detection ───────────────────────────────────────────────

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

    def _communities_dict(self) -> dict[str, str]:
        if self._communities is None:
            self.detect_communities()
        return self._communities or {}
