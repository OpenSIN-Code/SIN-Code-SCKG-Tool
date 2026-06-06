# src/sckg/html_generator.py

Single-file HTML generator for D3.js force-directed graph visualization.

## What it does
- Takes a JSON graph (nodes + edges + communities) and emits one `.html` file
- Embeds D3.js via CDN (`d3.v7.min.js`) so no build step is required
- Colors nodes by programming language and sizes them by symbol kind (class > function > module)
- Renders **cross-repo edges** as **purple dashed lines** (`#9C27B0`, `stroke-dasharray: 5,5`)
- Clicking a node opens a detail panel (name, kind, file, line, signature, docstring)
- Community bounding boxes are drawn with language-tinted fills and borders
- Optional dead-code report panel is embedded when `report` is provided
  - Dead nodes: red border (`stroke: #F44336`, `stroke-width: 3px`) + red fill at 50% opacity
  - Suspicious nodes: yellow border (`stroke: #FFC107`, `stroke-width: 2px`)
  - Entry points: green border (`stroke: #4CAF50`, `stroke-width: 2px`)
  - Legend adds "Dead Code", "Suspicious (1 ref)", "Entry Point" entries
  - Clicking a dead node shows "DEAD CODE — 0 references" in the info panel

## Why single file
- Users can open the HTML directly in any browser
- No webpack, no React, no dependencies except the D3 CDN

## Edge styling
- Normal edges: solid grey (`#aaa`)
- Cross-repo edges (`cross_repo_call`, `cross_repo_import`): purple dashed (`#9C27B0`, `5,5`)
- Legend includes a "Cross-Repo Call" entry when any cross-repo edges are present

## Files that import / touch it
- `cli.py` — `graph` command calls `generate_html()` after indexing or loading JSON
- `test_cli.py` — asserts the output contains D3.js strings
- `cross_repo.py` — produces the `cross_repo_call` / `cross_repo_import` edges that trigger the purple dashed styling
