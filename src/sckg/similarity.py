"""Code similarity search using AST structural features for SCKG.

Finds structurally similar functions/classes across the codebase using
call graph signatures, control flow patterns, and type signatures.

Docs: similarity.doc.md
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import sqrt
from typing import Any

from sckg.graph import KnowledgeGraph


@dataclass
class SimilarityResult:
    """A similarity search result."""
    node: dict[str, Any]
    score: float
    method: str
    matched_features: list[str]


def extract_call_signature(node: dict[str, Any], graph: KnowledgeGraph) -> set[str]:
    """Extract the set of functions called by this node."""
    calls = set()
    nid = node.get("id", "")
    for edge in graph.edges:
        if edge.get("source") == nid and edge.get("relation") == "calls":
            target = graph.nodes.get(edge.get("target", ""), {})
            if target:
                calls.add(target.get("name", ""))
    return calls


def extract_control_flow_features(node: dict[str, Any]) -> dict[str, int]:
    """Extract control flow features from node's AST (simplified from signature/docstring)."""
    features = {}
    signature = node.get("signature", "")
    docstring = node.get("docstring", "") or ""
    text = (signature + " " + docstring).lower()

    # Count control flow keywords
    for kw in ["if", "else", "elif", "for", "while", "try", "except", "finally", "with", "return", "yield", "await"]:
        features[kw] = text.count(kw)

    # Nesting depth approximation (count of opening braces/indentation in signature)
    features["nesting"] = signature.count("(") + signature.count("[")
    return features


def extract_type_signature(node: dict[str, Any]) -> dict[str, int]:
    """Extract type signature features from function signature."""
    features = {}
    signature = node.get("signature", "")
    # Count type hints
    for t in ["str", "int", "float", "bool", "list", "dict", "set", "tuple", "optional", "any", "none"]:
        features[t] = signature.lower().count(t)
    return features


def extract_ast_structure_features(node: dict[str, Any], graph: KnowledgeGraph) -> dict[str, Any]:
    """Extract combined structural features for a node."""
    return {
        "calls": extract_call_signature(node, graph),
        "control_flow": extract_control_flow_features(node),
        "types": extract_type_signature(node),
        "kind": node.get("kind", ""),
        "language": node.get("language", ""),
    }


def jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not set1 and not set2:
        return 1.0
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union


def cosine_similarity(vec1: dict[str, float], vec2: dict[str, float]) -> float:
    """Compute cosine similarity between two feature vectors."""
    all_keys = set(vec1.keys()) | set(vec2.keys())
    if not all_keys:
        return 1.0

    dot = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in all_keys)
    norm1 = sqrt(sum(v * v for v in vec1.values()))
    norm2 = sqrt(sum(v * v for v in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def ast_similarity(features1: dict[str, Any], features2: dict[str, Any]) -> float:
    """Compute combined AST structural similarity."""
    scores = []

    # Call signature similarity (Jaccard)
    calls1 = features1.get("calls", set())
    calls2 = features2.get("calls", set())
    scores.append(jaccard_similarity(calls1, calls2))

    # Control flow similarity (cosine)
    cf1 = features1.get("control_flow", {})
    cf2 = features2.get("control_flow", {})
    scores.append(cosine_similarity(cf1, cf2))

    # Type signature similarity (cosine)
    types1 = features1.get("types", {})
    types2 = features2.get("types", {})
    scores.append(cosine_similarity(types1, types2))

    # Kind/language match bonus
    if features1.get("kind") == features2.get("kind"):
        scores.append(1.0)
    else:
        scores.append(0.0)

    if features1.get("language") == features2.get("language"):
        scores.append(1.0)
    else:
        scores.append(0.0)

    # Weighted average
    weights = [0.4, 0.2, 0.2, 0.1, 0.1]
    return sum(s * w for s, w in zip(scores, weights)) / sum(weights)


def find_similar(
    node_id: str,
    graph: KnowledgeGraph,
    top_k: int = 10,
    method: str = "jaccard",
) -> list[SimilarityResult]:
    """Find nodes similar to the given node."""
    target_node = graph.nodes.get(node_id)
    if not target_node:
        return []

    target_features = extract_ast_structure_features(target_node, graph)

    results = []
    for nid, node in graph.nodes.items():
        if nid == node_id:
            continue

        # Skip different kinds unless same language
        if node.get("kind") != target_node.get("kind") and node.get("language") != target_node.get("language"):
            continue

        node_features = extract_ast_structure_features(node, graph)

        if method == "jaccard":
            # Only call signature
            score = jaccard_similarity(target_features["calls"], node_features["calls"])
            matched = list(target_features["calls"] & node_features["calls"])
        elif method == "cosine":
            # Control flow + types
            score = (cosine_similarity(target_features["control_flow"], node_features["control_flow"]) +
                     cosine_similarity(target_features["types"], node_features["types"])) / 2
            matched = [k for k in target_features["control_flow"] if k in node_features["control_flow"]]
            matched += [k for k in target_features["types"] if k in node_features["types"]]
        elif method == "ast":
            # Full structural similarity
            score = ast_similarity(target_features, node_features)
            # Find matched features
            matched = list(target_features["calls"] & node_features["calls"])
            matched += [k for k in target_features["control_flow"] if k in node_features["control_flow"]]
            matched += [k for k in target_features["types"] if k in node_features["types"]]
        else:
            raise ValueError(f"Unknown method: {method}")

        if score > 0:
            results.append(SimilarityResult(
                node=node,
                score=score,
                method=method,
                matched_features=matched,
            ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_k]