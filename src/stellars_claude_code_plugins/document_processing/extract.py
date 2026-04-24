"""Claim extraction: turn a document into a claims.json for ground-many.

The grounding tool's heaviest manual step is producing the claims list.
This module provides a deterministic sentence-per-line heuristic extractor
that emits JSON compatible with ``ground-many --claims``:

    [
        {"id": "c01", "claim": "We observed 42 concurrent sessions."},
        {"id": "c02", "claim": "The dataset grew to 1.7M rows."},
        ...
    ]

The heuristic is lossy by design - a sales brief with bullet lists and
markdown headers does not parse into clean assertions without human
judgement. The output is a starting point; the caller is expected to
review the extracted claims before grounding.

Filtering rules (drop a sentence when):
    - shorter than 20 chars (headers, stubs)
    - no verb-shaped content (crude: no word ending in -s/-ed/-ing/-e and
      at least one copula "is/are/was/were")
    - starts with a markdown control prefix (``#``, ``>``, ``|``, ``---``)
    - empty after stripping list markers ``- ``, ``* ``, ``1. ``

Claims keep their order of appearance; IDs are ``c01``..``cNN``
zero-padded to two digits (fits up to 99 claims; beyond that the ID
widens automatically).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass
class ExtractedClaim:
    """A single candidate claim with stable ID + source line number."""

    id: str
    claim: str
    line_number: int


# Sentence-end regex. Splits on ``. ! ?`` followed by whitespace and a
# capital-letter or digit start. Tolerates common abbreviations by
# requiring a capital/digit after the whitespace (a sentence rarely
# continues with lowercase).
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

# Markdown bullet/number prefixes stripped before length check
_LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")

# Crude "has verb-like content" check: at least one copula or a word
# ending in -s/-ed/-ing. Used to drop pure noun-phrase headers like
# "Key Features" or "Technical Stack".
_COPULA_RE = re.compile(r"\b(is|are|was|were|has|have|had|will|can|should|must)\b", re.IGNORECASE)
_VERB_SUFFIX_RE = re.compile(r"\b\w+(?:ed|ing|s)\b")

# Minimum chars after trimming. Below this the sentence is almost
# always a heading or stub with no groundable assertion.
_MIN_CLAIM_CHARS = 20


def _strip_markdown_noise(line: str) -> str:
    """Remove leading markdown markup so the sentence starts cleanly."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return ""
    if stripped.startswith(">"):
        stripped = stripped.lstrip("> ").strip()
    if stripped.startswith("|"):
        return ""
    stripped = _LIST_PREFIX_RE.sub("", stripped)
    return stripped.strip()


def _looks_like_claim(candidate: str) -> bool:
    """Return True if the candidate sentence has verb-shaped content."""
    if len(candidate) < _MIN_CLAIM_CHARS:
        return False
    if _COPULA_RE.search(candidate):
        return True
    if _VERB_SUFFIX_RE.search(candidate):
        return True
    return False


def _split_document(text: str) -> list[tuple[int, str]]:
    """Split document into ``(source_line_number, sentence)`` pairs.

    Walks line-by-line so we can keep each claim's line number (helps
    the reviewer jump back to the source). Within a paragraph the text
    is joined and split on sentence boundaries.
    """
    out: list[tuple[int, str]] = []
    paragraph_lines: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph_lines:
            return
        para_text = " ".join(line for _, line in paragraph_lines).strip()
        if not para_text:
            paragraph_lines.clear()
            return
        start_line = paragraph_lines[0][0]
        sentences = _SENT_SPLIT_RE.split(para_text)
        for sent in sentences:
            sent = sent.strip()
            if sent:
                out.append((start_line, sent))
        paragraph_lines.clear()

    for idx, raw_line in enumerate(text.splitlines(), start=1):
        stripped = _strip_markdown_noise(raw_line)
        if not stripped:
            flush()
            continue
        paragraph_lines.append((idx, stripped))
    flush()
    return out


def extract_claims(document_text: str) -> list[ExtractedClaim]:
    """Extract candidate claims from document text.

    Heuristic: split into sentences, drop fragments that lack verb-shaped
    content, assign stable IDs in order of appearance.
    """
    sentences = _split_document(document_text)
    candidates: list[tuple[int, str]] = [
        (line_no, s) for line_no, s in sentences if _looks_like_claim(s)
    ]

    pad = max(2, len(str(len(candidates))))
    out: list[ExtractedClaim] = []
    for i, (line_no, claim_text) in enumerate(candidates, start=1):
        out.append(
            ExtractedClaim(
                id=f"c{i:0{pad}d}",
                claim=claim_text,
                line_number=line_no,
            )
        )
    return out


def extract_claims_from_file(path: str | Path) -> list[ExtractedClaim]:
    """Read ``path`` (UTF-8 strict) and extract claims.

    Raises ``UnicodeDecodeError`` on non-UTF-8 input so the caller can
    surface a clear error message (the CLI layer handles this).
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="strict")
    return extract_claims(text)
