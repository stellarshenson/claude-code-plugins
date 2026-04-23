"""Grounding: score a claim against one or more source texts.

Runs THREE independent matching layers and reports ALL scores:

    1. **Exact (regex)** — whitespace-tolerant, case-insensitive regex search.
       Score = 1.0 when a hit is found on any source, 0.0 otherwise.
    2. **Fuzzy (Levenshtein)** — ``rapidfuzz.fuzz.partial_ratio_alignment``
       finds the best-matching substring across all sources. Score in [0,1].
    3. **BM25 (lexical / topical)** — ``rank_bm25.BM25Okapi`` ranks source
       passages (paragraphs or sentences) for term overlap with IDF weighting.
       Score normalised to [0,1] via max-in-corpus. Handles paraphrase with
       same key terms but different word order.

Agent-friendly primary grounding approach: BM25 finds the *right passage*
even when wording differs. Use exact for quoted claims, fuzzy for paraphrases
with close wording, BM25 for topical grounding ("the claim is discussed in
this passage" even when wording differs). A disciplined generative
interpretation is the secondary fallback for semantic claims none of the
three lexical layers capture.

The returned :class:`GroundingMatch` carries all three scores plus a
:class:`Location` for each layer (line, column, paragraph, page, context) so
a grounding agent can cite the hit without rereading the source.

Location semantics:
    - line_start / line_end: 1-indexed, inclusive
    - column_start / column_end: 1-indexed character offset on line
    - paragraph: 1-indexed, paragraphs separated by blank lines
    - page: 1-indexed, pages separated by form-feed ``\\f`` (pdftotext convention)
    - context_before / context_after: up to one adjacent line, trimmed to
      ``context_chars``
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal, Sequence

import numpy as np
from rank_bm25 import BM25Okapi
from rapidfuzz.fuzz import partial_ratio_alignment

MatchType = Literal["exact", "fuzzy", "bm25", "none"]

SourceInput = str | tuple[str, str]
"""A source is either raw text or a ``(path, text)`` pair for provenance."""


@dataclass
class Location:
    """Location of a match inside source text.

    All line/column/paragraph/page indices 1-based; ``char_start``/``char_end``
    are 0-based character offsets matching Python slicing. Default ``-1``
    indicates "unknown / no match".
    """

    source_index: int = -1
    source_path: str = ""
    char_start: int = -1  # 0-indexed inclusive
    char_end: int = -1  # 0-indexed exclusive
    line_start: int = -1  # 1-indexed inclusive
    line_end: int = -1  # 1-indexed inclusive
    column_start: int = -1  # 1-indexed (column on line_start)
    column_end: int = -1  # 1-indexed (column on line_end)
    paragraph: int = -1  # 1-indexed; paragraphs separated by blank lines
    page: int = -1  # 1-indexed; pages separated by \f form-feed
    context_before: str = ""
    context_after: str = ""


@dataclass
class GroundingMatch:
    """Result of grounding a single claim against a set of sources.

    Three layers always run independently. ``match_type`` is a convenience
    classifier based on thresholds; ``combined_score`` is the max of the
    three normalised scores.

    ``exact_location``, ``fuzzy_location``, and ``bm25_location`` give the
    grounding agent enough metadata (line, paragraph, page, context) to cite
    the hit without rereading the source.
    """

    claim: str
    # Regex / exact layer
    exact_score: float = 0.0  # 1.0 on hit, 0.0 otherwise
    exact_matched_text: str = ""
    exact_location: Location = field(default_factory=Location)
    # Levenshtein / fuzzy layer
    fuzzy_score: float = 0.0  # Levenshtein partial ratio in [0, 1]
    fuzzy_matched_text: str = ""
    fuzzy_location: Location = field(default_factory=Location)
    # BM25 lexical / topical layer
    bm25_score: float = 0.0  # Normalised [0, 1] - best passage vs max in corpus
    bm25_raw_score: float = 0.0  # Raw BM25 Okapi score (unbounded, clamped >= 0)
    bm25_token_recall: float = 0.0  # Fraction of unique claim tokens in best passage
    bm25_matched_text: str = ""
    bm25_location: Location = field(default_factory=Location)
    # Resolution
    match_type: MatchType = "none"
    combined_score: float = 0.0  # max(exact_score, fuzzy_score, bm25_score)


def _normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space, strip ends."""
    return re.sub(r"\s+", " ", text).strip()


