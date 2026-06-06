# communities.py

Language-aware community detection for SCKG knowledge graphs.

## What it does

Splits a knowledge graph by programming language (Python, Go, TypeScript, …)
and runs community detection *inside* each language subgraph.  Also supports
mixed-language detection (e.g. Python calling Go via `subprocess`).

## Key exports

| Symbol | Purpose |
|---|---|
| `detect_language_communities` | Language-first community detection |
| `detect_mixed_communities` | Cross-language community detection |
| `resolve_cross_language_edges` | Post-process `subprocess` edges into `cross-language` edges |

## Dependencies

- `sckg.graph.KnowledgeGraph` & `Community`
- `sckg.parsers.base.Edge`, `SymbolNode`

## Language-first algorithm

1. Partition nodes by `language` attribute.
2. For each language build a subgraph with internal edges only.
3. Run the existing directory-heuristic community detector on that subgraph.
4. Convert the raw community mapping into `Community` dataclass instances.

## Mixed detection

1. Run the generic detector on the *full* graph (all languages).
2. Compute the dominant language of each community.
3. If a community contains more than one language → mark as `dominant_language="mixed"`.

## Cross-language edge resolution

After parsing, a Python `subprocess.run(["go_binary", ...])` call creates a
`subprocess` edge whose target is the binary stem (`go_binary`).
`resolve_cross_language_edges` looks up matching Go / TypeScript nodes by file
stem and rewrites the edge to `cross-language` with the real node ID as target.

## Caveats

- The generic detector uses directory-based grouping, so all files in the same
directory may end up in the same community when mixed mode is used.
- Density is calculated for *directed* graphs: `E / (N * (N-1))`.
