# src/sckg/cli.py

Typer CLI entry point for `sckg`.

## Commands
- `index <repo> [--output graph.json]` — parses repo and writes JSON graph
- `query <repo_or_json> "text"` — searches indexed graph for matching symbols
- `graph <repo_or_json> [--output graph.html] [--mixed]` — emits D3.js HTML with community clustering
- `communities <repo> [--by-language] [--mixed]` — detects language-aware communities and emits JSON report
- `dead-code <repo> [--threshold] [--include-suspicious] [--output]` — analyzes dead code

## Why Typer
- Automatic `--help` generation
- Type-safe option parsing
- Easy test integration via `CliRunner`

## Files that import / touch it
- `parser.py` — `parse_directory()` for indexing
- `graph.py` — `KnowledgeGraph` for storage, querying, and community detection
- `html_generator.py` — `generate_html()` for output
- `communities.py` — `resolve_cross_language_edges()` and `detect_*_communities()`
- `test_cli.py` — integration tests for all commands