def _exact_match(claim: str, source: str) -> tuple[int, int] | None:
    """Find the claim inside ``source`` ignoring whitespace + case differences."""
    norm_claim = _normalize_whitespace(claim)
    if not norm_claim:
        return None
    tokens = norm_claim.split(" ")
    pattern = r"\s+".join(re.escape(t) for t in tokens)
    m = re.search(pattern, source, flags=re.IGNORECASE)
    if m:
        return (m.start(), m.end())
    return None


def _unpack_sources(sources: Sequence[SourceInput]) -> list[tuple[int, str, str]]:
    """Normalise heterogeneous source inputs to ``(index, path, text)`` tuples."""
    out: list[tuple[int, str, str]] = []
    for i, src in enumerate(sources):
        if isinstance(src, tuple):
            path, text = src
            out.append((i, path, text))
        else:
            out.append((i, "", src))
    return out


def _locate(
    text: str,
    start: int,
    end: int,
    *,
    source_index: int,
    source_path: str,
    context_chars: int = 80,
) -> Location:
    """Compute line/column/paragraph/page metadata for a char span."""
    line_start = text.count("\n", 0, start) + 1
    line_end = text.count("\n", 0, end) + 1

    prev_nl_start = text.rfind("\n", 0, start)
    col_start = start - prev_nl_start if prev_nl_start >= 0 else start + 1
    prev_nl_end = text.rfind("\n", 0, end)
    col_end = end - prev_nl_end if prev_nl_end >= 0 else end + 1

    paragraph = 1 + len(re.findall(r"\n\s*\n", text[:start]))
    page = 1 + text.count("\f", 0, start)

    line_begin = text.rfind("\n", 0, start) + 1
    prev_line_begin = text.rfind("\n", 0, line_begin - 1) + 1 if line_begin > 0 else 0
    context_before = text[prev_line_begin:start].replace("\n", " ").strip()
    if len(context_before) > context_chars:
        context_before = "…" + context_before[-context_chars:]

    line_finish = text.find("\n", end)
    if line_finish < 0:
        line_finish = len(text)
    next_line_finish = text.find("\n", line_finish + 1)
    if next_line_finish < 0:
        next_line_finish = len(text)
    context_after = text[end:next_line_finish].replace("\n", " ").strip()
    if len(context_after) > context_chars:
        context_after = context_after[:context_chars] + "…"

    return Location(
        source_index=source_index,
        source_path=source_path,
        char_start=start,
        char_end=end,
        line_start=line_start,
        line_end=line_end,
        column_start=col_start,
        column_end=col_end,
        paragraph=paragraph,
        page=page,
        context_before=context_before,
        context_after=context_after,
    )


