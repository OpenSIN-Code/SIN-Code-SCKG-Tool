"""Tests for GraphQL API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from sckg.api.server import create_app
from sckg.graph import KnowledgeGraph


def _make_test_graph() -> KnowledgeGraph:
    """Create a small test graph."""
    g = KnowledgeGraph()
    g.nodes = {
        "n1": {"id": "n1", "name": "main", "kind": "function", "language": "python",
               "filepath": "main.py", "line": 1, "docstring": "Main entry point",
               "signature": "main() -> None"},
        "n2": {"id": "n2", "name": "helper", "kind": "function", "language": "python",
               "filepath": "utils.py", "line": 10, "docstring": "Helper function",
               "signature": "helper() -> int"},
    }
    g.edges = [
        {"source": "n1", "target": "n2", "relation": "calls", "id": "e1"},
    ]
    return g


@pytest.fixture
def test_graph_path(tmp_path: Path) -> Path:
    g = _make_test_graph()
    p = tmp_path / "test_graph.json"
    g.save_json(p)
    return p


@pytest_asyncio.fixture
async def client(test_graph_path: Path):
    app = create_app(test_graph_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["graph_loaded"] is True


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    resp = await client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_count"] == 2
    assert data["edge_count"] == 1
    assert "python" in data["languages"]


@pytest.mark.asyncio
async def test_schema_endpoint(client):
    resp = await client.get("/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert "schema" in data
    assert "type Query" in data["schema"]


@pytest.mark.asyncio
async def test_graphql_query_nodes(client):
    query = """
    query {
      nodes(language: "python", type: "function", limit: 5) {
        id
        name
        type
        language
        filePath
        inDegree
        outDegree
      }
    }
    """
    resp = await client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" not in data
    assert "data" in data
    nodes = data["data"]["nodes"]
    assert len(nodes) == 2
    assert nodes[0]["name"] in ["main", "helper"]
    assert nodes[0]["language"] == "python"


@pytest.mark.asyncio
async def test_graphql_query_hot_paths(client):
    query = """
    query {
      hotPaths(weight: "in_degree", top: 10) {
        weightMethod
        hotNodes {
          node { name }
          score
          rank
        }
      }
    }
    """
    resp = await client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" not in data
    hp = data["data"]["hotPaths"]
    assert hp["weightMethod"] == "in_degree"
    assert len(hp["hotNodes"]) == 2
    # helper has 1 incoming, main has 0
    assert hp["hotNodes"][0]["node"]["name"] == "helper"
    assert hp["hotNodes"][0]["score"] == 1.0


@pytest.mark.asyncio
async def test_graphql_query_search(client):
    query = """
    query {
      search(query: "main entry", top: 5) {
        node { name }
        score
        matchedNgrams
        snippet
      }
    }
    """
    resp = await client.post("/graphql", json={"query": query})
    assert resp.status_code == 200
    data = resp.json()
    assert "errors" not in data
    results = data["data"]["search"]
    assert len(results) >= 1
    assert results[0]["node"]["name"] == "main"