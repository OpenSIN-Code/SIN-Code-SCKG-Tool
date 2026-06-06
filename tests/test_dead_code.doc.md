# tests/test_dead_code.py

Unit tests for the dead-code detection module.

## What it tests
1. `test_find_dead_function` — 0-edge non-entry-point is flagged dead.
2. `test_main_not_dead` — `main()` is always an entry point.
3. `test_class_method_not_dead` — `__init__` is treated as an entry point.
4. `test_suspicious_one_reference` — exactly one incoming edge → suspicious.
5. `test_coverage_calculation` — 4 nodes, 1 dead, 1 entry point, 2 normal → 75%.

## Fixtures used
- Synthetic graphs built with `SymbolNode` + `Edge` (no filesystem I/O).
- `tests/fixtures/dead_code_sample/` is used for CLI integration tests in `test_cli.py`.
