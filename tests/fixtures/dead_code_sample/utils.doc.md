# tests/fixtures/dead_code_sample/utils.py

Dead-code sample fixture — utility module.

## What it does
- Defines `format_data()` — never called → dead code.
- Defines `parse_json()` — called by `main.py::main` → normal/suspicious.
