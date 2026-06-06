# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-06-06 — Multi-language support: Go + TypeScript

### Added
- Go parser (tree-sitter-go) — indexes functions, structs, methods, imports, calls
- TypeScript/TSX parser (tree-sitter-typescript) — indexes functions, classes, imports, JSX components
- Multi-language dispatcher (`parsers/` package) — auto-detects language from file extension
- Language-color coding in graph visualization — Python (blue), Go (cyan), TypeScript (orange)
- Graph legend showing language → color mapping
- Language filtering in query results (optional)

### Changed
- `parser.py` refactored to dispatcher pattern (`parsers/` package)
- Graph nodes now include `language` field
- HTML output uses D3.js color coding per language

### Fixed
- Go repos now show real AST nodes instead of 0 nodes
- TypeScript/Next.js repos now indexable

## [0.1.0] - 2026-06-06 — MVP Python-only SCKG

### Added
- Python AST parser (stdlib `ast`) — indexes functions, classes, imports, calls
- Knowledge graph data structure with community detection
- Interactive D3.js force-directed graph HTML generation
- Typer CLI: `index`, `query`, `graph` commands
- JSON serialization for graph persistence
