"""Hybrid code search combining n-gram (BM25) and AST structural similarity.

Provides search results that blend textual relevance with code structure
similarity for better code discovery.

Docs: hybrid_search.doc.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sckg.graph import KnowledgeGraph
from sckg.search import NgramIndex, SearchResult as NgramResult, build_ngram_index, search as ngram_search
from sckg.similarity import find_similar


@dataclass
class HybridResult:
    """A hybrid search result combining BM25 and structural similarity."""
    node: dict[str, Any]
    score: float
    ngram_score: float
    similarity_score: float
    matched_ngrams: list[str]
    matched_features: list[str]


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize scores to [0, 1] range using min-max normalization."""
    if not scores:
        return {}
    min_s = min(scores.values())
    max_s = max(scores.values())
    if max_s == min_s:
        return {k: 1.0 for k in scores}
    return {k: (v - min_s) / (max_s - min_s) for k, v in scores.items()}


def hybrid_search(
    query: str,
    graph: KnowledgeGraph,
    ngram_index: NgramIndex | None = None,
    top_k: int = 10,
    alpha: float = 0.5,
) -> list[HybridResult]:
    """Hybrid search combining BM25 (n-gram) and AST structural similarity.

    Args:
        query: Search query string
        graph: KnowledgeGraph to search
        ngram_index: Pre-built n-gram index (built if None)
        top_k: Number of results to return
        alpha: Weight for n-gram score (0.0-1.0). 1.0 = pure n-gram, 0.0 = pure similarity.

    Returns:
        List of HybridResult sorted by combined score descending.
    """
    if not graph.nodes:
        return []

    if ngram_index is None:
        ngram_index = build_ngram_index(graph)

    # 1. N-gram (BM25) search
    ngram_results = ngram_search(query, graph, ngram_index, top_k=top_k * 2)
    ngram_scores: dict[str, tuple[float, list[str]]] = {}
    for r in ngram_results:
        nid = r.node.get("id", "")
        ngram_scores[nid] = (r.score, r.matched_ngrams)

    # 2. For top n-gram result, find similar nodes (structural)
    similarity_scores: dict[str, tuple[float, list[str]]] = {}
    if ngram_results:
        top_ngram = ngram_results[0]
        top_nid = top_ngram.node.get("id", "")
        similar = find_similar(top_nid, graph, top_k=top_k * 2, method="ast")
        for s in similar:
            nid = s.node.get("id", "")
            similarity_scores[nid] = (s.score, s.matched_features)

    # 3. Normalize scores to [0, 1]
    norm_ngram = normalize_scores({k: v[0] for k, v in ngram_scores.items()})
    norm_sim = normalize_scores({k: v[0] for k, v in similarity_scores.items()})

    # 4. Combine: score = alpha * ngram + (1-alpha) * similarity
    all_node_ids = set(norm_ngram.keys()) | set(norm_sim.keys())
    combined: dict[str, dict[str, Any]] = {}

    for nid in all_node_ids:
        ng = norm_ngram.get(nid, 0.0)
        sim = norm_sim.get(nid, 0.0)
        combined[nid] = {
            "score": alpha * ng + (1 - alpha) * sim,
            "ngram_score": ng,
            "sim_score": sim,
            "matched_ngrams": ngram_scores.get(nid, (0.0, []))[1],
            "matched_features": similarity_scores.get(nid, (0.0, []))[1],
        }

    # 5. Sort and build results
    sorted_results = sorted(combined.items(), key=lambda x: x[1]["score"], reverse=True)

    results: list[HybridResult] = []
    for nid, data in sorted_results[:top_k]:
        if data["score"] <= 0:
            continue
        results.append(HybridResult(
            node=graph.nodes[nid],
            score=data["score"],
            ngram_score=data["ngram_score"],
            similarity_score=data["sim_score"],
            matched_ngrams=data["matched_ngrams"],
            matched_features=data["matched_features"],
        ))

    return results