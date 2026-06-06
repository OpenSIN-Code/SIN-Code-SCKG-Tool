# Code Similarity Search (AST-Structural)

## Purpose
Find structurally similar code across the codebase using AST-derived features, not just textual n-grams.

## Dependencies
- `sckg.graph.KnowledgeGraph` - graph with call edges
- Pure Python - no external ML dependencies

## Feature Extraction
| Feature | Source | Weight (AST method) |
|---------|--------|---------------------|
| Call signature | Outgoing `calls` edges | 40% |
| Control flow | Signature + docstring keywords | 20% |
| Type hints | Function signature | 20% |
| Kind match | Node kind (function/class) | 10% |
| Language match | Node language | 10% |

## Methods
| Method | Description | Use Case |
|--------|-------------|----------|
| `jaccard` | Call set overlap only | Find functions calling same dependencies |
| `cosine` | Control flow + types | Find functions with similar logic patterns |
| `ast` | Combined structural | Comprehensive similarity |

## Usage
```python
from sckg.similarity import find_similar

results = find_similar("node_id", graph, top_k=10, method="ast")
# Returns: List[SimilarityResult(node, score, method, matched_features)]
```

## CLI
```bash
sckg similar graph.json <node_id> --top 10 --method ast
```

## GraphQL
```graphql
query {
  similar(nodeId: "n123", top: 10, method: "ast") {
    node { name filePath }
    score
    method
    matchedFeatures
  }
}
```

## Caveats
- Relies on call edges being present (parser must extract calls)
- Control flow from signature/docstring only (no full AST walk)
- Type hints only from signature (no inference)
- Jaccard on calls is fast; AST is slower but more accurate