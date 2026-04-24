"""Batch validation across multiple clients declared in ``source_map.yaml``.

source_map.yaml convention::

    clients:
      actone:
        sources:
          - clients/actone/transcript.md
          - clients/actone/research_doc.md
        document: clients/actone/opportunity_brief.md
        primary_source: clients/actone/transcript.md   # optional
      arelion:
        sources: [clients/arelion/transcript.md]
        document: clients/arelion/opportunity_brief.md

For every entry the pipeline runs, in order:

1. Claim extraction from ``document`` into ``<output>/<client>/claims.json``.
2. Grounding of those claims against ``sources`` into
   ``<output>/<client>/grounding-report.md``.
3. Self-consistency check on ``document`` into
   ``<output>/<client>/consistency-report.md``.

Failures on a single client are logged to ``<output>/<client>/error.log``
and the batch continues. Use ``--stop-on-error`` to abort on first
failure. Exit code summarises the batch: 0 when every client succeeded,
1 when any client produced findings/errors, 2 when the map itself was
bad.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import traceback

import yaml

from stellars_claude_code_plugins.document_processing import settings as settings_mod
from stellars_claude_code_plugins.document_processing.consistency import (
    check_consistency_in_file,
    format_consistency_report,
)
from stellars_claude_code_plugins.document_processing.extract import (
    extract_claims_from_file,
)
from stellars_claude_code_plugins.document_processing.grounding import (
    ground_many,
)


@dataclass
class ClientEntry:
    name: str
    sources: list[Path]
    document: Path
    primary_source: Path | None = None


def _load_source_map(path: Path) -> list[ClientEntry]:
    """Parse source_map.yaml into a list of :class:`ClientEntry`.

    Raises ``ValueError`` with a clear message on malformed input so the
    CLI can surface it with exit code 2.
    """
    if not path.is_file():
        raise ValueError(f"source_map not found: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: bad yaml: {exc}") from exc
    if not isinstance(raw, dict) or "clients" not in raw:
        raise ValueError(f"{path}: must contain top-level 'clients' mapping")
    clients_raw = raw["clients"]
    if not isinstance(clients_raw, dict):
        raise ValueError(f"{path}: 'clients' must be a mapping")
    base = path.parent
    entries: list[ClientEntry] = []
    for name, spec in clients_raw.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{path}: client '{name}' must be a mapping")
        if "sources" not in spec or "document" not in spec:
            raise ValueError(f"{path}: client '{name}' must define 'sources' and 'document'")
        sources = [base / s for s in spec["sources"]]
        document = base / spec["document"]
        primary = spec.get("primary_source")
        primary_path = base / primary if primary else None
        entries.append(
            ClientEntry(
                name=name,
                sources=sources,
                document=document,
                primary_source=primary_path,
            )
        )
    return entries


def _read_source_pairs(paths: list[Path]) -> list[tuple[str, str]]:
    """Read sources strictly as UTF-8; surface decode errors verbatim."""
    out: list[tuple[str, str]] = []
    for p in paths:
        text = p.read_text(encoding="utf-8", errors="strict")
        out.append((str(p), text))
    return out


def _run_single_client(
    entry: ClientEntry,
    output_dir: Path,
    *,
    fuzzy_threshold: float,
    bm25_threshold: float,
    semantic_threshold: float,
    semantic_threshold_percentile: float | None,
    semantic_grounder,
) -> tuple[int, int]:
    """Run the full pipeline for one client.

    Returns ``(unconfirmed_count, consistency_finding_count)``.
    """
    client_dir = output_dir / entry.name
    client_dir.mkdir(parents=True, exist_ok=True)

    # --- Step 1: extract claims
    extracted = extract_claims_from_file(entry.document)
    claims_path = client_dir / "claims.json"
    claims_payload = [
        {"id": c.id, "claim": c.claim, "line_number": c.line_number} for c in extracted
    ]
    claims_path.write_text(json.dumps(claims_payload, indent=2), encoding="utf-8")

    # --- Step 2: ground the claims
    source_pairs = _read_source_pairs(entry.sources)
    primary = str(entry.primary_source) if entry.primary_source else None
    matches = ground_many(
        [c.claim for c in extracted],
        source_pairs,
        fuzzy_threshold=fuzzy_threshold,
        bm25_threshold=bm25_threshold,
        semantic_threshold=semantic_threshold,
        semantic_threshold_percentile=semantic_threshold_percentile,
        semantic_grounder=semantic_grounder,
        primary_source=primary,
    )
    grounding_report = _render_grounding_report(entry, matches)
    (client_dir / "grounding-report.md").write_text(grounding_report, encoding="utf-8")

    # --- Step 3: self-consistency
    findings = check_consistency_in_file(entry.document)
    consistency_report = format_consistency_report(findings, document_path=str(entry.document))
    (client_dir / "consistency-report.md").write_text(consistency_report, encoding="utf-8")

    unconfirmed = sum(1 for m in matches if m.match_type == "none")
    return unconfirmed, len(findings)


def _render_grounding_report(entry: ClientEntry, matches) -> str:
    """Compact per-client grounding report (same shape as ground-many output)."""
    total = len(matches)
    grounded = sum(1 for m in matches if m.match_type in ("exact", "fuzzy", "bm25", "semantic"))
    verify = sum(1 for m in matches if m.verification_needed)
    contradicted = sum(1 for m in matches if m.match_type == "contradicted")
    unconfirmed = sum(1 for m in matches if m.match_type == "none")
    lines = [
        f"# Grounding Report - {entry.name}",
        "",
        f"- Document: `{entry.document}`",
        f"- Sources: {', '.join(f'`{s}`' for s in entry.sources)}",
    ]
    if entry.primary_source:
        lines.append(f"- Primary source: `{entry.primary_source}`")
    lines.extend(
        [
            f"- Claims: {total}  (grounded {grounded}, contradicted {contradicted}, "
            f"unconfirmed {unconfirmed})",
            f"- Verification needed: {verify}",
            "",
            "## Matches",
            "",
        ]
    )
    for i, m in enumerate(matches, start=1):
        status = {
            "exact": "CONFIRMED",
            "fuzzy": "CONFIRMED (fuzzy)",
            "bm25": "CONFIRMED (bm25)",
            "semantic": "CONFIRMED (semantic)",
            "contradicted": "CONTRADICTED",
            "none": "UNCONFIRMED",
        }[m.match_type]
        verify_tag = " - VERIFY" if m.verification_needed else ""
        lines.append(f"### {i}. {status}{verify_tag}")
        lines.append(f"**Claim**: {m.claim!r}")
        if m.grounded_source:
            primary_flag = "" if m.is_primary_source else " [NON-PRIMARY]"
            lines.append(f"**Source file**: `{m.grounded_source}`{primary_flag}")
        lines.append("")
    return "\n".join(lines)


def run_validate_many(
    *,
    source_map_path: Path,
    output_dir: Path,
    fuzzy_threshold: float,
    bm25_threshold: float,
    semantic_threshold: float,
    semantic_threshold_percentile: float | None,
    semantic: str | None,
    stop_on_error: bool,
) -> int:
    """Execute the batch described by ``source_map_path`` and return exit code."""
    try:
        entries = _load_source_map(source_map_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if not entries:
        print(f"ERROR: {source_map_path} declares no clients", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build semantic grounder once; reused across every client for speed.
    cfg = settings_mod.ensure_loaded(auto_prompt=False)
    grounder = _maybe_build_grounder(cfg, semantic)

    total_unconfirmed = 0
    total_findings = 0
    errors: list[tuple[str, str]] = []
    for entry in entries:
        try:
            unconfirmed, findings_count = _run_single_client(
                entry,
                output_dir,
                fuzzy_threshold=fuzzy_threshold,
                bm25_threshold=bm25_threshold,
                semantic_threshold=semantic_threshold,
                semantic_threshold_percentile=semantic_threshold_percentile,
                semantic_grounder=grounder,
            )
        except Exception as exc:  # noqa: BLE001 - we surface any failure per-client
            err = f"{type(exc).__name__}: {exc}"
            errors.append((entry.name, err))
            client_dir = output_dir / entry.name
            client_dir.mkdir(parents=True, exist_ok=True)
            (client_dir / "error.log").write_text(
                err + "\n\n" + traceback.format_exc(),
                encoding="utf-8",
            )
            print(f"  client {entry.name!r}: FAILED - {err}", file=sys.stderr)
            if stop_on_error:
                break
            continue
        total_unconfirmed += unconfirmed
        total_findings += findings_count
        print(
            f"  client {entry.name!r}: ok  (unconfirmed {unconfirmed}, "
            f"consistency findings {findings_count})",
            file=sys.stderr,
        )

    print(
        f"validate-many done: {len(entries)} clients, {len(errors)} errors, "
        f"{total_unconfirmed} unconfirmed claims, {total_findings} consistency findings",
        file=sys.stderr,
    )
    if errors:
        return 1
    if total_unconfirmed or total_findings:
        return 1
    return 0


def _maybe_build_grounder(cfg, semantic_override: str | None):
    """Copy of cli._build_semantic_grounder avoiding a circular import."""
    use = cfg.semantic_enabled
    if semantic_override == "on":
        use = True
    elif semantic_override == "off":
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
    from stellars_claude_code_plugins.document_processing.semantic import SemanticGrounder

    return SemanticGrounder(
        model_name=cfg.semantic_model,
        device=cfg.semantic_device,
        cache_dir=cfg.cache_dir,
    )
