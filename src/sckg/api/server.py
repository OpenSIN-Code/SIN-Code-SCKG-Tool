"""FastAPI + Strawberry GraphQL server for SCKG knowledge graph.

Provides HTTP API with GraphQL endpoint and GraphiQL playground.

Docs: server.doc.md
"""

from __future__ import annotations

import json
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from sckg.api.resolvers import load_graph
from sckg.search import build_ngram_index
from sckg.api.schema import schema


# ── App Lifecycle ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load graph on startup."""
    global _graph, _index
    if _graph is None and hasattr(app.state, "graph_path") and app.state.graph_path:
        _graph = load_graph(app.state.graph_path)
        _index = None  # Will be built on first query
    yield
    # Cleanup on shutdown


def create_app(graph_path: Optional[Path] = None) -> FastAPI:
    """Create FastAPI app with GraphQL endpoint."""
    global _graph, _graph_path, _index
    from sckg.api.resolvers import _graph as resolver_graph, _graph_path as resolver_graph_path, _index as resolver_index
    import sckg.api.resolvers as resolvers_module

    # Load graph immediately if path provided
    if graph_path:
        _graph = load_graph(graph_path)
        _graph_path = graph_path
        _index = build_ngram_index(_graph)
        # Also update the module globals
        resolvers_module._graph = _graph
        resolvers_module._graph_path = _graph_path
        resolvers_module._index = _index

    app = FastAPI(
        title="SCKG GraphQL API",
        description="Semantic Codebase Knowledge Graph - GraphQL API",
        version="0.4.0",
        lifespan=lifespan,
    )

    # Store graph path in app state
    if graph_path:
        app.state.graph_path = graph_path

    # CORS for dashboard access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # GraphQL endpoint
    graphql_app = GraphQLRouter(
        schema,
        graphql_ide="graphiql",  # Enable GraphiQL playground at /graphql
    )
    app.include_router(graphql_app, prefix="/graphql")

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "graph_loaded": _graph is not None}

    # Schema SDL endpoint
    @app.get("/schema")
    async def get_schema():
        return {"schema": str(schema)}

    # Graph stats (simple REST endpoint)
    @app.get("/stats")
    async def get_stats():
        if _graph is None:
            return {"error": "No graph loaded"}
        from sckg.dead_code import find_dead_code
        lang_counts = {}
        type_counts = {}
        for node in _graph.nodes.values():
            lang = node.get("language", "unknown")
            kind = node.get("kind", "unknown")
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            type_counts[kind] = type_counts.get(kind, 0) + 1
        dead_report = find_dead_code(_graph)
        return {
            "node_count": len(_graph.nodes),
            "edge_count": len(_graph.edges),
            "languages": lang_counts,
            "types": type_counts,
            "community_count": len(set(_graph._communities_dict().values())) if _graph._communities_dict() else 0,
            "dead_code_count": len(dead_report.dead_nodes),
            "entry_point_count": len(dead_report.entry_points),
            "coverage_pct": dead_report.coverage_pct,
        }

    return app


# ── CLI Entry Point ────────────────────────────────────────────────────────────

def run_server(
    graph_path: Path,
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
) -> None:
    """Run the GraphQL server."""
    app = create_app(graph_path)
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m sckg.api.server <graph.json> [host] [port]")
        sys.exit(1)
    run_server(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0", int(sys.argv[3]) if len(sys.argv) > 3 else 8080)