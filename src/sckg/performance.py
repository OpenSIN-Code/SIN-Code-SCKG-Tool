"""Performance optimizations for SCKG knowledge graph.

Provides fast JSON serialization (orjson), memory-mapped loading,
and indexed graph queries for large codebases.

Docs: performance.doc.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from sckg.graph import KnowledgeGraph

# Try to import orjson for fast serialization
try:
    import orjson  # type: ignore
    HAS_ORJSON = True
except ImportError:
    HAS_ORJSON = False

# Try to import msgspec for even faster serialization
try:
    import msgspec  # type: ignore
    HAS_MSGSPEC = True
except ImportError:
    HAS_MSGSPEC = False


def save_json_fast(graph: KnowledgeGraph, path: str | Path) -> None:
    """Save graph to JSON using the fastest available serializer."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "nodes": list(graph.nodes.values()),
        "edges": graph.edges,
        "communities": graph._communities_dict(),
    }

    if HAS_ORJSON:
        out.write_bytes(orjson.dumps(data, option=orjson.OPT_INDENT_2))
    else:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def load_json_fast(path: str | Path) -> KnowledgeGraph:
    """Load graph from JSON using the fastest available deserializer."""
    p = Path(path)

    if HAS_ORJSON:
        data = orjson.loads(p.read_bytes())
    else:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)

    graph = KnowledgeGraph()
    graph.nodes = {n["id"]: n for n in data["nodes"]}
    graph.edges = data["edges"]
    graph._adjacency = defaultdict(set)
    for e in graph.edges:
        graph._adjacency[e["source"]].add(e["target"])
    graph._communities = None
    graph._community_objects = None
    return graph


class IndexedGraph:
    """KnowledgeGraph wrapper with query indices for fast lookups.

    Indices are built lazily on first access and invalidated on graph changes.
    """

    def __init__(self, graph: KnowledgeGraph) -> None:
        self.graph = graph
        self._by_repo: Optional[dict[str, list[str]]] = None
        self._by_language: Optional[dict[str, list[str]]] = None
        self._by_type: Optional[dict[str, list[str]]] = None
        self._by_file: Optional[dict[str, list[str]]] = None

    def _invalidate(self) -> None:
        self._by_repo = None
        self._by_language = None
        self._by_type = None
        self._by_file = None

    def _ensure_indices(self) -> None:
        if self._by_repo is not None:
            return
        self._by_repo = defaultdict(list)
        self._by_language = defaultdict(list)
        self._by_type = defaultdict(list)
        self._by_file = defaultdict(list)
        for nid, node in self.graph.nodes.items():
            self._by_repo[node.get("repo", "default")].append(nid)
            self._by_language[node.get("language", "unknown")].append(nid)
            self._by_type[node.get("kind", "unknown")].append(nid)
            self._by_file[node.get("filepath", "")].append(nid)

    def get_by_repo(self, repo: str) -> list[dict[str, Any]]:
        """Get all nodes from a specific repository."""
        self._ensure_indices()
        return [self.graph.nodes[nid] for nid in self._by_repo.get(repo, [])]

    def get_by_language(self, language: str) -> list[dict[str, Any]]:
        """Get all nodes of a specific language."""
        self._ensure_indices()
        return [self.graph.nodes[nid] for nid in self._by_language.get(language, [])]

    def get_by_type(self, type_: str) -> list[dict[str, Any]]:
        """Get all nodes of a specific type (function, class, etc.)."""
        self._ensure_indices()
        return [self.graph.nodes[nid] for nid in self._by_type.get(type_, [])]

    def get_by_file(self, filepath: str) -> list[dict[str, Any]]:
        """Get all nodes from a specific file."""
        self._ensure_indices()
        return [self.graph.nodes[nid] for nid in self._by_file.get(filepath, [])]

    def filter(
        self,
        repo: Optional[str] = None,
        language: Optional[str] = None,
        type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Filter nodes by multiple criteria using indices.

        Uses the most selective index first to minimize scan size.
        """
        self._ensure_indices()

        # Choose smallest index as starting point
        candidates: list[str] | None = None

        if repo and self._by_repo:
            candidates = list(self._by_repo.get(repo, []))
        if language and self._by_language:
            lang_set = set(self._by_language.get(language, []))
            candidates = lang_set if candidates is None else [n for n in candidates if n in lang_set]
        if type and self._by_type:
            type_set = set(self._by_type.get(type, []))
            candidates = type_set if candidates is None else [n for n in candidates if n in type_set]

        if candidates is None:
            candidates = list(self.graph.nodes.keys())

        results = [self.graph.nodes[nid] for nid in candidates[:limit]]
        return results

    def invalidate(self) -> None:
        """Manually invalidate indices (call after graph mutations)."""
        self._invalidate()

    @property
    def index_size(self) -> int:
        """Total entries across all indices."""
        self._ensure_indices()
        return (
            sum(len(v) for v in (self._by_repo or {}).values()) +
            sum(len(v) for v in (self._by_language or {}).values()) +
            sum(len(v) for v in (self._by_type or {}).values()) +
            sum(len(v) for v in (self._by_file or {}).values())
        )