"""Unit tests for dead-code detection.

Docs: test_dead_code.doc.md
"""

from sckg.dead_code import DeadCodeReport, find_dead_code
from sckg.graph import KnowledgeGraph
from sckg.parser import Edge, SymbolNode


def _make_graph(nodes: list[SymbolNode], edges: list[Edge]) -> KnowledgeGraph:
    g = KnowledgeGraph()
    g.build_from_parser(nodes, edges)
    return g


def test_find_dead_function() -> None:
    """A function with zero incoming edges should be flagged as dead."""
    nodes = [
        SymbolNode(name="main", kind="function", filepath="/a.py"),
        SymbolNode(name="dead_func", kind="function", filepath="/a.py"),
    ]
    edges = []  # dead_func has 0 incoming edges
    g = _make_graph(nodes, edges)
    report = find_dead_code(g)

    assert len(report.dead_nodes) == 1
    assert report.dead_nodes[0]["name"] == "dead_func"


def test_main_not_dead() -> None:
    """A function named `main` should be treated as an entry point, not dead."""
    nodes = [
        SymbolNode(name="main", kind="function", filepath="/a.py"),
    ]
    g = _make_graph(nodes, [])
    report = find_dead_code(g)

    assert len(report.dead_nodes) == 0
    assert len(report.entry_points) == 1
    assert report.entry_points[0]["name"] == "main"


def test_class_method_not_dead() -> None:
    """`__init__` methods should be treated as entry points (constructors)."""
    nodes = [
        SymbolNode(name="Foo", kind="class", filepath="/a.py"),
        SymbolNode(name="__init__", kind="function", filepath="/a.py", parent="Foo"),
    ]
    g = _make_graph(nodes, [])
    report = find_dead_code(g)

    # Foo is a class with 0 incoming edges, so it is flagged dead (expected).
    # __init__ is an entry point and must NOT be in dead_nodes.
    assert any(n["name"] == "__init__" for n in report.entry_points)
    assert not any(n["name"] == "__init__" for n in report.dead_nodes)


def test_suspicious_one_reference() -> None:
    """A function with exactly one incoming edge should be flagged suspicious."""
    nodes = [
        SymbolNode(name="main", kind="function", filepath="/a.py"),
        SymbolNode(name="lonely", kind="function", filepath="/a.py"),
    ]
    edges = [Edge("/a.py::main", "lonely", "calls")]
    g = _make_graph(nodes, edges)
    report = find_dead_code(g)

    assert len(report.suspicious_nodes) == 1
    assert report.suspicious_nodes[0]["name"] == "lonely"
    assert len(report.dead_nodes) == 0  # main is entry point


def test_coverage_calculation() -> None:
    """4 nodes: 1 dead, 1 entry point, 2 normal → coverage = 75%."""
    nodes = [
        SymbolNode(name="main", kind="function", filepath="/a.py"),
        SymbolNode(name="dead_func", kind="function", filepath="/a.py"),
        SymbolNode(name="used_a", kind="function", filepath="/a.py"),
        SymbolNode(name="used_b", kind="function", filepath="/a.py"),
    ]
    edges = [
        Edge("/a.py::main", "used_a", "calls"),
        Edge("/a.py::dead_func", "used_a", "calls"),   # used_a now has 2 incoming edges
        Edge("/a.py::used_a", "used_b", "calls"),
        Edge("/a.py::main", "used_b", "calls"),       # used_b now has 2 incoming edges
    ]
    g = _make_graph(nodes, edges)
    report = find_dead_code(g)

    assert len(report.dead_nodes) == 1
    assert report.dead_nodes[0]["name"] == "dead_func"
    assert len(report.entry_points) == 1
    assert report.entry_points[0]["name"] == "main"
    assert len(report.suspicious_nodes) == 0
    assert report.coverage_pct == 0.75
