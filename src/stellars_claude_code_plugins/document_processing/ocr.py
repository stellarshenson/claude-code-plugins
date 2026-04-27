"""Optional OCR fallback for scanned PDFs.

Wraps pytesseract + pdf2image so callers get full-text extraction PLUS
quality metrics in one call. The companion ``cache_ocr_candidate``
always writes the result to ``<stem>.ocr.txt`` next to the source so:

1. Subsequent grounding runs find the candidate via the
   sibling-priority lookup (``.ocr.txt`` is the highest-priority match)
   and skip OCR entirely.
2. The agent has a starting point to edit corrections in place even
   when quality is poor.
3. The header comment in the candidate file carries the quality stats
   (mean confidence, page count, language, timestamp). Deleting the
   header marks the candidate as human-reviewed and silences the
   OCR-CANDIDATE warning the next run; keeping it re-fires the warning
   so a never-reviewed candidate cannot graduate silently.

OCR deps are optional. ``ocr_available()`` checks both Python imports
and the system ``tesseract`` binary; missing → caller emits
OCR-MISSING and points the agent at vision-OCR via the Read tool.

Language is the agent's responsibility - this module never picks one.
``ocr_pdf`` requires ``lang`` as a positional arg; the CLI surfaces
``--ocr-lang`` and fires OCR-LANG-NEEDED before invoking OCR if the
flag is missing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

# Quality-band thresholds. Module constants so tests can monkey-patch.
GOOD_CONFIDENCE_MIN: float = 80.0
CANDIDATE_CONFIDENCE_MIN: float = 60.0
GOOD_CHAR_MIN: int = 100
FAILED_CHAR_MIN: int = 20

OcrQuality = Literal["good", "candidate", "failed"]


class OcrUnavailable(Exception):
    """Raised when OCR is requested but deps / tesseract binary missing.

    Carries an install hint suitable for surfacing to the agent.
    """


@dataclass
class OcrResult:
    """Outcome of an OCR run with enough metadata for the gate to band."""

    text: str
    mean_confidence: float
    per_page_confidence: list[float] = field(default_factory=list)
    total_chars: int = 0
    quality: OcrQuality = "failed"
    failure_reason: str | None = None
    lang: str = "eng"

    def __post_init__(self) -> None:
        if not self.total_chars:
            self.total_chars = len(self.text.strip())


def ocr_available() -> bool:
    """True iff every OCR dep imports AND tesseract is on PATH."""
    try:
        import pdf2image  # noqa: F401
        from PIL import Image  # noqa: F401
        import pytesseract  # noqa: F401
    except ImportError:
        return False
    import shutil

    return shutil.which("tesseract") is not None


def install_hint() -> str:
    """Human-readable install instruction for the OCR extras."""
    return (
        "Install OCR extras: `pip install stellars-claude-code-plugins[ocr]` "
        "AND the system tesseract binary "
        "(`apt install tesseract-ocr` / `brew install tesseract` / etc)."
    )


def ocr_pdf(path: Path, lang: str, *, dpi: int = 200) -> OcrResult:
    """Run OCR on every page of the PDF, return text + quality metrics.

    ``lang`` is REQUIRED - the agent always confirms the right Tesseract
    model based on document inspection. We never auto-detect language
    inside this function.

    Raises ``OcrUnavailable`` when deps or tesseract binary are missing,
    so the caller can fall back to OCR-MISSING gate behaviour.
    """
    if not ocr_available():
        raise OcrUnavailable(install_hint())

    import pdf2image  # type: ignore[import-not-found]
    import pytesseract  # type: ignore[import-not-found]

    try:
        images = pdf2image.convert_from_path(str(path), dpi=dpi)
    except Exception as exc:
        return OcrResult(
            text="",
            mean_confidence=0.0,
            per_page_confidence=[],
            total_chars=0,
            quality="failed",
            failure_reason=f"pdf2image rasterisation failed: {exc}",
            lang=lang,
        )

    page_texts: list[str] = []
    page_confidences: list[float] = []
    for image in images:
        try:
            data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        except Exception as exc:
            page_texts.append("")
            page_confidences.append(0.0)
            failure_reason = f"pytesseract.image_to_data failed: {exc}"
            return OcrResult(
                text="\n\n".join(page_texts),
                mean_confidence=_mean(page_confidences),
                per_page_confidence=page_confidences,
                quality="failed",
                failure_reason=failure_reason,
                lang=lang,
            )
        page_text, page_conf = _aggregate_page(data)
        page_texts.append(page_text)
        page_confidences.append(page_conf)

    text = ""
    for i, p in enumerate(page_texts, start=1):
        if i > 1:
            text += f"\n\n--- page {i} ---\n\n"
        text += p
    mean_conf = _mean(page_confidences)
    total_chars = len(text.strip())
    quality = _classify_quality(mean_conf, total_chars)
    failure_reason = None
    if quality == "failed":
        failure_reason = _build_failure_reason(mean_conf, total_chars)
    return OcrResult(
        text=text,
        mean_confidence=mean_conf,
        per_page_confidence=page_confidences,
        total_chars=total_chars,
        quality=quality,
        failure_reason=failure_reason,
        lang=lang,
    )


def cache_ocr_candidate(source_path: Path, result: OcrResult) -> Path:
    """Write the OCR candidate alongside the source as ``<stem>.ocr.txt``.

    Always writes - even when ``quality="failed"`` - so the agent has a
    file to edit. The header comment carries the metadata; deleting the
    header on a manual review marks the file as accepted (the next
    grounding run treats it as a normal text sibling and the
    OCR-CANDIDATE / OCR-FAILED warning does not re-fire).
    """
    cache_path = source_path.with_suffix(".ocr.txt")
    header_lines = [
        f"# OCR candidate for {source_path.name}",
        f"# quality: {result.quality} "
        f"(mean conf {result.mean_confidence:.1f}%, "
        f"{len(result.per_page_confidence)} pages, "
        f"{result.total_chars} chars)",
        f"# lang: {result.lang}",
        f"# generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if result.failure_reason:
        header_lines.append(f"# failure: {result.failure_reason}")
    header_lines.extend(
        [
            "# NOTE: review this file before grounding consumes it. Edit",
            "# corrections in place. Delete this header block to mark the",
            "# candidate as human-reviewed and silence the candidate-warning",
            "# gate on the next grounding run.",
            "",
        ]
    )
    cache_path.write_text("\n".join(header_lines) + "\n" + result.text, encoding="utf-8")
    return cache_path


def has_unreviewed_header(cache_path: Path) -> bool:
    """True when the cache file still carries the tool-generated header.

    A file with no ``# OCR candidate for`` comment line is considered
    human-reviewed (the agent edited the candidate or it was always a
    sibling text file). The grounding gate uses this to suppress
    OCR-CANDIDATE warnings on subsequent runs once an agent has signed
    off on the candidate by deleting the header.
    """
    if not cache_path.exists():
        return False
    try:
        head = cache_path.read_text(encoding="utf-8", errors="replace")[:500]
    except OSError:
        return False
    return head.startswith("# OCR candidate for ")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _aggregate_page(image_to_data_result: dict) -> tuple[str, float]:
    """Reduce pytesseract.image_to_data DICT output to (text, mean_conf).

    Skips entries with confidence == -1 (sentinel for layout boxes that
    contain no text, per pytesseract's convention).
    """
    words: list[str] = []
    confidences: list[float] = []
    for text, conf in zip(
        image_to_data_result.get("text", []),
        image_to_data_result.get("conf", []),
    ):
        if not text or not text.strip():
            continue
        try:
            conf_val = float(conf)
        except (TypeError, ValueError):
            continue
        if conf_val < 0:
            continue
        words.append(text)
        confidences.append(conf_val)
    return " ".join(words), _mean(confidences)


def _mean(values: list[float]) -> float:
    """Arithmetic mean, 0.0 on empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def _classify_quality(mean_conf: float, total_chars: int) -> OcrQuality:
    if mean_conf >= GOOD_CONFIDENCE_MIN and total_chars >= GOOD_CHAR_MIN:
        return "good"
    if mean_conf >= CANDIDATE_CONFIDENCE_MIN and total_chars >= FAILED_CHAR_MIN:
        return "candidate"
    return "failed"


def _build_failure_reason(mean_conf: float, total_chars: int) -> str:
    parts: list[str] = []
    if mean_conf < CANDIDATE_CONFIDENCE_MIN:
        parts.append(f"mean confidence {mean_conf:.1f}% < {CANDIDATE_CONFIDENCE_MIN:.0f}%")
    if total_chars < FAILED_CHAR_MIN:
        parts.append(f"only {total_chars} chars extracted (< {FAILED_CHAR_MIN})")
    if not parts:
        # Both thresholds met for "candidate" but caller still classified
        # as failed - shouldn't happen given _classify_quality, but be
        # defensive.
        parts.append("unknown failure")
    return "; ".join(parts)
