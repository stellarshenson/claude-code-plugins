"""Single-gate "is this file shippable?" check.

Runs ALL validators in one call, aggregates findings into HARD / SOFT
tiers, and exits 0 when every HARD category is clean / 1 otherwise. One
subcommand, one exit code, one consolidated report - no per-validator
invocation loop for the agent.

Layers run:

- **validate** (XML well-formedness, root, viewBox) - HARD
- **overlaps** (element bounding-box collisions, spacing) - HARD
- **connectors** (zero-length, edge-snap, label clearance) - HARD
- **contrast** (WCAG 2.1 AA text contrast, light + dark) - HARD
- **visual** (text/icon collisions, corner padding, label centering,
  canvas balance, slot parity) - SOFT
- **connectors** (L-routing diagonals, stubby arrows 40/60 rule,
  manifold candidates) - SOFT
- **collide** (pairwise connector crossings) - SOFT
- **alignment** (grid snap @0.5px tolerance, rhythm, x-alignment) - SOFT
- **css** (inline fills, forbidden colours, dark-mode coverage) - SOFT

The visual layer runs over statically-extracted element geometry
(``render_inspect`` - transforms applied, heuristic text extents). No
browser involved; the human-visible render stays a plain high-quality
``render-png`` the agent reads ONCE after the gate passes.
``--no-visual`` skips the layer.

HARD findings flip the exit code and must be acknowledged per-token.
SOFT findings print but do not block delivery; they carry a
``SOFT-<LAYER>`` class so a whole layer can be acknowledged with one
``--ack-class SOFT-<LAYER>=reason`` instead of dozens of identical acks.

Batch-fix protocol (see references/workflow.md): run finalize once, fix
ALL findings in one editing pass, re-run once. Accepts multiple SVG paths
so a whole deck is gated in a single invocation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    enforce_warning_acks,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_arrowhead_edge_orientation as cc_arrowhead_edge,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_edge_arrival_direction as cc_edge_arrival,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_edge_snap as cc_edge_snap,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_l_chamfer_exit_direction as cc_edge_exit,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_l_routing as cc_l_routing,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_label_clearance as cc_label_clearance,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_stem_head_ratio as cc_stem_head_ratio,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_zero_length as cc_zero_length,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    parse_svg as cc_parse,
)
from stellars_claude_code_plugins.svg_tools.check_overlaps import (
    analyze_overlaps,
    check_spacing,
)
from stellars_claude_code_plugins.svg_tools.check_overlaps import (
    parse_svg as co_parse,
)
from stellars_claude_code_plugins.svg_tools.check_svg_valid import validate_svg


def _contrast_findings(svg_path: Path) -> list[str]:
    """WCAG AA text-contrast failures (light + dark). HARD tier."""
    from stellars_claude_code_plugins.svg_tools.check_contrast import (
        check_all_contrasts,
        parse_svg_for_contrast,
    )

    texts, backgrounds, light_classes, dark_classes = parse_svg_for_contrast(str(svg_path))
    results, _hints = check_all_contrasts(texts, backgrounds, light_classes, dark_classes)
    findings = []
    for r in results:
        if not r.aa_pass:
            findings.append(
                f'[contrast] {r.mode} {r.ratio:.2f}:1 "{r.text.content[:40]}" '
                f"text {r.text.fill} on {r.effective_bg}"
            )
    return findings


def _alignment_findings(svg_path: Path) -> list[str]:
    """Grid snap (0.5px tolerance), rhythm and alignment notices. SOFT tier."""
    from stellars_claude_code_plugins.svg_tools.check_alignment import (
        check_grid_snapping,
        check_rect_alignment,
        check_text_vertical_rhythm,
        check_x_alignment,
        parse_svg_elements,
    )

    elements = parse_svg_elements(str(svg_path))
    findings = []
    for f in check_grid_snapping(elements, grid=5, tolerance=0.5):
        findings.append(f"[alignment] {f.strip()}")
    for f in check_text_vertical_rhythm(elements):
        findings.append(f"[alignment] {f.strip()}")
    for f in check_x_alignment(elements):
        findings.append(f"[alignment] {f.strip()}")
    for f in check_rect_alignment(elements):
        findings.append(f"[alignment] {f.strip()}")
    return findings


def _css_findings(svg_path: Path) -> list[str]:
    """CSS-convention violations (inline fills, dark coverage). SOFT tier."""
    from stellars_claude_code_plugins.svg_tools.check_css import check_css_compliance

    violations, _stats = check_css_compliance(str(svg_path))
    return [f"[css] {v.rule}: {v.element} - {v.detail}" for v in violations]


def _collide_findings(connectors) -> list[str]:
    """Pairwise connector crossings. SOFT tier."""
    from stellars_claude_code_plugins.svg_tools.calc_connector import detect_collisions

    samples = [c.points for c in connectors if len(c.points) >= 2]
    labels = [c.elem_id or f"c{i}" for i, c in enumerate(connectors) if len(c.points) >= 2]
    if len(samples) < 2:
        return []
    findings = []
    for col in detect_collisions(samples, tolerance=0.0, labels=labels):
        if col.get("type") == "crossing":
            findings.append(f"[collide] {col['a']} crosses {col['b']}")
    return findings


def finalize(svg_path: Path, rendered_data: dict | None = None) -> tuple[list[str], list[str]]:
    """Return ``(hard_findings, soft_findings)`` for ``svg_path``.

    ``rendered_data`` is the bbox JSON for this file from
    ``render_inspect.extract_bboxes`` (pass None to skip the visual layer -
    ``main`` extracts it once for all files in a single browser session).

    Never raises - on parser / IO errors each sub-validator returns its
    own diagnostic that gets collected as a HARD finding. Callers use the
    return value to decide exit code; see ``main``.
    """
    hard: list[str] = []
    soft: list[str] = []

    # --- validate (XML + structural)
    errors, warnings, msgs = validate_svg(svg_path)
    for m in msgs:
        if m.startswith("ERROR"):
            hard.append(f"[validate] {m}")
        else:
            soft.append(f"[validate] {m}")
    # Abort downstream layers if XML is malformed - parsing anything else
    # will just produce cascading confused errors.
    if errors > 0:
        return hard, soft

    # --- overlaps (HARD)
    try:
        elements = co_parse(str(svg_path))
    except Exception as exc:
        hard.append(f"[overlaps] parse failed: {exc}")
        return hard, soft
    overlap_findings = analyze_overlaps(elements)
    for i, j, a, b, pct, cls in overlap_findings:
        # "contained" is a parent-child relationship (structural), and
        # "connector-contact" is a routed stroke touching what it attaches
        # to - the connectors / collide layers own those. Neither is an
        # overlap defect.
        if cls in ("contained", "connector-contact"):
            continue
        hard.append(f"[overlaps] #{i} <-> #{j} ({pct:.0f}%, {cls}): {a.label} vs {b.label}")
    spacing_findings = check_spacing(elements)
    for f in spacing_findings:
        hard.append(f"[overlaps] {f}")

    # --- connectors (mixed HARD + SOFT)
    try:
        cards, connectors, labels, arrowheads = cc_parse(str(svg_path))
    except Exception as exc:
        hard.append(f"[connectors] parse failed: {exc}")
        return hard, soft
    for f in cc_zero_length(connectors):
        hard.append(f"[connectors] {f}")
    for f in cc_edge_snap(connectors, cards):
        hard.append(f"[connectors] {f}")
    for f in cc_label_clearance(connectors, labels):
        hard.append(f"[connectors] {f}")
    # Parallel-edge contact at either end (exit or arrival) plus a
    # sideways arrowhead on an edge are HARD visual defects: the
    # connector joins the wrong face of the shape it should enter.
    for f in cc_edge_exit(connectors, cards):
        hard.append(f"[connectors] {f}")
    for f in cc_edge_arrival(connectors, cards):
        hard.append(f"[connectors] {f}")
    for f in cc_arrowhead_edge(arrowheads, cards):
        hard.append(f"[connectors] {f}")
    for f in cc_l_routing(connectors):
        soft.append(f"[connectors] {f}")
    for f in cc_stem_head_ratio(connectors, arrowheads):
        soft.append(f"[connectors] {f}")
    from stellars_claude_code_plugins.svg_tools.check_connectors import (
        check_manifold_candidates as cc_manifold,
    )

    for f in cc_manifold(connectors):
        soft.append(f"[connectors] {f}")

    # --- contrast (HARD - WCAG AA text fails in either mode)
    try:
        hard.extend(_contrast_findings(svg_path))
    except Exception as exc:
        hard.append(f"[contrast] check failed: {exc}")

    # --- collide (SOFT - connector crossings)
    try:
        soft.extend(_collide_findings(connectors))
    except Exception as exc:
        soft.append(f"[collide] check failed: {exc}")

    # --- alignment (SOFT)
    try:
        soft.extend(_alignment_findings(svg_path))
    except Exception as exc:
        soft.append(f"[alignment] check failed: {exc}")

    # --- css (SOFT)
    try:
        soft.extend(_css_findings(svg_path))
    except Exception as exc:
        soft.append(f"[css] check failed: {exc}")

    # --- visual (rendered geometry; HARD only with real renderer extents)
    if rendered_data is not None:
        try:
            from stellars_claude_code_plugins.svg_tools.check_visual import check_visual

            v_hard, v_soft = check_visual(rendered_data)
            hard.extend(v_hard)
            soft.extend(v_soft)
        except Exception as exc:
            soft.append(f"[visual] check failed: {exc}")

    return hard, soft


def _layer(finding: str) -> str:
    """The ``[layer]`` tag of a finding, upper-cased for class prefixes."""
    if finding.startswith("[") and "]" in finding:
        return finding[1 : finding.index("]")].upper()
    return "OTHER"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics finalize",
        description=(
            "Ship-ready gate: run ALL validators on one or more SVGs in a "
            "single call, aggregate findings into HARD/SOFT tiers, exit 0 "
            "when every HARD category is clean."
        ),
    )
    parser.add_argument("svg", nargs="+", help="Path(s) to SVG(s) to audit")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the findings report as JSON on stdout (after the ack gate)",
    )
    parser.add_argument(
        "--no-visual",
        action="store_true",
        help="Skip the visual-geometry layer (collisions, padding, balance, parity)",
    )
    add_ack_warning_arg(parser)
    args = parser.parse_args(argv)

    svg_paths = [Path(p) for p in args.svg]
    missing = [p for p in svg_paths if not p.is_file()]
    if missing:
        for p in missing:
            print(f"ERROR: svg not found: {p}", file=sys.stderr)
        return 2

    rendered: dict[str, dict] = {}
    if not args.no_visual:
        try:
            from stellars_claude_code_plugins.svg_tools.render_inspect import extract_bboxes

            rendered = extract_bboxes(svg_paths)
        except Exception as exc:
            print(
                f"note: visual layer unavailable ({exc}); continuing without it", file=sys.stderr
            )

    multi = len(svg_paths) > 1
    per_file: dict[str, tuple[list[str], list[str]]] = {}
    all_hard: list[str] = []
    all_soft: list[str] = []
    for svg_path in svg_paths:
        hard, soft = finalize(svg_path, rendered_data=rendered.get(str(svg_path)))
        per_file[str(svg_path)] = (hard, soft)
        prefix = f"[{svg_path.name}] " if multi else ""
        all_hard.extend(f"{prefix}{f}" for f in hard)
        all_soft.extend(f"{prefix}{f}" for f in soft)

    # Cross-file deck consistency (SOFT) when gating several files together.
    if multi and rendered:
        try:
            from stellars_claude_code_plugins.svg_tools.check_visual import (
                check_cross_file_consistency,
            )

            all_soft.extend(check_cross_file_consistency(list(rendered.values())))
        except Exception as exc:
            all_soft.append(f"[consistency] check failed: {exc}")

    if not all_hard and not all_soft:
        for svg_path in svg_paths:
            print(f"finalize {svg_path}: OK - shippable.", file=sys.stderr)
        if args.json:
            print(json.dumps({"files": {p: {"hard": [], "soft": []} for p in per_file}}))
        return 0

    # Gate: HARD findings require a conscious per-token ack with reasoning.
    # SOFT findings carry a SOFT-<LAYER> class so one --ack-class flag with
    # one reason covers a whole layer instead of dozens of identical acks
    # (51 hand-typed acks on one file trained the reflex that neutralised a
    # real finding). Tokens are deterministic for (finalize args, finding).
    gate_findings = [f"HARD: {f}" for f in all_hard] + [
        f"SOFT-{_layer(f if not multi else f.split('] ', 1)[-1])}: {f}" for f in all_soft
    ]
    # argv=None at invocation goes through sys.argv[1:]; subprocess
    # callers pass explicit argv here so use whichever was resolved.
    cli_argv = argv if argv is not None else sys.argv[1:]
    enforce_warning_acks(gate_findings, cli_argv, args.ack_warning)

    # Gate passed - print the (now-acked) findings for the human audit
    # trail, then exit 1 on any HARD / 0 on pure SOFT.
    if args.json:
        print(
            json.dumps(
                {
                    "files": {p: {"hard": h, "soft": s} for p, (h, s) in per_file.items()},
                    "totals": {"hard": len(all_hard), "soft": len(all_soft)},
                }
            )
        )
    else:
        if all_hard:
            print("HARD findings:")
            for f in all_hard:
                print(f"  {f}")
        if all_soft:
            print("SOFT findings:")
            for f in all_soft:
                print(f"  {f}")
    print(
        f"\nfinalize {', '.join(str(p) for p in svg_paths)}: "
        f"{len(all_hard)} hard, {len(all_soft)} soft",
        file=sys.stderr,
    )
    if all_hard:
        print(
            "next: batch-fix protocol - fix ALL findings above in ONE editing "
            "pass, then re-run finalize ONCE. Do not fix-and-revalidate one "
            "finding at a time. Drill into a class only if a finding is "
            "unclear: `svg-infographics overlaps|connectors|contrast|validate "
            "--svg <file>`.",
            file=sys.stderr,
        )
    else:
        print(
            "next: soft findings are stylistic nudges; shippable if you "
            "accept the tradeoffs. Otherwise fix all of them in one pass "
            "and re-run finalize once.",
            file=sys.stderr,
        )
    return 1 if all_hard else 0


if __name__ == "__main__":
    sys.exit(main())
