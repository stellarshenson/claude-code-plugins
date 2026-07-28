"""CLI entry point for document-processing tools.

Grounding, claim extraction, consistency, and calibration delegate to the
standalone ``groundrails`` engine; this CLI adds the document-reading layer
(PDF/DOCX/OCR), the multi-document ``validate`` orchestration, and the
``train-lexical`` manifold trainer that groundrails expects the consumer to own.

Subcommands:
    ground             - ground claims against sources (--claim, or --manifest for many)
    extract-claims     - heuristic sentence-to-claim extractor for a document
    check-consistency  - intra-document numeric/entity divergence detector
    validate           - grounding + self-consistency over one or many documents
    calibrate          - fit/update the Bayesian grounding-verdict calibrator
    config             - show config / transfer learned calibrator weights into it
    train-lexical      - fit a lexical effort-tier manifold from labelled data
    setup              - provision groundrails (init); writes the readiness token
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import sys

import groundrails
from groundrails import GroundingMatch, ground, ground_batch
from groundrails import settings as gr_settings
from groundrails.config import load_document_processing_config

from stellars_claude_code_plugins.document_processing import extractors
from stellars_claude_code_plugins.document_processing import ocr as ocr_mod
from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    enforce_warning_acks,
)

# document-processing grounds against the standalone groundrails engine. The
# project-local override dir matches groundrails' own config resolution
# (./.stellars-plugins/config_document_processing.yaml).
PROJECT_OVERRIDE_DIR = Path(".stellars-plugins")


def _default_home() -> str:
    """Stable per-user home for groundrails' readiness token (``groundrails.json``).

    Keeps the token out of arbitrary working directories. Honours an explicit
    ``GROUNDRAILS_HOME`` when the caller set one.
    """
    return os.environ.get("GROUNDRAILS_HOME") or str(
        Path.home() / ".stellars-plugins" / "groundrails"
    )


# What `--semantic` actually needs at run time. `ground_batch(semantic=True)` builds
# `groundrails.semantic_ov.SemanticCascade` (bge-m3 + reranker + mDeBERTa NLI as
# OpenVINO IRs) - NOT the legacy ONNX `semantic.SemanticGrounder`. Mirrors
# `semantic_ov.is_available()`; checking the ONNX layer's deps instead blocks runs
# that would work and misses `openvino`, the one that matters.
_SEMANTIC_MODULES = ("openvino", "transformers", "huggingface_hub")

#: File every cascade repo is loaded from; `setup --semantic` mirrors these repos.
_SEMANTIC_MODEL_FILE = "openvino_model.xml"


def _missing_semantic_components(*, models: bool = True) -> list[str]:
    """Cascade components absent from this machine - modules first, then models.

    Models are probed against the local cache only, never the network: the point
    is to answer before the run starts, offline, in milliseconds. Pass
    ``models=False`` from ``setup``, whose whole job is to fetch them - checking
    there would make the command refuse to do the thing that satisfies the check.
    """
    missing = [m for m in _SEMANTIC_MODULES if importlib.util.find_spec(m) is None]
    if missing or not models:
        return missing  # cannot probe the cache without huggingface_hub itself

    import groundrails.semantic_ov as gr_ov
    from huggingface_hub import try_to_load_from_cache

    # Read the repo list off groundrails rather than restating it: these are the
    # same repos `setup --semantic` mirrors, so the check and the remedy cannot
    # drift apart into a loop where the fix never satisfies the check.
    for repo in sorted(gr_ov.HF_REPOS.values()):
        if try_to_load_from_cache(repo, _SEMANTIC_MODEL_FILE) is None:
            missing.append(f"model {repo}")
    return missing


def _preflight_semantic(*, models: bool = True) -> None:
    """Refuse a --semantic run whose cascade is incomplete.

    groundrails does not refuse: it isolates the failure per claim, substitutes an
    empty match and still exits 0, so an incomplete cascade yields a report scoring
    0% that reads exactly like a document grounding nowhere. Checking up front is
    what turns that into an error the operator cannot miss.
    """
    missing = _missing_semantic_components(models=models)
    if not missing:
        return
    print(
        "ERROR: --semantic needs the grounding cascade; these components are "
        f"missing: {', '.join(missing)}\n"
        "  modules -> pip install 'stellars-claude-code-plugins[semantic]'\n"
        "  models  -> document-processing setup --semantic   (~1.4 GB, one time)\n"
        "Lexical grounding needs neither - drop --semantic to run it.",
        file=sys.stderr,
    )
    raise SystemExit(2)


def _ensure_ready(*, semantic: bool = False) -> None:
    """Satisfy groundrails' readiness gate before any grounding call.

    ``ground``/``ground_batch`` raise ``NotInitializedError`` until groundrails
    is initialised. We first try an existing ``groundrails.json`` (written by
    ``document-processing setup``), then lazy-init the offline lexical path
    (bundled calibration, no model downloads). A ``semantic`` run is preflighted
    first: groundrails degrades per claim instead of refusing, so the check has
    to happen here.
    """
    os.environ.setdefault("GROUNDRAILS_HOME", _default_home())
    if semantic:
        _preflight_semantic()
    if gr_settings.is_ready():
        return
    try:
        gr_settings.load_config_file()
    except Exception:  # noqa: BLE001 - absent/unreadable token -> fall through to init
        pass
    if gr_settings.is_ready():
        return
    # Lazy offline init for the lexical path. Semantic models are NOT fetched
    # here; run `document-processing setup` (groundrails init) for the cascade.
    groundrails.init(models="none")


def _grounding_config(args: argparse.Namespace):
    """Load groundrails' grounding config, overlaying the ``--effort`` tier.

    The effort tier (low/medium/high) is the single lexical knob; groundrails
    sets it via ``GroundingConfig.overlay`` rather than a ``ground`` kwarg.
    """
    cfg = load_document_processing_config()
    effort = getattr(args, "effort", None)
    if effort:
        cfg = cfg.overlay(lexical_effort=effort)
    return cfg


# Binary extensions rejected outright. Silent U+FFFD decode of a PDF/PNG
# is the #1 reason grounding returns zero hits with no diagnostic.
_BINARY_EXTENSIONS = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".pdf",
        ".zip",
        ".xlsx",
        ".xls",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".odt",
        ".ods",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".mp3",
        ".wav",
        ".flac",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
    }
)

# Magic-byte signatures (first 16 bytes). Catches renamed/extensionless binaries.
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"GIF87a", "GIF image"),
    (b"GIF89a", "GIF image"),
    (b"%PDF", "PDF document"),
    (b"PK\x03\x04", "ZIP-family archive (xlsx/docx/pptx/zip)"),
    (b"PK\x05\x06", "ZIP-family archive (empty)"),
    (b"PK\x07\x08", "ZIP-family archive (spanned)"),
    (b"\xd0\xcf\x11\xe0", "legacy OLE2 (doc/xls/ppt)"),
    (b"\x1f\x8b", "gzip archive"),
    (b"BZh", "bzip2 archive"),
    (b"7z\xbc\xaf\x27\x1c", "7z archive"),
    (b"Rar!\x1a\x07", "RAR archive"),
    (b"ftyp", "mp4/mov (offset 4)"),
]


def _sniff_binary(path: Path) -> str | None:
    """Return a description if the file is binary, else None.

    Checks extension first (cheap), then magic bytes (catches renames and
    extensionless files). Returns the binary-type description for the
    caller's error message; ``None`` means "looks text-shaped".
    """
    ext = path.suffix.lower()
    if ext in _BINARY_EXTENSIONS:
        return f"{ext} file"
    try:
        head = path.read_bytes()[:16]
    except OSError:
        return None
    for sig, description in _MAGIC_SIGNATURES:
        if sig == b"ftyp":
            if len(head) >= 8 and head[4:8] == b"ftyp":
                return description
        elif head.startswith(sig):
            return description
    return None


def _read_sources(
    paths: list[str],
    *,
    scanned_threshold: int = extractors.DEFAULT_SCANNED_THRESHOLD,
    ocr_lang: str | None = None,
    warnings: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Read source files with format-aware extractors + scanned-PDF fallback.

    Pipeline per source:

    1. Plain text / .md / .rst / .docx / .odt / .rtf / .html → extract.
    2. PDF with extractable text → pypdf extraction.
    3. PDF with near-empty extracted text (scanned) →
       a. find sibling (``<stem>.ocr.txt``, ``<stem>.txt``, ``.docx`` etc).
       b. fall through to auto-OCR if ``--ocr-lang`` provided AND OCR
          extras installed; cache result as ``<stem>.ocr.txt``.
       c. otherwise emit OCR-LANG-NEEDED or OCR-MISSING warning and
          skip the source so grounding does not silently produce empty
          hits.
    4. Unsupported formats → emit SKIPPED warning, skip source.
    5. UTF-8 decode failure on a text source → emit SKIPPED warning,
       skip source.

    All non-success outcomes append to ``warnings`` (caller passes the
    same list to ``enforce_warning_acks``). The function never calls
    ``sys.exit`` directly - the gate is responsible for blocking when
    the agent has not acked the warnings.
    """
    if warnings is None:
        warnings = []

    out: list[tuple[str, str]] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            warnings.append(f"SOURCE-MISSING: {p} not found - skipped.")
            continue

        # Try the format-aware dispatch first. If extract_text raises
        # UnsupportedFormat, fall through to a SKIPPED warning rather
        # than the historical exit 2.
        try:
            extracted = extractors.extract_text(path, scanned_threshold=scanned_threshold)
        except extractors.UnsupportedFormat as exc:
            # Last resort: try the historical UTF-8 read for files that
            # have an unfamiliar extension but are actually plain text.
            binary_kind = _sniff_binary(path)
            if binary_kind is None:
                try:
                    fallback = path.read_text(encoding="utf-8", errors="strict")
                except (UnicodeDecodeError, OSError):
                    warnings.append(f"SOURCE-SKIPPED: {p} - {exc}")
                    continue
                out.append((str(path), fallback))
                continue
            warnings.append(f"SOURCE-SKIPPED: {p} - {exc}")
            continue
        except OSError as exc:
            warnings.append(f"SOURCE-SKIPPED: {p} - read failed: {exc}")
            continue

        if extracted.kind != "pdf-scanned":
            out.append((str(path), extracted.text))
            continue

        # --- Scanned PDF fallback chain ---
        sibling = extractors.find_sibling(path)
        if sibling is not None:
            try:
                sibling_extracted = extractors.extract_text(
                    sibling, scanned_threshold=scanned_threshold
                )
            except (extractors.UnsupportedFormat, OSError) as exc:
                warnings.append(
                    f"SOURCE-SKIPPED: {path.name} sibling {sibling.name} could not be read - {exc}"
                )
                continue
            # If the sibling is itself a tool-generated OCR candidate
            # whose header is still in place, surface OCR-CANDIDATE so
            # the agent reviews before the candidate becomes ground
            # truth. Removing the header marks it as reviewed.
            if sibling.name == path.stem + ".ocr.txt" and ocr_mod.has_unreviewed_header(sibling):
                warnings.append(
                    f"OCR-CANDIDATE: {path.name} -> using cached candidate {sibling.name} "
                    f"(unreviewed - header still present). Open the file, scan for "
                    f"transcription errors (numbers, names, technical terms), edit "
                    f"corrections in place, delete the header block to mark reviewed, "
                    f"OR ack 'candidate-accepted-as-is' if a quick scan shows it is fine."
                )
            else:
                warnings.append(
                    f"OCR-FALLBACK: {path.name} -> sibling {sibling.name} (text extracted)."
                )
            out.append((str(path), sibling_extracted.text))
            continue

        # No sibling. Need OCR. Language is the agent's call.
        if ocr_lang is None:
            suggested = extractors.infer_pdf_language(extracted.text, path)
            warnings.append(
                f"OCR-LANG-NEEDED: {path.name} is a scanned PDF with no sibling text "
                f"file. OCR requires a language model - inspect the document (filename, "
                f"any visible page text via Read tool) and rerun with "
                f"`--ocr-lang <code>` (suggested from sparse extraction: "
                f"`--ocr-lang {suggested}`). Source SKIPPED until language is supplied."
            )
            continue

        if not ocr_mod.ocr_available():
            warnings.append(
                f"OCR-MISSING: {path.name} is a scanned PDF, no sibling found, OCR "
                f"engine unavailable. {ocr_mod.install_hint()} "
                f"OR Claude-OCR via the Read tool with `pages=N` per page, transcribe "
                f"in the source language ({ocr_lang}), save as {path.stem}.ocr.txt "
                f"next to the source, rerun. Source SKIPPED."
            )
            continue

        try:
            result = ocr_mod.ocr_pdf(path, ocr_lang)
        except ocr_mod.OcrUnavailable as exc:
            warnings.append(f"OCR-MISSING: {path.name} - {exc}. Source SKIPPED.")
            continue

        cache_path = ocr_mod.cache_ocr_candidate(path, result)

        if result.quality == "good":
            warnings.append(
                f"OCR-FALLBACK: {path.name} -> auto-OCR (lang={ocr_lang}, mean conf "
                f"{result.mean_confidence:.0f}%, cached as {cache_path.name}; review "
                f"optional)."
            )
            out.append((str(path), result.text))
        elif result.quality == "candidate":
            warnings.append(
                f"OCR-CANDIDATE: {path.name} -> auto-OCR produced usable but mid-confidence "
                f"text (lang={ocr_lang}, mean conf {result.mean_confidence:.0f}%, "
                f"{result.total_chars} chars). Candidate cached as {cache_path.name}. "
                f"Review and edit corrections in place before acking, OR ack "
                f"'candidate-accepted-as-is' if a quick scan shows it is fine."
            )
            out.append((str(path), result.text))
        else:  # failed
            warnings.append(
                f"OCR-FAILED: {path.name} -> auto-OCR produced low-quality text "
                f"(lang={ocr_lang}, mean conf {result.mean_confidence:.0f}%, "
                f"{result.total_chars} chars). Reason: {result.failure_reason}. "
                f"Candidate cached as {cache_path.name} for editing. Recommended: "
                f"do vision-OCR via Read tool on {path.name}, replace {cache_path.name} "
                f"with corrected transcript, rerun. Source SKIPPED."
            )
            # Source NOT appended - text is too poor for grounding to
            # be honest about hits/misses.

    return out


