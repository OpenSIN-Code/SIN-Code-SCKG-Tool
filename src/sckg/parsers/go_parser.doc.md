# src/sckg/parsers/go_parser.py

Tree-sitter Go parser for SCKG.

## What it does
- Parses `.go` files using `tree-sitter-go` via the `tree-sitter` Python bindings
- Extracts symbols: `function`, `method`, `struct`, `interface`, `type`
- Extracts edges: `imports`, `calls`, `inherits` (embedded structs)

## Key types
- `GoSymbolExtractor` — walks the tree-sitter AST, similar to Python's `SymbolExtractor`
- Returns same `SymbolNode` + `Edge` dataclasses as the Python parser

## Go-specific quirks
- Methods are detected by `method_declaration` node (receiver parameter list before name)
- Receiver type is extracted from the first `parameter_list` → `pointer_type` / `type_identifier`
- Call names are flattened: `fmt.Println` stays as `fmt.Println`, local calls stay bare
- Import aliases are tracked but not yet used for call resolution (future: `alias.Func` → `path.Func`)

## Files that import / touch it
- `parsers/__init__.py` — dispatched for `.go` files

## Caveats
- Requires `tree-sitter` and `tree-sitter-go` packages (not stdlib).
- Embedded struct fields are treated as `inherits` edges (Go's composition model).
- Call resolution is best-effort; method calls on variables are not type-inferred.