# -- BM25 passage ranking -----------------------------------------------


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenisation."""
    return _TOKEN_RE.findall(text.lower())


def _split_passages(text: str) -> list[tuple[int, int, str]]:
    """Split text into passages by blank-line boundaries.

    Returns ``[(start, end, passage_text), ...]`` with char offsets into the
    original text. Passages with no word characters are dropped.
    """
    if not text:
        return []
    passages: list[tuple[int, int, str]] = []
    # Match runs of non-blank lines as one passage
    for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text):
        p = m.group()
        if _TOKEN_RE.search(p):
            passages.append((m.start(), m.end(), p))
    return passages


@dataclass
class _BM25Hit:
    source_index: int
    source_path: str
    char_start: int
    char_end: int
    matched_text: str
    raw_score: float
    normalised_score: float
    token_recall: float


def _bm25_match(
    claim: str,
    pairs: list[tuple[int, str, str]],
) -> _BM25Hit | None:
    """Rank passages across all sources with BM25 Okapi. Return best hit."""
    claim_tokens = _tokenize(claim)
    if not claim_tokens:
        return None

    # Gather passages across all sources, track provenance
    corpus_tokens: list[list[str]] = []
    provenance: list[tuple[int, str, int, int, str]] = []  # (src_idx, path, start, end, text)
    for idx, path, text in pairs:
        for start, end, passage in _split_passages(text):
            tokens = _tokenize(passage)
            if tokens:
                corpus_tokens.append(tokens)
                provenance.append((idx, path, start, end, passage))

    if not corpus_tokens:
        return None

    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(claim_tokens)
    scores = np.maximum(scores, 0.0)  # BM25 can go negative on tiny corpora
    max_score = float(scores.max())
    if max_score == 0.0:
        return None

    best_idx = int(scores.argmax())
    raw = float(scores[best_idx])
    normalised = raw / max_score  # relative to top passage = 1.0 for winner

    # Token recall: fraction of unique claim tokens present in winner passage
    claim_set = set(claim_tokens)
    passage_set = set(corpus_tokens[best_idx])
    recall = len(claim_set & passage_set) / len(claim_set) if claim_set else 0.0

    src_idx, path, start, end, text = provenance[best_idx]
    return _BM25Hit(
        source_index=src_idx,
        source_path=path,
        char_start=start,
        char_end=end,
        matched_text=text,
        raw_score=raw,
        normalised_score=normalised,
        token_recall=recall,
    )


# -- Main API -----------------------------------------------------------


def ground(
    claim: str,
    sources: Sequence[SourceInput],
    *,
    fuzzy_threshold: float = 0.85,
    bm25_threshold: float = 0.5,
    context_chars: int = 80,
) -> GroundingMatch:
    """Ground a single claim against one or more sources.

    Always runs exact, fuzzy, AND BM25 passes independently on every source.
    All three scores are returned so callers see signal from each method and
    can cite line/paragraph/page without rereading.

    Args:
        claim: verbatim claim text to locate
        sources: iterable of raw source text or ``(path, text)`` pairs
        fuzzy_threshold: Levenshtein partial-ratio in [0,1] required to
            classify the best fuzzy alignment as ``"fuzzy"``
        bm25_threshold: token-recall in [0,1] required to classify the best
            BM25 passage as ``"bm25"``. Token-recall = fraction of unique
            claim tokens present in the winning passage
        context_chars: max chars of surrounding context per location

    Returns:
        :class:`GroundingMatch` with ``exact_score`` / ``fuzzy_score`` /
        ``bm25_score`` plus locations. ``match_type`` priority: exact > fuzzy
        (above threshold) > bm25 (token-recall above threshold) > none.
        ``combined_score`` = ``max(all three)``.
    """
    result = GroundingMatch(claim=claim)
    pairs = _unpack_sources(sources)
    if not pairs:
        return result

    # Exact (regex) pass — first hit wins
    for idx, path, text in pairs:
        span = _exact_match(claim, text)
        if span is not None:
            start, end = span
            result.exact_score = 1.0
            result.exact_matched_text = text[start:end]
            result.exact_location = _locate(
                text, start, end, source_index=idx, source_path=path, context_chars=context_chars
            )
            break

    # Fuzzy (Levenshtein partial-ratio) pass — best across all sources
    for idx, path, text in pairs:
        if not text or not claim:
            continue
        align = partial_ratio_alignment(claim, text)
        ratio = align.score / 100.0
        if ratio > result.fuzzy_score:
            result.fuzzy_score = ratio
            result.fuzzy_matched_text = text[align.dest_start : align.dest_end]
            result.fuzzy_location = _locate(
                text,
                align.dest_start,
                align.dest_end,
                source_index=idx,
                source_path=path,
                context_chars=context_chars,
            )

    # BM25 pass — rank passages across all sources
    bm25_hit = _bm25_match(claim, pairs)
    if bm25_hit is not None:
        result.bm25_score = bm25_hit.token_recall  # headline score: agent-interpretable
        result.bm25_raw_score = bm25_hit.raw_score
        result.bm25_token_recall = bm25_hit.token_recall
        result.bm25_matched_text = bm25_hit.matched_text
        # Locate inside the source
        source_text = next(t for i, _, t in pairs if i == bm25_hit.source_index)
        result.bm25_location = _locate(
            source_text,
            bm25_hit.char_start,
            bm25_hit.char_end,
            source_index=bm25_hit.source_index,
            source_path=bm25_hit.source_path,
            context_chars=context_chars,
        )

    # Resolve match_type: exact > fuzzy > bm25 > none
    result.combined_score = max(result.exact_score, result.fuzzy_score, result.bm25_score)
    if result.exact_score == 1.0:
        result.match_type = "exact"
    elif result.fuzzy_score >= fuzzy_threshold:
        result.match_type = "fuzzy"
    elif result.bm25_score >= bm25_threshold:
        result.match_type = "bm25"
    else:
        result.match_type = "none"

    return result


def ground_many(
    claims: Sequence[str],
    sources: Sequence[SourceInput],
    *,
    fuzzy_threshold: float = 0.85,
    bm25_threshold: float = 0.5,
    context_chars: int = 80,
) -> list[GroundingMatch]:
    """Batch version of :func:`ground`. Returns one match per claim."""
    return [
        ground(
            c,
            sources,
            fuzzy_threshold=fuzzy_threshold,
            bm25_threshold=bm25_threshold,
            context_chars=context_chars,
        )
        for c in claims
    ]