def _loc_str(loc) -> str:
    """Format a Location as 'path:line:col p<para> pg<page>'."""
    parts = []
    if loc.source_path:
        parts.append(loc.source_path)
    parts.append(f"L{loc.line_start}:C{loc.column_start}")
    if loc.line_end != loc.line_start:
        parts[-1] += f"-L{loc.line_end}:C{loc.column_end}"
    parts.append(f"¶{loc.paragraph}")
    if loc.page > 1:
        parts.append(f"pg{loc.page}")
    return " ".join(parts)


def _match_line(m: GroundingMatch) -> str:
    """One-line summary showing all layer scores with winning location."""
    if m.match_type == "exact":
        loc = _loc_str(m.exact_location)
        winning = m.exact_matched_text
    elif m.match_type == "fuzzy":
        loc = _loc_str(m.fuzzy_location)
        winning = m.fuzzy_matched_text
    elif m.match_type == "bm25":
        loc = _loc_str(m.bm25_location)
        winning = m.bm25_matched_text
    elif m.match_type == "semantic":
        loc = _loc_str(m.semantic_location)
        winning = m.semantic_matched_text
    elif m.match_type == "contradicted":
        # Show the winning-passage location even in contradicted mode
        if m.semantic_score > 0:
            loc = _loc_str(m.semantic_location)
            winning = m.semantic_matched_text
        elif m.bm25_score > 0:
            loc = _loc_str(m.bm25_location)
            winning = m.bm25_matched_text
        else:
            loc = _loc_str(m.fuzzy_location)
            winning = m.fuzzy_matched_text
    else:
        loc = "(no match)"
        winning = m.semantic_matched_text or m.bm25_matched_text or m.fuzzy_matched_text

    mismatch_info = ""
    if m.numeric_mismatches or m.entity_mismatches:
        mismatches = m.numeric_mismatches + m.entity_mismatches
        mismatch_info = f" mismatches={mismatches}"

    return (
        f"{m.match_type.upper()} "
        f"exact={m.exact_score:.3f} fuzzy={m.fuzzy_score:.3f} "
        f"bm25={m.bm25_score:.3f} semantic={m.semantic_score:.3f} "
        f"agreement={m.agreement_score:.3f}{mismatch_info} @ {loc} | {winning!r}"
    )


