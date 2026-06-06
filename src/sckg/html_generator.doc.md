# src/sckg/html_generator.py

Single-file HTML generator for D3.js force-directed graph visualization.

## What it does
- Takes a JSON graph (nodes + edges + communities) and emits one `.html` file
- Embeds D3.js via CDN (`d3.v7.min.js`) so no build step is required
- Colors nodes by community and sizes them by symbol kind (class > function > module)
- Clicking a node opens a detail panel (name, kind, file, line, signature, docstring)

## Why single file
- Users can open the HTML directly in any browser
- No webpack, no React, no dependencies except the D3 CDN

## Files that import / touch it
- `cli.py` — `graph` command calls `generate_html()` after indexing or loading JSON
- `test_cli.py` — asserts the output contains D3.js strings

## Customization
- `community_colors` list can be extended for more communities
- `radius` logic is hardcoded: class=10, function=8, other=6
