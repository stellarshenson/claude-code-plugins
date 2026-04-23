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
import logging
import re
from typing import Literal, Sequence

import numpy as np
from rank_bm25 import BM25Okapi
from rapidfuzz.fuzz import partial_ratio_alignment

from stellars_claude_code_plugins.document_processing.entity_check import (
    find_absent_entities,
    find_mismatches,
    list_claim_entities,
)

logger = logging.getLogger(__name__)

MatchType = Literal["exact", "fuzzy", "bm25", "semantic", "contradicted", "none"]

SourceInput = str | tuple[str, str]
"""A source is either raw text or a ``(path, text)`` pair for provenance."""


@dataclass
class SemanticHitSummary:
    """Compact summary of a semantic hit for ``semantic_top_k`` reporting.

    Avoids coupling :class:`GroundingMatch` to the optional
    :class:`semantic.SemanticHit` class (which is only importable with the
    ``[semantic]`` extra). All float scores in [0, 1] for L2-normalised
    embeddings.
    """

    score: float = 0.0
    matched_text: str = ""
    source_index: int = -1
    source_path: str = ""
    char_start: int = -1
    char_end: int = -1


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
    # Semantic (ModernBERT + FAISS) layer — optional, off unless enabled
    semantic_score: float = 0.0  # cosine similarity in [0, 1] with L2-normalised embeddings
    semantic_matched_text: str = ""
    semantic_location: Location = field(default_factory=Location)
    semantic_top_k: list[SemanticHitSummary] = field(default_factory=list)
    """Top-K semantic hits (up to 3 by default) for alternative pointers."""
    semantic_ratio: float = 0.0
    """semantic_score / claim_self_score; calibration anchor per claim. 0 when semantic layer off."""
    # Agreement across layers
    agreement_score: float = 0.0
    """Weighted combination of exact / fuzzy / bm25 / semantic layers with multi-voter bonus."""
    # Contradiction detection (numeric + named-entity mismatch between claim and winning passage)
    numeric_mismatches: list[tuple[str, str]] = field(default_factory=list)
    """List of ``(claim_value, passage_value)`` for numeric disagreements."""
    entity_mismatches: list[tuple[str, str]] = field(default_factory=list)
    """List of ``(claim_entity, passage_entity)`` for tech-entity disagreements."""
    entities_absent: list[str] = field(default_factory=list)
    """Proper-noun entities mentioned in the claim with zero occurrences in ANY source passage.

    Weaker than ``entity_mismatches`` (which requires the source to mention
    the same category with a different value) but catches fabricated-entity
    claims like "RoPE-Mid" or "NVIDIA H100 donated by Meta" when the source
    is a Liu-style paper that never names these. Non-empty ``entities_absent``
    downweights ``agreement_score`` via a graded penalty (does not force
    CONTRADICTED - absence is weaker evidence than disagreement).
    """
    # Borderline expansion flag (H5 - reserved, not set in iter 1)
    expanded: bool = False
    """True when chunk-boundary expansion fired on a borderline semantic hit."""
    # Resolution
    match_type: MatchType = "none"
    combined_score: float = 0.0  # max of all enabled layers


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


_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_MIN_PASSAGE_CHARS = 40


def _split_passages(text: str) -> list[tuple[int, int, str]]:
    """Split text into passages by blank-line boundaries.

    Returns ``[(start, end, passage_text), ...]`` with char offsets into the
    original text. Passages with no word characters are dropped.

    Falls back to sentence splitting when blank-line splitting produces a
    single mega-passage on long texts (common with ``pdftotext`` output that
    uses single-newline line breaks). Prevents BM25 from degenerating into a
    1-doc corpus where IDF is meaningless.
    """
    if not text:
        return []
    passages: list[tuple[int, int, str]] = []
    # Match runs of non-blank lines as one passage
    for m in re.finditer(r"[^\n]+(?:\n(?!\s*\n)[^\n]+)*", text):
        p = m.group()
        if _TOKEN_RE.search(p):
            passages.append((m.start(), m.end(), p))

    # Fallback: on long single-passage texts, split on sentence boundaries so
    # BM25 has a corpus to rank against.
    if len(passages) == 1 and len(text) > 1500:
        start_0, _, body = passages[0]
        sentence_passages: list[tuple[int, int, str]] = []
        cursor = 0
        for m in _SENT_SPLIT_RE.finditer(body):
            sent_end = m.start()
            sentence = body[cursor:sent_end].strip()
            if sentence:
                sentence_passages.append((start_0 + cursor, start_0 + sent_end, sentence))
            cursor = m.end()
        tail = body[cursor:].strip()
        if tail:
            sentence_passages.append((start_0 + cursor, start_0 + len(body), tail))

        # Merge too-short sentences with their successor so BM25 IDF stays useful
        merged: list[tuple[int, int, str]] = []
        pending: tuple[int, int, str] | None = None
        for s, e, p in sentence_passages:
            if pending is None:
                pending = (s, e, p)
                continue
            if len(pending[2]) < _MIN_PASSAGE_CHARS:
                pending = (pending[0], e, pending[2] + " " + p)
            else:
                merged.append(pending)
                pending = (s, e, p)
        if pending is not None:
            merged.append(pending)

        if len(merged) >= 2:
            return merged

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


