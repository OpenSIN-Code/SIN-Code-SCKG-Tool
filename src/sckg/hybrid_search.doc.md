# Hybrid Code Search (N-gram + Similarity)

## Purpose
Combines BM25 n-gram text search with AST structural similarity for better code discovery. Finds functions that are both textually relevant AND structurally similar to the top text match.

## Dependencies
- `sckg.search` - n-gram BM25 search
- `sckg.similarity` - AST structural similarity
- `sckg.graph.KnowledgeGraph` - graph

## Algorithm
1. Run BM25 n-gram search → top N results
2. Take top n-gram result as "anchor" node
3. Find structurally similar nodes to anchor
4. Normalize both score sets to [0, 1] via min-max
5. Combined: `score = alpha * ngram + (1-alpha) * similarity`
6. Sort by combined score, return top K

## Alpha Parameter
| Value | Behavior |
|-------|----------|
| `1.0` | Pure n-gram (BM25 only) |
| `0.7` | Mostly text, some structure |
| `0.5` | Balanced (default) |
| `0.3` | Mostly structure, some text |
| `0.0` | Pure structural similarity |

## Usage
```python
from sckg.hybrid_search import hybrid_search

results = hybrid_search("parse json", graph, top_k=10, alpha=0.5)
# Returns: List[HybridResult(node, score, ngram_score, similarity_score, matched_ngrams, matched_features)]
```

## CLI
```bash
sckg search --hybrid --alpha 0.5 "parse json"
```

## GraphQL
```graphql
query {
  searchHybrid(query: "parse json", top: 10, alpha: 0.5) {
    node { name filePath }
    score
    ngramScore
    similarityScore
    matchedNgrams
    matchedFeatures
  }
}
```

## Performance
- Two passes: one BM25 + one structural similarity
- Both O(n) where n = number of nodes
- N-gram index cached between calls
- Total: ~2x slower than pure n-gram search

## Caveats
- Falls back to n-gram only if no similar nodes found
- `alpha=0.0` is effectively `find_similar` on top n-gram result
- `alpha=1.0` is effectively `ngram_search`
- Min-max normalization assumes non-zero variance