"""Parser dispatcher — routes files to language-specific parsers.

Docs: parsers/__init__.doc.md
"""

from pathlib import Path
from typing import Any

from sckg.parsers.base import Edge, SymbolNode


def parse_file(filepath: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Route a single file to the correct language parser."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".py":
        from sckg.parsers.python_parser import parse_file as _parse_py

        return _parse_py(path)
    if suffix == ".go":
        from sckg.parsers.go_parser import parse_file as _parse_go

        return _parse_go(path)
    if suffix in (".ts", ".tsx", ".js", ".jsx"):
        from sckg.parsers.typescript_parser import parse_file as _parse_ts

        return _parse_ts(path)

    raise ValueError(f"Unsupported file type: {suffix}")


def parse_directory(repo_path: str | Path) -> tuple[list[SymbolNode], list[Edge]]:
    """Recursively parse all supported source files in a directory."""
    all_symbols: list[SymbolNode] = []
    all_edges: list[Edge] = []
    repo = Path(repo_path)

    for ext in (".py", ".go", ".ts", ".tsx", ".js", ".jsx"):
        for src_file in repo.rglob(f"*{ext}"):
            parts = src_file.relative_to(repo).parts
            if any(
                p.startswith(".") or p in ("venv", ".venv", "__pycache__", "node_modules", "vendor")
                for p in parts
            ):
                continue
            try:
                syms, edges = parse_file(src_file)
                all_symbols.extend(syms)
                all_edges.extend(edges)
            except Exception as exc:  # noqa: BLE001
                print(f"[WARN] Skipping {src_file}: {exc}")
    return all_symbols, all_edges
