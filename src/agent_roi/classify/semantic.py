"""Model-free semantic topic discovery.

Groups sessions that are about the same kind of work, without any LLM or external
service. The pipeline mirrors classic "local embedding + community detection"
setups, but uses lightweight, dependency-free building blocks so it runs anywhere
and costs nothing:

1. Each session's combined summary is tokenized and turned into a TF-IDF vector
   (a cheap, deterministic stand-in for an embedding).
2. Sessions whose vectors are close enough (cosine similarity) are linked, and
   the connected components of that graph become topic clusters — the same idea
   as graph community detection, kept simple with union-find.
3. Each cluster is labeled from its most distinctive shared terms.

Sessions with no meaningful text fall back to ``uncategorized`` rather than being
force-fit into a topic.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict

from agent_roi.classify.base import UNCATEGORIZED, Classifier, SessionDoc

# Generic words that carry no topic signal in coding-assistant chatter. Kept
# short and intentionally conservative — real topic terms should survive.
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "if",
        "then",
        "else",
        "for",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "with",
        "from",
        "into",
        "out",
        "up",
        "down",
        "so",
        "not",
        "no",
        "yes",
        "can",
        "will",
        "would",
        "should",
        "could",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "i",
        "you",
        "we",
        "they",
        "he",
        "she",
        "me",
        "my",
        "your",
        "our",
        "please",
        "help",
        "want",
        "need",
        "make",
        "let",
        "lets",
        "use",
        "using",
        "add",
        "added",
        "adding",
        "fix",
        "fixed",
        "fixing",
        "update",
        "updated",
        "change",
        "changed",
        "create",
        "created",
        "new",
        "code",
        "file",
        "files",
        "function",
        "error",
        "errors",
        "issue",
        "issues",
        "problem",
        "try",
        "trying",
        "now",
        "also",
        "like",
        "just",
        "get",
        "got",
        "set",
        "run",
        "running",
        "here",
        "there",
        "what",
        "how",
        "why",
        "when",
        "which",
        "user",
        "assistant",
        "message",
        "okay",
        "ok",
        "thanks",
        "thank",
    }
)

_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]{2,}")


class SemanticClassifier(Classifier):
    """Discover topics by clustering semantically similar sessions."""

    def __init__(
        self,
        similarity_threshold: float = 0.18,
        label_terms: int = 3,
    ) -> None:
        # Cosine similarity at/above which two sessions are treated as the same
        # topic. Higher = stricter (more, smaller topics).
        self.similarity_threshold = similarity_threshold
        # How many distinctive terms make up a generated topic label.
        self.label_terms = label_terms

    def label_sessions(self, sessions: list[SessionDoc]) -> dict[str, str]:
        if not sessions:
            return {}

        token_lists = [_tokenize(s.summary) for s in sessions]
        vectors = _tfidf_vectors(token_lists)

        clusters = _cluster(vectors, self.similarity_threshold)

        labels: dict[str, str] = {}
        used: dict[str, int] = {}
        for members in clusters:
            label = _label_for(members, vectors, self.label_terms)
            # Disambiguate identical labels from distinct clusters.
            if label != UNCATEGORIZED and label in used:
                used[label] += 1
                label = f"{label} {used[label]}"
            else:
                used.setdefault(label, 1)
            for idx in members:
                labels[sessions[idx].session_id] = label
        return labels


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def _tfidf_vectors(token_lists: list[list[str]]) -> list[dict[str, float]]:
    """Build L2-normalized TF-IDF vectors so dot product == cosine similarity."""
    n_docs = len(token_lists)
    doc_freq: dict[str, int] = defaultdict(int)
    for tokens in token_lists:
        for term in set(tokens):
            doc_freq[term] += 1

    idf = {term: math.log((n_docs + 1) / (df + 1)) + 1.0 for term, df in doc_freq.items()}

    vectors: list[dict[str, float]] = []
    for tokens in token_lists:
        term_freq: dict[str, int] = defaultdict(int)
        for term in tokens:
            term_freq[term] += 1
        vec = {term: tf * idf[term] for term, tf in term_freq.items()}
        norm = math.sqrt(sum(w * w for w in vec.values()))
        if norm > 0:
            vec = {term: w / norm for term, w in vec.items()}
        vectors.append(vec)
    return vectors


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    # Vectors are unit-normalized, so cosine is just the dot product. Iterate the
    # smaller vector for speed.
    if len(a) > len(b):
        a, b = b, a
    return sum(weight * b.get(term, 0.0) for term, weight in a.items())


def _cluster(vectors: list[dict[str, float]], threshold: float) -> list[list[int]]:
    """Greedy centroid clustering: assign each session to the cluster whose mean
    vector it is most similar to (above ``threshold``), else start a new cluster.

    Centroid linkage resists the "chaining" failure of single-linkage/connected
    components, where one borderline pair can merge unrelated work into a single
    giant topic. Empty vectors (no meaningful tokens) are returned as their own
    singletons so they can be labeled ``uncategorized`` downstream.
    """
    centroids: list[dict[str, float]] = []
    sizes: list[int] = []
    members: list[list[int]] = []
    empties: list[list[int]] = []

    for i, vec in enumerate(vectors):
        if not vec:
            empties.append([i])
            continue

        best, best_sim = -1, threshold
        for c, centroid in enumerate(centroids):
            sim = _cosine(vec, centroid)
            if sim >= best_sim:
                best, best_sim = c, sim

        if best == -1:
            centroids.append(dict(vec))
            sizes.append(1)
            members.append([i])
        else:
            members[best].append(i)
            sizes[best] += 1
            centroids[best] = _merge_centroid(centroids[best], sizes[best], vec)

    return members + empties


def _merge_centroid(
    centroid: dict[str, float], size: int, vec: dict[str, float]
) -> dict[str, float]:
    """Fold ``vec`` into a centroid as a running mean, then re-normalize."""
    merged = dict(centroid)
    weight = 1.0 / size
    for term, w in centroid.items():
        merged[term] = w * (size - 1) * weight
    for term, w in vec.items():
        merged[term] = merged.get(term, 0.0) + w * weight
    norm = math.sqrt(sum(x * x for x in merged.values()))
    if norm > 0:
        merged = {term: x / norm for term, x in merged.items()}
    return merged


def _label_for(
    members: list[int],
    vectors: list[dict[str, float]],
    max_terms: int,
) -> str:
    """Name a cluster from the highest-weighted terms shared by its sessions."""
    scores: dict[str, float] = defaultdict(float)
    for idx in members:
        for term, weight in vectors[idx].items():
            scores[term] += weight

    if not scores:
        return UNCATEGORIZED

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    # Singletons get a slightly shorter label; multi-session topics a bit longer.
    n_terms = max(1, max_terms if len(members) > 1 else max_terms - 1)
    top = [term for term, _ in ranked[:n_terms]]
    return " ".join(top) if top else UNCATEGORIZED
