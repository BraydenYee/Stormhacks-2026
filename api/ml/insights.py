"""Embedding-based insights: weak-spot clustering and vocab review scoring."""

from collections import Counter

import numpy as np
from sklearn.cluster import KMeans


def _normalize(x: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(x, axis=1, keepdims=True)
    return x / np.where(norms == 0, 1, norms)


def cluster_mistakes(mistakes: list[dict], max_clusters: int = 5) -> list[dict]:
    """Group a learner's mistakes into recurring weak spots.

    `mistakes` items need "embedding", "category", "original", "corrected".
    KMeans on L2-normalized vectors approximates cosine clustering.
    Returns clusters sorted by size, each with representative examples.
    """
    items = [m for m in mistakes if m.get("embedding") is not None]
    if not items:
        return []
    X = _normalize(np.asarray([m["embedding"] for m in items], dtype=float))
    k = max(1, min(max_clusters, len(items) // 3))
    labels = np.zeros(len(items), dtype=int) if k == 1 else KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(X)

    clusters = []
    for c in range(k):
        idx = np.where(labels == c)[0]
        if len(idx) == 0:
            continue
        centroid = X[idx].mean(axis=0)
        # Most central examples first: they best represent the cluster.
        order = idx[np.argsort(-(X[idx] @ centroid))]
        members = [items[i] for i in order]
        clusters.append(
            {
                "size": len(idx),
                "category": Counter(m["category"] for m in members).most_common(1)[0][0],
                "examples": [{"original": m["original"], "corrected": m["corrected"]} for m in members[:3]],
            }
        )
    return sorted(clusters, key=lambda c: -c["size"])


def vocab_review_score(times_heard: int, times_used: int, times_misused: int) -> float:
    """Higher = more worth reviewing. Misuse dominates; heard-but-never-used is next."""
    misuse_rate = times_misused / max(times_used, 1)
    passive_only = 1.0 if times_heard > 0 and times_used == 0 else 0.0
    return round(2.0 * misuse_rate + 0.5 * min(times_misused, 4) + passive_only, 3)
