# File Watcher for Incremental Indexing

## Purpose
Watch source files for changes and update the knowledge graph incrementally, enabling live-reloading GraphQL API.

## Dependencies
- `watchdog>=3.0.0` - file system events
- `sckg.graph.KnowledgeGraph` - graph with incremental updates
- `sckg.parser.parse_file` - single-file parsing

## Components
| Component | Description |
|-----------|-------------|
| `DebouncedFileHandler` | Watchdog handler with 500ms debounce |
| `FileWatcher` | Main watcher class, manages observer |
| `watch_and_serve()` | Convenience function: watch + GraphQL server |

## Usage
```python
from sckg.watcher import FileWatcher, watch_and_serve
from sckg.graph import KnowledgeGraph
from pathlib import Path

graph = KnowledgeGraph()
watcher = FileWatcher(Path("."), graph, on_update=lambda g: g.save_json("graph.json"))
watcher.start()
# ... later ...
watcher.stop()
```

Or combined with server:
```bash
sckg watch . --graph-path graph.json --port 8080
```

## Incremental Update Flow
1. File change detected (create/modify/delete)
2. Debounce: wait 500ms for burst of changes
3. Re-parse changed file only (`parse_file`)
4. `graph.upsert_file()` or `graph.remove_nodes_by_file()`
5. Save updated graph to JSON
6. GraphQL server sees new data on next query

## Supported Extensions
`.py`, `.go`, `.ts`, `.tsx`, `.js`, `.jsx`

## Caveats
- Debounce may delay updates by 500ms
- No atomic transactions - partial updates possible
- GraphQL subscriptions notify subscribers of changes
- Large repos: initial index still required