def _compute_agreement_score(
    exact_score: float,
    fuzzy_score: float,
    bm25_token_recall: float,
    semantic_score: float,
    semantic_ratio: float = 0.0,
) -> float:
    """Weighted cross-layer agreement score with multi-voter bonus.

    Per H1 spec: ``any layer firing alone < two layers firing together``.
    Real paraphrases light up multiple layers weakly; fabrications typically
    fire only on semantic (topical similarity with no lexical overlap).

    Each layer has a per-layer "vote" threshold. Layers above threshold are
    counted as voters. The score is a weighted sum of per-layer
    contributions plus a multi-voter bonus that rewards independent signals.

    Semantic contribution (H7, Iter 4): when ``semantic_ratio`` is provided
    (the claim's cosine against itself-as-passage, already computed on the
    semantic path), the ramp uses it as a model-normalised measure instead
    of the raw cosine. ``ratio = cos(claim, match) / cos(claim, claim)`` is
    naturally bounded in [0, 1] and is roughly model-independent for real
    hits (~1.0) versus noise (~0.85 or below). Ramp centre 0.88 so real
    hits contribute strongly regardless of whether the underlying model is
    E5-small (absolute hits 0.85+) or mpnet (absolute hits 0.70+). When
    ``semantic_ratio`` is 0 (semantic layer disabled or no hit), falls back
    to the absolute-cosine ramp for backward compatibility.

    Layer vote thresholds (tuned low so real-but-weak signals still count):
    - exact:    >= 1.0 (exact is binary)
    - fuzzy:    >= 0.55 (partial-ratio of ~half the claim)
    - bm25:     >= 0.15 (some token overlap)
    - semantic: ratio >= 0.90 when available, else raw cosine >= 0.70

    Returns value in [0, 1].
    """
    v_exact = 1.0 if exact_score >= 1.0 else 0.0
    v_fuzzy = max(0.0, min(1.0, (fuzzy_score - 0.5) / 0.5))  # ramp over [0.5, 1.0]
    v_bm25 = max(0.0, min(1.0, bm25_token_recall / 0.5))  # ramp over [0, 0.5]
    # Semantic contribution: take the MAX of the absolute-cosine ramp and
    # the model-normalised ratio ramp so whichever signal fires more
    # strongly dominates. Ratio path gives portability benefit for
    # low-scale models (mpnet); absolute path protects corpora where
    # ratio happens to be noisy. Either alone is enough to contribute.
    v_sem_abs = max(0.0, min(1.0, (semantic_score - 0.5) / 0.5))
    v_sem_ratio = (
        max(0.0, min(1.0, (semantic_ratio - 0.80) / 0.20)) if semantic_ratio > 0.0 else 0.0
    )
    v_sem = max(v_sem_abs, v_sem_ratio)

    raw = 0.30 * v_exact + 0.25 * v_fuzzy + 0.20 * v_bm25 + 0.25 * v_sem

    # Count voters with per-layer thresholds (lower than 0.3 so weak-but-real
    # fuzzy/bm25 signals still register agreement with a strong semantic hit).
    # Semantic voter uses semantic_ratio when available (model-agnostic) and
    # falls back to raw cosine when not.
    sem_votes = semantic_score >= 0.70 or semantic_ratio >= 0.90
    voter_flags = (
        exact_score >= 1.0,
        fuzzy_score >= 0.55,
        bm25_token_recall >= 0.15,
        sem_votes,
    )
    voters = sum(voter_flags)

    # Multi-voter bonus per H1: "any one alone < two together".
    # 1 voter: no bonus. 2 voters: +0.20. 3+: +0.35. Cap raw+bonus at 1.0.
    if voters >= 3:
        bonus = 0.35
    elif voters == 2:
        bonus = 0.20
    else:
        bonus = 0.0

    return min(1.0, raw + bonus)


