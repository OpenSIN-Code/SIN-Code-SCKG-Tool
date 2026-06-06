# GraphQL Server

## Purpose
FastAPI + Strawberry GraphQL server for SCKG knowledge graph. Provides HTTP API with GraphQL endpoint and GraphiQL playground.

## Dependencies
- `fastapi` - web framework
- `uvicorn` - ASGI server
- `strawberry-graphql` - GraphQL
- `sckg.api.resolvers` - query resolvers
- `sckg.api.schema` - GraphQL schema

## Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/graphql` | POST | GraphQL queries (GraphiQL UI at GET) |
| `/health` | GET | Health check + graph loaded status |
| `/schema` | GET | GraphQL SDL schema |
| `/stats` | GET | Simple REST stats endpoint |

## CORS
Enabled for all origins (`*`) for dashboard access.

## CLI Usage
```bash
sckg serve /path/to/graph.json --host 0.0.0.0 --port 8080 --reload
```

## Python Usage
```python
from sckg.api.server import create_app, run_server
from pathlib import Path

app = create_app(Path("graph.json"))
run_server(Path("graph.json"), host="0.0.0.0", port=8080)
```

## Graph Loading
- Graph loaded at startup from `graph_path`
- Global state in `resolvers` module updated
- Lifespan handler for startup/shutdown

## Caveats
- Single graph per server instance
- No hot reload of graph (restart required)
- GraphiQL enabled by default at `/graphql`
- Not production-hardened (no auth, rate limiting)