"""CLI entry point for document-processing tools.

Subcommands:
    ground        — ground a single claim against source files
    ground-many   — ground many claims (from JSON) against sources, emit report
    setup         — first-run: configure optional semantic grounding
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


def _read_sources(paths: list[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            print(f"ERROR: source not found: {p}", file=sys.stderr)
            sys.exit(1)
        out.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
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
    else:
        loc = "(no match)"
        winning = m.semantic_matched_text or m.bm25_matched_text or m.fuzzy_matched_text
    return (
        f"{m.match_type.upper()} "
        f"exact={m.exact_score:.3f} fuzzy={m.fuzzy_score:.3f} "
        f"bm25={m.bm25_score:.3f} semantic={m.semantic_score:.3f} "
        f"combined={m.combined_score:.3f} @ {loc} | {winning!r}"
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
        semantic_grounder=grounder,
    )
    exact = sum(1 for m in matches if m.match_type == "exact")
    fuzzy = sum(1 for m in matches if m.match_type == "fuzzy")
    bm25 = sum(1 for m in matches if m.match_type == "bm25")
    semantic = sum(1 for m in matches if m.match_type == "semantic")
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
                    "none": "UNCONFIRMED",
                }[m.match_type]
                lines.append(
                    f"### {i}. {status} (exact {m.exact_score:.3f}, "
                    f"fuzzy {m.fuzzy_score:.3f}, bm25 {m.bm25_score:.3f}, "
                    f"semantic {m.semantic_score:.3f})"
                )
                lines.append(f"**Claim**: {m.claim!r}")
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
        "--semantic",
        choices=["on", "off"],
        default=None,
        help="Override settings.semantic_enabled for this call",
    )
    gm.add_argument("--output", help="Write report to this path instead of stdout")
    gm.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    gm.set_defaults(func=cmd_ground_many)

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