def _read_claims_manifest(path_str: str) -> list[str]:
    """Read a claims manifest: a JSON list of strings or ``{claim, ...}`` objects."""
    claims_path = Path(path_str)
    if not claims_path.is_file():
        print(f"ERROR: claims manifest not found: {path_str}", file=sys.stderr)
        raise SystemExit(1)
    raw = json.loads(claims_path.read_text(encoding="utf-8"))
    if isinstance(raw, list) and all(isinstance(x, str) for x in raw):
        return raw
    if isinstance(raw, list) and all(isinstance(x, dict) and "claim" in x for x in raw):
        return [x["claim"] for x in raw]
    print(
        "ERROR: claims manifest must be a JSON list of strings or objects with a 'claim' key",
        file=sys.stderr,
    )
    raise SystemExit(1)


def cmd_ground(args: argparse.Namespace) -> int:
    source_warnings: list[str] = []
    sources = _read_sources(
        args.source,
        scanned_threshold=getattr(args, "scanned_threshold", extractors.DEFAULT_SCANNED_THRESHOLD),
        ocr_lang=getattr(args, "ocr_lang", None),
        warnings=source_warnings,
    )
    enforce_warning_acks(
        source_warnings,
        sys.argv[1:],
        getattr(args, "ack_warning", []) or [],
    )
    if not sources:
        print(
            "ERROR: every source was skipped (see warnings above) or no --source was provided",
            file=sys.stderr,
        )
        return 1
    # groundrails builds the semantic + NLI + calibrated-verdict bundle internally
    # when semantic=True; the lexical layers always run. Satisfy the readiness gate
    # first, then apply the --effort tier via the grounding config.
    enabled = bool(getattr(args, "semantic", False))
    _ensure_ready(semantic=enabled)
    gcfg = _grounding_config(args)

    # Batch mode: --manifest carries many claims -> ground_batch + report.
    if getattr(args, "manifest", None):
        claims = _read_claims_manifest(args.manifest)
        matches = ground_batch(
            claims,
            sources,
            fuzzy_threshold=args.threshold,
            bm25_threshold=args.bm25_threshold,
            semantic_threshold=args.semantic_threshold,
            semantic_threshold_percentile=getattr(args, "semantic_threshold_percentile", None),
            semantic=enabled,
            config=gcfg,
            primary_source=getattr(args, "primary_source", None),
            max_workers=getattr(args, "workers", 5),
        )
        return _emit_batch_report(matches, args)

    # Single claim.
    m = ground(
        args.claim,
        sources,
        fuzzy_threshold=args.threshold,
        bm25_threshold=args.bm25_threshold,
        semantic_threshold=args.semantic_threshold,
        semantic_threshold_percentile=getattr(args, "semantic_threshold_percentile", None),
        semantic=enabled,
        config=gcfg,
    )
    if args.json:
        print(json.dumps(asdict(m), indent=2))
    else:
        print(_match_line(m))
    # Exit 0 if grounded, 1 if none
    return 0 if m.match_type != "none" else 1


