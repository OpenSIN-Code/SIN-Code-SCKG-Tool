"""Typer CLI for SCKG (Semantic Codebase Knowledge Graphs).

Docs: cli.doc.md
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from sckg.communities import resolve_cross_language_edges
from sckg.cross_repo import build_cross_repo_graph, find_repos_in_workspace
from sckg.dead_code import find_dead_code
from sckg.graph import KnowledgeGraph
from sckg.html_generator import generate_html
from sckg.parser import parse_directory

app = typer.Typer(help="SCKG — Semantic Codebase Knowledge Graphs")

DEFAULT_OUTPUT = "sckg_graph.json"


@app.command()
def index(
    repo_path: str | None = typer.Argument(None, help="Path to the repository to index"),
    output: str = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Path for the JSON graph output"),
    workspace: str | None = typer.Option(None, "--workspace", help="Index all repositories in a workspace directory"),
) -> None:
    """Build a knowledge graph from source code and save to JSON."""
    if workspace:
        repos = find_repos_in_workspace(Path(workspace))
        if not repos:
            typer.echo(f"Error: no repositories found in {workspace}", err=True)
            raise typer.Exit(1)
        typer.echo(f"Indexing workspace {workspace} ({len(repos)} repos) ...")
        graph = build_cross_repo_graph(repos)
    elif repo_path:
        repo = Path(repo_path).resolve()
        if not repo.exists():
            typer.echo(f"Error: path not found: {repo}", err=True)
            raise typer.Exit(1)
        typer.echo(f"Indexing {repo} ...")
        symbols, edges = parse_directory(repo)
        graph = KnowledgeGraph()
        graph.build_from_parser(symbols, edges)
        graph.detect_communities()
    else:
        typer.echo("Error: provide either repo_path or --workspace", err=True)
        raise typer.Exit(1)

    graph.save_json(output)

    cross_edges = [e for e in graph.edges if e.get("relation") in ("cross_repo_call", "cross_repo_import")]
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    cross_count = len(cross_edges)
    comm_count = len(set(graph._communities_dict().values())) if graph._communities_dict() else 0
    typer.echo(f"Done. Nodes: {node_count}, Edges: {edge_count}, Cross-repo: {cross_count}, Communities: {comm_count}")
    typer.echo(f"Graph saved to {output}")


@app.command()
def cross_repo(
    repo_paths: list[str] = typer.Argument(..., help="One or more repository paths to analyze"),
    output: str = typer.Option(DEFAULT_OUTPUT, "--output", "-o", help="Path for the JSON graph output"),
    packages: str | None = typer.Option(None, "--packages", help="JSON dict mapping package names to repo names"),
) -> None:
    """Detect cross-repo dependencies between multiple repositories."""
    resolved = [Path(p).resolve() for p in repo_paths]
    missing = [p for p in resolved if not p.exists()]
    if missing:
        typer.echo(f"Error: path not found: {missing}", err=True)
        raise typer.Exit(1)

    known_packages: dict[str, str] | None = None
    if packages:
        try:
            known_packages = json.loads(packages)
        except json.JSONDecodeError as exc:
            typer.echo(f"Error: invalid JSON for --packages: {exc}", err=True)
            raise typer.Exit(1)

    graph = build_cross_repo_graph(resolved, known_packages)
    graph.save_json(output)

    cross_edges = [e for e in graph.edges if e.get("relation") in ("cross_repo_call", "cross_repo_import")]
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)
    cross_count = len(cross_edges)
    comm_count = len(set(graph._communities_dict().values())) if graph._communities_dict() else 0
    typer.echo(f"Done. Nodes: {node_count}, Edges: {edge_count}, Cross-repo: {cross_count}, Communities: {comm_count}")
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
    mixed: bool = typer.Option(False, "--mixed", help="Use mixed-language community detection"),
) -> None:
    """Generate an interactive D3.js force-directed graph HTML."""
    repo = Path(repo_path).resolve()

    if repo.is_file() and repo.suffix == ".json":
        kg = KnowledgeGraph()
        kg.load_json(repo)
        with open(repo, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    else:
        if not repo.exists():
            typer.echo(f"Error: path not found: {repo}", err=True)
            raise typer.Exit(1)
        symbols, edges = parse_directory(repo)
        kg = KnowledgeGraph()
        kg.build_from_parser(symbols, edges)
        resolve_cross_language_edges(kg)
        communities = kg.get_communities(mixed=mixed)
        data = {
            "nodes": list(kg.nodes.values()),
            "edges": kg.edges,
            "communities": kg._communities_dict(),
            "community_objects": [
                {
                    "id": c.id,
                    "dominant_language": c.dominant_language,
                    "languages": c.languages,
                    "size": c.size,
                    "density": c.density,
                    "node_ids": [n["id"] for n in c.nodes],
                }
                for c in communities
            ],
        }

    report = find_dead_code(kg).to_dict()
    out_path = generate_html(data, output, report=report)
    typer.echo(f"Interactive graph written to {out_path}")
    typer.echo(f"Open it with: open {out_path}")


@app.command()
def communities(
    repo_path: str = typer.Argument(..., help="Path to the repository to analyze"),
    by_language: bool = typer.Option(True, "--by-language", help="Group by language first (default)"),
    mixed: bool = typer.Option(False, "--mixed", help="Detect mixed-language communities"),
) -> None:
    """Detect and report language-aware communities in a repository."""
    repo = Path(repo_path).resolve()
    if not repo.exists():
        typer.echo(f"Error: path not found: {repo}", err=True)
        raise typer.Exit(1)

    symbols, edges = parse_directory(repo)
    graph = KnowledgeGraph()
    graph.build_from_parser(symbols, edges)
    resolve_cross_language_edges(graph)

    if mixed:
        comms = graph.get_communities(mixed=True)
    elif by_language:
        lang_comms = graph.detect_communities_by_language()
        # Flatten for JSON output
        comms = []
        for idx, (lang, c_list) in enumerate(lang_comms.items(), 1):
            for c in c_list:
                c.id = idx + len(comms) - 1
                comms.append(c)
        for i, c in enumerate(comms, 1):
            c.id = i
    else:
        comms = graph.get_communities(mixed=False)

    # Build output
    output = {
        "communities": [
            {
                "id": c.id,
                "dominant_language": c.dominant_language,
                "languages": c.languages,
                "size": c.size,
                "density": round(c.density, 4),
                "top_nodes": [n["id"] for n in c.nodes[:5]],
            }
            for c in comms
        ],
        "total_communities": len(comms),
        "mixed_communities_count": sum(1 for c in comms if c.dominant_language == "mixed"),
    }

    typer.echo(json.dumps(output, indent=2))

    # Summary line
    typer.echo(f"\nTotal communities: {output['total_communities']}")
    typer.echo(f"Mixed communities: {output['mixed_communities_count']}")
    for c in output["communities"]:
        lang_str = ", ".join(f"{k}={v}" for k, v in c["languages"].items())
        typer.echo(f"  Community #{c['id']} [{c['dominant_language']}] — size={c['size']}, density={c['density']}, languages={lang_str}")


@app.command()
def dead_code(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    threshold: float = typer.Option(0.0, "--threshold", "-t", help="Fail if coverage is below this value (0.0–1.0)"),
    include_suspicious: bool = typer.Option(False, "--include-suspicious", help="Include suspicious nodes (1 incoming edge) in the report"),
    output: str = typer.Option(None, "--output", "-o", help="Path for JSON report output (optional)"),
) -> None:
    """Analyze the graph for dead code and emit a JSON report."""
    repo = Path(repo_path).resolve()

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

    report = find_dead_code(graph)
    report_dict = report.to_dict()

    if not include_suspicious:
        report_dict.pop("suspicious_nodes", None)

    json_out = json.dumps(report_dict, indent=2, ensure_ascii=False)

    if output:
        Path(output).write_text(json_out, encoding="utf-8")
        typer.echo(f"Report saved to {output}")

    typer.echo(json_out)

    dead_count = len(report.dead_nodes)
    entry_count = len(report.entry_points)
    suspicious_count = len(report.suspicious_nodes)
    coverage = report.coverage_pct

    typer.echo(f"\nSummary: {dead_count} dead, {entry_count} entry points, {suspicious_count} suspicious — coverage: {coverage:.2%}")

    if dead_count > 0:
        raise typer.Exit(1)
    if threshold > 0 and coverage < threshold:
        typer.echo(f"Coverage {coverage:.2%} is below threshold {threshold:.2%}", err=True)
        raise typer.Exit(1)


def main() -> None:
    app()
