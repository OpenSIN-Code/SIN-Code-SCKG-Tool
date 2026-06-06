# GraphQL Resolvers

## Purpose
Resolve GraphQL queries by loading the knowledge graph and executing the requested operations.

## Dependencies
- `sckg.api.schema` - GraphQL types
- `sckg.graph.KnowledgeGraph` - graph data structure
- `sckg.hotpaths` - hot paths computation
- `sckg.dead_code` - dead code analysis
- `sckg.search` - n-gram search
- `sckg.communities` - community detection

## Global State
- `_graph` - loaded KnowledgeGraph (singleton)
- `_index` - NgramIndex for search
- `_graph_path` - path to JSON graph file

## Resolvers
| Resolver | GraphQL Field | Description |
|----------|---------------|-------------|
| `resolve_nodes` | Query.nodes | Filter nodes by language/type |
| `resolve_node` | Query.node | Single node by ID |
| `resolve_edges` | Query.edges | Filter edges by source/target/type |
| `resolve_communities` | Query.communities | Language-aware communities |
| `resolve_hot_paths` | Query.hot_paths | Top N hot paths |
| `resolve_dead_code` | Query.dead_code | Dead code report |
| `resolve_search` | Query.search | N-gram search |
| `resolve_stats` | Query.stats | Graph statistics |

## Graph Loading
- `load_graph(path)` - loads KnowledgeGraph from JSON
- On first query: loads from `graph_path` passed to `create_app()`
- Context fallback: `info.context.graph` if set by middleware
- Cached globally after first load

## Caveats
- Global state not thread-safe (single graph per process)
- Index rebuilt on graph load
- No invalidation - restart server to reload graph