"""Tests for watcher module."""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

from sckg.watcher import FileWatcher, DebouncedFileHandler
from sckg.graph import KnowledgeGraph


def test_debounced_handler_collects_events():
    """DebouncedFileHandler collects file events."""
    events = []

    def callback(path: Path):
        events.append(path)

    handler = DebouncedFileHandler(callback, debounce_ms=50)

    # Simulate events
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
        tmp = Path(f.name)

    # Need to run in event loop for asyncio.create_task
    async def run_test():
        handler.on_modified(type("Event", (), {"src_path": str(tmp), "is_directory": False})())
        handler.on_modified(type("Event", (), {"src_path": str(tmp), "is_directory": False})())

        # Wait for debounce
        await asyncio.sleep(0.1)
        return events

    events = asyncio.run(run_test())

    assert len(events) == 1
    assert events[0] == tmp

    tmp.unlink()


def test_file_watcher_upserts_on_change():
    """FileWatcher upserts graph when file changes."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        graph = KnowledgeGraph()

        # Create initial file
        test_file = repo / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        watcher = FileWatcher(repo, graph, debounce_ms=50)
        watcher._on_file_change(test_file)

        # Check graph was updated
        assert len(graph.nodes) > 0
        names = [n.get("name") for n in graph.nodes.values()]
        assert "hello" in names

        # Modify file
        test_file.write_text("def hello():\n    return 'world'\n\ndef goodbye():\n    return 'moon'\n")
        watcher._on_file_change(test_file)

        names = [n.get("name") for n in graph.nodes.values()]
        assert "goodbye" in names


def test_file_watcher_removes_on_delete():
    """FileWatcher removes nodes when file is deleted."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        graph = KnowledgeGraph()

        test_file = repo / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")

        watcher = FileWatcher(repo, graph, debounce_ms=50)
        watcher._on_file_change(test_file)

        assert len(graph.nodes) > 0

        # Delete file
        test_file.unlink()
        watcher._on_file_change(test_file)

        # Nodes from that file should be gone
        for node in graph.nodes.values():
            assert node.get("filepath") != str(test_file)


def test_watcher_ignores_non_matching_extensions():
    """FileWatcher ignores files with non-matching extensions."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        graph = KnowledgeGraph()

        test_file = repo / "test.txt"
        test_file.write_text("not a python file")

        watcher = FileWatcher(repo, graph, debounce_ms=50, extensions=(".py",))
        watcher._on_file_change(test_file)

        # Should not have added any nodes
        assert len(graph.nodes) == 0


def test_file_watcher_context_manager():
    """FileWatcher works as context manager."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        graph = KnowledgeGraph()

        with FileWatcher(repo, graph, debounce_ms=50) as watcher:
            assert watcher._running is True
        assert watcher._running is False