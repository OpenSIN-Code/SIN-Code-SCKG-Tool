"""Architecture Decision Record (ADR) generation from SCKG knowledge graphs.

Analyzes communities, cross-repo edges, hot paths, and dead code to
generate architectural decision records documenting significant findings.

Docs: adr.doc.md
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sckg.graph import KnowledgeGraph
from sckg.communities import Community
from sckg.dead_code import find_dead_code
from sckg.hotpaths import compute_hot_paths


@dataclass
class ADR:
    """An Architecture Decision Record."""
    id: str
    title: str
    status: str
    date: str
    decision: str
    context: str
    consequences: str
    alternatives: str
    tags: list[str]


def generate_adrs(graph: KnowledgeGraph, output_dir: Path | None = None) -> list[ADR]:
    """Generate ADRs from significant findings in the graph."""
    adrs: list[ADR] = []
    adr_counter = 0

    def add_adr(title: str, decision: str, context: str, consequences: str,
                alternatives: str, tags: list[str], status: str = "proposed") -> ADR:
        nonlocal adr_counter
        adr_counter += 1
        adr = ADR(
            id=f"ADR-{adr_counter:03d}",
            title=title,
            status=status,
            date=datetime.now().strftime("%Y-%m-%d"),
            decision=decision,
            context=context,
            consequences=consequences,
            alternatives=alternatives,
            tags=tags,
        )
        adrs.append(adr)
        return adr

    # 1. Cross-repo edges (subprocess calls, imports)
    cross_edges = graph.get_cross_repo_edges()
    if cross_edges:
        # Group by source repo
        by_source: dict[str, list] = {}
        for edge in cross_edges:
            src_repo = graph.nodes.get(edge["source"], {}).get("repo", "unknown")
            by_source.setdefault(src_repo, []).append(edge)

        for src_repo, edges in by_source.items():
            targets = set()
            for e in edges:
                tgt_repo = graph.nodes.get(e["target"], {}).get("repo", "unknown")
                targets.add(tgt_repo)

            add_adr(
                title=f"Cross-Repository Calls from {src_repo}",
                decision=f"{src_repo} calls {len(targets)} other repositories via subprocess/imports: {', '.join(sorted(targets))}",
                context=f"Found {len(edges)} cross-repo edges originating from {src_repo}. These represent tight runtime coupling between repositories.",
                consequences="Changes in target repositories may break {src_repo} at runtime. Deployment order matters. Testing requires all target repos available.",
                alternatives="Consider replacing subprocess calls with HTTP/gRPC APIs. Use message queues for async communication. Define clear API contracts.",
                tags=["cross-repo", "coupling", "subprocess", src_repo],
            )

    # 2. Mixed-language communities
    lang_communities = graph.detect_communities_by_language()
    mixed_communities = []
    for lang, comms in lang_communities.items():
        for comm in comms:
            if len(comm.languages) > 1:
                mixed_communities.append(comm)

    if mixed_communities:
        for comm in mixed_communities:
            langs = ", ".join(f"{k}={v}" for k, v in comm.languages.items())
            add_adr(
                title=f"Mixed-Language Community: {langs}",
                decision=f"Community #{comm.id} contains {comm.size} nodes across multiple languages: {langs}",
                context=f"Community detection found a cluster spanning {len(comm.languages)} languages with density {comm.density:.2f}. This indicates polyglot components that interact closely.",
                consequences="Cross-language refactoring is risky. Build/test pipelines must handle multiple languages. Debugging spans language boundaries.",
                alternatives="Consider isolating language-specific components behind well-defined interfaces. Use language-agnostic protocols (protobuf, JSON).",
                tags=["mixed-language", "community", "polyglot"],
            )

    # 3. Hot paths spanning repositories
    hot_report = compute_hot_paths(graph, top_n=20, weight="in_degree")
    cross_repo_hot = []
    for hn in hot_report.hot_nodes:
        node = hn.node
        node_repo = node.get("repo", "")
        # Check if this hot node has cross-repo callers
        for edge in graph.edges:
            if edge["target"] == node["id"]:
                src_repo = graph.nodes.get(edge["source"], {}).get("repo", "")
                if src_repo and src_repo != node_repo:
                    cross_repo_hot.append(hn)
                    break

    if cross_repo_hot:
        add_adr(
            title="Hot Paths with Cross-Repository Dependencies",
            decision=f"{len(cross_repo_hot)} hot path nodes are called from other repositories",
            context="These are the most frequently called functions in the codebase, but they have incoming calls from different repositories. This creates critical cross-repo dependencies.",
            consequences="Changes to these hot paths affect multiple repositories. High risk for breaking changes. Performance regressions cascade.",
            alternatives="Stabilize APIs for cross-repo hot paths. Add integration tests. Consider versioning or backward compatibility layers.",
            tags=["hot-paths", "cross-repo", "critical-path"],
        )

    # 4. Dead code in public APIs
    dead_report = find_dead_code(graph)
    public_dead = []
    for node in dead_report.dead_nodes:
        # Check if node is exported (no parent, or in __init__.py, or public naming)
        name = node.get("name", "")
        filepath = node.get("filepath", "")
        if not node.get("parent") or "__init__" in filepath or name.startswith("export_"):
            public_dead.append(node)

    if public_dead:
        add_adr(
            title="Dead Code in Public API Surface",
            decision=f"{len(public_dead)} dead code nodes found in public API locations",
            context="These functions/classes have no incoming calls but are in public locations (__init__.py, no parent, or export_ prefix). They may be intended as public APIs but are unused.",
            consequences="Unused public APIs increase maintenance burden and attack surface. May indicate incomplete features or deprecated code not cleaned up.",
            alternatives="Remove if truly unused. If intended for external use, add documentation and example usage. Consider deprecation cycle.",
            tags=["dead-code", "public-api", "cleanup"],
        )

    # 5. Circular dependencies between repos
    circular_repos = find_circular_repo_dependencies(graph)
    if circular_repos:
        for cycle in circular_repos:
            add_adr(
                title=f"Circular Repository Dependency: {' -> '.join(cycle)}",
                decision=f"Repositories form a circular dependency: {' -> '.join(cycle)}",
                context="Cross-repo edge analysis detected a cycle in repository dependencies. This creates deployment and testing deadlocks.",
                consequences="Cannot deploy independently. Build order undefined. Changes require coordinated rollout.",
                alternatives="Break cycle by introducing shared library, event-driven architecture, or reversing one dependency direction.",
                tags=["circular-dependency", "cross-repo", "architecture"],
            )

    # Write to files if output_dir provided
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        for adr in adrs:
            content = render_adr_markdown(adr)
            filename = f"{adr.id.lower()}-{adr.title.lower().replace(' ', '-')}.md"
            (output_dir / filename).write_text(content, encoding="utf-8")

    return adrs


def find_circular_repo_dependencies(graph: KnowledgeGraph) -> list[list[str]]:
    """Find circular dependencies between repositories."""
    # Build repo-level adjacency
    repos = graph.get_repos()
    repo_adj: dict[str, set[str]] = {r: set() for r in repos}

    for edge in graph.edges:
        src_repo = graph.nodes.get(edge["source"], {}).get("repo", "")
        tgt_repo = graph.nodes.get(edge["target"], {}).get("repo", "")
        if src_repo and tgt_repo and src_repo != tgt_repo:
            repo_adj[src_repo].add(tgt_repo)

    # Find cycles using DFS
    cycles = []
    visited = set()
    path = []

    def dfs(node: str):
        visited.add(node)
        path.append(node)
        for neighbor in repo_adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in path:
                # Found cycle
                idx = path.index(neighbor)
                cycle = path[idx:] + [neighbor]
                if cycle not in cycles:
                    cycles.append(cycle)
        path.pop()

    for repo in repos:
        if repo not in visited:
            dfs(repo)

    return cycles


def render_adr_markdown(adr: ADR) -> str:
    """Render ADR as Markdown with frontmatter."""
    tags_str = ", ".join(f'"{t}"' for t in adr.tags)
    return f"""---
id: {adr.id}
title: {adr.title}
status: {adr.status}
date: {adr.date}
tags: [{tags_str}]
---

# {adr.id}: {adr.title}

## Status
{adr.status}

## Context
{adr.context}

## Decision
{adr.decision}

## Consequences
{adr.consequences}

## Alternatives
{adr.alternatives}

## Tags
{', '.join(adr.tags)}
"""