# src/sckg/cli.py

Typer CLI entry point for `sckg`.

## Commands
- `index <repo> [--output graph.json]` — parses repo and writes JSON graph
- `index --workspace <dir> [--output graph.json]` — indexes all repos in a workspace directory, auto-detects cross-repo edges (subprocess calls and imports)
- `cross-repo <repo1> <repo2> ... [--output graph.json] [--packages '{...}']` — explicit cross-repo analysis across multiple repositories
- `query <repo_or_json> "text"` — searches indexed graph for matching symbols
- `graph <repo_or_json> [--output graph.html]` — emits D3.js HTML
- `communities <repo> [--by-language|--mixed]` — language-aware community detection
- `dead-code <repo> [--threshold 0.8] [--output report.json]` — dead-code analysis

## Why Typer
- Automatic `--help` generation
- Type-safe option parsing
- Easy test integration via `CliRunner`

## Files that import / touch it
- `parser.py` — `parse_directory()` for indexing
- `cross_repo.py` — `build_cross_repo_graph()` and `find_repos_in_workspace()` for workspace indexing and cross-repo detection
- `graph.py` — `KnowledgeGraph` for storage, querying, and community detection
- `html_generator.py` — `generate_html()` for output
- `test_cli.py` — integration tests for all commands
