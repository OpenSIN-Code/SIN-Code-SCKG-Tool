# src/sckg/parser.py

AST-based source parser for Python files. Extracts symbols (functions, classes) and edges (calls, imports, inheritance).

## What it does
- Walks the `ast` tree of each `.py` file
- Collects `SymbolNode` (name, kind, line, docstring, signature)
- Collects `Edge` (source → target, relation type)

## Key types
- `SymbolNode` — immutable-ish data container; `_id()` is `filepath::name` (or `filepath::parent.name` for methods)
- `Edge` — typed relation: `calls`, `imports`, `inherits`

## Heuristics
- Call resolution is best-effort via `_name()` which walks `Name`, `Attribute`, `Call`, `Subscript` nodes.
- Import aliases are tracked in `_imports` but not yet used for call resolution (future: alias → fully qualified lookup).

## Why ast (not jedi)
- `jedi` is great for cross-file inference but requires source code availability and has a heavy dependency graph.
- `ast` is stdlib, zero dependency, fast enough for MVP.

## Files that import / touch it
- `cli.py` — calls `parse_directory()` for `index` and `graph` commands
- `graph.py` — consumes `SymbolNode` + `Edge` lists to build the knowledge graph
- `test_parser.py` — unit tests for AST extraction

## Caveats
- `SyntaxError` files are silently skipped with a warning.
- Does not resolve cross-file call targets (e.g., `from utils import helper` → `helper()` is recorded as `calls: helper`, not `calls: utils.helper`).
