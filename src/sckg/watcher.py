"""File watcher for incremental indexing of SCKG knowledge graphs.

Watches source files for changes and updates the graph incrementally.

Docs: watcher.doc.md
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from sckg.graph import KnowledgeGraph
from sckg.parser import parse_file
from sckg.parsers.base import SymbolNode, Edge
from sckg.api.resolvers import publish_graph_updated, publish_node_changed


class DebouncedFileHandler(FileSystemEventHandler):
    """File system event handler with debouncing."""

    def __init__(
        self,
        callback: Callable[[Path], None],
        extensions: tuple[str, ...] = (".py", ".go", ".ts", ".tsx", ".js", ".jsx"),
        debounce_ms: int = 500,
    ):
        self.callback = callback
        self.extensions = extensions
        self.debounce_ms = debounce_ms
        self._pending: dict[Path, float] = {}
        self._task: Optional[asyncio.Task] = None

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix in self.extensions:
            self._pending[path] = time.time()
            self._schedule_debounce()

    def on_created(self, event):
        self.on_modified(event)

    def on_deleted(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix in self.extensions:
            self._pending[path] = time.time()
            self._schedule_debounce()

    def _schedule_debounce(self):
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = asyncio.create_task(self._debounce())

    async def _debounce(self):
        await asyncio.sleep(self.debounce_ms / 1000)
        now = time.time()
        to_process = [
            path for path, timestamp in self._pending.items()
            if now - timestamp >= self.debounce_ms / 1000
        ]
        for path in to_process:
            del self._pending[path]
            if path.exists():
                self.callback(path)


class FileWatcher:
    """Watches a repository for file changes and updates the knowledge graph incrementally."""

    def __init__(
        self,
        repo_path: Path,
        graph: KnowledgeGraph,
        on_update: Optional[Callable[[KnowledgeGraph], None]] = None,
        extensions: tuple[str, ...] = (".py", ".go", ".ts", ".tsx", ".js", ".jsx"),
        debounce_ms: int = 500,
    ):
        self.repo_path = repo_path.resolve()
        self.graph = graph
        self.on_update = on_update
        self.extensions = extensions
        self.debounce_ms = debounce_ms
        self._observer: Optional[Observer] = None
        self._handler: Optional[DebouncedFileHandler] = None
        self._running = False

    def _on_file_change(self, file_path: Path) -> None:
        """Handle a file change by re-parsing and updating the graph."""
        try:
            repo_name = self.repo_path.name
            if file_path.exists():
                # Re-parse the file
                symbols, edges = parse_file(file_path)
                # Update graph
                self.graph.upsert_file(str(file_path), symbols, edges)
                # Publish GraphQL subscription events
                for sym in symbols:
                    publish_node_changed(repo_name, sym._id(), "updated")
                publish_graph_updated(f"File updated: {file_path}")
            else:
                # File deleted - remove from graph
                self.graph.remove_nodes_by_file(str(file_path))
                publish_graph_updated(f"File deleted: {file_path}")
                publish_node_changed(repo_name, str(file_path), "deleted")

            # Trigger callback
            if self.on_update:
                self.on_update(self.graph)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def start(self) -> None:
        """Start watching the repository."""
        if self._running:
            return

        self._handler = DebouncedFileHandler(
            callback=self._on_file_change,
            extensions=self.extensions,
            debounce_ms=self.debounce_ms,
        )
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.repo_path), recursive=True)
        self._observer.start()
        self._running = True
        print(f"Watching {self.repo_path} for changes...")

    def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
        self._running = False
        print("File watcher stopped.")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


async def watch_and_serve(
    repo_path: Path,
    graph_path: Path,
    host: str = "0.0.0.0",
    port: int = 8080,
) -> None:
    """Watch a repo and serve GraphQL API with live updates."""
    import uvicorn
    from sckg.api.server import create_app

    # Load or create graph
    graph = KnowledgeGraph()
    if graph_path.exists():
        graph.load_json(graph_path)
    else:
        print(f"Graph not found at {graph_path}, indexing {repo_path}...")
        from sckg.parser import parse_directory
        symbols, edges = parse_directory(repo_path)
        graph.build_from_parser(symbols, edges)
        graph.save_json(graph_path)

    # Create app with graph
    app = create_app(graph_path)

    # Watcher callback saves graph
    def on_update(g: KnowledgeGraph):
        g.save_json(graph_path)
        print(f"Graph updated and saved to {graph_path}")

    watcher = FileWatcher(repo_path, graph, on_update=on_update)

    try:
        watcher.start()
        # Run server
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()
    finally:
        watcher.stop()