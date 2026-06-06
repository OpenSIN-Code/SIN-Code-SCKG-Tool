"""Generate an interactive D3.js force-directed graph HTML file.

Docs: html_generator.doc.md
"""

import json
from pathlib import Path
from typing import Any

# Language → color mapping used for node fill in the D3 graph.
LANGUAGE_COLORS = {
    "python": "#4A90D9",
    "go": "#00ADD8",
    "typescript": "#3178C6",
    "javascript": "#F7DF1E",
}

DEFAULT_LANGUAGE_COLOR = "#999"

# Community background colors by dominant language
COMMUNITY_BG_COLORS = {
    "python": "#E3F2FD",
    "go": "#E0F7FA",
    "typescript": "#FFF3E0",
    "mixed": "#F3E5F5",
}

COMMUNITY_BORDER_COLORS = {
    "python": "#1976D2",
    "go": "#0097A7",
    "typescript": "#F57C00",
    "mixed": "#7B1FA2",
}

# Dead-code visual markers
DEAD_STROKE = "#F44336"
SUSPICIOUS_STROKE = "#FFC107"
ENTRY_STROKE = "#4CAF50"
DEAD_FILL = "#F44336"


def generate_html(
    graph_data: dict[str, Any],
    output_path: str | Path,
    report: dict[str, Any] | None = None,
) -> Path:
    """Write a single-file HTML with embedded D3.js force graph.

    Nodes are colored by programming language. Communities (if present) are
    visualised as background bounding boxes with language-tinted fills and
    labelled in the top-left corner.

    When a ``report`` dict is provided (from ``DeadCodeReport.to_dict()``),
    dead nodes get a red border + red fill at 50% opacity, suspicious nodes
    get a yellow border, and entry points get a green border.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    communities = graph_data.get("communities", {})
    community_objects = graph_data.get("community_objects", [])

    # Build lookup sets from report for fast membership checks.
    dead_ids: set[str] = set()
    suspicious_ids: set[str] = set()
    entry_ids: set[str] = set()
    if report:
        dead_ids = {n.get("id", "") for n in report.get("dead_nodes", [])}
        suspicious_ids = {n.get("id", "") for n in report.get("suspicious_nodes", [])}
        entry_ids = {n.get("id", "") for n in report.get("entry_points", [])}

    # Assign community colors as fallback for nodes without language
    community_colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    comm_to_color = {}
    for i, comm in enumerate(set(communities.values())):
        comm_to_color[comm] = community_colors[i % len(community_colors)]

    # Determine which languages are present so the legend only shows active ones
    active_languages = {n.get("language") for n in nodes if n.get("language")}

    # Build community node mapping and centres for D3 force layout
    community_node_map = {}  # node_id → community_index
    community_centres = {}   # community_index → {x, y, label, color, border}

    if community_objects:
        for idx, comm in enumerate(community_objects):
            label = f"{comm.get('dominant_language', 'unknown').capitalize()} Community #{idx + 1}"
            lang = comm.get("dominant_language", "mixed")
            bg = COMMUNITY_BG_COLORS.get(lang, COMMUNITY_BG_COLORS["mixed"])
            border = COMMUNITY_BORDER_COLORS.get(lang, COMMUNITY_BORDER_COLORS["mixed"])
            community_centres[idx] = {
                "x": (idx % 3) * 250 + 200,  # simple grid layout for centres
                "y": (idx // 3) * 250 + 200,
                "label": label,
                "bg": bg,
                "border": border,
            }
            for nid in comm.get("node_ids", []):
                community_node_map[nid] = idx
    elif communities:
        for i, comm in enumerate(set(communities.values())):
            community_centres[i] = {
                "x": (i % 3) * 250 + 200,
                "y": (i // 3) * 250 + 200,
                "label": f"Community #{i + 1}",
                "bg": COMMUNITY_BG_COLORS["mixed"],
                "border": COMMUNITY_BORDER_COLORS["mixed"],
            }
        for nid, cid in communities.items():
            for i, comm in enumerate(set(communities.values())):
                if comm == cid:
                    community_node_map[nid] = i

    for n in nodes:
        lang = n.get("language")
        n["color"] = LANGUAGE_COLORS.get(lang, comm_to_color.get(communities.get(n["id"], "default"), DEFAULT_LANGUAGE_COLOR))
        n["radius"] = 8 if n.get("kind") == "function" else 10 if n.get("kind") == "class" else 6
        n["community"] = community_node_map.get(n["id"], -1)

    # Build legend HTML for dead-code categories (only when report is present)
    dead_code_legend_html = ""
    if report:
        dead_code_legend_html = f"""<div id="dead-code-legend">
  <div style="font-weight:bold; margin-bottom:6px;">Dead Code</div>
  <div class="legend-item"><div class="legend-dot" style="background:{DEAD_FILL};opacity:0.5;border:2px solid {DEAD_STROKE}"></div>Dead Code</div>
  <div class="legend-item"><div class="legend-dot" style="background:transparent;border:2px solid {SUSPICIOUS_STROKE}"></div>Suspicious (1 ref)</div>
  <div class="legend-item"><div class="legend-dot" style="background:transparent;border:2px solid {ENTRY_STROKE}"></div>Entry Point</div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SCKG Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  body {{ margin: 0; overflow: hidden; font-family: sans-serif; background: #1a1a1a; color: #eee; }}
  #graph {{ width: 100vw; height: 100vh; }}
  .node {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; }}
  .node:hover {{ stroke: #ff0; stroke-width: 3px; }}
  .link {{ stroke: #aaa; stroke-opacity: 0.6; stroke-width: 1.5px; }}
  text {{ font-size: 10px; fill: #eee; pointer-events: none; text-shadow: 1px 1px 2px #000; }}
  #info {{
    position: absolute; top: 10px; left: 10px; background: rgba(0,0,0,0.7);
    padding: 12px; border-radius: 8px; max-width: 300px; font-size: 12px;
  }}
  #info h3 {{ margin: 0 0 6px; font-size: 14px; }}
  #legend {{
    position: absolute; bottom: 10px; right: 10px; background: rgba(0,0,0,0.7);
    padding: 10px; border-radius: 8px; font-size: 12px;
  }}
  #language-legend {{
    position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.7);
    padding: 10px; border-radius: 8px; font-size: 12px;
  }}
  #community-legend {{
    position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7);
    padding: 10px; border-radius: 8px; font-size: 12px;
  }}
  #dead-code-legend {{
    position: absolute; bottom: 10px; left: 10px; background: rgba(0,0,0,0.7);
    padding: 10px; border-radius: 8px; font-size: 12px;
  }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
  .legend-box {{ width: 12px; height: 12px; border-radius: 2px; }}
  .community-label {{
    font-size: 11px; font-weight: bold; fill: #fff; text-shadow: 1px 1px 2px #000;
    pointer-events: none;
  }}
  .community-bg {{
    fill-opacity: 0.15; rx: 8; ry: 8;
  }}
