# SCKG Skill

## Purpose

Semantic Codebase Knowledge Graphs for local code indexing and query.

## Usage

```bash
# Index a repository
sckg index <repo_path> [--output graph.json]

# Query symbols
sckg query <repo_path> "natural language query"

# Generate interactive graph
sckg graph <repo_path> [--output graph.html]
```

## Capabilities

- Python-native AST parsing (no Node.js dependency)
- Extracts functions, classes, imports, and call relationships
- Community detection via directory clustering + shared import merging
- D3.js force-directed HTML output (single file, no build step)

## Integration

Use `sckg index` before analysis, then `sckg query` to find relevant symbols for any downstream task.

## CoDocs

All modules have `.doc.md` companions and inline `#` comments per the SIN-Code standard.
