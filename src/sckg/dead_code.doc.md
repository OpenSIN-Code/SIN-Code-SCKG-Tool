# src/sckg/dead_code.py

Dead-code analysis for SCKG knowledge graphs.

## What it does
- `find_dead_code(graph)` scans all nodes and counts incoming edges.
- Nodes with **0 incoming edges** that are not entry points are flagged as **dead code**.
- Nodes with **1 incoming edge** are flagged as **suspicious** (low usage, review candidates).
- Entry points (`main`, `__init__`, explicit list) are excluded from the dead set.
- Computes a **coverage percentage** (non-dead / total nodes).

## Why incoming edge counting
- The parser stores call targets as bare names (e.g. `helper`) rather than fully qualified ids (`utils.py::helper`).
- `_count_incoming_edges` compensates by matching on both full `id` and bare `name`.

## Files that import / touch it
- `cli.py` — `dead-code` command invokes `find_dead_code()` and prints the report.
- `html_generator.py` — uses report fields (`dead_nodes`, `suspicious_nodes`, `entry_points`) to style the D3 graph.
- `test_dead_code.py` — unit tests for heuristics, coverage calculation, and edge counting.

## Caveats
- Entry-point heuristics are conservative (name-based only). CLI decorators are not captured by the current parser.
- Import edges are counted as incoming edges, which can inflate the count for heavily imported utilities.
