"""Integration tests for the CLI commands.

Docs: test_cli.doc.md
"""

import json
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from sckg.cli import app

runner = CliRunner()

FIXTURES = Path(__file__).with_name("fixtures") / "sample_project"
DEAD_CODE_FIXTURES = Path(__file__).with_name("fixtures") / "dead_code_sample"


def test_cli_help_shows_commands() -> None:
    """sckg --help should list index, query, graph, and dead-code commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("index", "query", "graph", "dead-code"):
        assert cmd in result.output, f"Command {cmd} missing from help"


def test_index_creates_json_graph() -> None:
    """sckg index should produce a valid JSON graph file."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
        out_path = fh.name
    result = runner.invoke(app, ["index", str(FIXTURES), "--output", out_path])
    assert result.exit_code == 0, result.output
    assert Path(out_path).exists()
    with open(out_path, "r") as fh:
        data = json.load(fh)
    assert "nodes" in data and "edges" in data
    assert len(data["nodes"]) >= 4
    assert len(data["edges"]) >= 3
    Path(out_path).unlink()


def test_query_returns_helper() -> None:
    """sckg query for 'helper' should return utils.helper."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as fh:
        graph_path = fh.name
    runner.invoke(app, ["index", str(FIXTURES), "--output", graph_path])

    result = runner.invoke(app, ["query", graph_path, "helper"])
    assert result.exit_code == 0, result.output
    assert "helper" in result.output
    Path(graph_path).unlink()


def test_graph_creates_html_with_d3js() -> None:
    """sckg graph should emit a single HTML file containing D3.js."""
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as fh:
        out_path = fh.name
    result = runner.invoke(app, ["graph", str(FIXTURES), "--output", out_path])
    assert result.exit_code == 0, result.output
    assert Path(out_path).exists()
    html = Path(out_path).read_text()
    assert "d3.v7.min.js" in html
    assert "forceSimulation" in html
    assert "forceLink" in html
    assert "forceCenter" in html
    Path(out_path).unlink()


def test_dead_code_finds_format_data() -> None:
    """sckg dead-code should flag format_data as dead and main as entry point."""
    result = runner.invoke(app, ["dead-code", str(DEAD_CODE_FIXTURES)])
    assert result.exit_code == 1, result.output  # dead code found
    data = json.loads(result.output.split("\nSummary:")[0])
    dead_names = {n["name"] for n in data["dead_nodes"]}
    entry_names = {n["name"] for n in data["entry_points"]}
    assert "format_data" in dead_names, f"Expected format_data in dead nodes, got {dead_names}"
    assert "main" in entry_names, f"Expected main in entry points, got {entry_names}"


def test_dead_code_threshold_fails() -> None:
    """sckg dead-code --threshold 0.9 should exit 1 when coverage < 90%."""
    result = runner.invoke(app, ["dead-code", str(DEAD_CODE_FIXTURES), "--threshold", "0.9"])
    assert result.exit_code == 1, result.output
    assert "coverage" in result.output.lower() or "below" in result.output.lower()


def test_dead_code_include_suspicious() -> None:
    """sckg dead-code --include-suspicious should include 1-edge nodes."""
    result = runner.invoke(app, ["dead-code", str(DEAD_CODE_FIXTURES), "--include-suspicious"])
    assert result.exit_code == 1, result.output
    data = json.loads(result.output.split("\nSummary:")[0])
    suspicious_names = {n["name"] for n in data.get("suspicious_nodes", [])}
    assert "unused" in suspicious_names, f"Expected unused in suspicious nodes, got {suspicious_names}"
