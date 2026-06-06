# tests/fixtures/dead_code_sample/main.py

Dead-code sample fixture — main entry point.

## What it does
- Defines `main()` (entry point) that calls `helper()` and `parse_json()`.
- Defines `helper()` which calls `unused()`.
- Defines `unused()` (1 incoming edge → suspicious in dead-code analysis).
