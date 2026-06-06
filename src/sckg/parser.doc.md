# src/sckg/parser.py

Shared data structures and re-export of the parser dispatcher.

## What it does
- Defines `SymbolNode` and `Edge` dataclasses (language-agnostic)
- Re-exports `parse_file` and `parse_directory` from `parsers/__init__.py`

## Architecture change
- Originally this file contained the monolithic Python parser (`ast` visitor).
- As of Go support, the Python logic moved to `parsers/python_parser.py` and
  this file only keeps the shared data layer + re-exports.

## Files that import / touch it
- `cli.py` — calls `parse_directory()` for `index` and `graph` commands
- `graph.py` — consumes `SymbolNode` + `Edge` lists
- `parsers/__init__.py` — imports `SymbolNode` and `Edge` from here
- `parsers/python_parser.py` — imports `SymbolNode` and `Edge` from here
- `parsers/go_parser.py` — imports `SymbolNode` and `Edge` from here

## Note
- `parse_file` and `parse_directory` are imported from `parsers/__init__.py` to
  keep backward compatibility for existing callers (`cli.py`, `graph.py`, tests).
