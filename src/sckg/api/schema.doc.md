# GraphQL Schema

## Purpose
GraphQL schema definition for SCKG knowledge graph API. Exposes nodes, edges, communities, hot paths, dead code, and search via GraphQL.

## Dependencies
- `strawberry-graphql` - GraphQL library
- `sckg.graph` types - Node, Edge, Community, etc.

## Schema Types
| Type | Description |
|------|-------------|
| `Node` | Code symbol (function, class, variable, module) |
| `Edge` | Relationship between symbols |
| `Community` | Detected cluster of related symbols |
| `HotPathReport` | Hot paths analysis result |
| `HotNode` | Single hot path entry |
| `DeadCodeReport` | Dead code analysis result |
| `SearchResult` | Search result with score and snippet |
| `Stats` | Graph statistics |
| `JSON` | Flexible scalar for arbitrary JSON |

## Queries
| Query | Parameters | Returns |
|-------|------------|---------|
| `nodes` | language, type, limit | List[Node] |
| `node` | id | Node |
| `edges` | source, target, type | List[Edge] |
| `communities` | - | List[Community] |
| `hot_paths` | weight, top | HotPathReport |
| `dead_code` | - | DeadCodeReport |
| `search` | query, top | List[SearchResult] |
| `stats` | - | JSON |

## Weight Methods (hot_paths)
- `in_degree` - most called
- `out_degree` - most calling
- `betweenness` - bridges
- `pagerank` - importance

## Usage
```graphql
query {
  nodes(language: "python", type: "function", limit: 10) {
    id name type language filePath inDegree outDegree
  }
  hotPaths(weight: "pagerank", top: 20) {
    hotNodes { node { name } score rank }
  }
  search(query: "parse json", top: 5) {
    node { name filePath } score matchedNgrams snippet
  }
}
```

## Caveats
- `languages` field on Community uses JSON scalar (Dict[str, int])
- Graph must be loaded via `sckg serve --graph-path` or context
- No authentication/authorization built-in
- CORS enabled for all origins