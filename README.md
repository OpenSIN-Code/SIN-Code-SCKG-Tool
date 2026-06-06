# SCKG — Semantic Codebase Knowledge Graphs

Python-native code intelligence graph. Replaces GitNexus with a lightweight, stable indexing engine built on the `ast` module.

## SOTA Status

- Tests: **96 passing** (`pytest tests/ -q`, ~1.5s)
- CI: ![ci](https://img.shields.io/badge/ci-pending-lightgrey) (placeholder — wire up GitHub Actions)
- Maturity tier: **2 / 3** (Beta — v0.6.x, multi-iteration, large test surface)
- Last commit: 2026-06-06

## Integration

This tool is exposed in the unified `sin code` hub:

```bash
sin code sckg index .           # alias of: sckg index .
sin code sckg query . "main"    # alias of: sckg query . "main"
sin code sckg dashboard         # alias of: sckg dashboard
```

See `AGENTS.md` for the full agent-engineering surface (boundaries, key files, verification steps).

## CLI

```bash
# Build graph from a repo
sckg index ./my-project --output graph.json

# Query for symbols
sckg query ./my-project "helper function"

# Generate interactive HTML graph
sckg graph ./my-project --output graph.html
```

## Install

```bash
pip install -e .
symlink sckg to ~/.local/bin/ (or use pipx)
```

## Test

```bash
pytest tests/ -q
```

## Architecture

- `parser.py` — AST visitor extracting symbols and edges
- `graph.py` — adjacency-list graph with community detection
- `html_generator.py` — D3.js force-directed single-file HTML
- `cli.py` — Typer CLI (`index`, `query`, `graph`, …)

See `AGENTS.md` for the full key-files map (14 subcommands + 96 tests).

## License

MIT
