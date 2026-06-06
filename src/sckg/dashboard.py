"""Multi-repo dashboard HTML generator for SCKG.

Generates standalone HTML dashboards with repo comparison, cross-repo
chord diagrams, community overview, and live WebSocket updates.

Docs: dashboard.doc.md
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from sckg.dead_code import find_dead_code
from sckg.graph import KnowledgeGraph
from sckg.hotpaths import compute_hot_paths


def collect_repo_stats(graph: KnowledgeGraph) -> list[dict[str, Any]]:
    """Collect per-repository statistics from the graph."""
    repo_data: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "node_count": 0,
        "edge_count": 0,
        "languages": defaultdict(int),
        "types": defaultdict(int),
        "entry_points": 0,
    })

    for node in graph.nodes.values():
        repo = node.get("repo") or "default"
        data = repo_data[repo]
        data["node_count"] += 1
        data["languages"][node.get("language", "unknown")] += 1
        data["types"][node.get("kind", "unknown")] += 1
        if node.get("kind") == "function" and (
            node.get("name") in ("main", "__init__") or
            not node.get("parent")
        ):
            data["entry_points"] += 1

    for edge in graph.edges:
        src_repo = graph.nodes.get(edge.get("source", ""), {}).get("repo") or "default"
        repo_data[src_repo]["edge_count"] += 1

    return [
        {
            "name": name,
            "node_count": d["node_count"],
            "edge_count": d["edge_count"],
            "languages": dict(d["languages"]),
            "types": dict(d["types"]),
            "entry_points": d["entry_points"],
        }
        for name, d in sorted(repo_data.items())
    ]


def build_cross_repo_matrix(graph: KnowledgeGraph) -> dict[str, Any]:
    """Build a matrix of cross-repo edge counts for the chord diagram."""
    repos = graph.get_repos()
    matrix = {r: {r2: 0 for r2 in repos} for r in repos}

    for edge in graph.get_cross_repo_edges():
        src_node = graph.nodes.get(edge.get("source", ""), {})
        tgt_node = graph.nodes.get(edge.get("target", ""), {})
        src_repo = src_node.get("repo", "")
        tgt_repo = tgt_node.get("repo", "")
        if src_repo in matrix and tgt_repo in matrix and src_repo != tgt_repo:
            matrix[src_repo][tgt_repo] += 1

    # Convert to list of [src, tgt, count] tuples for D3
    links = []
    for src, targets in matrix.items():
        for tgt, count in targets.items():
            if count > 0 and src != tgt:
                links.append({"source": src, "target": tgt, "count": count})
    return {"repos": repos, "links": links}


def collect_community_overview(graph: KnowledgeGraph) -> list[dict[str, Any]]:
    """Collect community overview with language breakdown and size."""
    communities = graph.get_communities()
    overview = []
    for comm in communities:
        overview.append({
            "id": comm.id,
            "dominant_language": comm.dominant_language,
            "languages": dict(comm.languages),
            "size": comm.size,
            "density": round(comm.density, 4),
            "top_node": comm.nodes[0].get("name", "") if comm.nodes else "",
        })
    return overview


def collect_hot_paths_per_repo(graph: KnowledgeGraph, top: int = 5) -> dict[str, list[dict[str, Any]]]:
    """Collect top hot paths for each repository."""
    report = compute_hot_paths(graph, top_n=top * 3, weight="in_degree")
    by_repo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for hn in report.hot_nodes:
        repo = hn.node.get("repo") or "default"
        if len(by_repo[repo]) < top:
            by_repo[repo].append({
                "name": hn.node.get("name", "?"),
                "file": hn.node.get("filepath", ""),
                "score": round(hn.score, 3),
                "in_degree": hn.in_degree,
            })
    return dict(by_repo)


def collect_dead_code_per_repo(graph: KnowledgeGraph) -> dict[str, int]:
    """Count dead code nodes per repository."""
    report = find_dead_code(graph)
    by_repo: dict[str, int] = defaultdict(int)
    for node in report.dead_nodes:
        repo = node.get("repo") or "default"
        by_repo[repo] += 1
    return dict(by_repo)


def generate_dashboard(
    graph: KnowledgeGraph,
    output_path: str | Path,
    workspace_path: str | None = None,
    graphql_url: str = "ws://localhost:8080/graphql",
) -> Path:
    """Generate a standalone HTML dashboard for multi-repo analysis."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    repo_stats = collect_repo_stats(graph)
    cross_matrix = build_cross_repo_matrix(graph)
    communities = collect_community_overview(graph)
    hot_paths_by_repo = collect_hot_paths_per_repo(graph)
    dead_by_repo = collect_dead_code_per_repo(graph)

    data = {
        "workspace_path": workspace_path or "",
        "graphql_url": graphql_url,
        "total_repos": len(repo_stats),
        "total_nodes": sum(r["node_count"] for r in repo_stats),
        "total_edges": sum(r["edge_count"] for r in repo_stats),
        "repo_stats": repo_stats,
        "cross_repo_matrix": cross_matrix,
        "communities": communities,
        "hot_paths_by_repo": hot_paths_by_repo,
        "dead_by_repo": dead_by_repo,
    }

    html = _render_dashboard_html(data)
    out.write_text(html, encoding="utf-8")
    return out