def _emit_batch_report(matches, args: argparse.Namespace) -> int:
    """Render the batch grounding report (markdown or JSON) + stderr summary;
    return exit code (0 when nothing is unconfirmed, else 1)."""
    exact = sum(1 for m in matches if m.match_type == "exact")
    fuzzy = sum(1 for m in matches if m.match_type == "fuzzy")
    bm25 = sum(1 for m in matches if m.match_type == "bm25")
    semantic = sum(1 for m in matches if m.match_type == "semantic")
    contradicted = sum(1 for m in matches if m.match_type == "contradicted")
    none = sum(1 for m in matches if m.match_type == "none")
    total = len(matches)
    grounded = exact + fuzzy + bm25 + semantic

    if args.output:
        if args.json:
            payload = {
                "summary": {
                    "total": total,
                    "exact": exact,
                    "fuzzy": fuzzy,
                    "bm25": bm25,
                    "semantic": semantic,
                    "contradicted": contradicted,
                    "none": none,
                    "grounded": grounded,
                    "grounding_score": grounded / total if total else 0.0,
                },
                "matches": [asdict(m) for m in matches],
            }
            Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            lines = [
                "# Source Grounding Report",
                "",
                f"- Total claims: {total}",
                f"- Exact: {exact}",
                f"- Fuzzy: {fuzzy}",
                f"- BM25: {bm25}",
                f"- Semantic: {semantic}",
                f"- Contradicted: {contradicted}",
                f"- Unconfirmed: {none}",
                f"- Grounding score: {grounded}/{total} ({100 * grounded / total:.1f}%)"
                if total
                else "- Grounding score: 0/0 (N/A)",
                "",
                "## Matches",
                "",
            ]
            for i, m in enumerate(matches, 1):
                status = {
                    "exact": "CONFIRMED",
                    "fuzzy": "CONFIRMED (fuzzy)",
                    "bm25": "CONFIRMED (bm25 / topical)",
                    "semantic": "CONFIRMED (semantic)",
                    "contradicted": "CONTRADICTED",
                    "none": "UNCONFIRMED",
                }[m.match_type]
                verify_tag = " - VERIFY" if m.verification_needed else ""
                lines.append(
                    f"### {i}. {status}{verify_tag} (exact {m.exact_score:.3f}, "
                    f"fuzzy {m.fuzzy_score:.3f}, bm25 {m.bm25_score:.3f}, "
                    f"semantic {m.semantic_score:.3f})"
                )
                lines.append(f"**Claim**: {m.claim!r}")
                if m.grounded_source:
                    primary_flag = "" if m.is_primary_source else " [NON-PRIMARY]"
                    lines.append(f"**Source file**: `{m.grounded_source}`{primary_flag}")
                if m.verification_needed:
                    signals: list[str] = []
                    if m.match_type == "semantic" and not m.lexical_co_support:
                        signals.append("no lexical co-support")
                    if not m.is_primary_source:
                        signals.append("grounded on non-primary source")
                    if (
                        m.claim_attributes.get("numbers")
                        and m.claim_attributes.get("passage_numbers")
                        and not m.numeric_mismatches
                    ):
                        signals.append("numeric co-presence without clear mismatch")
                    if not signals:
                        signals.append("score near threshold")
                    lines.append(f"**Verification**: second-guess signals - {', '.join(signals)}")
                    attrs = m.claim_attributes
                    if attrs.get("numbers") or attrs.get("passage_numbers"):
                        lines.append(
                            f"  - Claim numbers: {attrs.get('numbers', [])}  |  "
                            f"Passage numbers: {attrs.get('passage_numbers', [])}"
                        )
                    if attrs.get("entities") or attrs.get("passage_entities"):
                        lines.append(
                            f"  - Claim entities: {attrs.get('entities', [])}  |  "
                            f"Passage entities: {attrs.get('passage_entities', [])}"
                        )
                if m.exact_score == 1.0:
                    lines.append(
                        f"**Exact match**: {m.exact_matched_text!r} @ {_loc_str(m.exact_location)}"
                    )
                    if m.exact_location.context_before or m.exact_location.context_after:
                        lines.append(
                            f"  - Context: …{m.exact_location.context_before}"
                            f" **{m.exact_matched_text}** "
                            f"{m.exact_location.context_after}…"
                        )
                if m.fuzzy_score > 0:
                    lines.append(
                        f"**Best fuzzy**: {m.fuzzy_matched_text!r} @ "
                        f"{_loc_str(m.fuzzy_location)} (ratio {m.fuzzy_score:.3f})"
                    )
                if m.bm25_score > 0:
                    lines.append(
                        f"**Best BM25 passage** (token recall {m.bm25_score:.3f}, "
                        f"raw {m.bm25_raw_score:.3f}) @ {_loc_str(m.bm25_location)}:"
                    )
                    snippet = m.bm25_matched_text[:200].replace("\n", " ")
                    lines.append(f"  > {snippet}{'…' if len(m.bm25_matched_text) > 200 else ''}")
                if m.semantic_score > 0:
                    lines.append(
                        f"**Best semantic passage** (cosine {m.semantic_score:.3f}) @ "
                        f"{_loc_str(m.semantic_location)}:"
                    )
                    snippet = m.semantic_matched_text[:200].replace("\n", " ")
                    lines.append(
                        f"  > {snippet}{'…' if len(m.semantic_matched_text) > 200 else ''}"
                    )
                if (
                    m.exact_score == 0
                    and m.fuzzy_score == 0
                    and m.bm25_score == 0
                    and m.semantic_score == 0
                ):
                    lines.append("**Match**: (no signal from any layer)")
                lines.append("")
            Path(args.output).write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        for m in matches:
            print(_match_line(m))

    print(
        f"\n{total} claims: {exact} exact, {fuzzy} fuzzy, {bm25} bm25, "
        f"{semantic} semantic, {none} unconfirmed. "
        f"score={grounded}/{total} ({100 * grounded / total:.1f}%)"
        if total
        else "0 claims",
        file=sys.stderr,
    )
    return 0 if none == 0 else 1


