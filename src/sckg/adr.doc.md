# Architecture Decision Record (ADR) Generation

## Purpose
Automatically generate Architecture Decision Records from knowledge graph analysis findings.

## Dependencies
- `sckg.graph.KnowledgeGraph` - analyzed graph
- `sckg.communities` - community detection
- `sckg.dead_code` - dead code analysis
- `sckg.hotpaths` - hot paths analysis

## Generated ADR Categories
| Category | Trigger | Example |
|----------|---------|---------|
| Cross-repo calls | `subprocess`/`import` edges between repos | "Repo A calls Repo B via subprocess" |
| Mixed-language communities | Community with >1 language | "Python + Go community #3" |
| Cross-repo hot paths | Hot nodes called from other repos | "Hot function X called from Repo B" |
| Dead public API | Dead code in `__init__.py` or exported | "Unused export in public API" |
| Circular repo deps | Cycle in repo-level graph | "A -> B -> C -> A" |

## ADR Structure
```markdown
---
id: ADR-001
title: Cross-Repository Calls from repo-a
status: proposed
date: 2026-06-06
tags: ["cross-repo", "coupling", "repo-a"]
---

# ADR-001: Cross-Repository Calls from repo-a

## Status
proposed

## Context
Found 15 cross-repo edges originating from repo-a...

## Decision
repo-a calls 3 other repositories via subprocess/imports...

## Consequences
Changes in target repositories may break repo-a at runtime...

## Alternatives
Consider replacing subprocess calls with HTTP/gRPC APIs...
```

## Usage
```python
from sckg.adr import generate_adrs

adrs = generate_adrs(graph, output_dir=Path("./adrs"))
# Writes one .md file per ADR to output_dir
```

## CLI
```bash
sckg adr . --output-dir ./adrs
```

## GraphQL
```graphql
query {
  adrs {
    id title status date decision context consequences alternatives tags
  }
}
```

## Caveats
- Heuristics-based - may produce false positives
- Templates are fixed - customize by forking
- Requires cross-repo edges to be detected first
- Circular dependency detection is O(n³) in repo count