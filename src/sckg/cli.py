"""Typer CLI for SCKG (Semantic Codebase Knowledge Graphs).

Docs: cli.doc.md
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from sckg.graph import KnowledgeGraph
from sckg.html_generator import generate_html
from sckg.parsers import parse_directory

app = typer.Typer(help="SCKG — Semantic Codebase Knowledge Graphs")

DEFAULT_OUTPUT = "sckg_graph.json"


@app.command()
def index(
    repo_path: str = typer.Argument(..., help="Path to the repository to index"),
    output: str = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Path for the JSON graph output"),
) -> None:
    """Build a knowledge graph from source code and save to JSON."""
    repo = Path(repo_path).resolve()
    if not repo.exists():
        typer.echo(f"Error: path not found: {repo}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Indexing {repo} ...")
    symbols, edges = parse_directory(repo)
    graph = KnowledgeGraph()
    graph.build_from_parser(symbols, edges)
    graph.detect_communities()
    graph.save_json(output)

    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    comm_count = len(set(graph._communities_dict().values())) if graph._communities_dict() else 0
    typer.echo(f"Done. Nodes: {node_count}, Edges: {edge_count}, Communities: {comm_count}")
    typer.echo(f"Graph saved to {output}")


@app.command()
def query(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    q: str = typer.Argument(..., help="Natural language query"),
    limit: int = typer.Option(10, "--limit", "-n", help="Max number of results"),
    language: str = typer.Option(None, "--language", "--language-filter", help="Filter results by language (python, go, typescript, ...)"),
) -> None:
    """Query the knowledge graph for relevant symbols."""
    repo = Path(repo_path).resolve()

    # If repo_path is a JSON file, load it directly; otherwise index first
    if repo.is_file() and repo.suffix == ".json":
        graph = KnowledgeGraph()
        graph.load_json(repo)
    else:
        if not repo.exists():
            typer.echo(f"Error: path not found: {repo}", err=True)
            raise typer.Exit(1)
        symbols, edges = parse_directory(repo)
        graph = KnowledgeGraph()
        graph.build_from_parser(symbols, edges)

    results = graph.find_symbol(q)[:limit]
    if language:
        results = [r for r in results if r.get("language") == language]
    if not results:
        typer.echo("No matching symbols found.")
        raise typer.Exit(0)

    typer.echo(f"Found {len(results)} result(s) for '{q}':")
    for i, node in enumerate(results, 1):
        kind_emoji = {"function": "⚙️", "class": "📦", "module": "📁"}.get(node["kind"], "🔹")
        lang_label = f" [{node.get('language', '?')}]" if node.get("language") else ""
        typer.echo(f"  {i}. {kind_emoji} {node['name']} ({node['kind']}){lang_label} — {node['filepath']}:{node['line']}")
        if node.get("signature"):
            typer.echo(f"     Sig: {node['signature']}")


@app.command()
def graph(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    output: str = typer.Option("sckg_graph.html", "--output", "-o", help="Path for the HTML output"),
) -> None:
    """Generate an interactive D3.js force-directed graph HTML."""
    repo = Path(repo_path).resolve()

    if repo.is_file() and repo.suffix == ".json":
        with open(repo, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        if not repo.exists():
            typer.echo(f"Error: path not found: {repo}", err=True)
            raise typer.Exit(1)
        symbols, edges = parse_directory(repo)
        kg = KnowledgeGraph()
        kg.build_from_parser(symbols, edges)
        kg.detect_communities()
        data = {
            "nodes": list(kg.nodes.values()),
            "edges": kg.edges,
            "communities": kg._communities_dict(),
        }

    out_path = generate_html(data, output)
    typer.echo(f"Interactive graph written to {out_path}")
    typer.echo(f"Open it with: open {out_path}")


def main() -> None:
    app()
