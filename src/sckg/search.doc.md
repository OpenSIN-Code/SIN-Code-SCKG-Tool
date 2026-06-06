# N-gram Semantic Code Search

## Purpose
Fuzzy/semantic search over code symbols using n-grams extracted from AST features. Enables queries like "parse json", "handle error", "auth related" without exact name matches.

## Dependencies
- `sckg.graph.KnowledgeGraph` - input graph
- Pure Python - no external ML dependencies

## N-gram Extraction
Tokens extracted from:
1. **Function/class names** (weight 3.0) - split camelCase/snake_case
2. **Docstrings** (weight 1.5) - tokenized, stopwords removed
3. **Parameter names** (weight 1.0) - from signature
4. **Called function names** (weight 1.0) - from outgoing "calls" edges

N-gram sizes: unigrams (1), bigrams (2), trigrams (3)

## BM25 Scoring
Uses BM25 (Okapi) ranking:
- TF: n-gram weight in document
- IDF: log((N - df + 0.5) / (df + 0.5) + 1)
- Parameters: k1=1.5, b=0.75

## Public API
- `build_ngram_index(graph, ngram_sizes)` - builds inverted index
- `search(query, graph, index, top_k)` - BM25 search
- `search_pattern(pattern, graph, top_k)` - wildcard pattern search (fnmatch)
- `split_identifier(name)` - camelCase/snake_case tokenizer
- `tokenize(text)` - natural language tokenizer

## Usage
```python
from sckg.search import build_ngram_index, search

index = build_ngram_index(graph)
results = search("parse json", graph, index, top_k=10)
# Results: SearchResult(node, score, matched_ngrams, snippet)
```

## Pattern Search
```python
from sckg.search import search_pattern
results = search_pattern("handle_*", graph)  # finds handle_error, handle_request
```

## Visualization
Search panel in generated HTML:
- Input field at top center
- Real-time results as you type
- Click result → centers node, shows info panel
- Results scored by token matches in name/docstring/filepath

## Caveats
- Index rebuilds on each search call (could be cached)
- Stopwords list is minimal - may need expansion
- No stemming/lemmatization - "parsing" ≠ "parse"
- BM25 parameters tuned for code, not natural language