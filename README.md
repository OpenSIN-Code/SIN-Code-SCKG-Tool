# SCKG — Semantic Codebase Knowledge Graphs

Python-native code intelligence graph. Replaces GitNexus with a lightweight, stable indexing engine built on the `ast` module.

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
- `cli.py` — Typer CLI (`index`, `query`, `graph`)

## License

MIT
