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


def generate_html(graph_data: dict[str, Any], output_path: str | Path) -> Path:
    """Write a single-file HTML with embedded D3.js force graph.

    Nodes are colored by programming language. A language legend is rendered
    in the top-right corner. Unsupported languages fall back to community
    colors (if available) or grey.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    communities = graph_data.get("communities", {})

    # Assign community colors as fallback
    community_colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
    ]
    comm_to_color = {}
    for i, comm in enumerate(set(communities.values())):
        comm_to_color[comm] = community_colors[i % len(community_colors)]

    # Determine which languages are present so the legend only shows active ones
    active_languages = {n.get("language") for n in nodes if n.get("language")}

    for n in nodes:
        lang = n.get("language")
        n["color"] = LANGUAGE_COLORS.get(lang, comm_to_color.get(communities.get(n["id"], "default"), DEFAULT_LANGUAGE_COLOR))
        n["radius"] = 8 if n.get("kind") == "function" else 10 if n.get("kind") == "class" else 6

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
  .legend-item {{ display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; }}
</style>
</head>
<body>
<div id="graph"></div>
<div id="info">
  <h3>SCKG Graph</h3>
  <p>Nodes: {len(nodes)} | Edges: {len(edges)}</p>
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
<script>
const nodes = {json.dumps(nodes, ensure_ascii=False)};
const links = {json.dumps(edges, ensure_ascii=False)};

const width = window.innerWidth;
const height = window.innerHeight;

const svg = d3.select("#graph").append("svg").attr("width", width).attr("height", height);

const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2))
  .force("collide", d3.forceCollide().radius(d => d.radius + 5));

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
  .attr("fill", d => d.color)
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
  info.innerHTML = `<h3>${{d.name}}</h3>
    <p><strong>Kind:</strong> ${{d.kind}}</p>
    <p><strong>Language:</strong> ${{d.language || "unknown"}}</p>
    <p><strong>File:</strong> ${{d.filepath}}</p>
    <p><strong>Line:</strong> ${{d.line}}</p>
    <p><strong>Signature:</strong> <code>${{d.signature || "N/A"}}</code></p>
    <p><strong>Docstring:</strong> ${{d.docstring || "None"}}</p>`;
}});

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
}});
</script>
</body>
</html>
"""

    out.write_text(html, encoding="utf-8")
    return out
