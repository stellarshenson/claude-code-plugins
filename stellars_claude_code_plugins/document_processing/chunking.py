"""Recursive text chunking for semantic grounding.

Pure stdlib, no heavy deps. Splits a source text into overlapping passages
small enough for an embedding model while respecting natural boundaries
(paragraphs > sentences > words).

Each returned :class:`Chunk` carries its char offsets in the original
source so the semantic layer can locate hits with line/paragraph/page
metadata without a second scan.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

PARA_SPLIT_RE = re.compile(r"(\n\s*\n)")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WS_RE = re.compile(r"\s+")


@dataclass
class Chunk:
    text: str
    char_start: int
    char_end: int

    def __len__(self) -> int:
        return len(self.text)


def _approx_tokens(text: str) -> int:
    """Cheap token count — number of whitespace-split words.

    Real transformer tokenisers chunk sub-words, so use a conservative ratio:
    most natural-language tokenisers emit ~1.3 tokens per word. We treat
    ``max_tokens`` as "target words × 0.75" in callers.
    """
    return len(WS_RE.findall(text)) + 1


def recursive_chunk(
    text: str,
    *,
    max_chars: int = 1500,
    overlap_chars: int | None = None,
    overlap_ratio: float = 0.25,
    min_chunk_chars: int = 20,
) -> list[Chunk]:
    """Recursively split text into overlapping chunks.

    Strategy:
        1. Split by blank-line paragraphs.
        2. For any paragraph > ``max_chars``, split by sentences.
        3. For any sentence > ``max_chars``, split by words with overlap.
        4. Merge adjacent small chunks up to ``max_chars`` to reduce count.

    Char offsets are preserved throughout so semantic hits report the exact
    span in the original source for line/paragraph/page lookup.

    Args:
        text: raw source text.
        max_chars: upper bound on a single chunk (roughly ~375 tokens for
            mmBERT-small at 1500 chars).
        overlap_chars: chars of trailing context carried into the next
            chunk when word-level splitting is needed.
        min_chunk_chars: drop chunks smaller than this (likely whitespace).

    Returns:
        list of :class:`Chunk` in document order.
    """
    if not text:
        return []

    if overlap_chars is None:
        overlap_chars = int(max_chars * overlap_ratio)

    raw_chunks: list[Chunk] = []

    # Step 1: paragraph split (preserves offsets via finditer on the joined text)
    paragraphs: list[tuple[int, int, str]] = []
    cursor = 0
    for m in PARA_SPLIT_RE.finditer(text):
        end = m.start()
        if end > cursor:
            paragraphs.append((cursor, end, text[cursor:end]))
        cursor = m.end()
    if cursor < len(text):
        paragraphs.append((cursor, len(text), text[cursor:]))

    for p_start, p_end, p_text in paragraphs:
        if len(p_text) <= max_chars:
            raw_chunks.append(Chunk(p_text, p_start, p_end))
            continue

        # Step 2: sentence split inside oversized paragraph
        for s_start, s_end, s_text in _split_sentences(p_text, p_start):
            if len(s_text) <= max_chars:
                raw_chunks.append(Chunk(s_text, s_start, s_end))
                continue

            # Step 3: word-level sliding window on oversized sentence
            raw_chunks.extend(_sliding_window(s_text, s_start, max_chars, overlap_chars))

    # Step 4: drop slivers, strip whitespace
    cleaned: list[Chunk] = []
    for c in raw_chunks:
        stripped = c.text.strip()
        if len(stripped) < min_chunk_chars:
            continue
        # Recompute char_start if we stripped leading whitespace
        lead = len(c.text) - len(c.text.lstrip())
        trail = len(c.text) - len(c.text.rstrip())
        cleaned.append(
            Chunk(
                text=stripped,
                char_start=c.char_start + lead,
                char_end=c.char_end - trail,
            )
        )

    # Step 5: merge adjacent small chunks to reduce count
    return _merge_small(cleaned, max_chars)


def _split_sentences(text: str, base_offset: int) -> list[tuple[int, int, str]]:
    """Split by sentence boundaries, preserving offsets."""
    result: list[tuple[int, int, str]] = []
    parts = SENTENCE_SPLIT_RE.split(text)
    cursor = 0
    for part in parts:
        if not part:
            continue
        # find the part in the original starting at cursor
        idx = text.find(part, cursor)
        if idx < 0:
            idx = cursor
        start = base_offset + idx
        end = start + len(part)
        result.append((start, end, part))
        cursor = idx + len(part)
    return result


def _sliding_window(
    text: str, base_offset: int, max_chars: int, overlap_chars: int
) -> list[Chunk]:
    """Word-aware sliding window on a single oversized sentence."""
    if not text:
        return []
    step = max(max_chars - overlap_chars, max_chars // 2)
    out: list[Chunk] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        # Snap end to nearest whitespace to avoid mid-word cuts
        if end < len(text):
            last_ws = text.rfind(" ", start, end)
            if last_ws > start + max_chars // 2:
                end = last_ws
        out.append(Chunk(text[start:end], base_offset + start, base_offset + end))
        if end >= len(text):
            break
        start += step
    return out


def _merge_small(chunks: list[Chunk], max_chars: int) -> list[Chunk]:
    """Merge adjacent chunks up to ``max_chars`` to reduce total count."""
    if not chunks:
        return []
    merged: list[Chunk] = [chunks[0]]
    for c in chunks[1:]:
        prev = merged[-1]
        combined_len = c.char_end - prev.char_start
        if combined_len <= max_chars:
            merged[-1] = Chunk(
                text=prev.text + " " + c.text,
                char_start=prev.char_start,
                char_end=c.char_end,
            )
        else:
            merged.append(c)
    return merged