def ground(
    claim: str,
    sources: Sequence[SourceInput],
    *,
    fuzzy_threshold: float = 0.85,
    bm25_threshold: float = 0.5,
    semantic_threshold: float = 0.6,
    semantic_threshold_percentile: float | None = None,
    agreement_threshold: float = 0.45,
    context_chars: int = 80,
    semantic_grounder=None,
    semantic_top_k: int = 3,
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

    # Semantic pass (optional; off unless caller passes a grounder)
    effective_semantic_threshold = semantic_threshold
    if semantic_grounder is not None:
        try:
            # Index only if not already indexed (ground_many pre-indexes once)
            if getattr(semantic_grounder, "_index", None) is None:
                semantic_grounder.index_sources(pairs)
            # H3: model-agnostic percentile-based threshold override
            if semantic_threshold_percentile is not None:
                pct_thr = semantic_grounder.percentile_threshold(
                    top_pct=semantic_threshold_percentile
                )
                if pct_thr > 0:
                    effective_semantic_threshold = pct_thr
            # Fetch top-3 for semantic_top_k reporting and alternative pointers
            hits = semantic_grounder.search(claim, top_k=semantic_top_k)
            if hits:
                best = hits[0]
                # Raw cosine similarity; for L2-normalised embeddings it lives in
                # [-1, 1] but typical retrieval signal is [0, 1]. Clamp negatives
                # to 0 so the score always reads as an "agreement" level.
                result.semantic_score = max(0.0, min(1.0, best.score))
                result.semantic_matched_text = best.matched_text
                source_text = next(t for i, _, t in pairs if i == best.source_index)
                result.semantic_location = _locate(
                    source_text,
                    best.char_start,
                    best.char_end,
                    source_index=best.source_index,
                    source_path=best.source_path,
                    context_chars=context_chars,
                )
                # Populate top_k summaries
                result.semantic_top_k = [
                    SemanticHitSummary(
                        score=max(0.0, min(1.0, h.score)),
                        matched_text=h.matched_text,
                        source_index=h.source_index,
                        source_path=h.source_path,
                        char_start=h.char_start,
                        char_end=h.char_end,
                    )
                    for h in hits
                ]
                # semantic_ratio (H7): claim vs itself as calibration anchor
                try:
                    self_score = semantic_grounder.self_score(claim)
                    if self_score > 0:
                        result.semantic_ratio = result.semantic_score / self_score
                except Exception as exc:
                    logger.warning("semantic self_score failed (claim=%r): %s", claim[:80], exc)
        except Exception as exc:
            logger.warning(
                "semantic layer failed (claim=%r): %s - lexical-only result returned",
                claim[:80],
                exc,
            )

    # Entity-presence check: flag claim proper nouns absent from ANY source
    # passage (Iter 3 addition). Weaker than contradiction (entity mismatch in
    # the winning passage) but catches fabricated-entity fakes where the
    # specific named entity doesn't appear anywhere in the source.
    full_source_text = "\n".join(t for _, _, t in pairs)
    result.entities_absent = find_absent_entities(claim, full_source_text)

    # Agreement score across layers (always computed; uses 0 for disabled layers).
    # semantic_ratio (H7) is passed so the semantic contribution is
    # model-normalised when available.
    result.agreement_score = _compute_agreement_score(
        exact_score=result.exact_score,
        fuzzy_score=result.fuzzy_score,
        bm25_token_recall=result.bm25_token_recall,
        semantic_score=result.semantic_score,
        semantic_ratio=result.semantic_ratio,
    )

    # Entity-presence penalty: graded downweight when claim proper-noun
    # entities are absent from the source (Iter 3). Penalty scales with the
    # FRACTION of claim entities missing, capped so agreement_score stays in
    # [0, 1]. Absence is weaker than contradiction so we never escalate to
    # CONTRADICTED here.
    all_claim_entities = list_claim_entities(claim)
    if all_claim_entities and result.entities_absent:
        penalty = 0.15 * (len(result.entities_absent) / len(all_claim_entities))
        result.agreement_score = max(0.0, result.agreement_score - penalty)

    # combined_score = max of all per-layer scores (legacy, preserved)
    result.combined_score = max(
        result.exact_score,
        result.fuzzy_score,
        result.bm25_score,
        result.semantic_score,
    )

    # Contradiction detection: compare claim against winning passage (H2)
    # Pick the "winning" passage for extraction: priority exact > semantic > bm25 > fuzzy
    # If no layer isolated a clear span, fall back to the single-source text so
    # contradictions are still caught on tiny sources where passage-ranking fails.
    winning_passage = ""
    if result.exact_score == 1.0:
        winning_passage = result.exact_matched_text
    elif result.semantic_score > 0.0 and result.semantic_matched_text:
        winning_passage = result.semantic_matched_text
    elif result.bm25_score > 0.0 and result.bm25_matched_text:
        winning_passage = result.bm25_matched_text
    elif result.fuzzy_score > 0.0 and result.fuzzy_matched_text:
        # Widen the fuzzy window to the full line containing the match so
        # the claim's key value (year, percentage, entity) is not clipped.
        idx = result.fuzzy_location.source_index
        if 0 <= idx < len(pairs):
            src_text = pairs[idx][2]
            start = max(0, result.fuzzy_location.char_start - 100)
            end = min(len(src_text), result.fuzzy_location.char_end + 200)
            winning_passage = src_text[start:end]
        else:
            winning_passage = result.fuzzy_matched_text
    elif len(pairs) == 1:
        # Only one source and no layer anchored: compare claim against the
        # full source text directly. Conservative category-matching in
        # ``find_mismatches`` prevents spurious mismatches here.
        winning_passage = pairs[0][2]

    if winning_passage:
        num_mm, ent_mm = find_mismatches(claim, winning_passage)
        result.numeric_mismatches = num_mm
        result.entity_mismatches = ent_mm

    # Resolve match_type:
    # priority: contradicted (always wins) > exact > fuzzy > bm25 > semantic > agreement > none
    has_contradiction = bool(result.numeric_mismatches or result.entity_mismatches)
    has_any_signal = (
        result.exact_score > 0
        or result.fuzzy_score > 0
        or result.bm25_score > 0
        or result.semantic_score > 0
    )

    if has_contradiction and has_any_signal:
        result.match_type = "contradicted"
    elif result.exact_score == 1.0:
        result.match_type = "exact"
    elif result.fuzzy_score >= fuzzy_threshold:
        result.match_type = "fuzzy"
    elif result.bm25_score >= bm25_threshold:
        result.match_type = "bm25"
    elif result.semantic_score >= effective_semantic_threshold:
        result.match_type = "semantic"
    elif result.agreement_score >= agreement_threshold:
        # Multi-layer agreement can confirm even when no single layer passed threshold
        # Classify by highest-contributing layer for the match_type label
        if (
            result.semantic_score >= result.bm25_score
            and result.semantic_score >= result.fuzzy_score
        ):
            result.match_type = "semantic"
        elif result.bm25_score >= result.fuzzy_score:
            result.match_type = "bm25"
        elif result.fuzzy_score > 0:
            result.match_type = "fuzzy"
        else:
            result.match_type = "none"
    else:
        result.match_type = "none"

    return result


def ground_many(
    claims: Sequence[str],
    sources: Sequence[SourceInput],
    *,
    fuzzy_threshold: float = 0.85,
    bm25_threshold: float = 0.5,
    semantic_threshold: float = 0.6,
    semantic_threshold_percentile: float | None = None,
    agreement_threshold: float = 0.45,
    context_chars: int = 80,
    semantic_grounder=None,
    semantic_top_k: int = 3,
) -> list[GroundingMatch]:
    """Batch version of :func:`ground`.

    If ``semantic_grounder`` is provided, the source passages are indexed
    once (chunked + embedded + FAISS) and reused across all claims — major
    speedup over re-indexing per claim.
    """
    # Eagerly index sources once for the semantic layer if supplied
    if semantic_grounder is not None:
        try:
            pairs = _unpack_sources(sources)
            semantic_grounder.index_sources(pairs)
        except Exception as exc:
            logger.error(
                "semantic index_sources failed: %s - disabling semantic layer for this batch",
                exc,
            )
            semantic_grounder = None  # disable on error

    return [
        ground(
            c,
            sources,
            fuzzy_threshold=fuzzy_threshold,
            bm25_threshold=bm25_threshold,
            semantic_threshold=semantic_threshold,
            semantic_threshold_percentile=semantic_threshold_percentile,
            agreement_threshold=agreement_threshold,
            context_chars=context_chars,
            semantic_grounder=semantic_grounder,
            semantic_top_k=semantic_top_k,
        )
        for c in claims
    ]