</style>
</head>
<body>
<div id="graph"></div>
<div id="info">
  <h3>SCKG Graph</h3>
  <p>Nodes: {len(nodes)} | Edges: {len(edges)}</p>
  <p>Communities: {len(community_centres)}</p>
  <p>Click a node to see details.</p>
</div>
<div id="language-legend">
  <div style="font-weight:bold; margin-bottom:6px;">Language</div>
  {''.join(f'<div class="legend-item"><div class="legend-dot" style="background:{LANGUAGE_COLORS.get(lang, DEFAULT_LANGUAGE_COLOR)}"></div>{lang.capitalize()}</div>' for lang in sorted(active_languages))}
</div>
<div id="legend">
  <div style="font-weight:bold; margin-bottom:6px;">Kind</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ff7f0e"></div>Function</div>
  <div class="legend-item"><div class="legend-dot" style="background:#1f77b4"></div>Class</div>
  <div class="legend-item"><div class="legend-dot" style="background:#2ca02c"></div>Module</div>
</div>
<div id="community-legend">
  <div style="font-weight:bold; margin-bottom:6px;">Community Colors</div>
  {''.join(f'<div class="legend-item"><div class="legend-box" style="background:{c["bg"]};border:1px solid {c["border"]}"></div>{c["label"]}</div>' for c in community_centres.values())}
</div>
{dead_code_legend_html}
<script>
const nodes = {json.dumps(nodes, ensure_ascii=False)};
const links = {json.dumps(edges, ensure_ascii=False)};
const communityCentres = {json.dumps(community_centres, ensure_ascii=False)};
const deadIds = new Set({json.dumps(list(dead_ids))});
const suspiciousIds = new Set({json.dumps(list(suspicious_ids))});
const entryIds = new Set({json.dumps(list(entry_ids))});

const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("#graph").append("svg").attr("width", width).attr("height", height);

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide().radius(d => d.radius + 5));

// Add community force attraction if communities exist
if (Object.keys(communityCentres).length > 0) {{
  simulation.force("communityX", d3.forceX(d => communityCentres[d.community]?.x || width/2).strength(0.05))
            .force("communityY", d3.forceY(d => communityCentres[d.community]?.y || height/2).strength(0.05));
}}

const communityGroups = svg.append("g").attr("class", "community-bgs");
const communityLabels = svg.append("g").attr("class", "community-labels");

const link = svg.append("g")
  .attr("class", "links")
  .selectAll("line")
  .data(links)
  .join("line")
  .attr("class", "link");

