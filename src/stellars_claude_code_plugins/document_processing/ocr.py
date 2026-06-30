"""OCR fallback for scanned PDFs - pure-Python, no OS dependency.

Reads and rasterises each page with OnnxTR's ``DocumentFile`` (PDFium
under the hood, no system poppler) and recognises text with an ONNX
detection + recognition model (no system tesseract). The model weights
are bundled in the package (``document_processing/models/*.onnx``) and
loaded by local path, so OCR runs fully offline - no first-run
download. The ``cpu-headless`` OnnxTR extra pulls
``opencv-python-headless``, so there is no ``libGL`` system dependency
either.

Callers get full-text extraction PLUS quality metrics in one call. The
companion ``cache_ocr_candidate`` always writes the result to
``<stem>.ocr.txt`` next to the source so:

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

The OCR stack ships with the package (core dependencies + bundled
models), so ``ocr_available()`` only verifies the imports and the model
files. If either is missing (broken install), the caller emits
OCR-MISSING and points the agent at vision-OCR via the Read tool.

``ocr_pdf`` keeps ``lang`` as a positional arg for the sidecar record
and CLI flow, but the bundled recognition model is latin-script and is
not switched per language - ``lang`` is advisory metadata, not a model
selector.
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

# Bundled ONNX models (shipped as package-data, loaded by local path -> offline).
_MODELS_DIR = Path(__file__).resolve().parent / "models"
_DET_ONNX = _MODELS_DIR / "db_mobilenet_v3_large.onnx"
_RECO_ONNX = _MODELS_DIR / "crnn_mobilenet_v3_small.onnx"


class OcrUnavailable(Exception):
    """Raised when OCR is requested but the engine / models are missing.

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
    """True iff the OCR engine imports AND the bundled models are present."""
    try:
        from onnxtr.io import DocumentFile  # noqa: F401
        from onnxtr.models import ocr_predictor  # noqa: F401
    except ImportError:
        return False
    return _DET_ONNX.is_file() and _RECO_ONNX.is_file()


def install_hint() -> str:
    """Human-readable install instruction for the OCR engine."""
    return (
        "The OCR engine (onnxtr) and its models ship with the package - "
        "reinstall `stellars-claude-code-plugins` if the import or the "
        "bundled models failed to load. No system binary is required."
    )


def ocr_pdf(path: Path, lang: str, *, dpi: int = 200) -> OcrResult:
    """Run OCR on every page of the PDF, return text + quality metrics.

    ``lang`` is recorded on the result (sidecar metadata) but does not
    select a model - the bundled recognition model is latin-script.

    Raises ``OcrUnavailable`` when the OCR engine fails to import or
    initialise, so the caller can fall back to OCR-MISSING gate
    behaviour.
    """
    if not ocr_available():
        raise OcrUnavailable(install_hint())

    from onnxtr.io import DocumentFile

    try:
        engine = _engine()
    except Exception as exc:  # model load / construction failure
        raise OcrUnavailable(f"OnnxTR initialisation failed: {exc}") from exc

    try:
        doc = DocumentFile.from_pdf(str(path), scale=dpi / 72.0)
        result = engine(doc)
    except Exception as exc:
        return OcrResult(
            text="",
            mean_confidence=0.0,
            per_page_confidence=[],
            total_chars=0,
            quality="failed",
            failure_reason=f"OnnxTR OCR failed: {exc}",
            lang=lang,
        )

    page_texts: list[str] = []
    page_confidences: list[float] = []
    for page in result.pages:
        page_texts.append(page.render())
        word_confidences = [
            word.confidence * 100.0
            for block in page.blocks
            for line in block.lines
            for word in line.words
        ]
        page_confidences.append(_mean(word_confidences))

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

# Lazily-constructed OnnxTR predictor, reused across pages and calls so the
# ONNX models load once per process rather than per PDF.
_ENGINE = None


def _engine():
    """Return the process-wide OnnxTR predictor, built from the bundled models."""
    global _ENGINE
    if _ENGINE is None:
        from onnxtr.models import crnn_mobilenet_v3_small, db_mobilenet_v3_large, ocr_predictor

        det = db_mobilenet_v3_large(model_path=str(_DET_ONNX))
        reco = crnn_mobilenet_v3_small(model_path=str(_RECO_ONNX))
        _ENGINE = ocr_predictor(det_arch=det, reco_arch=reco)
    return _ENGINE


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
