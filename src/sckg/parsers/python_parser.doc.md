# src/sckg/parsers/python_parser.py

AST-based Python parser extracted from the original `parser.py`.

## What it does
- Uses `ast` (stdlib) to walk Python source files
- Extracts `SymbolNode` (functions, classes, methods) and `Edge` (imports, calls, inheritance)
- Detects cross-language `subprocess` calls (e.g. `subprocess.run(["go_binary", ...])`) and emits `subprocess` edges for downstream resolution
- Same behaviour as the original monolithic `parser.py`

## Why extracted
- Monolithic `parser.py` only supported Python.
- Splitting into `parsers/python_parser.py` allows a clean dispatcher (`parsers/__init__.py`) and room for Go / other languages.

## Files that import / touch it
- `parsers/__init__.py` — dispatched for `.py` files

## Caveats
- See `parser.doc.md` — same limitations (best-effort call resolution, no cross-file alias resolution).
