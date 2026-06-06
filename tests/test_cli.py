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


def test_cli_help_shows_three_commands() -> None:
    """sckg --help should list index, query, and graph commands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("index", "query", "graph"):
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
