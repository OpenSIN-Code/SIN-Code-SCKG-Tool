# SIN-Code-SCKG-Tool — Semantic Codebase Knowledge Graphs — Python-native code-intelligence indexer (AST, tree-sitter) for Python and Go codebases.

<!--
  Docs: this file follows the SIN-Code AGENTS.md standard
  (see OpenSIN-Code/SIN-Code AGENTS.md section "Ecosystem map" and
  issue #40). sin-brain discovers rules via the section headers below;
  sin-context-bridge queries this file via the "## Architecture" anchor.
  Generated: 2026-06-13; standard version: v1 (chore/issue-40).
-->

## Architecture

Indexes a Python/Go repository into a queryable knowledge graph (symbols, edges, communities, hot-paths, dead-code, ADR refs). Uses the `ast` module for Python, tree-sitter for Go. Emits a self-contained D3.js force-directed HTML graph, exposes a FastAPI/Strawberry GraphQL server (`sckg serve`), and feeds the `sin code sckg` HubTool. Main entry point: `src/sckg/cli.py` (Typer dispatcher, 14 subcommands).

## Services

| Service | Port | Purpose |
| ------- | ---- | ------- |
| CLI     | N/A  | `sckg <subcommand>` — index, query, graph, serve, etc. |
| FastAPI/GraphQL | 8475 (default, `--port`) | `sckg serve` — live query endpoint |

## Quick-Start

```bash
pip install -e .
sckg --help
sckg index . --output /tmp/sckg.json
```

## Key Endpoints / Commands

- `sckg index` — build the knowledge graph from a repo
- `sckg cross_repo` — cross-repo dependency analysis
- `sckg query` — query the graph by pattern
- `sckg graph` — emit adjacency-list graph output
- `sckg communities` — Louvain community detection
- `sckg dead_code` — detect dead/unused code
- `sckg hot-paths` — identify hot execution paths
- `sckg search` — code search (BM25 or hybrid)
- `sckg serve` — start FastAPI/GraphQL server
- `sckg graphql_schema` — print the GraphQL schema
- `sckg watch` — file-watcher with live re-index
- `sckg similar` — find similar code regions
- `sckg adr` — extract ADR references
- `sckg dashboard` — multi-repo HTML dashboard

## CoDocs

- All Python source files in `src/sckg/` MUST have a `.doc.md` companion.
- Run `sin codocs check` to validate. Output MUST be `OK: 24 files` to pass.
- CoDocs companion for THIS file: none (AGENTS.md is itself a doc).

## Testing

```bash
pytest tests/ -v
pytest tests/test_agents_md.py -v
```

Expected: 97 tests pass (96 existing + 1 from issue #40).

## Integration

- **sin-code HubTool:** `sin code sckg <action>` (e.g. `sin code sckg index .`).
- **MCP server:** `sckg` exposes MCP via the `sin-code serve` adapter; the
  tool prefix in MCP namespace is `sckg__*` (e.g. `sckg__index`).
- **Cross-repo:** called by `sin code full` pipeline as stage 4 (after preflight → codocs → debt → sckg → map → grasp → harvest → orchestrate).

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **SIN-Code-SCKG-Tool** (1695 symbols, 3061 relationships, 146 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/SIN-Code-SCKG-Tool/context` | Codebase overview, check index freshness |
| `gitnexus://repo/SIN-Code-SCKG-Tool/clusters` | All functional areas |
| `gitnexus://repo/SIN-Code-SCKG-Tool/processes` | All execution flows |
| `gitnexus://repo/SIN-Code-SCKG-Tool/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
