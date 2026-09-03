"""BM25 ranking over the mesh catalogue, with fuzzy query tokens.

Fields are weighted (a name hit beats a category hit) and every query token is
expanded over the corpus vocabulary before scoring, so a one-letter typo
(``anvel`` -> ``anvil``) still finds its asset and a run-together compound
(``woodenchair``) matches on its leading word (``wooden``). Standard library only.
"""

from __future__ import annotations

import math
import re

FIELD_WEIGHTS = {"name": 3.0, "category": 2.0, "tags": 1.5, "description": 1.0}

_K1 = 1.5
_B = 0.75
_MIN_FUZZY_LEN = 3
_EDIT_WEIGHT = 0.8
_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenise(text: str) -> list[str]:
    """Lowercase alphanumeric runs of a string, in order."""
    return _TOKEN_RE.findall(text.lower())


def entry_fields(entry: dict) -> dict[str, list[str]]:
    """Tokenised searchable fields of one catalogue entry.

    The slug joins the name field because it carries the same words with the
    hyphens that make them tokenise well (``sports-car-01``).

    Args:
        entry: Catalogue entry.

    Returns:
        dict[str, list[str]]: Field name to token list, keyed by FIELD_WEIGHTS.
    """
    return {
        "name": tokenise(f"{entry.get('name', '')} {entry.get('slug', '')}"),
        "category": tokenise(" ".join(entry.get("categories") or [entry.get("category", "")])),
        "tags": tokenise(" ".join(entry.get("tags") or [])),
        "description": tokenise(entry.get("description") or ""),
    }


def _within_one_edit(a: str, b: str) -> bool:
    """Whether two strings are at most one insertion, deletion or substitution apart."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    for i, (ca, cb) in enumerate(zip(a, b)):
        if ca != cb:
            return a[i + 1 :] == b[i + 1 :] if len(a) == len(b) else a[i:] == b[i + 1 :]
    return True


def _expand(word: str, vocabulary: list[str]) -> dict[str, float]:
    """Vocabulary tokens matching one query token, each with a confidence weight.

    Args:
        word: Query token.
        vocabulary: Every token present in the corpus.

    Returns:
        dict[str, float]: Matching token to weight - 1.0 exact, the length ratio
        for a prefix either way, and 0.8 for a single-edit neighbour.
    """
    matches = {}
    for candidate in vocabulary:
        if candidate == word:
            matches[candidate] = 1.0
        elif len(word) < _MIN_FUZZY_LEN or len(candidate) < _MIN_FUZZY_LEN:
            continue
        elif candidate.startswith(word) or word.startswith(candidate):
            matches[candidate] = min(len(word), len(candidate)) / max(len(word), len(candidate))
        elif _within_one_edit(word, candidate):
            matches[candidate] = _EDIT_WEIGHT
    return matches


def rank(query: str, entries: list[dict]) -> list[tuple[float, dict]]:
    """Score entries against a query, best first, dropping anything scoring zero.

    Args:
        query: Free-text query.
        entries: Catalogue entries to rank.

    Returns:
        list[tuple[float, dict]]: ``(score, entry)`` pairs sorted by score then slug.

    Raises:
        ValueError: The query has no searchable word.
    """
    query_tokens = list(dict.fromkeys(tokenise(query)))
    if not query_tokens:
        raise ValueError("the query has no searchable word")
    if not entries:
        return []

    weighted, lengths, document_frequency = [], [], {}
    for entry in entries:
        counts: dict[str, float] = {}
        for field, tokens in entry_fields(entry).items():
            for token in tokens:
                counts[token] = counts.get(token, 0.0) + FIELD_WEIGHTS[field]
        weighted.append(counts)
        lengths.append(sum(counts.values()))
        for token in counts:
            document_frequency[token] = document_frequency.get(token, 0) + 1

    total = len(entries)
    average_length = sum(lengths) / total or 1.0
    vocabulary = list(document_frequency)
    expansions = {word: _expand(word, vocabulary) for word in query_tokens}

    hits = []
    for entry, counts, length in zip(entries, weighted, lengths):
        score = 0.0
        for matches in expansions.values():
            best = 0.0
            for token, weight in matches.items():
                frequency = counts.get(token)
                if not frequency:
                    continue
                df = document_frequency[token]
                idf = math.log(1 + (total - df + 0.5) / (df + 0.5))
                norm = frequency + _K1 * (1 - _B + _B * length / average_length)
                best = max(best, weight * idf * frequency * (_K1 + 1) / norm)
            score += best
        if score > 0:
            hits.append((score, entry))
    hits.sort(key=lambda hit: (-hit[0], hit[1].get("slug", "")))
    return hits
