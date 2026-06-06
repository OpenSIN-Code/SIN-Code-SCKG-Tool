# typescript_parser.doc.md

TypeScript / TSX / JavaScript / JSX parser for SCKG.

## What it does

Extracts symbols and edges from TS/TSX/JS/JSX files using tree-sitter (preferred) or a regex fallback.

## Symbols extracted

- `function` — function declarations, arrow functions, async functions
- `class` — class declarations
- `interface` — interface declarations
- `variable` — const/let/var declarations (non-arrow)

## Edges extracted

- `imports` — import statements
- `exports` — export statements (default and named)
- `calls` — call expressions (function calls, hooks, JSX components)
- `inherits` — class extends clauses

## Dependencies

- `tree-sitter` and `tree-sitter-typescript` (optional, falls back to regex)
- `sckg.parser.SymbolNode`, `sckg.parser.Edge`

## Known caveats

- JSDoc docstrings are not extracted (tree-sitter grammar limitation)
- Generic type parameters are omitted from signatures
- Nested arrow functions inside JSX attributes are not captured as separate symbols
