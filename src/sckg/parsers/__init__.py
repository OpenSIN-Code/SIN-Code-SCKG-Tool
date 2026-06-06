"""Multi-language parser dispatcher for SCKG.

Docs: parsers/__init__.doc.md
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode

logger = logging.getLogger(__name__)

PARSERS: dict[str, Any] = {}

# ── Graceful parser imports ──────────────────────────────────────────────────
# Each parser is imported with try/except so missing language parsers do not
# break the dispatcher.

try:
    from sckg.parsers.python_parser import parse_file as _parse_python_file

    PARSERS[".py"] = (_parse_python_file, None)
except ImportError as exc:
    logger.warning("Python parser not available: %s", exc)

try:
    from sckg.parsers.go_parser import parse_file as _parse_go_file

    PARSERS[".go"] = (_parse_go_file, None)
except ImportError as exc:
    logger.warning("Go parser not available: %s", exc)

try:
    from sckg.parsers.typescript_parser import parse_file as _parse_ts_file

    PARSERS[".ts"] = (_parse_ts_file, None)
    PARSERS[".tsx"] = (_parse_ts_file, None)
    PARSERS[".js"] = (_parse_ts_file, None)
    PARSERS[".jsx"] = (_parse_ts_file, None)
except ImportError as exc:
    logger.warning("TypeScript parser not available: %s", exc)


def get_parser(file_path: str | Path) -> Any | None:
    """Return the parser function for a given file path based on extension."""
    ext = Path(file_path).suffix.lower()
    entry = PARSERS.get(ext)
    return entry[0] if entry else None


def parse_file(filepath: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Parse a single source file and return symbols + edges."""
    path = Path(filepath)
    ext = path.suffix.lower()
    entry = PARSERS.get(ext)
    if entry:
        return entry[0](path)
    raise ValueError(f"Unsupported file type: {ext}")


def parse_directory(repo_path: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Recursively parse all supported source files in a directory."""
    all_symbols: list[SymbolNode] = []
    all_edges: list[Edge] = []
    repo = Path(repo_path)

    for ext, (file_fn, _) in PARSERS.items():
        for src_file in repo.rglob(f"*{ext}"):
            parts = src_file.relative_to(repo).parts
            if any(
                p.startswith(".") or p in ("venv", ".venv", "__pycache__", "node_modules", "vendor", "dist", "build", ".next")
                for p in parts
            ):
                continue
            try:
                syms, edges = file_fn(src_file)
                all_symbols.extend(syms)
                all_edges.extend(edges)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping %s: %s", src_file, exc)
    return all_symbols, all_edges
