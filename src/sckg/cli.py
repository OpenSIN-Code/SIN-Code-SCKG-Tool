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
from sckg.hotpaths import compute_hot_paths
from sckg.graph import KnowledgeGraph
from sckg.html_generator import generate_html
from sckg.parser import parse_directory
from sckg.search import build_ngram_index, search, search_pattern
from sckg.api.server import create_app, run_server
from sckg.watcher import FileWatcher, watch_and_serve
from sckg.similarity import find_similar
from sckg.adr import generate_adrs
from sckg.dashboard import generate_dashboard
from sckg.hybrid_search import hybrid_search

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
    hot_report = compute_hot_paths(kg, top_n=50, weight="in_degree")
    hot_paths_data = hot_report.to_dict().get("hot_nodes", [])
    out_path = generate_html(data, output, report=report, hot_paths=hot_paths_data)
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


@app.command(name="hot-paths")
def hot_paths(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    top: int = typer.Option(20, "--top", "-n", help="Number of top hot paths to show"),
    weight: str = typer.Option("in_degree", "--weight", "-w", help="Weight method: in_degree, out_degree, betweenness, pagerank"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
) -> None:
    """Show the most frequently called functions (hot paths) in the codebase."""
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

    try:
        report = compute_hot_paths(graph, top_n=top, weight=weight)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    if format == "json":
        typer.echo(report.to_dict())
        return

    # Table output
    typer.echo(f"Hot Paths (weight={weight}, top={top}):")
    typer.echo(f"Total nodes in graph: {report.total_nodes}")
    typer.echo("")
    typer.echo(f"{'Rank':>4} {'Function':<30} {'File':<35} {'Score':>10} {'In':>4} {'Out':>4}")
    typer.echo("-" * 95)
    for hn in report.hot_nodes:
        node = hn.node
        name = node.get("name", "?")
        filepath = node.get("filepath", "?")
        # Truncate long names/paths for table display
        if len(name) > 28:
            name = name[:25] + "..."
        if len(filepath) > 33:
            filepath = "..." + filepath[-30:]
        typer.echo(f"{hn.rank:>4} {name:<30} {filepath:<35} {hn.score:>10.3f} {hn.in_degree:>4} {hn.out_degree:>4}")

    # Summary line
    top_node = report.hot_nodes[0] if report.hot_nodes else None
    if top_node:
        typer.echo(f"\nTop hot path: {top_node.node.get('name', '?')} (score: {top_node.score:.3f}, method: {weight})")


@app.command()
def search(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    query: str = typer.Argument(..., help="Search query string"),
    top: int = typer.Option(10, "--top", "-n", help="Number of results to return"),
    ngram_size: str = typer.Option("1,2,3", "--ngram-size", help="Comma-separated n-gram sizes (e.g., 1,2,3)"),
    pattern: bool = typer.Option(False, "--pattern", "-p", help="Use wildcard pattern search instead of n-gram search"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Use hybrid search (n-gram + structural similarity)"),
    alpha: float = typer.Option(0.5, "--alpha", help="Hybrid alpha: weight for n-gram (0.0-1.0, 1.0=pure n-gram)"),
) -> None:
    """Search the knowledge graph for symbols matching the query."""
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

    if pattern:
        results = search_pattern(query, graph, top_k=top)
        for i, r in enumerate(results, 1):
            node = r.node
            kind_emoji = {"function": "⚙️", "class": "📦", "module": "📁"}.get(node.get("kind"), "🔹")
            lang_label = f" [{node.get('language', '?')}]" if node.get("language") else ""
            typer.echo(f"  {i}. {kind_emoji} {node['name']} ({node['kind']}){lang_label} — {node['filepath']}:{node['line']}")
            typer.echo(f"     {r.snippet}")
        return

    if hybrid:
        index = build_ngram_index(graph)
        hybrid_results = hybrid_search(query, graph, index, top_k=top, alpha=alpha)
        if not hybrid_results:
            typer.echo("No matching symbols found.")
            raise typer.Exit(0)
        typer.echo(f"Found {len(hybrid_results)} hybrid result(s) for '{query}' (alpha={alpha}):")
        for i, r in enumerate(hybrid_results, 1):
            node = r.node
            kind_emoji = {"function": "⚙️", "class": "📦", "module": "📁"}.get(node.get("kind"), "🔹")
            lang_label = f" [{node.get('language', '?')}]" if node.get("language") else ""
            typer.echo(f"  {i}. {kind_emoji} {node['name']} ({node['kind']}){lang_label} — {node['filepath']}:{node['line']}")
            typer.echo(f"     Combined: {r.score:.3f} | N-gram: {r.ngram_score:.3f} | Similarity: {r.similarity_score:.3f}")
        return

    index = build_ngram_index(graph)
    results = search(query, graph, index, top_k=top)

    if not results:
        typer.echo("No matching symbols found.")
        raise typer.Exit(0)

    typer.echo(f"Found {len(results)} result(s) for '{query}':")
    for i, r in enumerate(results, 1):
        node = r.node
        kind_emoji = {"function": "⚙️", "class": "📦", "module": "📁"}.get(node.get("kind"), "🔹")
        lang_label = f" [{node.get('language', '?')}]" if node.get("language") else ""
        typer.echo(f"  {i}. {kind_emoji} {node['name']} ({node['kind']}){lang_label} — {node['filepath']}:{node['line']}")
        typer.echo(f"     Score: {r.score:.3f} | Matched: {', '.join(r.matched_ngrams)}")
        typer.echo(f"     {r.snippet}")


@app.command()
def serve(
    graph_path: str = typer.Argument(..., help="Path to the JSON graph file"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind to"),
    port: int = typer.Option(8080, "--port", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload (dev mode)"),
) -> None:
    """Start the GraphQL API server with GraphiQL playground."""
    path = Path(graph_path).resolve()
    if not path.exists():
        typer.echo(f"Error: graph file not found: {path}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting SCKG GraphQL server on http://{host}:{port}")
    typer.echo(f"GraphQL Playground: http://{host}:{port}/graphql")
    typer.echo(f"Graph: {path}")
    run_server(path, host=host, port=port, reload=reload)


@app.command()
def graphql_schema(
    output: str = typer.Option(None, "--output", "-o", help="Output file (stdout if omitted)"),
) -> None:
    """Print the GraphQL schema (SDL) to stdout or file."""
    sdl = str(schema)
    if output:
        Path(output).write_text(sdl, encoding="utf-8")
        typer.echo(f"Schema written to {output}")
    else:
        typer.echo(sdl)


@app.command()
def watch(
    repo_path: str = typer.Argument(..., help="Path to the repository to watch"),
    graph_path: str = typer.Option("sckg_graph.json", "--graph-path", "-g", help="Path to the JSON graph file"),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind GraphQL server"),
    port: int = typer.Option(8080, "--port", help="Port to bind GraphQL server"),
) -> None:
    """Watch a repository for changes and serve GraphQL API with live updates."""
    import asyncio
    repo = Path(repo_path).resolve()
    graph = Path(graph_path).resolve()

    if not repo.exists():
        typer.echo(f"Error: repo path not found: {repo}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting watcher for {repo} with GraphQL on http://{host}:{port}")
    asyncio.run(watch_and_serve(repo, graph, host=host, port=port))


@app.command()
def similar(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    node_id: str = typer.Argument(..., help="Node ID or name to find similar functions for"),
    top: int = typer.Option(10, "--top", "-n", help="Number of results to return"),
    method: str = typer.Option("ast", "--method", "-m", help="Similarity method: jaccard, cosine, ast"),
) -> None:
    """Find code symbols similar to the given node using structural analysis."""
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

    # Find node by ID or name
    target_nid = None
    if node_id in graph.nodes:
        target_nid = node_id
    else:
        # Search by name
        for nid, node in graph.nodes.items():
            if node.get("name") == node_id:
                target_nid = nid
                break

    if not target_nid:
        typer.echo(f"Error: node not found: {node_id}", err=True)
        raise typer.Exit(1)

    results = find_similar(target_nid, graph, top_k=top, method=method)

    if not results:
        typer.echo("No similar symbols found.")
        raise typer.Exit(0)

    typer.echo(f"Found {len(results)} similar symbol(s) to '{graph.nodes[target_nid].get('name', target_nid)}' (method={method}):")
    for i, r in enumerate(results, 1):
        node = r.node
        kind_emoji = {"function": "⚙️", "class": "📦", "module": "📁"}.get(node.get("kind"), "🔹")
        lang_label = f" [{node.get('language', '?')}]" if node.get("language") else ""
        typer.echo(f"  {i}. {kind_emoji} {node['name']} ({node['kind']}){lang_label} — {node['filepath']}:{node['line']}")
        typer.echo(f"     Score: {r.score:.3f} | Matched: {', '.join(r.matched_features) if r.matched_features else 'none'}")


@app.command()
def adr(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    output_dir: str = typer.Option("./adrs", "--output-dir", "-o", help="Output directory for ADR files"),
) -> None:
    """Generate Architecture Decision Records from graph analysis."""
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

    out_dir = Path(output_dir)
    adrs = generate_adrs(graph, out_dir)

    if not adrs:
        typer.echo("No significant findings for ADR generation.")
        raise typer.Exit(0)

    typer.echo(f"Generated {len(adrs)} ADR(s) in {out_dir}:")
    for adr in adrs:
        typer.echo(f"  {adr.id}: {adr.title} [{adr.status}]")


@app.command()
def dashboard(
    repo_path: str = typer.Argument(..., help="Path to the repository (or path to existing JSON graph)"),
    output: str = typer.Option("dashboard.html", "--output", "-o", help="Path for the HTML dashboard output"),
    workspace: str = typer.Option(None, "--workspace", help="Workspace path for display (e.g., ~/dev)"),
    graphql: str = typer.Option("ws://localhost:8080/graphql", "--graphql", help="GraphQL WebSocket URL for live updates"),
) -> None:
    """Generate a multi-repo dashboard HTML with chord diagram and live updates."""
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

    out_path = generate_dashboard(
        graph,
        Path(output),
        workspace_path=workspace or str(repo),
        graphql_url=graphql,
    )
    typer.echo(f"Dashboard written to {out_path}")
    typer.echo(f"Open it with: open {out_path}")
