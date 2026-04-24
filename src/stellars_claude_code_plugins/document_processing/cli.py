"""CLI entry point for document-processing tools.

Subcommands:
    ground             - ground a single claim against source files
    ground-many        - ground many claims (from JSON) against sources, emit report
    extract-claims     - heuristic sentence-to-claim extractor for a document
    check-consistency  - intra-document numeric/entity divergence detector
    validate-many      - batch-run grounding + consistency across many clients
    setup              - first-run: configure optional semantic grounding
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from stellars_claude_code_plugins.document_processing import settings as settings_mod
from stellars_claude_code_plugins.document_processing.grounding import (
    GroundingMatch,
    ground,
    ground_many,
)


def _build_semantic_grounder(cfg: settings_mod.Settings, cli_override: str | None):
    """Return a SemanticGrounder or None based on settings + CLI override.

    ``cli_override`` may be ``"on"``, ``"off"``, or ``None``.
    """
    use = cfg.semantic_enabled
    if cli_override == "on":
        use = True
    elif cli_override == "off":
        use = False
    if not use:
        return None
    if not settings_mod.is_semantic_available():
        print(
            "WARNING: semantic grounding requested but dependencies missing.\n"
            + settings_mod.semantic_install_hint(),
            file=sys.stderr,
        )
        return None
    # Lazy import only when actually instantiating
    from stellars_claude_code_plugins.document_processing.semantic import SemanticGrounder

    return SemanticGrounder(
        model_name=cfg.semantic_model,
        device=cfg.semantic_device,
        cache_dir=cfg.cache_dir,
    )


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


def _read_sources(paths: list[str]) -> list[tuple[str, str]]:
    """Read source files, failing loud on binary/undecodable input.

    Exit code 2 (distinct from 1 = legitimate no-hit) so automation can
    distinguish a config error from a grounding miss. Rejects binary
    formats by extension AND magic-byte sniff before decode is attempted;
    a renamed PDF or a rogue PNG will still be caught.
    """
    out: list[tuple[str, str]] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            print(f"ERROR: source not found: {p}", file=sys.stderr)
            sys.exit(2)
        binary_kind = _sniff_binary(path)
        if binary_kind is not None:
            print(
                f"ERROR: source {p} looks like a {binary_kind}, not text. "
                f"Extract text first (e.g. pdftotext / pypdf / ocrmypdf for PDFs, "
                f"docx2txt / pandoc for docx, unzip for archives) and pass the "
                f"extracted .txt to --source.",
                file=sys.stderr,
            )
            sys.exit(2)
        try:
            text = path.read_text(encoding="utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            print(
                f"ERROR: source {p} is not valid UTF-8 at byte {exc.start}: {exc.reason}. "
                f"Re-encode the file (iconv / recode) or extract text with a format-aware "
                f"tool (pdftotext / pypdf / ocrmypdf / pandoc). "
                f"Previous silent U+FFFD replacement masked this as a grounding miss.",
                file=sys.stderr,
            )
            sys.exit(2)
        out.append((str(path), text))
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


def cmd_ground(args: argparse.Namespace) -> int:
    sources = _read_sources(args.source)
    if not sources:
        print("ERROR: at least one --source required", file=sys.stderr)
        return 1
    cfg = settings_mod.ensure_loaded(auto_prompt=False)
    grounder = _build_semantic_grounder(cfg, getattr(args, "semantic", None))
    m = ground(
        args.claim,
        sources,
        fuzzy_threshold=args.threshold,
        bm25_threshold=args.bm25_threshold,
        semantic_threshold=args.semantic_threshold,
        semantic_threshold_percentile=getattr(args, "semantic_threshold_percentile", None),
        semantic_grounder=grounder,
    )
    if args.json:
        print(json.dumps(asdict(m), indent=2))
    else:
        print(_match_line(m))
    # Exit 0 if exact/fuzzy, 1 if none
    return 0 if m.match_type != "none" else 1


def cmd_ground_many(args: argparse.Namespace) -> int:
    sources = _read_sources(args.source)
    if not sources:
        print("ERROR: at least one --source required", file=sys.stderr)
        return 1
    claims_path = Path(args.claims)
    if not claims_path.is_file():
        print(f"ERROR: claims file not found: {args.claims}", file=sys.stderr)
        return 1
    raw = json.loads(claims_path.read_text(encoding="utf-8"))
    claims: list[str]
    if isinstance(raw, list) and all(isinstance(x, str) for x in raw):
        claims = raw
    elif isinstance(raw, list) and all(isinstance(x, dict) and "claim" in x for x in raw):
        claims = [x["claim"] for x in raw]
    else:
        print(
            "ERROR: claims file must be JSON list of strings or objects with 'claim' key",
            file=sys.stderr,
        )
        return 1

    cfg = settings_mod.ensure_loaded(auto_prompt=False)
    grounder = _build_semantic_grounder(cfg, getattr(args, "semantic", None))
    matches = ground_many(
        claims,
        sources,
        fuzzy_threshold=args.threshold,
        bm25_threshold=args.bm25_threshold,
        semantic_threshold=args.semantic_threshold,
        semantic_threshold_percentile=getattr(args, "semantic_threshold_percentile", None),
        semantic_grounder=grounder,
        primary_source=getattr(args, "primary_source", None),
    )
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="document-processing",
        description="Document processing tools: source grounding, compliance checks.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser(
        "ground",
        help="Ground a single claim against source files (regex + Levenshtein + BM25).",
        description=(
            "Score a claim against source texts. Three layers run independently: "
            "regex exact (score=1.0 on hit), Levenshtein partial-ratio (score in [0,1]), "
            "BM25 Okapi on passages (token-recall in [0,1]). All scores always reported. "
            "Priority: exact > fuzzy >= threshold > bm25 >= bm25-threshold > none. "
            "Exit 0 if grounded, 1 if unconfirmed."
        ),
    )
    g.add_argument("--claim", required=True, help="The verbatim claim text to locate")
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
        choices=["on", "off"],
        default=None,
        help="Override settings.semantic_enabled for this call",
    )
    g.add_argument("--json", action="store_true", help="Emit the full match as JSON")
    g.set_defaults(func=cmd_ground)

    gm = sub.add_parser(
        "ground-many",
        help="Ground many claims from a JSON file against sources.",
        description=(
            "Batch grounding. Claims JSON = list of strings OR list of "
            "{'claim': str, ...} objects. Emits markdown report by default, "
            "JSON with --json."
        ),
    )
    gm.add_argument("--claims", required=True, help="Path to claims JSON")
    gm.add_argument(
        "--source",
        action="append",
        default=[],
        required=True,
        help="Source file path (repeatable)",
    )
    gm.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Levenshtein ratio threshold for 'fuzzy' classification (default 0.85)",
    )
    gm.add_argument(
        "--bm25-threshold",
        type=float,
        default=0.5,
        help="BM25 token-recall threshold for 'bm25' classification (default 0.5)",
    )
    gm.add_argument(
        "--semantic-threshold",
        type=float,
        default=0.6,
        help="Semantic cosine-similarity threshold for 'semantic' classification (default 0.6)",
    )
    gm.add_argument(
        "--semantic-threshold-percentile",
        type=float,
        default=None,
        help=(
            "Model-agnostic percentile threshold (H3): fraction of random chunk-pair "
            "cosines that count as the tail (e.g. 0.02 = top 2%%). Overrides "
            "--semantic-threshold when set. Self-calibrates when embedding model swaps."
        ),
    )
    gm.add_argument(
        "--semantic",
        choices=["on", "off"],
        default=None,
        help="Override settings.semantic_enabled for this call",
    )
    gm.add_argument("--output", help="Write report to this path instead of stdout")
    gm.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    gm.add_argument(
        "--primary-source",
        dest="primary_source",
        default=None,
        help=(
            "Path of the one source expected to ground the claims. Any claim "
            "grounded elsewhere gets flagged verification_needed=True "
            "(cross-source pollution signal, WI#3)."
        ),
    )
    gm.set_defaults(func=cmd_ground_many)

    # extract-claims subcommand
    ex = sub.add_parser(
        "extract-claims",
        help="Heuristic sentence-to-claim extractor; emits claims.json for ground-many.",
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

    # validate-many subcommand
    vm = sub.add_parser(
        "validate-many",
        help="Batch-run grounding + consistency across clients declared in source_map.yaml.",
        description=(
            "Walk a source_map.yaml (one entry per client: sources[] and "
            "document) and produce validation/<client>/grounding-report.md + "
            "consistency-report.md per entry."
        ),
    )
    vm.add_argument("--source-map", required=True, help="Path to source_map.yaml")
    vm.add_argument(
        "--output-dir",
        required=True,
        help="Root output directory; one subdirectory per client is created under it.",
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
        choices=["on", "off"],
        default=None,
        help="Override settings.semantic_enabled for this call",
    )
    vm.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Abort the batch on the first client error (default: skip and continue).",
    )
    vm.set_defaults(func=cmd_validate_many)

    # setup subcommand
    su = sub.add_parser(
        "setup",
        help="First-run setup: ask about semantic grounding, write settings",
        description=(
            "Interactive setup for .stellars-plugins/settings.json. Asks whether to "
            "enable the optional semantic grounding layer (ModernBERT + FAISS)."
        ),
    )
    su.add_argument(
        "--force",
        action="store_true",
        help="Re-prompt even if settings already exist",
    )
    su.set_defaults(func=cmd_setup)

    return parser


def cmd_extract_claims(args: argparse.Namespace) -> int:
    """Emit claims.json from a document using the heuristic extractor."""
    from stellars_claude_code_plugins.document_processing.extract import (
        extract_claims_from_file,
    )

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
        "running ground-many - short/ambiguous sentences may need rewording.",
        file=sys.stderr,
    )
    return 0


def cmd_check_consistency(args: argparse.Namespace) -> int:
    """Flag intra-document divergences: same number / entity category with different values."""
    from stellars_claude_code_plugins.document_processing.consistency import (
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


def cmd_validate_many(args: argparse.Namespace) -> int:
    """Batch grounding+consistency across clients declared in source_map.yaml."""
    from stellars_claude_code_plugins.document_processing.validate_many import run_validate_many

    return run_validate_many(
        source_map_path=Path(args.source_map),
        output_dir=Path(args.output_dir),
        fuzzy_threshold=args.threshold,
        bm25_threshold=args.bm25_threshold,
        semantic_threshold=args.semantic_threshold,
        semantic_threshold_percentile=args.semantic_threshold_percentile,
        semantic=getattr(args, "semantic", None),
        stop_on_error=args.stop_on_error,
    )


def cmd_setup(args: argparse.Namespace) -> int:
    if settings_mod.settings_exist() and not args.force:
        cfg = settings_mod.load()
        print(
            f"Settings already present at {settings_mod.settings_path()}.\n"
            f"  semantic_enabled = {cfg.semantic_enabled}\n"
            f"  semantic_model   = {cfg.semantic_model}\n"
            f"  semantic_device  = {cfg.semantic_device}\n"
            f"  cache_dir        = {cfg.cache_dir}\n"
            "Re-run with --force to reconfigure.",
            file=sys.stderr,
        )
        return 0
    settings_mod.prompt_first_run()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
