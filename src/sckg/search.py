"""N-gram based semantic code search for SCKG knowledge graphs.

Provides fuzzy search over code symbols using n-grams extracted from
function/class names, docstrings, parameters, and call patterns.

Docs: search.doc.md
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from math import log
from typing import Any

from sckg.graph import KnowledgeGraph


# ── Tokenization ────────────────────────────────────────────────────────────────

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
    "to", "was", "were", "will", "with", "or", "if", "then", "else",
    "this", "that", "these", "those", "but", "not", "you", "your",
    "we", "our", "us", "they", "them", "their", "i", "my", "me",
}

def split_identifier(name: str) -> list[str]:
    """Split camelCase, snake_case, PascalCase into tokens."""
    # snake_case
    if "_" in name:
        parts = name.split("_")
    # camelCase / PascalCase - split on lowercase->uppercase and uppercase->uppercase+lowercase transitions
    else:
        # Insert space before uppercase letters that follow lowercase or are followed by lowercase
        parts = re.sub(r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", name).split()
    return [p.lower() for p in parts if p and p.lower() not in STOPWORDS]


def tokenize(text: str) -> list[str]:
    """Tokenize natural language text (docstrings, queries)."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


# ── N-Gram Extraction ──────────────────────────────────────────────────────────

@dataclass
class NgramEntry:
    """An n-gram entry with its weight."""
    ngram: str
    weight: float

@dataclass
class NgramIndex:
    """Inverted index: ngram -> list of (node_id, weight)."""
    index: dict[str, list[tuple[str, float]]]
    node_weights: dict[str, dict[str, float]]  # node_id -> {ngram: weight}

    @classmethod
    def empty(cls) -> "NgramIndex":
        return cls(index=defaultdict(list), node_weights=defaultdict(dict))


def extract_ngrams(text: str, max_n: int = 3) -> list[str]:
    """Extract n-grams (1 to max_n) from tokenized text."""
    tokens = tokenize(text)
    ngrams = []
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            ngrams.append(" ".join(tokens[i:i+n]))
    return ngrams


def build_ngram_index(graph: KnowledgeGraph, ngram_sizes: list[int] = [1, 2, 3]) -> NgramIndex:
    """Build inverted n-gram index from knowledge graph nodes."""
    idx = NgramIndex.empty()

    for nid, node in graph.nodes.items():
        ngram_weights: dict[str, float] = defaultdict(float)

        # Function/class name tokens (highest weight)
        name = node.get("name", "")
        name_tokens = split_identifier(name)
        for n in ngram_sizes:
            for i in range(len(name_tokens) - n + 1):
                ngram = " ".join(name_tokens[i:i+n])
                ngram_weights[ngram] += 3.0

        # Docstring tokens
        docstring = node.get("docstring", "") or ""
        if docstring:
            doc_ngrams = extract_ngrams(docstring, max(ngram_sizes))
            for ng in doc_ngrams:
                ngram_weights[ng] += 1.5

        # Parameter names (if available in signature)
        signature = node.get("signature", "") or ""
        if signature:
            # Extract param names from signature
            param_tokens = split_identifier(signature.replace(")", "").replace("(", " "))
            for n in ngram_sizes:
                for i in range(len(param_tokens) - n + 1):
                    ngram = " ".join(param_tokens[i:i+n])
                    ngram_weights[ngram] += 1.0

        # Called function names (from outgoing edges)
        for edge in graph.edges:
            if edge.get("source") == nid and edge.get("relation") == "calls":
                target_name = graph.nodes.get(edge.get("target", ""), {}).get("name", "")
                if target_name:
                    call_tokens = split_identifier(target_name)
                    for n in ngram_sizes:
                        for i in range(len(call_tokens) - n + 1):
                            ngram = " ".join(call_tokens[i:i+n])
                            ngram_weights[ngram] += 1.0

        # Add to index
        for ngram, weight in ngram_weights.items():
            idx.index[ngram].append((nid, weight))
            idx.node_weights[nid][ngram] = weight

    return idx


# ── BM25 Scoring ────────────────────────────────────────────────────────────────

def bm25_score(
    query_ngrams: list[str],
    index: NgramIndex,
    nid: str,
    avg_doc_len: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    """Compute BM25 score for a node against query n-grams."""
    score = 0.0
    node_ngrams = index.node_weights.get(nid, {})
    doc_len = len(node_ngrams)

    for q_ngram in query_ngrams:
        postings = index.index.get(q_ngram, [])
        df = len(postings)  # document frequency
        if df == 0:
            continue

        # IDF component
        idf = log((len(index.node_weights) - df + 0.5) / (df + 0.5) + 1.0)

        # TF component (weight in this document)
        tf = node_ngrams.get(q_ngram, 0.0)

        # BM25 formula
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))

    return score


@dataclass
class SearchResult:
    """A search result with relevance score and context."""
    node: dict[str, Any]
    score: float
    matched_ngrams: list[str]
    snippet: str


def search(query: str, graph: KnowledgeGraph, index: NgramIndex | None = None, top_k: int = 10) -> list[SearchResult]:
    """Search the graph for symbols matching the query string."""
    if not graph.nodes:
        return []

    if index is None:
        index = build_ngram_index(graph)

    query_ngrams = extract_ngrams(query, max_n=3)
    if not query_ngrams:
        return []

    # Compute average document length
    avg_doc_len = sum(len(w) for w in index.node_weights.values()) / max(1, len(index.node_weights))

    # Score all nodes
    scores: list[tuple[str, float, list[str]]] = []
    for nid in graph.nodes:
        score = bm25_score(query_ngrams, index, nid, avg_doc_len)
        if score > 0:
            # Find which n-grams matched
            matched = [ng for ng in query_ngrams if ng in index.node_weights.get(nid, {})]
            scores.append((nid, score, matched))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Build results
    results: list[SearchResult] = []
    for nid, score, matched in scores[:top_k]:
        node = graph.nodes[nid]
        snippet = _make_snippet(node)
        results.append(SearchResult(
            node=node,
            score=score,
            matched_ngrams=matched,
            snippet=snippet,
        ))

    return results


def _make_snippet(node: dict[str, Any]) -> str:
    """Create a short snippet for display."""
    parts = []
    if node.get("signature"):
        parts.append(node["signature"])
    if node.get("docstring"):
        ds = node["docstring"].strip().split("\n")[0]
        if len(ds) > 150:
            ds = ds[:147] + "..."
        parts.append(ds)
    if not parts:
        parts.append(f"{node.get('kind', 'symbol')}: {node.get('name', '?')}")
    return " | ".join(parts)


# ── Pattern Search (simpler, wildcard-based) ──────────────────────────────────

def search_pattern(pattern: str, graph: KnowledgeGraph, top_k: int = 10) -> list[SearchResult]:
    """Search by wildcard pattern (e.g., 'handle_*', '*_error')."""
    import fnmatch
    regex = fnmatch.translate(pattern)
    prog = re.compile(regex)

    results: list[SearchResult] = []
    for nid, node in graph.nodes.items():
        name = node.get("name", "")
        if prog.match(name):
            results.append(SearchResult(
                node=node,
                score=1.0,
                matched_ngrams=[pattern],
                snippet=_make_snippet(node),
            ))

    results.sort(key=lambda r: len(r.node.get("name", "")), reverse=True)
    return results[:top_k]


# ── Public API ─────────────────────────────────────────────────────────────────

__all__ = [
    "NgramIndex",
    "build_ngram_index",
    "SearchResult",
    "search",
    "search_pattern",
    "split_identifier",
    "tokenize",
]