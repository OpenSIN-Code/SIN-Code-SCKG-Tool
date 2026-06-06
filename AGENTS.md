# SIN-Code-SCKG-Tool — Agent-Engineering Hints

## What it does (1 sentence)
Semantic Codebase Knowledge Graphs — Python-native code intelligence graph that replaces GitNexus with a lightweight, stable indexing engine built on the `ast` module (Python) and tree-sitter (Go).

## Stack
- Language: Python
- Version: 0.6.1
- Test count: 96 tests
- CLI: `sckg` with 14 subcommands (`index`, `cross_repo`, `query`, `graph`, `communities`, `dead_code`, `hot-paths`, `search`, `serve`, `graphql_schema`, `watch`, `similar`, `adr`, `dashboard`)

## When to use
- Building a code-intelligence index for a Python or Go repo (prefer over GitNexus for stability).
- Need a queryable graph: symbols, edges, communities, hot-paths, dead-code, ADR refs.
- Need a self-contained interactive HTML graph (D3.js force-directed) or a FastAPI/GraphQL server for live querying.

## Boundaries
- Do NOT touch `src/sckg/*.py.bak` files — they are pre-fix snapshots kept for diffing.
- Do NOT edit `src/sckg/parser.py` without re-running the full test suite — every other module depends on its AST contract.
- Always keep `.doc.md` companions in sync with their `.py` files (CoDocs convention).
- Always preserve the Typer command surface — external scripts and `sin code sckg` depend on stable subcommand names.

## Key files
- `src/sckg/parser.py` — AST visitor extracting symbols and edges (the contract every other module relies on).
- `src/sckg/graph.py` — adjacency-list graph + community detection (Louvain).
- `src/sckg/html_generator.py` — self-contained D3.js force-directed HTML output.
- `src/sckg/cli.py` — Typer entry point (14 subcommands, dispatcher pattern).
- `src/sckg/api/` — FastAPI + Strawberry GraphQL server (`sckg serve`, `sckg graphql_schema`).
- `src/sckg/hotpaths.py`, `communities.py`, `dead_code.py`, `cross_repo.py`, `adr.py`, `dashboard.py` — analysis modules.
- `tests/test_cli.py`, `test_dispatcher.py`, `test_graph.py`, `test_hotpaths.py`, `test_hybrid_search.py`, `test_watcher.py` — core behavioral tests.

## Verification
- `pytest tests/ -v` — all 96 tests pass (~1.5s).
- `sckg --help` — prints help with 14 subcommands.
- `sckg index . --output /tmp/sckg.json && sckg query . "main"` — smoke test on this repo.