def _add_source_format_args(parser: argparse.ArgumentParser) -> None:
    """Register the source-format / OCR flags shared by the grounding commands.

    ``--ocr-lang`` is intentionally not defaulted - the agent inspects each
    scanned PDF and records its language. The bundled OnnxTR recognition
    model is latin-script and not switched per language, so the code is
    advisory metadata for the sidecar record. The CLI fires OCR-LANG-NEEDED
    through the warning-ack gate when a scanned PDF is detected and the flag
    is missing, with a suggested code from filename / partial-PDF inference.
    """
    parser.add_argument(
        "--ocr-lang",
        dest="ocr_lang",
        default=None,
        help=(
            "Language code recorded for auto-OCR of scanned PDFs (e.g. eng, "
            "deu, fra, spa). Advisory metadata for the sidecar record - the "
            "bundled OnnxTR model is latin-script and is not switched per "
            "language. REQUIRED when any --source is a scanned PDF without a "
            "sibling text file (the OCR-LANG-NEEDED gate). Inspect the "
            "document (filename tokens, visible page text via the Read tool) "
            "and supply the detected language; the tool suggests a code from "
            "sparse extraction if you omit the flag, then asks you to rerun."
        ),
    )
    parser.add_argument(
        "--scanned-threshold",
        dest="scanned_threshold",
        type=int,
        default=extractors.DEFAULT_SCANNED_THRESHOLD,
        help=(
            f"Chars-per-page threshold below which a PDF is classified as "
            f"scanned (default {extractors.DEFAULT_SCANNED_THRESHOLD}). Tune "
            f"upward for heavy-image PDFs with sparse legitimate captions."
        ),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="document-processing",
        description="Document processing tools: source grounding, compliance checks.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser(
        "ground",
        help="Ground claims against sources (regex + Levenshtein + BM25; --semantic adds the bundle).",
        description=(
            "Grounding only. One claim via --claim, or many via --manifest (a "
            "claims file). Three lexical layers always run - regex exact, "
            "Levenshtein partial-ratio, BM25 token-recall; all scores reported. "
            "--semantic adds the embedding + NLI entailment + calibrated-verdict "
            "bundle. Single-claim mode prints one match line (exit 0 if grounded, "
            "1 if not); manifest mode writes a report."
        ),
    )
    claim_src = g.add_mutually_exclusive_group(required=True)
    claim_src.add_argument("--claim", help="A single claim to locate (single-claim mode)")
    claim_src.add_argument(
        "--manifest",
        help="Claims manifest path (JSON list of strings or {claim,...}); batch mode -> report",
    )
    g.add_argument(
        "--source",
        action="append",
        default=[],
        required=True,
        help="Source file path (repeatable)",
    )
    g.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Levenshtein ratio threshold for 'fuzzy' classification (default 0.85)",
    )
    g.add_argument(
        "--bm25-threshold",
        type=float,
        default=0.5,
        help="BM25 token-recall threshold for 'bm25' classification (default 0.5)",
    )
    g.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.6,
        help="Semantic cosine-similarity threshold for 'semantic' classification (default 0.6)",
    )
    g.add_argument(
        "--semantic-threshold-percentile",
        type=float,
        default=None,
        help=(
            "Model-agnostic percentile threshold (H3): fraction of random chunk-pair "
            "cosines that count as the tail (e.g. 0.02 = top 2%%). Overrides "
            "--semantic-threshold when set. Self-calibrates when embedding model swaps."
        ),
    )
    g.add_argument(
        "--semantic",
        action="store_true",
        help=(
            "Enable the semantic bundle (embedding retrieval + NLI entailment + "
            "calibrated verdict) for this call; default off = three lexical layers only"
        ),
    )
    g.add_argument(
        "--primary-source",
        dest="primary_source",
        default=None,
        help=(
            "Path of the one source expected to ground the claims. Any claim "
            "grounded elsewhere gets flagged verification_needed=True "
            "(cross-source pollution signal, WI#3). Manifest mode."
        ),
    )
    g.add_argument(
        "--output",
        help="Manifest mode: write the report to this path instead of stdout",
    )
    g.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON (the full match in single-claim mode, the report in manifest mode)",
    )
    g.add_argument(
        "--workers",
        type=int,
        default=5,
        help=(
            "Manifest mode: worker threads for per-claim grounding (default 5). "
            "Parallelises the semantic path (bge-m3 embedding, reranker, NLI); "
            "sources are indexed once up front. Set 1 to run serial."
        ),
    )
    g.add_argument(
        "--effort",
        choices=["low", "medium", "high"],
        default=None,
        help=(
            "Lexical effort tier (the single lexical knob): low (13 feat, core "
            "only), medium (16, +lingua +WordNet), high (18, +MT translate-then-"
            "recall). Default = the config's lexical_effort (high)."
        ),
    )
    _add_source_format_args(g)
    add_ack_warning_arg(g)
    g.set_defaults(func=cmd_ground)

    # extract-claims subcommand
    ex = sub.add_parser(
        "extract-claims",
        help="Heuristic sentence-to-claim extractor; emits claims.json for `ground --manifest`.",
        description=(
            "Walk a markdown/text document and emit a list of claim candidates. "
            "Assigns stable IDs (c01, c02, ...), keeps order, drops sub-20-char "
            "stubs and headers. LOSSY - review claims.json before grounding."
        ),
    )
    ex.add_argument("--document", required=True, help="Source document (markdown or plain text)")
    ex.add_argument(
        "--output",
        help="Write claims.json to this path. When omitted, emits JSON to stdout.",
    )
    ex.set_defaults(func=cmd_extract_claims)

    # check-consistency subcommand
    cc = sub.add_parser(
        "check-consistency",
        help="Flag intra-document divergences (same category, different value).",
        description=(
            "Pure intra-document check; no source needed. Extracts numbers and "
            "named entities and reports categories where multiple distinct "
            "values appear. Catches failures grounding fundamentally cannot, "
            "e.g. 'dev/test/staging' on one page vs 'dev/staging/prod' on another."
        ),
    )
    cc.add_argument("--document", required=True, help="Document to analyse")
    cc.add_argument(
        "--output",
        help="Write markdown consistency report to this path. When omitted, prints to stdout.",
    )
    cc.set_defaults(func=cmd_check_consistency)

    # validate subcommand (grounding + self-consistency, one or many documents)
    vm = sub.add_parser(
        "validate",
        help="Validate documents: grounding + self-consistency. --document(s) or --manifest.",
        description=(
            "Grounding + rules (self-consistency) over one or many documents. "
            "Inline: --document FILE (repeatable) + --source (shared). Manifest: "
            "--manifest source_map.yaml (per-document sources embedded). Each "
            "document -> grounding-report.md + consistency-report.md under "
            "--output-dir. --semantic adds the embedding + NLI + calibrated-"
            "verdict bundle. (Tone/style/format compliance is layered by the "
            "validate skill, not this CLI.)"
        ),
    )
    vm_in = vm.add_mutually_exclusive_group(required=True)
    vm_in.add_argument(
        "--document",
        action="append",
        default=[],
        help="Document to validate (repeatable; >1 => batch). Pair with --source.",
    )
    vm_in.add_argument("--manifest", help="Path to source_map.yaml (per-document sources)")
    vm.add_argument(
        "--source",
        action="append",
        default=[],
        help="Source file path (repeatable); shared across --document inputs",
    )
    vm.add_argument(
        "--output-dir",
        required=True,
        help="Root output directory; one subdirectory per document is created under it.",
    )
    vm.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Levenshtein ratio threshold for 'fuzzy' classification (default 0.85)",
    )
    vm.add_argument(
        "--bm25-threshold",
        type=float,
        default=0.5,
        help="BM25 token-recall threshold for 'bm25' classification (default 0.5)",
    )
    vm.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.6,
        help="Semantic cosine threshold for 'semantic' classification (default 0.6)",
    )
    vm.add_argument(
        "--semantic-threshold-percentile",
        type=float,
        default=None,
        help="H3 percentile threshold; overrides --semantic-threshold when set.",
    )
    vm.add_argument(
        "--semantic",
        action="store_true",
        help=(
            "Enable the semantic bundle (embedding retrieval + NLI entailment + "
            "calibrated verdict); default off = three lexical layers only"
        ),
    )
    vm.add_argument(
        "--primary-source",
        dest="primary_source",
        default=None,
        help="Inline mode: the source expected to ground the claims (cross-source flag).",
    )
    vm.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort on the first document error (default: skip and continue).",
    )
    vm.add_argument(
        "--workers",
        type=int,
        default=5,
        help=(
            "Worker threads for per-claim grounding within each document "
            "(default 5). Parallelises the semantic path. Set 1 to run serial."
        ),
    )
    vm.add_argument(
        "--effort",
        choices=["low", "medium", "high"],
        default=None,
        help="Lexical effort tier (low/medium/high); default = config lexical_effort.",
    )
    vm.set_defaults(func=cmd_validate)

    # setup subcommand
    su = sub.add_parser(
        "setup",
        help="Provision groundrails and write the readiness token (groundrails.json).",
        description=(
            "Initialise the groundrails grounding engine: load the bundled "
            "calibration and write groundrails.json under GROUNDRAILS_HOME so "
            "grounding calls pass the readiness gate. Plain setup is offline "
            "(lexical only). Pass --semantic to also provision the OpenVINO "
            "cascade models (~1.4 GB) for embedding/NLI grounding."
        ),
    )
    su.add_argument(
        "--force",
        action="store_true",
        help="Re-provision even if groundrails.json already exists",
    )
    su.add_argument(
        "--semantic",
        action="store_true",
        help="Also provision the semantic cascade models (embedding + NLI; ~1.4 GB)",
    )
    su.set_defaults(func=cmd_setup)

    # calibrate subcommand
    ca = sub.add_parser(
        "calibrate",
        help="Fit/update the Bayesian grounding-verdict calibrator from labelled evidence.",
        description=(
            "Run the Bayesian calibrator (bambi / PyMC) over labelled grounding "
            "evidence. Each evidence record is grounded to extract its feature "
            "vector, then the calibrator is fit / incrementally updated and the "
            "posterior saved as a JSON profile. Actions: init (write the default "
            "prior profile), update (fit / update from evidence), eval (precision "
            "/ recall vs labels), show (print the posterior)."
        ),
    )
    ca.add_argument(
        "--action",
        choices=["init", "update", "eval", "show"],
        default="update",
        help="init | update (default) | eval | show",
    )
    ca.add_argument(
        "--evidence",
        help=(
            "Path to evidence JSON - a list of records: "
            '{"claim": str, "sources": [paths] (or "source_text": str), '
            '"label": 0|1, "lang"?: str, "weight"?: float}. '
            "Required for update / eval."
        ),
    )
    ca.add_argument(
        "--profile",
        default=".stellars-plugins/calibrator.json",
        help="Calibrator profile path to write/read (default .stellars-plugins/calibrator.json)",
    )
    ca.add_argument(
        "--from",
        dest="from_profile",
        default=None,
        help="Existing profile to update FROM (incremental: its posterior seeds the new prior)",
    )
    ca.add_argument(
        "--semantic",
        action="store_true",
        help=(
            "Extract evidence features with the semantic bundle on (embedding + "
            "NLI), so the calibrator learns the NLI weights it will deploy"
        ),
    )
    ca.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision threshold on P(grounded) (default 0.5)",
    )
    ca.add_argument("--draws", type=int, default=1000, help="Posterior draws (default 1000)")
    ca.add_argument("--tune", type=int, default=1000, help="Tuning steps (default 1000)")
    ca.add_argument(
        "--balance",
        choices=["balanced", "none"],
        default="balanced",
        help=(
            "Imbalanced-label handling for the fit (default balanced): "
            "'balanced' oversamples the minority class (seeded) to the majority "
            "count so the rare class influences the learned weights; 'none' fits "
            "the evidence as-is."
        ),
    )
    ca.set_defaults(func=cmd_calibrate)

    # config subcommand
    cf = sub.add_parser(
        "config",
        help="Inspect config and transfer learned calibrator weights into it.",
        description=(
            "show: print the resolved grounding config plus any calibration "
            "block. set-calibrator: read a fitted calibrator profile and write "
            "its learned coefficient means + threshold into the project config "
            "(.stellars-plugins/config_document_processing.yaml) as a "
            "'calibration:' block - so grounding uses the locally-learned "
            "weights with no fitting at run time."
        ),
    )
    cf.add_argument(
        "config_action", choices=["show", "set-calibrator"], help="show | set-calibrator"
    )
    cf.add_argument(
        "--profile",
        default=".stellars-plugins/calibrator.json",
        help="Calibrator profile to read (set-calibrator)",
    )
    cf.add_argument(
        "--config",
        default=None,
        help="Config yaml to write (default: project .stellars-plugins/config_document_processing.yaml)",
    )
    cf.set_defaults(func=cmd_config)

    # train-lexical subcommand
    tl = sub.add_parser(
        "train-lexical",
        help="Fit a lexical-mode effort-tier manifold from labelled data; write weights into config.",
        description=(
            "Fit the frozen-weight verdict manifold for ONE effort tier "
            "(low/medium/high) from one or more labelled datasets and write "
            "intercept + per-feature weights + threshold into the document-"
            "processing config (calibration.lexical_manifolds.<effort>).\n\n"
            "Dataset shape (parquet or jsonl, repeatable via --data; all files "
            "concatenated):\n"
            "  required columns - claim:str, source_text:str, label:int "
            "(1=supported / 0=hallucination)\n"
            "  optional column  - lang:str (claim ISO code; used by medium/high "
            "language features, else auto-detected)\n\n"
            "Minimum size (enforced) - >= 200 total rows with >= 40 of EACH class "
            "after concatenation; smaller sets are rejected with a clear error "
            "naming the counts found.\n\n"
            "Features use the SAME groundrails.lexical pipeline the "
            "grounder uses, so shipped weights match shipped features. All tier "
            "deps ship with the package (lingua, nltk/WordNet, the MT stack); "
            "training HARD-ERRORS if a feature dep is somehow unimportable (no "
            "silent degradation in the fit path). Client data is read in place, "
            "never copied or committed; only aggregate weights are written."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    tl.add_argument("--effort", choices=["low", "medium", "high"], required=True)
    tl.add_argument(
        "--data",
        action="append",
        required=True,
        help="Labelled dataset (parquet or jsonl); repeatable, concatenated",
    )
    tl.add_argument(
        "--out",
        default=None,
        help=(
            "Config yaml to write (default: project "
            ".stellars-plugins/config_document_processing.yaml)"
        ),
    )
    tl.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Decision threshold; tuned on the training data by macro-F1 when omitted",
    )
    tl.set_defaults(func=cmd_train_lexical)

    return parser


def _load_evidence_features(args: argparse.Namespace):
    """Ground each evidence record and assemble a calibration DataFrame.

    Evidence record: ``{claim, sources:[paths] | source_text, label, lang?,
    weight?}``. Each claim is grounded against its sources and turned into the
    calibrator's feature vector via ``grounding.extract_features``.
    """
    from groundrails.grounding import extract_features
    import pandas as pd

    if not args.evidence:
        print("ERROR: --evidence is required for this action", file=sys.stderr)
        raise SystemExit(2)
    raw = json.loads(Path(args.evidence).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("ERROR: evidence file must be a JSON list of records", file=sys.stderr)
        raise SystemExit(2)

    gcfg = load_document_processing_config()
    # NLI rides with semantic: groundrails feeds its scores into the features so
    # the calibrator learns on the same bundle the deployed verdict uses.
    enabled = bool(getattr(args, "semantic", False))
    _ensure_ready(semantic=enabled)

    rows: list[dict] = []
    for i, item in enumerate(raw):
        if "claim" not in item or "label" not in item:
            print(f"ERROR: evidence[{i}] needs 'claim' and 'label'", file=sys.stderr)
            raise SystemExit(2)
        src_paths = item.get("sources") or ([item["source"]] if item.get("source") else [])
        if src_paths:
            warns: list[str] = []
            sources = _read_sources(src_paths, warnings=warns)
            for w in warns:
                print(w, file=sys.stderr)
        elif item.get("source_text"):
            sources = [("inline", item["source_text"])]
        else:
            print(
                f"ERROR: evidence[{i}] needs 'sources', 'source', or 'source_text'",
                file=sys.stderr,
            )
            raise SystemExit(2)
        m = ground(
            item["claim"],
            sources,
            semantic=enabled,
            config=gcfg,
        )
        feat = extract_features(m, gcfg, m.nli_scores or None)
        feat["grounded"] = float(item["label"])
        feat["lang"] = item.get("lang", "und")
        feat["weight"] = float(item.get("weight", 1.0))
        rows.append(feat)
    return pd.DataFrame(rows)


def cmd_calibrate(args: argparse.Namespace) -> int:
    from groundrails import calibration as C

    profile = args.profile

    if args.action == "init":
        cal = C.default_calibrator(threshold=args.threshold, draws=args.draws, tune=args.tune)
        cal.save(profile)
        print(f"wrote default calibrator profile -> {profile}")
        return 0

    if args.action == "show":
        p = Path(profile)
        if not (p.exists() or (p / "calibrator.json").exists()):
            print(f"ERROR: profile not found: {profile}", file=sys.stderr)
            return 1
        cal = C.CalibratedVerdict.load(profile)
        print(f"threshold = {cal.threshold}")
        print("posterior (coefficient mean +/- sd):")
        for name, (mu, sd) in cal.posterior_summary().items():
            print(f"  {name:18s} {mu:+.3f} +/- {sd:.3f}")
        return 0

    df = _load_evidence_features(args)

    if args.action == "eval":
        cal = C.CalibratedVerdict.load(profile)
        print(json.dumps(C.evaluate(cal, df), indent=2))
        return 0

    # update (default): incremental from --from, else a fresh fit. include_anchor
    # keeps every predictor non-degenerate on small batches (bambi rejects a
    # constant predictor) and anchors untrained-region behaviour.
    balance = getattr(args, "balance", "balanced")
    if args.from_profile:
        prior = C.CalibratedVerdict.load(args.from_profile)
        cal = C.update_calibrator(
            prior,
            df,
            draws=args.draws,
            tune=args.tune,
            threshold=args.threshold,
            include_anchor=True,
            balance=balance,
        )
    else:
        cal = C.fit_calibrator(
            df,
            threshold=args.threshold,
            draws=args.draws,
            tune=args.tune,
            include_anchor=True,
            balance=balance,
        )
    cal.save(profile)
    print(json.dumps(C.evaluate(cal, df), indent=2))
    print(f"wrote calibrator profile -> {profile}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    from dataclasses import asdict

    from groundrails import calibration as C
    import yaml

    if args.config_action == "show":
        cfg = load_document_processing_config()
        print("# resolved document-processing config")
        print(yaml.safe_dump(asdict(cfg), sort_keys=False).rstrip())
        block = C.load_calibration_from_config()
        print("\n# calibration block")
        if block:
            print(yaml.safe_dump({"calibration": block}, sort_keys=False).rstrip())
        else:
            print("calibration: (none - deterministic classifier / default prior in use)")
        return 0

    # set-calibrator: transfer learned weights from a profile into the config
    p = Path(args.profile)
    if not (p.exists() or (p / "calibrator.json").exists()):
        print(f"ERROR: calibrator profile not found: {args.profile}", file=sys.stderr)
        return 1
    cal = C.CalibratedVerdict.load(args.profile)
    weights = {name: round(mu, 6) for name, (mu, _sd) in cal.posterior_summary().items()}
    d = asdict(load_document_processing_config())
    d["calibration"] = {
        "engine": "calibrated",
        "threshold": float(cal.threshold),
        "weights": weights,
    }
    out = (
        Path(args.config)
        if args.config
        else (PROJECT_OVERRIDE_DIR / "config_document_processing.yaml")
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    print(f"wrote learned calibration weights ({len(weights)} coefficients) -> {out}")
    print("grounding will now use these learned weights (calibration.engine=calibrated).")
    return 0


def _load_lexical_dataset(paths: list[str]) -> list[dict]:
    """Concatenate one or more labelled datasets into a list of row dicts.

    Reads ``.parquet`` (pandas; clear error if pyarrow missing) and ``.jsonl``
    (stdlib json, one object per line). Validates the required columns claim /
    source_text / label on each file; passes through the optional lang column.
    """
    rows: list[dict] = []
    required = ("claim", "source_text", "label")
    for raw_path in paths:
        p = Path(raw_path)
        if not p.is_file():
            print(f"ERROR: dataset not found: {raw_path}", file=sys.stderr)
            raise SystemExit(2)
        if p.suffix == ".parquet":
            try:
                import pandas as pd
            except ImportError:
                print(
                    "ERROR: reading parquet needs pandas + pyarrow (both ship with "
                    "the package); reinstall stellars-claude-code-plugins",
                    file=sys.stderr,
                )
                raise SystemExit(2) from None
            recs = pd.read_parquet(p).to_dict("records")
        elif p.suffix in (".jsonl", ".ndjson"):
            recs = [
                json.loads(line)
                for line in p.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            print(
                f"ERROR: {raw_path} - unsupported format (expected .parquet or .jsonl)",
                file=sys.stderr,
            )
            raise SystemExit(2)
        for i, r in enumerate(recs):
            missing = [c for c in required if c not in r]
            if missing:
                print(
                    f"ERROR: {raw_path} row {i} missing column(s): {', '.join(missing)}",
                    file=sys.stderr,
                )
                raise SystemExit(2)
        rows.extend(recs)
    return rows


def cmd_train_lexical(args: argparse.Namespace) -> int:
    """Fit one effort tier's lexical manifold and write it into the config.

    Concatenates the --data files, enforces the >=200-row / >=40-per-class floor,
    extracts that tier's features via the SAME ``lexical.extract_lexical_features``
    the grounder uses, fits ``lexical.fit_lexical_manifold`` (sklearn, training-
    only), and writes the frozen weights under
    ``calibration.lexical_manifolds.<effort>`` following the cmd_config set-
    calibrator write pattern. Client data is read in place; only aggregate weights
    are written.
    """
    from dataclasses import asdict

    from groundrails import calibration as C
    from groundrails import lexical as L
    import yaml

    raw_rows = _load_lexical_dataset(args.data)

    # Enforce the training floor (shared with the tests via the lexical constants).
    n = len(raw_rows)
    pos = sum(1 for r in raw_rows if int(r["label"]) == 1)
    neg = n - pos
    if n < L.LEXICAL_MIN_ROWS or min(pos, neg) < L.LEXICAL_MIN_PER_CLASS:
        print(
            f"ERROR: dataset too small to fit the {args.effort} manifold - need "
            f">= {L.LEXICAL_MIN_ROWS} rows with >= {L.LEXICAL_MIN_PER_CLASS} of each "
            f"class; got {n} rows ({pos} supported, {neg} hallucination).",
            file=sys.stderr,
        )
        raise SystemExit(2)

    # Short-source regime augmentation: truncate sources to one sentence so the
    # manifold learns the degenerate single-chunk regime (label inherited, only
    # length changes). Applied automatically; aug rows go through the same pipeline.
    aug_rows = L.short_source_augment(raw_rows)
    all_rows = raw_rows + aug_rows

    # Extract features per row with the grounder's own pipeline. The optional-dep
    # import for the tier must raise (no fitting on silently-zeroed features).
    feat_rows: list[dict] = []
    for r in all_rows:
        feat = L.extract_lexical_features(
            str(r["claim"]),
            [str(r["source_text"])],
            effort=args.effort,
            det_lang=(str(r["lang"]) if r.get("lang") else None),
        )
        feat["label"] = int(r["label"])
        feat_rows.append(feat)

    manifold = L.fit_lexical_manifold(feat_rows, effort=args.effort, threshold=args.threshold)
    print(f"  (+{len(aug_rows)} short-source augmentation rows)", file=sys.stderr)

    # Write following the cmd_config set-calibrator pattern: load the full config
    # dict, merge the manifold into the calibration block, dump.
    out = (
        Path(args.out) if args.out else (PROJECT_OVERRIDE_DIR / "config_document_processing.yaml")
    )
    d = asdict(load_document_processing_config())
    cal = C.load_calibration_from_config(args.out) or d.get("calibration") or {}
    cal["mode"] = "lexical"
    cal.pop("engine", None)  # mode is the public knob; drop any derived/legacy engine key
    cal.setdefault("lexical_manifolds", {})[args.effort] = manifold
    d["calibration"] = cal
    d["lexical_effort"] = args.effort
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    print(
        f"fit {args.effort} manifold ({len(manifold['feature_order'])} features, "
        f"threshold {manifold['threshold']:.3f}) from {n} rows "
        f"({pos} supported / {neg} hallucination) -> {out}"
    )
    return 0


def cmd_extract_claims(args: argparse.Namespace) -> int:
    """Emit claims.json from a document using the heuristic extractor."""
    from groundrails.extract import extract_claims_from_file

    doc_path = Path(args.document)
    if not doc_path.is_file():
        print(f"ERROR: document not found: {args.document}", file=sys.stderr)
        return 2
    try:
        extracted = extract_claims_from_file(doc_path)
    except UnicodeDecodeError as exc:
        print(
            f"ERROR: {args.document} is not valid UTF-8 at byte {exc.start}: {exc.reason}. "
            f"Convert or re-encode first.",
            file=sys.stderr,
        )
        return 2

    payload = [{"id": c.id, "claim": c.claim, "line_number": c.line_number} for c in extracted]
    output = Path(args.output) if args.output else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(
            f"wrote {len(payload)} claims to {output}",
            file=sys.stderr,
        )
    else:
        print(json.dumps(payload, indent=2))
    # Lossy by design - warn so the user knows to review before grounding.
    print(
        "NOTE: extract-claims uses a heuristic. Review claims.json before "
        "running `ground --manifest` - short/ambiguous sentences may need rewording.",
        file=sys.stderr,
    )
    return 0


def cmd_check_consistency(args: argparse.Namespace) -> int:
    """Flag intra-document divergences: same number / entity category with different values."""
    from groundrails.consistency import (
        check_consistency_in_file,
        format_consistency_report,
    )

    doc_path = Path(args.document)
    if not doc_path.is_file():
        print(f"ERROR: document not found: {args.document}", file=sys.stderr)
        return 2
    try:
        findings = check_consistency_in_file(doc_path)
    except UnicodeDecodeError as exc:
        print(
            f"ERROR: {args.document} is not valid UTF-8 at byte {exc.start}: {exc.reason}.",
            file=sys.stderr,
        )
        return 2

    report = format_consistency_report(findings, document_path=str(doc_path))
    output = Path(args.output) if args.output else None
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report, encoding="utf-8")
        print(
            f"wrote consistency report to {output} ({len(findings)} findings)",
            file=sys.stderr,
        )
    else:
        print(report)
    return 0 if not findings else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate one or many documents: grounding + self-consistency.

    Resolves inputs to a list of ``ClientEntry`` from either ``--manifest``
    (source_map.yaml) or one entry per ``--document`` with the shared
    ``--source`` list, then runs the batch.
    """
    from stellars_claude_code_plugins.document_processing.validate import (
        ClientEntry,
        _load_source_map,
        validate_batch,
    )

    if args.manifest:
        try:
            entries = _load_source_map(Path(args.manifest))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    else:
        if not args.source:
            print("ERROR: --document requires at least one --source", file=sys.stderr)
            return 2
        sources = [Path(s) for s in args.source]
        primary = Path(args.primary_source) if args.primary_source else None
        entries = [
            ClientEntry(
                name=Path(doc).stem,
                sources=sources,
                document=Path(doc),
                primary_source=primary,
            )
            for doc in args.document
        ]

    semantic = bool(getattr(args, "semantic", False))
    _ensure_ready(semantic=semantic)

    return validate_batch(
        entries,
        output_dir=Path(args.output_dir),
        fuzzy_threshold=args.threshold,
        bm25_threshold=args.bm25_threshold,
        semantic_threshold=args.semantic_threshold,
        semantic_threshold_percentile=args.semantic_threshold_percentile,
        semantic=semantic,
        config=_grounding_config(args),
        stop_on_error=args.stop_on_error,
        max_workers=getattr(args, "workers", 5),
    )


def cmd_setup(args: argparse.Namespace) -> int:
    """Provision groundrails and write the readiness token (``groundrails.json``).

    Lexical grounding needs no downloads - the bundled calibration is enough, so
    plain ``setup`` is offline. Pass ``--semantic`` to also provision the
    OpenVINO cascade models (embedding + NLI); that pulls ~1.4 GB on first run.
    The token persists under ``GROUNDRAILS_HOME`` so later grounding calls skip
    re-provisioning.
    """
    os.environ.setdefault("GROUNDRAILS_HOME", _default_home())
    semantic = bool(getattr(args, "semantic", False))
    if semantic:
        # Modules only: provisioning the models IS this command's job.
        _preflight_semantic(models=False)
    already = False
    try:
        gr_settings.load_config_file()
        already = gr_settings.is_ready()
    except Exception:  # noqa: BLE001 - no token yet -> provision below
        already = False
    # A prior lexical `setup` leaves the token in place, so `already` says nothing
    # about the cascade. Short-circuiting on it swallowed --semantic entirely: the
    # operator asked for the cascade, got "already initialised … or pass --semantic"
    # advising the flag they had just passed, and grounded against an engine that
    # was never provisioned. Only skip when this run adds nothing.
    if already and not args.force and not semantic:
        print(
            f"groundrails already initialised (home={_default_home()}).\n"
            "Re-run with --force to re-provision, or pass --semantic to add the "
            "cascade models.",
            file=sys.stderr,
        )
        return 0

    models = None if semantic else "none"
    info = groundrails.init(models=models)
    print(
        f"groundrails initialised -> {info.get('config_file')}\n"
        f"  calibration: {info.get('calibration')}\n"
        f"  models:      {info.get('models')}\n"
        "Lexical grounding is ready. Semantic grounding (--semantic on any "
        "grounding command) additionally needs the cascade models; run "
        "`groundrails download` if they were not provisioned here.",
        file=sys.stderr,
    )
    return 0


# Caveman-style one-liners (drop articles + copulas; keep technical accuracy).
# Used by `document-processing --caveman` for a terse catalogue.
CAVEMAN_DESCRIPTIONS: dict[str, str] = {
    "ground": "claims -> source. --claim one, --manifest many. score 3 ways. --semantic adds bundle",
    "extract-claims": "doc -> claims.json. lossy. review first",
    "check-consistency": "doc fight self? same fact different number?",
    "validate": "docs -> grounding + consistency reports. --document(s) or --manifest",
    "setup": "provision groundrails (init). writes readiness token. --semantic adds cascade models",
    "train-lexical": "labelled data -> lexical tier manifold. --effort low/med/high. weights into config",
}


def _print_caveman_catalogue() -> None:
    print("document-processing - source grounding + compliance tools (caveman)")
    print()
    print("Subcommands:")
    for name, desc in CAVEMAN_DESCRIPTIONS.items():
        print(f"  {name:<20} {desc}")
    print()
    print("Run 'document-processing --help' for the full flags of each subcommand.")


def main(argv: list[str] | None = None) -> int:
    # Caveman shortcut: terse catalogue, no argparse subcommand required.
    effective = list(argv) if argv is not None else sys.argv[1:]
    if effective in (["--caveman"], ["caveman"]):
        _print_caveman_catalogue()
        return 0

    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
