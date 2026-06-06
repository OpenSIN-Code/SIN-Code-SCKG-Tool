# Multi-Repo Dashboard

## Purpose
Generate standalone HTML dashboards for multi-repository analysis with repo comparison, cross-repo chord diagrams, community overview, hot paths, and live WebSocket updates.

## Dependencies
- `sckg.graph.KnowledgeGraph` - input graph
- `sckg.hotpaths` - hot paths per repo
- `sckg.dead_code` - dead code per repo
- D3.js (CDN) - chord diagram, tables, charts

## Components
| Function | Description |
|----------|-------------|
| `collect_repo_stats()` | Per-repo node/edge/language counts |
| `build_cross_repo_matrix()` | Cross-repo edge matrix for chord diagram |
| `collect_community_overview()` | Community list with language breakdown |
| `collect_hot_paths_per_repo()` | Top hot paths grouped by repo |
| `collect_dead_code_per_repo()` | Dead code count per repo |
| `generate_dashboard()` | Main entry point - writes HTML file |

## Usage
```python
from sckg.dashboard import generate_dashboard
from sckg.graph import KnowledgeGraph
from pathlib import Path

graph = KnowledgeGraph()
graph.load_json("workspace_graph.json")
generate_dashboard(
    graph,
    output_path=Path("dashboard.html"),
    workspace_path="~/dev",
    graphql_url="ws://localhost:8080/graphql",
)
```

## CLI
```bash
sckg dashboard graph.json --output dashboard.html --graphql ws://localhost:8080/graphql
```

## Dashboard Sections
1. **Stats overview** - repos, nodes, edges, communities counts
2. **Repository comparison table** - nodes/edges/entry points/languages per repo
3. **Cross-repo chord diagram** - D3.js chord diagram showing repo-to-repo call flows
4. **Community overview table** - language, size, density, top node
5. **Hot paths by repo** - top functions per repo with scores
6. **Dead code by repo** - dead code count per repo
7. **Live events log** - WebSocket connection to GraphQL subscriptions

## Live Updates
The dashboard connects to GraphQL subscriptions via WebSocket:
- Shows green indicator when connected
- Red when disconnected
- Displays incoming events (graph_updated, node_changed, hot_paths_changed) in real-time
- Requires the GraphQL server to be running (`sckg serve` or `sckg watch`)

## Caveats
- WebSocket connection is best-effort - dashboard works without it
- Large repos may slow chord diagram rendering
- Standalone HTML - no server required for viewing (except live updates)
- D3.js loaded from CDN (requires internet for first load)