"""Intra-document consistency checks.

Source grounding catches disagreement between a claim and an external
source. It cannot see divergences INSIDE a single document - the brief
that claims ``dev/test/staging`` on line 42 and ``dev/staging/prod`` on
line 119. This module walks one document, extracts numeric + named
entities, and flags categories that carry multiple distinct values.

Two check kinds:
    - **numeric**: same (unit, context_word) key with different values
      (e.g. ``42 users`` on line 10 vs ``50 users`` on line 80).
    - **entity-set**: a capitalised multi-word entity phrase and a
      phrase that shares a token-set neighbour of length >= 2 but
      diverges (e.g. ``dev, test, staging`` on line 42 vs
      ``dev, staging, prod`` on line 119 - both 3-sets of environment
      names but different members).

Reuses ``extract_numbers`` and ``extract_entities`` from
:mod:`entity_check`; no new regex algorithms are added here.

Output is a list of :class:`ConsistencyFinding` with the category,
competing values, and the line numbers where each was seen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

from stellars_claude_code_plugins.document_processing.entity_check import (
    extract_entities,
    extract_numbers,
)


@dataclass
class ConsistencyFinding:
    """One divergence: same category, different values at different lines."""

    kind: str  # "numeric" | "entity_set"
    category: str  # human-readable label (e.g. "% users", "3-item set")
    occurrences: list[tuple[int, str]] = field(default_factory=list)
    """List of (line_number, rendered_value) pairs. Length >= 2 by construction."""


# --- numeric consistency --------------------------------------------------


def _group_numbers_by_key(
    text: str,
) -> dict[tuple[str, str], list[tuple[int, str]]]:
    """Group ``extract_numbers`` hits by (unit, context) with source lines.

    Two numbers share a key when they share both unit and context_word. A
    partial-key match (unit-only or context-only) is NOT used here:
    consistency is stricter than contradiction detection because we are
    looking for values the author intended to be identical, not values
    the author might have meant differently.
    """
    grouped: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for line_no, line_text in enumerate(text.splitlines(), start=1):
        for value, unit, ctx in extract_numbers(line_text):
            if not unit and not ctx:
                continue  # bare numbers carry no comparable category
            key = (unit, ctx)
            rendered = value + (f" {unit}" if unit else "") + (f" {ctx}" if ctx else "")
            grouped.setdefault(key, []).append((line_no, rendered))
    return grouped


def _find_numeric_findings(text: str) -> list[ConsistencyFinding]:
    findings: list[ConsistencyFinding] = []
    for (unit, ctx), occurrences in _group_numbers_by_key(text).items():
        # Extract distinct values; single-value categories are consistent.
        distinct_values = {rendered.split(" ", 1)[0] for _, rendered in occurrences}
        if len(distinct_values) < 2:
            continue
        # Build a category label readers can scan in a report
        label_parts = [p for p in (unit, ctx) if p]
        category = " ".join(label_parts) if label_parts else "(uncategorised)"
        findings.append(
            ConsistencyFinding(
                kind="numeric",
                category=category,
                occurrences=occurrences,
            )
        )
    return findings


# --- entity-set consistency ----------------------------------------------


# List-style enumeration separator. Order matters: longer Oxford-comma
# combos must come BEFORE bare comma so "test, and staging" is consumed
# whole instead of leaving "and" as a spurious token.
_SPLITTER_PATTERN = r"\s*(?:,\s+and\s+|,\s+or\s+|,|\s+and\s+|\s+or\s+|/|\s+&\s+)\s*"

# Captures patterns like "dev, test, staging" or "dev/test/staging" - the
# core signal for this check. Matches only sequences of 2-6 short tokens
# to avoid false positives on long capitalised phrases.
_SET_RE = re.compile(
    rf"""
    \b
    (?P<first>[A-Za-z][A-Za-z\-]{{1,20}})
    (?P<rest>
        (?:
            {_SPLITTER_PATTERN}
            [A-Za-z][A-Za-z\-]{{1,20}}
        ){{1,5}}
    )
    \b
    """,
    re.VERBOSE,
)

_SPLITTER_RE = re.compile(_SPLITTER_PATTERN)

# Very common English tokens that frequently appear inside lists without
# carrying category signal. Dropping them prevents noise findings like
# "faster, better, stronger" matching against unrelated triples.
_GENERIC_WORDS = frozenset(
    {
        "and",
        "or",
        "the",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "is",
        "are",
        "be",
        "for",
        "with",
        "without",
        "such",
        "also",
    }
)


def _extract_sets(text: str) -> list[tuple[int, frozenset[str]]]:
    """Find list-style enumerations; return ``(line_no, frozenset(tokens))``.

    Token membership is lowercased. Sets with fewer than 2 tokens or with
    only generic words are dropped.
    """
    out: list[tuple[int, frozenset[str]]] = []
    for line_no, line_text in enumerate(text.splitlines(), start=1):
        for m in _SET_RE.finditer(line_text):
            raw = m.group(0)
            tokens = [t.strip().lower() for t in _SPLITTER_RE.split(raw) if t.strip()]
            tokens = [t for t in tokens if t and t not in _GENERIC_WORDS]
            if len(tokens) < 2:
                continue
            out.append((line_no, frozenset(tokens)))
    return out


def _find_entity_set_findings(text: str) -> list[ConsistencyFinding]:
    """Flag list-like sets that share most tokens but differ in at least one.

    A pair ``(S1, S2)`` is a finding when:
        - both sets are 2-6 tokens,
        - Jaccard(S1, S2) >= 0.5 (they overlap substantially),
        - but S1 != S2 (they actually differ).

    Pairs are reported at most once; sets that appear multiple times with
    identical membership are ignored (that's a consistent repetition).
    """
    entries = _extract_sets(text)
    # Deduplicate identical (set) groupings so we report divergences, not
    # repetitions. Keep earliest line number as the representative.
    by_set: dict[frozenset[str], int] = {}
    for line_no, tokens in entries:
        by_set.setdefault(tokens, line_no)

    findings: list[ConsistencyFinding] = []
    seen_pairs: set[tuple[frozenset[str], frozenset[str]]] = set()
    sets_ordered = sorted(by_set.items(), key=lambda p: p[1])
    for i, (tokens_a, line_a) in enumerate(sets_ordered):
        for tokens_b, line_b in sets_ordered[i + 1 :]:
            if tokens_a == tokens_b:
                continue
            intersection = tokens_a & tokens_b
            union = tokens_a | tokens_b
            if not union:
                continue
            jaccard = len(intersection) / len(union)
            if jaccard < 0.5:
                continue
            # Normalise pair ordering so each pair only emits once.
            key = (tokens_a, tokens_b) if hash(tokens_a) < hash(tokens_b) else (tokens_b, tokens_a)
            if key in seen_pairs:
                continue
            seen_pairs.add(key)
            size_label = f"{len(tokens_a)}-item set" if len(tokens_a) == len(tokens_b) else "set"
            findings.append(
                ConsistencyFinding(
                    kind="entity_set",
                    category=size_label,
                    occurrences=[
                        (line_a, "{" + ", ".join(sorted(tokens_a)) + "}"),
                        (line_b, "{" + ", ".join(sorted(tokens_b)) + "}"),
                    ],
                )
            )
    return findings


# --- entity-mention consistency ------------------------------------------


def _find_entity_mention_findings(text: str) -> list[ConsistencyFinding]:
    """Flag capitalised entities mentioned in obviously-divergent forms.

    Cheap signal: the same "head token" (first word of an entity phrase)
    appearing with different trailing tokens in two different lines,
    e.g. ``Python 3.11`` on one line and ``Python 3.12`` on another. We
    rely on ``extract_entities`` to get the candidate phrases.
    """
    by_head: dict[str, list[tuple[int, str]]] = {}
    for line_no, line_text in enumerate(text.splitlines(), start=1):
        for phrase in extract_entities(line_text):
            parts = phrase.split()
            if len(parts) < 2:
                continue
            head = parts[0]
            by_head.setdefault(head, []).append((line_no, phrase))

    findings: list[ConsistencyFinding] = []
    for head, occurrences in by_head.items():
        distinct = {phrase for _, phrase in occurrences}
        if len(distinct) < 2:
            continue
        # Drop when the variants share no meaningful suffix difference
        # (e.g. "United Kingdom" vs "United States" - different real
        # entities, no divergence signal). Require the trailing tokens to
        # LOOK like versions or numeric suffixes for the finding to count;
        # otherwise false positive rate is too high.
        has_numeric_tail = any(re.search(r"\d", phrase) for phrase in distinct)
        if not has_numeric_tail:
            continue
        findings.append(
            ConsistencyFinding(
                kind="entity_set",
                category=f"'{head}' variants",
                occurrences=occurrences,
            )
        )
    return findings


# --- public API ----------------------------------------------------------


def check_consistency(document_text: str) -> list[ConsistencyFinding]:
    """Return all intra-document divergence findings for ``document_text``."""
    findings: list[ConsistencyFinding] = []
    findings.extend(_find_numeric_findings(document_text))
    findings.extend(_find_entity_set_findings(document_text))
    findings.extend(_find_entity_mention_findings(document_text))
    return findings


def check_consistency_in_file(path: str | Path) -> list[ConsistencyFinding]:
    """Read ``path`` (UTF-8 strict) and run :func:`check_consistency`."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="strict")
    return check_consistency(text)


def format_consistency_report(
    findings: list[ConsistencyFinding],
    *,
    document_path: str | None = None,
) -> str:
    """Render findings as a markdown report."""
    lines: list[str] = ["# Self-Consistency Report", ""]
    if document_path:
        lines.append(f"- Document: `{document_path}`")
    lines.append(f"- Findings: {len(findings)}")
    lines.append("")
    if not findings:
        lines.append("No divergences detected. Numeric categories and entity sets are consistent.")
        return "\n".join(lines)
    for i, f in enumerate(findings, start=1):
        lines.append(f"## {i}. {f.kind.upper()} - {f.category}")
        for line_no, rendered in f.occurrences:
            lines.append(f"- line {line_no}: `{rendered}`")
        lines.append("")
    return "\n".join(lines)
