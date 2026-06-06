# src/sckg/cli.py

Typer CLI entry point for `sckg`.

## Commands
- `index <repo> [--output graph.json]` — parses repo and writes JSON graph
- `query <repo_or_json> "text"` — searches indexed graph for matching symbols
- `graph <repo_or_json> [--output graph.html]` — emits D3.js HTML

## Why Typer
- Automatic `--help` generation
- Type-safe option parsing
- Easy test integration via `CliRunner`

## Files that import / touch it
- `parser.py` — `parse_directory()` for indexing
- `graph.py` — `KnowledgeGraph` for storage, querying, and community detection
- `html_generator.py` — `generate_html()` for output
- `test_cli.py` — integration tests for all three commands
