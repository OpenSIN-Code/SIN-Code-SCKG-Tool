# src/sckg/parsers/__init__.py

Parser dispatcher that routes `.py` → `python_parser` and `.go` → `go_parser`.

## What it does
- `parse_file(path)` — selects parser by file extension
- `parse_directory(path)` — recursively finds `.py` and `.go`, skips hidden / vendored dirs

## Supported extensions
| Extension | Parser | Backend |
|-----------|--------|---------|
| `.py` | `python_parser` | `ast` (stdlib) |
| `.go` | `go_parser` | `tree-sitter-go` |

## Files that import / touch it
- `parser.py` — re-exports `parse_file` and `parse_directory`
- `cli.py` — calls `parse_directory()` for indexing

## Caveats
- Unknown extensions raise `ValueError`.
- Files with syntax errors or parser failures are skipped with a warning.