const node = svg.append("g")
  .attr("class", "nodes")
  .selectAll("circle")
  .data(nodes)
  .join("circle")
  .attr("class", "node")
  .attr("r", d => d.radius)
  .attr("fill", d => deadIds.has(d.id) ? "{DEAD_FILL}" : d.color)
  .attr("fill-opacity", d => deadIds.has(d.id) ? 0.5 : 1.0)
  .attr("stroke", d => {{
    if (deadIds.has(d.id)) return "{DEAD_STROKE}";
    if (suspiciousIds.has(d.id)) return "{SUSPICIOUS_STROKE}";
    if (entryIds.has(d.id)) return "{ENTRY_STROKE}";
    return "#fff";
  }})
  .attr("stroke-width", d => {{
    if (deadIds.has(d.id)) return 3;
    if (suspiciousIds.has(d.id)) return 2;
    if (entryIds.has(d.id)) return 2;
    return 1.5;
  }})
  .call(d3.drag()
    .on("start", (event, d) => {{ if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }})
    .on("drag", (event, d) => {{ d.fx = event.x; d.fy = event.y; }})
    .on("end", (event, d) => {{ if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }})
  );

const label = svg.append("g")
  .attr("class", "labels")
  .selectAll("text")
  .data(nodes)
  .join("text")
  .text(d => d.name)
  .attr("dx", 12)
  .attr("dy", 4);

node.on("click", (event, d) => {{
  const info = document.getElementById("info");
  let extra = "";
  if (deadIds.has(d.id)) {{
    extra = `<p style="color:#F44336;font-weight:bold;">DEAD CODE — 0 references</p>`;
  }} else if (suspiciousIds.has(d.id)) {{
    extra = `<p style="color:#FFC107;font-weight:bold;">SUSPICIOUS — 1 reference</p>`;
  }} else if (entryIds.has(d.id)) {{
    extra = `<p style="color:#4CAF50;font-weight:bold;">ENTRY POINT</p>`;
  }}
  info.innerHTML = `<h3>${{d.name}}</h3>
    <p><strong>Kind:</strong> ${{d.kind}}</p>
    <p><strong>Language:</strong> ${{d.language || "unknown"}}</p>
    <p><strong>Community:</strong> ${{d.community >= 0 ? (communityCentres[d.community]?.label || "Community " + d.community) : "none"}}</p>
    <p><strong>File:</strong> ${{d.filepath}}</p>
    <p><strong>Line:</strong> ${{d.line}}</p>
    <p><strong>Signature:</strong> <code>${{d.signature || "N/A"}}</code></p>
    <p><strong>Docstring:</strong> ${{d.docstring || "None"}}</p>`
    + extra;
}});

function updateCommunityBounds() {{
  const bounds = {{}};
  for (const d of nodes) {{
    if (d.community < 0) continue;
    if (!bounds[d.community]) bounds[d.community] = {{minX: d.x, maxX: d.x, minY: d.y, maxY: d.y}};
    bounds[d.community].minX = Math.min(bounds[d.community].minX, d.x);
    bounds[d.community].maxX = Math.max(bounds[d.community].maxX, d.x);
    bounds[d.community].minY = Math.min(bounds[d.community].minY, d.y);
    bounds[d.community].maxY = Math.max(bounds[d.community].maxY, d.y);
  }}
  for (const [idx, b] of Object.entries(bounds)) {{
    const pad = 30;
    const bg = communityCentres[idx];
    if (!bg) continue;
    const rect = communityGroups.selectAll(`.comm-bg-${{idx}}`).data([idx]);
    rect.enter().append("rect")
      .attr("class", `comm-bg comm-bg-${{idx}}`)
      .merge(rect)
      .attr("x", b.minX - pad)
      .attr("y", b.minY - pad)
      .attr("width", b.maxX - b.minX + pad * 2)
      .attr("height", b.maxY - b.minY + pad * 2)
      .attr("fill", bg.bg)
      .attr("stroke", bg.border)
      .attr("stroke-width", 1.5)
      .attr("class", "community-bg");
    rect.exit().remove();

    const lbl = communityLabels.selectAll(`.comm-lbl-${{idx}}`).data([idx]);
    lbl.enter().append("text")
      .attr("class", `comm-lbl comm-lbl-${{idx}} community-label`)
      .merge(lbl)
      .attr("x", b.minX - pad + 4)
      .attr("y", b.minY - pad + 14)
      .text(bg.label);
    lbl.exit().remove();
  }}
}}

simulation.on("tick", () => {{
  link
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y);
  node
    .attr("cx", d => d.x)
    .attr("cy", d => d.y);
  label
    .attr("x", d => d.x)
    .attr("y", d => d.y);
  updateCommunityBounds();
}});
</script>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    return out
