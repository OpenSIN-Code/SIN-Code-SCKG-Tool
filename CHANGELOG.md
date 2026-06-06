# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-06-06 — Cross-repo edges, dead-code detection, language-aware communities

### Added
- Cross-repo edge detection — finds `subprocess` / `os.system` calls and cross-repo imports between repositories
- `sckg cross-repo` CLI command + `sckg index --workspace` for multi-repo indexing
- Cross-repo edges visualized as purple dashed lines in D3.js graph (`#9C27B0`, `stroke-dasharray: 5,5`)
- Dead-code detection — flags nodes with 0 incoming edges (excluding entry points: `main`, `__init__`, CLI handlers, exports)
- `sckg dead-code` CLI command with `--threshold` for CI integration (exit code 1 if coverage < threshold)
- Dead / suspicious / entry-point visual markers in graph (red border, yellow border, green border)
- Language-aware community detection — clusters by language first, then by code relationships within each language
- `sckg communities` CLI command with `--by-language` (default) and `--mixed` flags
- Mixed-language communities detected (e.g., Python calling Go via subprocess) — purple background in graph
- Community bounding boxes and labels in D3.js visualization with language-colored backgrounds
- `Community` dataclass with dominant language, language breakdown, size, and density metrics
- `DeadCodeReport` dataclass with dead nodes, entry points, suspicious nodes, coverage percentage
- `find_repos_in_workspace()` utility for auto-discovering repositories in a directory
- 17 new tests (cross-repo: 7, dead-code: 5, communities: 5) — 48 total tests, 100% passing

### Changed
- `html_generator.py` now supports multiple edge styles (solid, dashed) and node border colors (red/yellow/green)
- Graph legend expanded to show edge types and node state categories
- `graph.py` extended with `detect_communities_by_language()` and `get_communities()` methods
- Community detection algorithm enhanced with language-aware clustering (primary: language, secondary: code relationships)

### Fixed
- N/A (all additions, no breaking changes)

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
