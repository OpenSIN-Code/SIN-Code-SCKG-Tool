# Hot Paths Detection

## Purpose
Identify the most frequently called functions (hot paths) in a codebase using various centrality measures. Helps understand architecture, find optimization targets, and locate critical infrastructure code.

## Dependencies
- `sckg.graph.KnowledgeGraph` - input graph
- `networkx` - centrality algorithms (betweenness, pagerank)

## Usage
```python
from sckg.hotpaths import compute_hot_paths

report = compute_hot_paths(graph, top_n=20, weight="in_degree")
# weight options: "in_degree", "out_degree", "betweenness", "pagerank"
```

## Public API
- `HotNode` - ranked node with score, rank, in/out degree
- `HotPathReport` - collection of hot nodes with metadata
- `compute_hot_paths(graph, top_n, weight)` - main function

## Weight Methods
| Method | Description | Use Case |
|--------|-------------|----------|
| `in_degree` | Number of incoming edges | Most called functions |
| `out_degree` | Number of outgoing edges | Most calling functions |
| `betweenness` | Betweenness centrality | Bridge functions between clusters |
| `pagerank` | PageRank score | Overall importance in graph |

## Visualization
Hot nodes rendered with:
- Gold border (`#FFD700`, 4px)
- Glow filter (`feGaussianBlur`)
- Radius scaled by score (base + up to 12px)

## Caveats
- Requires NetworkX (installed as dependency)
- Betweenness/Pagerank are O(V+E) and O(V) respectively - may be slow on large graphs
- Empty graphs return empty report gracefully