# src/sckg/graph.py

In-memory adjacency-list graph of code symbols with community detection.

## What it does
- Stores nodes (`dict[str, dict]`) and edges (`list[dict]`)
- Provides JSON serialization (`save_json`, `load_json`)
- Query engine: `find_symbol()` ranks by name match, docstring match, signature match, and function boost
- Community detection: directory-based grouping + shared-import merging

## Why adjacency list
- Natural for sparse code graphs (most functions call only a few others)
- JSON serialization is human-readable and fast to load

## Community detection heuristic
1. Assign each file's directory to a unique community ID
2. If two directories share any import target, merge their communities
- This is O(n²) but fine for repos up to ~10K files (n = distinct directories)

## Files that import / touch it
- `cli.py` — `index`, `query`, `graph` commands build and save graphs
- `html_generator.py` — reads `graph.nodes`, `graph.edges`, `graph.communities` for D3 output
- `test_graph.py` — tests for building, saving, querying, and community detection

## Caveats
- `find_symbol` is not fuzzy; it uses lowercase substring matching.
- `related_symbols` does a simple DFS without cycle detection (but `seen` set prevents infinite loops).