def _render_dashboard_html(data: dict[str, Any]) -> str:
    repos_json = json.dumps(data["repo_stats"], ensure_ascii=False)
    cross_json = json.dumps(data["cross_repo_matrix"], ensure_ascii=False)
    communities_json = json.dumps(data["communities"], ensure_ascii=False)
    hot_json = json.dumps(data["hot_paths_by_repo"], ensure_ascii=False)
    dead_json = json.dumps(data["dead_by_repo"], ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SCKG Multi-Repo Dashboard</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #0e1117; color: #e6edf3; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
  h1 {{ border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
  h2 {{ color: #58a6ff; margin-top: 30px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }}
  .stat-card .label {{ color: #8b949e; font-size: 12px; text-transform: uppercase; }}
  .stat-card .value {{ font-size: 28px; font-weight: bold; color: #58a6ff; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; background: #161b22; border-radius: 8px; overflow: hidden; }}
  th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #30363d; }}
  th {{ background: #1c2128; color: #58a6ff; font-weight: 600; }}
  tr:hover {{ background: #1c2128; }}
  .lang-python {{ color: #3572A5; }}
  .lang-go {{ color: #00ADD8; }}
  .lang-typescript {{ color: #3178C6; }}
  #chord-diagram {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 20px; margin: 20px 0; }}
  .live-indicator {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #f85149; margin-left: 10px; }}
  .live-indicator.connected {{ background: #3fb950; }}
  #events-log {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 12px; max-height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; }}
  .event {{ padding: 4px 0; border-bottom: 1px solid #21262d; }}
  .event-time {{ color: #8b949e; margin-right: 10px; }}
</style>
</head>
<body>
<div class="container">
  <h1>SCKG Multi-Repo Dashboard <span id="live-indicator" class="live-indicator" title="WebSocket status"></span></h1>
  <p>Workspace: <code>{data['workspace_path']}</code></p>

  <div class="stats-grid">
    <div class="stat-card"><div class="label">Repositories</div><div class="value">{data['total_repos']}</div></div>
    <div class="stat-card"><div class="label">Total Nodes</div><div class="value">{data['total_nodes']}</div></div>
    <div class="stat-card"><div class="label">Total Edges</div><div class="value">{data['total_edges']}</div></div>
    <div class="stat-card"><div class="label">Communities</div><div class="value">{len(data['communities'])}</div></div>
  </div>

  <h2>Repository Comparison</h2>
  <table>
    <thead>
      <tr><th>Repository</th><th>Nodes</th><th>Edges</th><th>Entry Points</th><th>Languages</th></tr>
    </thead>
    <tbody id="repo-table"></tbody>
  </table>

  <h2>Cross-Repo Call Graph (Chord Diagram)</h2>
  <div id="chord-diagram">
    <svg id="chord-svg" width="100%" height="400"></svg>
  </div>

  <h2>Communities</h2>
  <table>
    <thead>
      <tr><th>ID</th><th>Dominant Language</th><th>Size</th><th>Density</th><th>Top Node</th></tr>
    </thead>
    <tbody id="community-table"></tbody>
  </table>

  <h2>Hot Paths by Repository</h2>
  <div id="hot-paths-container"></div>

  <h2>Dead Code by Repository</h2>
  <table>
    <thead><tr><th>Repository</th><th>Dead Code Count</th></tr></thead>
    <tbody id="dead-table"></tbody>
  </table>

  <h2>Live Events</h2>
  <div id="events-log"><em>Connecting to GraphQL subscriptions...</em></div>
</div>

<script>
const repoStats = {repos_json};
const crossMatrix = {cross_json};
const communities = {communities_json};
const hotPathsByRepo = {hot_json};
const deadByRepo = {dead_json};
const graphqlUrl = "{data['graphql_url']}";

// Render repo table
const repoTable = document.getElementById("repo-table");
repoStats.forEach(r => {{
  const langs = Object.entries(r.languages).map(([k, v]) => `<span class="lang-${{k}}">${{k}}=${{v}}</span>`).join(", ");
  repoTable.innerHTML += `<tr><td><strong>${{r.name}}</strong></td><td>${{r.node_count}}</td><td>${{r.edge_count}}</td><td>${{r.entry_points}}</td><td>${{langs}}</td></tr>`;
}});

// Render chord diagram
const svg = d3.select("#chord-svg");
const width = document.getElementById("chord-svg").clientWidth;
const height = 400;
const radius = Math.min(width, height) / 2 - 40;

if (crossMatrix.repos.length > 0) {{
  const chord = d3.chordDirected().padAngle(0.05).sortSubgroups(d3.descending);
  const ribbon = d3.ribbonArrow().radius(radius - 10);
  const arc = d3.arc().innerRadius(radius).outerRadius(radius + 5);

  const matrix = crossMatrix.repos.map(src =>
    crossMatrix.repos.map(tgt => {{
      const link = crossMatrix.links.find(l => l.source === src && l.target === tgt);
      return link ? link.count : 0;
    }})
  );

  const chords = chord(matrix);
  const g = svg.append("g").attr("transform", `translate(${{width/2}},${{height/2}})`);
  const color = d3.scaleOrdinal(d3.schemeTableau10).domain(crossMatrix.repos);

  g.append("g").selectAll("path")
    .data(chords.groups)
    .join("path")
    .attr("fill", d => color(crossMatrix.repos[d.index]))
    .attr("stroke", d => d3.rgb(color(crossMatrix.repos[d.index])).darker())
    .attr("d", arc);

  g.append("g").selectAll("text")
    .data(chords.groups)
    .join("text")
    .each(d => {{ this._current = d; }})
    .attr("dy", "0.35em")
    .attr("transform", d => `translate(${{arc.centroid(d)}}), rotate(${{(d.startAngle + d.endAngle) / 2 * 180 / Math.PI - 90}})`)
    .attr("text-anchor", "middle")
    .style("font-size", "11px")
    .style("fill", "#e6edf3")
    .text(d => crossMatrix.repos[d.index]);

  g.append("g").selectAll("path")
    .data(chords)
    .join("path")
    .attr("class", "ribbon")
    .attr("fill", d => color(crossMatrix.repos[d.source.index]))
    .attr("stroke", d => d3.rgb(color(crossMatrix.repos[d.source.index])).darker())
    .attr("d", ribbon);
}} else {{
  svg.append("text").attr("x", width/2).attr("y", height/2)
    .attr("text-anchor", "middle").attr("fill", "#8b949e")
    .text("No cross-repo edges detected");
}}

// Render community table
const communityTable = document.getElementById("community-table");
communities.forEach(c => {{
  const langs = Object.entries(c.languages).map(([k, v]) => `<span class="lang-${{k}}">${{k}}=${{v}}</span>`).join(", ");
  communityTable.innerHTML += `<tr><td>${{c.id}}</td><td>${{langs}}</td><td>${{c.size}}</td><td>${{c.density}}</td><td><code>${{c.top_node}}</code></td></tr>`;
}});

// Render hot paths
const hotContainer = document.getElementById("hot-paths-container");
Object.entries(hotPathsByRepo).forEach(([repo, paths]) => {{
  const items = paths.map(p => `<li><code>${{p.name}}</code> in ${{p.file}} (score: ${{p.score}}, in: ${{p.in_degree}})</li>`).join("");
  hotContainer.innerHTML += `<h3>${{repo}}</h3><ul>${{items}}</ul>`;
}});

// Render dead code table
const deadTable = document.getElementById("dead-table");
Object.entries(deadByRepo).forEach(([repo, count]) => {{
  deadTable.innerHTML += `<tr><td>${{repo}}</td><td>${{count}}</td></tr>`;
}});

// WebSocket connection for live updates
const eventsLog = document.getElementById("events-log");
const liveIndicator = document.getElementById("live-indicator");

function addEvent(msg) {{
  if (eventsLog.innerHTML.includes("Connecting")) eventsLog.innerHTML = "";
  const time = new Date().toLocaleTimeString();
  eventsLog.innerHTML = `<div class="event"><span class="event-time">${{time}}</span>${{msg}}</div>` + eventsLog.innerHTML;
}}

try {{
  const ws = new WebSocket(graphqlUrl.replace("http", "ws").replace("/graphql", "/graphql"));
  ws.onopen = () => {{
    liveIndicator.classList.add("connected");
    liveIndicator.title = "Connected to " + graphqlUrl;
    addEvent("✓ Connected to GraphQL subscriptions");
  }};
  ws.onmessage = (event) => {{
    addEvent("📡 " + event.data);
  }};
  ws.onerror = () => {{
    liveIndicator.title = "Connection error";
    addEvent("✗ WebSocket error (server may not be running)");
  }};
  ws.onclose = () => {{
    liveIndicator.classList.remove("connected");
    liveIndicator.title = "Disconnected";
  }};
}} catch (e) {{
  addEvent("✗ Failed to connect: " + e.message);
}}
</script>
</body>
</html>
"""