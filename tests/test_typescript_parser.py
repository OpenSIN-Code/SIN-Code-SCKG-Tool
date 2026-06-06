"""Tests for the TypeScript/TSX parser.

Docs: test_typescript_parser.doc.md
"""

from pathlib import Path

from sckg.parsers.typescript_parser import parse_file

FIXTURES = Path(__file__).with_name("fixtures") / "ts_sample"


def test_extract_functions() -> None:
    """Parser should extract function declarations and arrow functions."""
    syms, _ = parse_file(FIXTURES / "page.tsx")
    funcs = [s for s in syms if s.kind == "function"]
    names = {f.name for f in funcs}
    assert "HomePage" in names, f"Expected HomePage in {names}"
    assert "render" in names, f"Expected render in {names}"


def test_extract_imports() -> None:
    """Parser should record import edges."""
    _, edges = parse_file(FIXTURES / "page.tsx")
    imports = [e for e in edges if e.relation == "imports"]
    targets = {e.target for e in imports}
    assert "react" in targets, f"Expected react in import targets: {targets}"
    assert any("useState" in t for t in targets), f"Expected useState import: {targets}"


def test_extract_jsx_components() -> None:
    """Parser should detect JSX component usage as call edges."""
    _, edges = parse_file(FIXTURES / "page.tsx")
    calls = [e for e in edges if e.relation == "calls"]
    targets = {e.target for e in calls}
    assert "Component" in targets, f"Expected Component in call targets: {targets}"
    assert "Button" in targets, f"Expected Button in call targets: {targets}"


def test_extract_hooks() -> None:
    """Parser should detect hook calls like useState()."""
    _, edges = parse_file(FIXTURES / "page.tsx")
    calls = [e for e in edges if e.relation == "calls"]
    targets = {e.target for e in calls}
    assert "useState" in targets, f"Expected useState in call targets: {targets}"
    assert "useEffect" in targets, f"Expected useEffect in call targets: {targets}"


def test_extract_exports() -> None:
    """Parser should record export edges."""
    _, edges = parse_file(FIXTURES / "page.tsx")
    exports = [e for e in edges if e.relation == "exports"]
    targets = {e.target for e in exports}
    assert "HomePage" in targets or "default" in targets, f"Expected export targets: {targets}"
