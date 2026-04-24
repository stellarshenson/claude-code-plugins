"""Single-gate "is this file shippable?" check.

Runs the structural validators (svg_valid, overlaps, connectors) that catch
the biggest defect classes, aggregates findings, and exits 0 when every
HARD category is clean / 1 otherwise. One subcommand, one exit code, one
answer - no per-validator interpretation for the agent.

Layers run:

- **validate** (XML well-formedness, root, viewBox) - HARD
- **overlaps** (element bounding-box collisions, spacing) - HARD
- **connectors** (zero-length, edge-snap, label clearance) - HARD
- **connectors** (L-routing diagonals, stubby arrows 40/60 rule) - SOFT

HARD findings flip the exit code. SOFT findings print but do not block
delivery; the agent should still address them but they are stylistic
nudges not structural failures.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    enforce_warning_acks,
)
from stellars_claude_code_plugins.svg_tools.check_connectors import (
    check_edge_snap as cc_edge_snap,
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


def finalize(svg_path: Path) -> tuple[list[str], list[str]]:
    """Return ``(hard_findings, soft_findings)`` for ``svg_path``.

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
        # Classification "contained" is a parent-child relationship - the
        # overlap is structural (e.g. a <g> wrapping children). Not a defect.
        if cls == "contained":
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
    for f in cc_l_routing(connectors):
        soft.append(f"[connectors] {f}")
    for f in cc_stem_head_ratio(connectors, arrowheads):
        soft.append(f"[connectors] {f}")

    return hard, soft


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics finalize",
        description=(
            "Ship-ready gate: run structural validators on one SVG, "
            "aggregate findings, exit 0 when every HARD category is clean."
        ),
    )
    parser.add_argument("svg", help="Path to SVG to audit")
    add_ack_warning_arg(parser)
    args = parser.parse_args(argv)

    svg_path = Path(args.svg)
    if not svg_path.is_file():
        print(f"ERROR: svg not found: {svg_path}", file=sys.stderr)
        return 2

    hard, soft = finalize(svg_path)
    if not hard and not soft:
        print(f"finalize {svg_path}: OK - shippable.", file=sys.stderr)
        return 0

    # Gate: every HARD and SOFT finding requires a conscious ack with
    # reasoning. The gate lives at finalize's layer so sub-validator
    # findings surfaced here must be acknowledged per-finding, same as
    # producer-tool warnings. Tokens are deterministic for the
    # (finalize args, finding_text) pair.
    gate_findings = [f"HARD: {f}" for f in hard] + [f"SOFT: {f}" for f in soft]
    # argv=None at invocation goes through sys.argv[1:]; subprocess
    # callers pass explicit argv here so use whichever was resolved.
    cli_argv = argv if argv is not None else sys.argv[1:]
    enforce_warning_acks(gate_findings, cli_argv, args.ack_warning)

    # Gate passed - print the (now-acked) findings for the human audit
    # trail, then exit 1 on any HARD / 0 on pure SOFT.
    if hard:
        print("HARD findings:")
        for f in hard:
            print(f"  {f}")
    if soft:
        print("SOFT findings:")
        for f in soft:
            print(f"  {f}")
    print(
        f"\nfinalize {svg_path}: {len(hard)} hard, {len(soft)} soft",
        file=sys.stderr,
    )
    if hard:
        print(
            "next: drill into any specific class with its sub-command: "
            "`svg-infographics overlaps --svg <file>`, "
            "`svg-infographics connectors --svg <file>`, or "
            "`svg-infographics validate --svg <file>`. Fix, re-run finalize.",
            file=sys.stderr,
        )
    else:
        print(
            "next: soft findings are stylistic nudges; shippable if you "
            "accept the tradeoffs. Otherwise fix and re-run finalize.",
            file=sys.stderr,
        )
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
