# tests/test_communities.py

Tests for language-aware community detection.

## What it tests
- `detect_language_communities` splits graphs by language and clusters within each language
- `detect_mixed_communities` detects communities across all languages and marks mixed ones
- `resolve_cross_language_edges` resolves `subprocess` edges into `cross-language` edges
- `Community` dataclass density calculation for complete directed graphs

## Test scenarios
- `test_python_community_isolated`: Python-only graph → 1 Python community
- `test_go_community_isolated`: Go-only graph → 1 Go community
- `test_mixed_repo_detects_multiple_communities`: Mixed repo fixture (Python + Go + TS) → ≥3 communities
- `test_mixed_community_detected`: Manual cross-language edge → mixed community detected
- `test_community_density_calculation`: Complete directed graph (3 nodes, 6 edges) → density = 1.0

## Fixtures
- `tests/fixtures/mixed_repo/` — Python (`python_app.py`), Go (`go_binary.go`), TypeScript (`ts_component.tsx`)
- Python app calls `subprocess.run(["go_binary", ...])` which resolves to a cross-language edge

## Dependencies
- `sckg.graph.Community`, `KnowledgeGraph`
- `sckg.communities` (detect + resolve functions)
- `sckg.parser.parse_directory`
