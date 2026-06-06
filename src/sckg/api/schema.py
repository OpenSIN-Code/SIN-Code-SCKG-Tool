"""GraphQL schema for SCKG knowledge graph API.

Docs: schema.doc.md
"""

from __future__ import annotations

import strawberry
from strawberry.types import Info
from typing import Optional, List, Dict, Any, AsyncGenerator, AsyncIterator
import json


@strawberry.type
class Node:
    """A code symbol (function, class, variable, module, etc.) in the knowledge graph."""

    id: str
    name: str
    type: str
    language: str
    file_path: str
    line_start: int
    line_end: int
    docstring: Optional[str]
    in_degree: int
    out_degree: int
    community_id: Optional[int]
    is_hot: bool
    is_dead: bool
    is_entry_point: bool
    repo: str


@strawberry.type
class Edge:
    """A relationship between two symbols in the knowledge graph."""

    id: str
    source: str
    target: str
    type: str
    weight: float
    repo: str


@strawberry.type
class Community:
    """A detected community (cluster) of related code symbols."""

    id: int
    dominant_language: str
    languages: JSON
    size: int
    density: float
    nodes: List[Node]


@strawberry.type
class HotNode:
    """A node in the hot paths report with its score and rank."""

    node: Node
    score: float
    rank: int


@strawberry.type
class HotPathReport:
    """Report of hot paths (most important nodes) in the graph."""

    hot_nodes: List[HotNode]
    weight_method: str


@strawberry.type
class DeadCodeReport:
    """Report of dead code analysis."""

    dead_nodes: List[Node]
    entry_points: List[Node]
    suspicious_nodes: List[Node]
    coverage_pct: float


@strawberry.type
class SearchResult:
    """A search result with relevance score and context."""

    node: Node
    score: float
    matched_ngrams: List[str]
    snippet: str


@strawberry.type
class Stats:
    """Statistics about the knowledge graph."""

    node_count: int
    edge_count: int
    languages: Dict[str, int]
    types: Dict[str, int]
    community_count: int
    dead_code_count: int
    entry_point_count: int
    coverage_pct: float


@strawberry.type
class SimilarityResult:
    """A code similarity search result."""

    node: Node
    score: float
    method: str
    matched_features: List[str]


@strawberry.type
class ADR:
    """An Architecture Decision Record."""

    id: str
    title: str
    status: str
    date: str
    decision: str
    context: str
    consequences: str
    alternatives: str
    tags: List[str]


# ── JSON scalar for flexible stats output ────────────────────────────────────

@strawberry.type
class JSON:
    """Arbitrary JSON value for flexible query returns."""

    data: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "JSON":
        return cls(data=json.dumps(d))

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self.data)


# ── Query ────────────────────────────────────────────────────────────────────


@strawberry.type
class Query:
    """Root GraphQL query type for SCKG knowledge graph."""

    @strawberry.field
    def nodes(
        self,
        info: Info,
        language: Optional[str] = None,
        type: Optional[str] = None,
        repo: Optional[str] = None,
        limit: int = 100,
    ) -> List[Node]:
        """Return nodes with optional filtering by language, type, and repo."""
        from sckg.api.resolvers import resolve_nodes

        return resolve_nodes(info, language=language, type=type, repo=repo, limit=limit)

    @strawberry.field
    def node(self, info: Info, id: str) -> Optional[Node]:
        """Return a single node by its unique ID."""
        from sckg.api.resolvers import resolve_node

        return resolve_node(info, id=id)

    @strawberry.field
    def edges(
        self,
        info: Info,
        source: Optional[str] = None,
        target: Optional[str] = None,
        type: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> List[Edge]:
        """Return edges with optional filtering by source, target, type, and repo."""
        from sckg.api.resolvers import resolve_edges

        return resolve_edges(info, source=source, target=target, type=type, repo=repo)

    @strawberry.field
    def communities(self, info: Info) -> List[Community]:
        """Return all detected communities in the graph."""
        from sckg.api.resolvers import resolve_communities

        return resolve_communities(info)

    @strawberry.field
    def hot_paths(
        self, info: Info, weight: str = "in_degree", top: int = 20
    ) -> HotPathReport:
        """Return hot paths (most connected/important nodes) using specified weight method."""
        from sckg.api.resolvers import resolve_hot_paths

        return resolve_hot_paths(info, weight=weight, top=top)

    @strawberry.field
    def dead_code(self, info: Info) -> DeadCodeReport:
        """Return dead code analysis report."""
        from sckg.api.resolvers import resolve_dead_code

        return resolve_dead_code(info)

    @strawberry.field
    def search(self, info: Info, query: str, top: int = 10) -> List[SearchResult]:
        """Search the graph for symbols matching the query string."""
        from sckg.api.resolvers import resolve_search

        return resolve_search(info, query=query, top=top)

    @strawberry.field
    def stats(self, info: Info) -> JSON:
        """Return graph statistics as JSON."""
        from sckg.api.resolvers import resolve_stats

        return resolve_stats(info)

    @strawberry.field
    def repos(self, info: Info) -> List[str]:
        """Return list of repository names in the graph."""
        from sckg.api.resolvers import resolve_repos

        return resolve_repos(info)

    @strawberry.field
    def cross_repo_edges(self, info: Info) -> List[Edge]:
        """Return edges that connect different repositories."""
        from sckg.api.resolvers import resolve_cross_repo_edges

        return resolve_cross_repo_edges(info)

    @strawberry.field
    def similar(self, info: Info, node_id: str, top: int = 10, method: str = "jaccard") -> List[SimilarityResult]:
        """Find code symbols similar to the given node using structural analysis."""
        from sckg.api.resolvers import resolve_similar

        return resolve_similar(info, node_id=node_id, top=top, method=method)

    @strawberry.field
    def adrs(self, info: Info) -> List[ADR]:
        """Return generated Architecture Decision Records."""
        from sckg.api.resolvers import resolve_adrs

        return resolve_adrs(info)


# ── Subscription ──────────────────────────────────────────────────────────────


@strawberry.type
class Subscription:
    """GraphQL subscriptions for real-time updates."""

    @strawberry.subscription
    async def graph_updated(self, info: Info) -> AsyncIterator[str]:
        """Fires when the graph is updated (full reload or incremental)."""
        from sckg.api.resolvers import subscribe_graph_updated

        async for msg in subscribe_graph_updated(info):
            yield msg

    @strawberry.subscription
    async def node_changed(self, info: Info, repo: Optional[str] = None) -> AsyncIterator[str]:
        """Fires when a node is added, updated, or deleted."""
        from sckg.api.resolvers import subscribe_node_changed

        async for msg in subscribe_node_changed(info, repo=repo):
            yield msg

    @strawberry.subscription
    async def hot_paths_changed(self, info: Info, weight: str = "in_degree") -> AsyncIterator[str]:
        """Fires when hot paths are recomputed."""
        from sckg.api.resolvers import subscribe_hot_paths_changed

        async for msg in subscribe_hot_paths_changed(info, weight=weight):
            yield msg


schema = strawberry.Schema(query=Query, subscription=Subscription)