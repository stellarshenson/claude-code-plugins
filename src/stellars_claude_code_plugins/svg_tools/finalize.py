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
    check_arrowhead_axis_alignment as cc_arrowhead_axis,
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
    results, hints = check_all_contrasts(texts, backgrounds, light_classes, dark_classes)
    findings = []
    for r in results:
        if not r.aa_pass:
            findings.append(
                f'[contrast] {r.mode} {r.ratio:.2f}:1 "{r.text.content[:40]}" '
                f"text {r.text.fill} on {r.effective_bg}"
            )
    # UNMEASURABLE IS NOT CLEAN, and this is the ONE consumer that decides the
    # exit code. Dropping these printed `[PASS] text meets WCAG AA` over a file
    # where 15 of 48 texts were never judged - and because the checker used to
    # score an unreadable fill as #000000, which failed on a dark ground, the
    # honest refusal to guess turned 63 real HARD findings into silence.
    # `check_css` already answers the identical situation this way on the
    # backplate; two opposite answers inside one gate is the defect.
    findings.extend(
        f"[contrast] {h.strip()}" for h in hints if h.strip().startswith("UNMEASURABLE")
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
    # Dial lives in check_alignment; a second copy here drifted from the CLI.
    for f in check_grid_snapping(elements):
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


def finalize(
    svg_path: Path,
    rendered_data: dict | None = None,
    ran: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Return ``(hard_findings, soft_findings)`` for ``svg_path``.

    ``rendered_data`` is the bbox JSON for this file from
    ``render_inspect.extract_bboxes`` (pass None to skip the visual layer -
    ``main`` extracts it once for all files in a single browser session).

    ``ran``, when given, is filled with the name of every layer that executed
    to completion. An early return on malformed XML skips every downstream
    layer, and a checklist that cannot tell "found nothing" from "never looked"
    reports those skipped layers as passes - which is the failure the checklist
    exists to abolish. Populated as an out-parameter so callers that do not
    care keep the two-value return.

    Never raises - on parser / IO errors each sub-validator returns its
    own diagnostic that gets collected as a HARD finding. Callers use the
    return value to decide exit code; see ``main``.
    """
    hard: list[str] = []
    soft: list[str] = []
    done = ran if ran is not None else set()

    # --- validate (XML + structural)
    errors, warnings, msgs = validate_svg(svg_path)
    done.add("validate")
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
        hard.append(f"[overlaps] check failed: {exc}")
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
    done.add("overlaps")

    # --- connectors (mixed HARD + SOFT)
    try:
        cards, connectors, labels, arrowheads = cc_parse(str(svg_path))
    except Exception as exc:
        hard.append(f"[connectors] check failed: {exc}")
        return hard, soft
    # Every connector checker behind the same guard as the rest. `finalize`
    # promises above that it never raises; the parse was guarded but the nine
    # checkers reading its output were not, so one raising checker escaped as a
    # traceback with no roster at all - and `main` has no guard either.
    _cc_hard = (
        (cc_zero_length, (connectors,)),
        (cc_edge_snap, (connectors, cards)),
        (cc_label_clearance, (connectors, labels)),
        # Parallel-edge contact at either end (exit or arrival) plus a
        # sideways arrowhead on an edge are HARD visual defects: the
        # connector joins the wrong face of the shape it should enter.
        (cc_edge_exit, (connectors, cards)),
        (cc_edge_arrival, (connectors, cards)),
        (cc_arrowhead_edge, (arrowheads, cards)),
        (cc_arrowhead_axis, (connectors, arrowheads)),
    )
    try:
        for fn, argv in _cc_hard:
            for f in fn(*argv):
                hard.append(f"[connectors] {f}")
    except Exception as exc:
        hard.append(f"[connectors] check failed: {exc}")
        return hard, soft
    for f in cc_l_routing(connectors):
        soft.append(f"[connectors] {f}")
    for f in cc_stem_head_ratio(connectors, arrowheads):
        soft.append(f"[connectors] {f}")
    from stellars_claude_code_plugins.svg_tools.check_connectors import (
        check_manifold_candidates as cc_manifold,
    )

    for f in cc_manifold(connectors):
        soft.append(f"[connectors] {f}")
    done.add("connectors")

    def run_layer(name: str, produce, target: list) -> None:
        """Run one layer, or record that it crashed.

        `build_checklist` parses the exact wording `] check failed` to decide a
        layer's rows are unjudged. This covers the four layers whose shape fits;
        the connector and overlaps blocks abort downstream layers and so spell
        it themselves - grep the literal before changing it.
        """
        try:
            target.extend(produce())
            done.add(name)
        except Exception as exc:
            # HARD regardless of the layer's normal tier. A dead checker
            # produced no verdict at all; routing that to SOFT let a run with
            # eight unjudged rows exit 0 under "shippable if you accept the
            # tradeoffs", and one `--ack-class SOFT-CSS=…` swallowed it.
            hard.append(f"[{name}] check failed: {exc}")

    # contrast is HARD - a WCAG AA text failure in either mode is not ackable.
    run_layer("contrast", lambda: _contrast_findings(svg_path), hard)
    run_layer("collide", lambda: _collide_findings(connectors), soft)
    run_layer("alignment", lambda: _alignment_findings(svg_path), soft)
    run_layer("css", lambda: _css_findings(svg_path), soft)

    # --- visual (rendered geometry; HARD only with real renderer extents)
    if rendered_data is not None:
        try:
            from stellars_claude_code_plugins.svg_tools.check_visual import check_visual

            v_hard, v_soft = check_visual(rendered_data)
            hard.extend(v_hard)
            soft.extend(v_soft)
            done.add("visual")
        except Exception as exc:
            hard.append(f"[visual] check failed: {exc}")

    return hard, soft


# Roster of verifiable aspects, one row per thing the toolchain can actually
# decide. Findings tell you what is WRONG; they cannot tell you what was never
# looked at, and an aspect nobody checks reads exactly like one that passed.
# That is how a deck shipped 17 files whose dark-mode block was never measured
# for whether it changed anything.
#
# Each row: (group, label, layer, token, applies-when). `token` is the marker a
# failing check puts in its finding; None means any finding in that layer counts
# against the row. `applies-when` reads the inventory below - a row whose subject
# is absent from the file prints NA instead of a free PASS.
_CHECKLIST: list[tuple[str, str, str, str | None, str | None]] = [
    ("structure", "xml well-formed", "validate", None, None),
    ("structure", "no element overlaps", "overlaps", None, "elements"),
    ("theme", "dark block present", "css", "missing-dark-block", None),
    (
        "theme",
        # Not "class": the checker judges `text {}` and `#plate {}` alike, and a
        # label naming only classes sent an operator to search the wrong list.
        "every painting rule overridden",
        "css",
        # Not gated on the dark block: without one, every painting rule
        # produces a finding, and FAIL precedes NA - so that half of the gate
        # was unreachable.
        "missing-dark-override",
        "painting_rules",
    ),
    (
        "theme",
        "overrides change the rendering",
        "css",
        "inert-dark-mode",
        # Not `dark rules exist` + `painting rules exist` - the two can both be
        # true with no rule in common, and the row then reported that nothing
        # was measured as everything being fine.
        "measured_overrides",
    ),
    ("theme", "background inverts", "css", "unthemed-background", "dark_rules+backplate"),
    ("theme", "no #000/#fff", "css", "forbidden-color", None),
    ("theme", "no inline fill on text", "css", "inline-fill-on-text", "text"),
    ("theme", "no opacity on text", "css", "text-opacity", "text"),
    ("theme", "no non-standard font attribute", "css", "non-standard-font", "text"),
    ("contrast", "text meets WCAG AA", "contrast", None, "text"),
    ("connectors", "no zero-length segments", "connectors", "zero-length", "connectors"),
    ("connectors", "endpoints snap to edges", "connectors", "edge-snap", "connectors+cards"),
    ("connectors", "exits square to the edge", "connectors", "l-chamfer-exit", "connectors+cards"),
    ("connectors", "arrives square to the edge", "connectors", "edge-arrival", "connectors+cards"),
    (
        "connectors",
        "head points into the card",
        "connectors",
        "arrowhead-edge",
        "arrowheads+cards",
    ),
    (
        "connectors",
        "head continues its stroke",
        "connectors",
        "arrowhead-axis",
        "arrowheads+connectors",
    ),
    ("connectors", "stem/head ratio", "connectors", "stem-head-ratio", "arrowheads+connectors"),
    ("connectors", "no diagonal L legs", "connectors", "l-routing", "connectors"),
    # Clearance is measured between a label and a ROUTE - no connectors, no
    # verdict, whatever the label count.
    ("connectors", "labels clear the route", "connectors", "clearance", "connectors+labels"),
    ("connectors", "routes do not cross", "collide", None, "connectors"),
    ("layout", "alignment and rhythm", "alignment", None, "aligned_elements"),
    ("render", "rendered geometry", "visual", None, "rendered"),
]


# Inventory keys are internal; the note an operator reads should not be one.
# Each note names the RULE the layer applies, never the contents of the file:
# `no card <rect>s` was read - correctly - as a claim about the document, and a
# file whose whole content is two 90x40 node rects falsified it in one line.
# Naming the rule tells an operator what to change; naming the contents tells
# them the tool cannot see what is in front of it.
# What a `None` inventory means, per key. The generic fallback says only that
# nothing could be determined; these say why.
_UNKNOWN_NOTE = {
    "connectors": "connectors the parser skipped",
    "arrowheads": "arrowheads the parser skipped",
}

_NEEDS_LABEL = {
    # The CONNECTOR layer's notion of a card: a <rect> whose class says card/box
    # or which is over 50x50 in BOTH axes. A deck drawing its cards as paths, or
    # as smaller rects, has cards - this layer just has no edge to snap to.
    # The threshold itself (class card/box, or over 50x50 in BOTH axes) lives in
    # validation.md - spelled out here it pushed the compound arrowhead rows
    # past 80 columns, and a roster that wraps is a roster nobody reads.
    "cards": "card-rule <rect>",
    "backplate": "canvas-covering <rect>",
    "painting_rules": "painting rules",
    # Two parsers, two keys, two labels. One word for both printed `no elements`
    # 24 lines under `no element overlaps  (1 HARD)` on a real corpus file.
    "aligned_elements": "elements the alignment layer reads",
    "dark_rules": "dark-mode rules",
    # These four fell through `.get(k, k)` and printed the raw key, so a file
    # with nine `class="connector"` lines under a `translate()` group - which the
    # connector parser excludes - was told it had `no connectors`.
    # "parsed", not "present": the connector layer reads untransformed
    # <line>/<polyline>/open <path> only, so a file CAN hold arrows it does not
    # see. The rule itself is in validation.md - spelled out here it pushed the
    # compound arrowhead rows to 123 columns.
    "connectors": "parsed connector",
    "arrowheads": "parsed arrowhead",
    "labels": "parsed label <text>",
    "text": "<text> elements",
    "measured_overrides": "light/dark pair to compare",
    "elements": "elements",
    "rendered": "render data",
}


def _tier_note(hits: list[tuple[str, str]]) -> str:
    """`2 HARD, 3 SOFT` - counted per tier, because they are different work."""
    n_hard = sum(1 for _, t in hits if t == "HARD")
    n_soft = len(hits) - n_hard
    parts = []
    if n_hard:
        parts.append(f"{n_hard} HARD")
    if n_soft:
        parts.append(f"{n_soft} SOFT")
    return ", ".join(parts)


def build_checklist(
    svg_path,
    hard: list[str],
    soft: list[str],
    rendered: bool,
    ran: set[str] | None = None,
    skip_reasons: dict[str, str] | None = None,
) -> tuple[list[tuple[str, str, str, str]], dict[str, int]]:
    """Per-aspect PASS / FAIL / NA / SKIP roster for one file.

    Returns ``(rows, counts)``. Precedence, and the order matters:

    - **FAIL** - a finding carries the row's token. Checked FIRST, so a row can
      never be gated into silence over a defect that was actually reported.
    - **SKIP** - the layer never ran (early return on malformed XML) or crashed.
      A layer that did not execute has no verdict to give, and printing PASS
      there is the precise lie this roster exists to stop.
    - **NA** - the layer ran and the file holds nothing for it to judge.
    - **PASS** - the layer ran, the subject exists, nothing was found.

    ``ran`` is the layer set filled by ``finalize``; omit it and every layer is
    assumed to have run (the pre-existing behaviour, for callers with only
    findings in hand).
    """
    skip_reasons = skip_reasons or {}
    text = ""
    inv = {"rendered": rendered}
    try:
        text = Path(svg_path).read_text(encoding="utf-8")
    except Exception:
        pass
    # Both answers come from the PARSER, never from a grep over the file. A raw
    # scan counted `prefers-color-scheme: dark` inside an XML comment (a shipped
    # example with no <style> element at all reported a dark block present), and
    # a probe written to a different tolerance than the parser's disagreed with
    # it in both directions on legal CSS like `(prefers-color-scheme : dark)`.
    # A dark block holding nothing but element selectors yields no class rules
    # for the two measuring rows, so they read NA rather than clean.
    from stellars_claude_code_plugins.svg_tools.check_css import parse_style_block as _psb

    try:
        from stellars_claude_code_plugins.svg_tools.check_css import (
            painting_selectors as _painting,
        )
        from stellars_claude_code_plugins.svg_tools.check_css import (
            theme_deltas as _deltas,
        )

        _light, _dark, _colors, _meta = _psb(text)
        # Every dark rule shape, matching the guard in `check_theme_background`.
        # Counting classes alone left an id-themed plate permanently NA under a
        # note claiming the file had no dark rules, which it did.
        inv["dark_rules"] = bool(_meta["dark_rules"])
        # THE CHECKER'S OWN PREDICATE, not a second one written beside it.
        # A gate computed over a wider set than the checker reads does not make
        # the row stricter - it turns "nothing was judged" into PASS.
        inv["painting_rules"] = bool(_painting(_meta["light_rules"]))
        # Same again for the row that MEASURES the overrides: a dark block
        # redeclaring only selectors the light sheet never paints leaves it
        # nothing to compare, and it was reporting that as agreement.
        inv["measured_overrides"] = bool(_deltas(_meta["light_rules"], _meta["dark_rules"]))
    except Exception:
        # NOT False. `False` renders as `NA (no painting rules)` - a positive
        # claim about a file nobody managed to read. An inventory that could not
        # be taken leaves those rows unjudged, which is what SKIP means.
        inv["dark_rules"] = inv["painting_rules"] = inv["measured_overrides"] = None
    # ONE parse for both probes below - they read the same file ten lines apart.
    try:
        import xml.etree.ElementTree as _ET

        _root = _ET.parse(str(svg_path)).getroot()
    except Exception:
        _root = None
    # Is there a ground to judge at all? `background inverts` was gated on the
    # dark block existing, so on 55 of 71 example files it printed PASS with no
    # plate ever examined.
    try:
        from stellars_claude_code_plugins.svg_tools.check_css import find_backplate as _fbp

        inv["backplate"] = None if _root is None else _fbp(_root, _meta["light_rules"]) is not None
    except Exception:
        inv["backplate"] = None
    # Parsed, not grepped: `<text` inside an XML comment made four rows PASS on
    # a document with no text elements at all.
    inv["text"] = _root is not None and any(
        el.tag.rsplit("}", 1)[-1] == "text" for el in _root.iter()
    )
    try:
        cards, connectors, labels, arrowheads = cc_parse(str(svg_path))
        # TRI-STATE, not boolean. The connector parser reads untransformed
        # <line>/<polyline>/open <path> only, so a deck authored inside
        # `<g transform=…>` groups has connectors the parser cannot see. Calling
        # that `False` printed `NA (no parsed connector)` - which the ship bar
        # accepts as green - on a file whose overlaps layer names those very
        # arrows by coordinate two lines below. `None` routes to SKIP, which the
        # bar does not accept, and SKIP is the honest word for "not judged".
        # COUNT, not truthiness. `bool(connectors) or …` only reached the
        # tri-state at zero, so a file where the parser read 1 of 10 arrows
        # printed eight green connector rows decided on that one - including
        # the new arrowhead-axis rule, which reported PASS over nine heads it
        # never paired.
        _skipped = _skipped_connectors(_root)
        # Per TAG: a skipped named polygon is an unjudged HEAD, a skipped line
        # or path an unjudged CONNECTOR. One shared count left the head row
        # PASSing on the one parsed arrowhead over nine the parser refused.
        inv["connectors"] = None if any(tag != "polygon" for tag in _skipped) else bool(connectors)
        inv["arrowheads"] = None if _skipped.get("polygon") else bool(arrowheads)
        inv["labels"] = bool(labels)
        inv["cards"] = bool(cards)
    except Exception:
        inv.update({"connectors": False, "arrowheads": False, "labels": False, "cards": False})
    # The overlaps and alignment layers run on a DIFFERENT element model than the
    # connector parser, so asking the connector parser whether they have anything
    # to judge printed NA over findings those layers had already produced.
    try:
        inv["elements"] = bool(co_parse(str(svg_path)))
    except Exception:
        inv["elements"] = False
    # One key per parser. The alignment layer runs on its own element model, and
    # sharing the overlaps key printed PASS on the one corpus file where the two
    # disagree - the only PASS that row has, and it is false.
    try:
        from stellars_claude_code_plugins.svg_tools.check_alignment import (
            parse_svg_elements as _ap,
        )

        inv["aligned_elements"] = bool(_ap(str(svg_path)))
    except Exception:
        inv["aligned_elements"] = False

    findings = [(f, "HARD") for f in hard] + [(f, "SOFT") for f in soft]
    # A layer whose checker raised reported one diagnostic and no verdicts; its
    # rows are unjudged regardless of what the inventory says about the file.
    crashed = {
        f[1 : f.index("]")] for f, _ in findings if f.startswith("[") and "] check failed" in f
    }
    claimed: set[int] = set()

    rows: list[tuple[str, str, str, str]] = []
    for group, label, layer, token, needs in _CHECKLIST:
        hits = []
        for i, (f, tier) in enumerate(findings):
            if f.startswith(f"[{layer}]") and (token is None or token in f):
                hits.append((f, tier))
                claimed.add(i)
        # `a+b` means the checker consumes both, so either being absent leaves
        # it nothing to judge. Gating on one of two inputs is how three
        # arrowhead rows passed on a file with heads but no connectors.
        keys = [k for k in (needs or "").split("+") if k]
        missing = [_NEEDS_LABEL.get(k, k) for k in keys if inv.get(k) is False]
        # `None` means the inventory probe itself failed. That is not "the file
        # has none of these" - nobody managed to look, and saying NA there is a
        # positive claim about a file that was never read.
        unknown = [k for k in keys if inv.get(k) is None]
        # Crashed BEFORE hits: for a row with no token every `[layer]` finding
        # counts as a hit, including the `check failed` diagnostic itself - so a
        # dead checker was reporting a confident FAIL on a defect it never found.
        if layer in crashed:
            rows.append((group, label, "SKIP", "checker crashed"))
        elif hits:
            rows.append((group, label, "FAIL", _tier_note(hits)))
        elif ran is not None and layer not in ran:
            rows.append((group, label, "SKIP", skip_reasons.get(layer, "not run")))
        elif unknown:
            # Why the probe could not answer, not just that it could not. A
            # connector under `<g transform=…>` is geometry the layer declined
            # to parse - saying "inventory unavailable" about it claims the
            # probe failed, when the probe succeeded and found exactly that.
            rows.append(
                (group, label, "SKIP", _UNKNOWN_NOTE.get(unknown[0], "inventory unavailable"))
            )
        elif missing:
            rows.append((group, label, "NA", f"no {' or '.join(missing)}"))
        else:
            rows.append((group, label, "PASS", ""))

    # A finding no row claims is a finding the roster is silent about, and a
    # roster quieter than the findings beside it reads as the fuller account.
    # One catch-all per group keeps the two in bijection as checks are added.
    leftovers: dict[str, list[tuple[str, str]]] = {}
    for i, (f, tier) in enumerate(findings):
        if i in claimed or "] check failed" in f:
            continue
        leftovers.setdefault(_layer(f).lower(), []).append((f, tier))
    for layer, hits in sorted(leftovers.items()):
        # Its own group: rendered inside `theme`, a catch-all FAIL carrying an
        # inline white fill sat directly under `[PASS] no #000/#fff`, two rows
        # of one block contradicting each other.
        rows.append(("other", f"other {layer} findings", "FAIL", _tier_note(hits)))
    # Keep catch-alls inside their own group, so the block still prints one
    # header per group. Stable, so row order within a group is unchanged.
    order = [*dict.fromkeys(g for g, _, _, _, _ in _CHECKLIST), "other"]
    rows.sort(key=lambda r: order.index(r[0]) if r[0] in order else len(order))

    counts = {s: sum(1 for r in rows if r[2] == s) for s in ("PASS", "FAIL", "NA", "SKIP")}
    return rows, counts


def format_checklist(name: str, rows, counts, diagnostics: list[str] | None = None) -> str:
    """Render the roster as an indented, grouped block.

    ``diagnostics`` are the `check failed` lines behind any SKIP rows. The
    roster is the artefact read first, and for the one state that means "the
    tool is broken, not your file" it was withholding the reason it already
    held - eight rows saying `checker crashed` and the exception sorted into the
    findings wall below them.
    """
    out = [f"CHECKLIST  {name}"]
    seen = None
    for group, label, status, note in rows:
        if group != seen:
            out.append(f"  {group}")
            seen = group
        mark = {"PASS": "PASS", "FAIL": "FAIL", "NA": " NA ", "SKIP": "SKIP"}[status]
        suffix = f"  ({note})" if note else ""
        out.append(f"    [{mark}] {label}{suffix}")
    total = sum(counts.values())
    out.append(
        f"\n  {total} aspect{'' if total == 1 else 's'}: {counts['PASS']} PASS  "
        f"{counts['FAIL']} FAIL  {counts['NA']} NA  {counts['SKIP']} SKIP"
    )
    n_hard = sum(1 for _, _, s, n in rows if s == "FAIL" and "HARD" in n)
    if counts["FAIL"]:
        out.append(
            f"  {counts['FAIL']} failing row{'' if counts['FAIL'] == 1 else 's'}: "
            f"{n_hard} with hard findings, {counts['FAIL'] - n_hard} soft-only"
        )
    # Only nag about SKIPs the operator did not ask for - saying "these are not
    # passes" about a layer they switched off, on a file the tool then calls
    # shippable, trains them to ignore the line that matters.
    unasked = [n for _, _, s, n in rows if s == "SKIP" and not n.startswith("--")]
    if unasked:
        causes = ", ".join(f"{unasked.count(c)} {c}" for c in dict.fromkeys(unasked))
        out.append(f"  {len(unasked)} unjudged ({causes}) - these are not passes")
    for line in diagnostics or []:
        out.append(f"  {line}")
    return "\n".join(out)


def _layer(finding: str) -> str:
    """The ``[layer]`` tag of a finding, upper-cased for class prefixes.

    Read from the UNPREFIXED finding, before ``main`` glues a `[file.svg] `
    prefix on for a multi-file run - recovering it afterwards means guessing
    where that prefix ended, and an `[alignment] [  2] …` payload hands back
    its own inner token.
    """
    if finding.startswith("[") and "]" in finding:
        return finding[1 : finding.index("]")].upper()
    return "OTHER"


def _one_line(text: str, limit: int = 96) -> str:
    """Collapse whitespace and bound the length of a diagnostic.

    The roster is a fixed-width block. A Playwright "install browsers" banner is
    six lines of box-drawing at column 0, and splicing it in raw breaks the
    indentation of the one state that means "the tool is broken, not your file".
    """
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _skipped_connectors(root) -> dict[str, int]:
    """Named geometry the parser refuses, counted PER TAG: `{line: 2, …}`.

    The parser reads untransformed `<line>`/`<polyline>`/open `<path>` outside
    icon and background contexts, and triangular `<polygon>` arrowheads on the
    same terms. Anything NAMED as a connector that it did not return is
    geometry the layer could not judge - and the count is per tag because a
    skipped `polygon` is an unjudged HEAD while a skipped `line` is not: one
    shared count left `head points into the card` PASSing on the one parsed
    head over nine the parser refused.

    Naming, not transforms. Keying on "under any transformed ancestor" made 18
    lucide icon glyph strokes and 445 texture hairlines read as unjudged
    connectors - three of the four corpus files it fired on have no connectors
    at all, and a SKIP that is wrong three times in four is a SKIP nobody
    believes. `<path>` is included because the connector tool emits `trimmed
    path_d`, so path IS the house connector format.
    """
    if root is None:
        return {}
    transformed = {
        id(child) for parent in root.iter() if parent.get("transform") for child in parent.iter()
    }
    counts: dict[str, int] = {}
    # `polygon` is the arrowhead shape; a named one under a transform is a head
    # the parser refused, and leaving the tag out routed its rows to NA - "no
    # parsed arrowhead" - about a file that has 45 of them.
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in ("line", "polyline", "path", "polygon"):
            continue
        ident = f"{el.get('class') or ''} {el.get('id') or ''}".lower()
        if not any(k in ident for k in ("conn", "arrow", "edge", "link")):
            continue
        # Mirror the parser's OWN rejections. It reads open, unfilled strokes;
        # a filled or closed `<path>` is a shape however it is named, so a chain
        # -link glyph called `ic-link` outnumbered the parsed set and sent every
        # connector row to SKIP on a file whose connectors were all judged.
        if tag == "path":
            d = (el.get("d") or "").strip().lower()
            fill = (el.get("fill") or "").strip().lower()
            if not d or d.endswith("z") or (fill and fill not in ("none", "transparent")):
                continue
        # Only the ones the parser REFUSED. Counting every named element and
        # comparing against the total parsed count mixed two different sets -
        # unnamed decoration the parser accepted cancelled out named connectors
        # it skipped, and a grid rule bought a PASS over an unread arrow.
        if id(el) in transformed:
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _deck_subjects(rendered: dict[str, dict]) -> int:
    """Files the cross-file check has something to compare, 0 if it cannot say."""
    from stellars_claude_code_plugins.svg_tools.check_visual import consistency_subjects

    return consistency_subjects(list(rendered.values()))


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
    parser.add_argument(
        "--checklist",
        action="store_true",
        help=(
            "Print a per-aspect PASS/FAIL/NA roster per file before the findings, "
            "so an aspect that was never checked is visible instead of reading as a pass"
        ),
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
    render_failures: dict[str, str] = {}
    if not args.no_visual:
        # PER FILE. `extract_bboxes` is one dict comprehension, so one bad file
        # took the visual layer away from every other file in the deck - and a
        # healthy file that would have passed the layer was told `not run`, the
        # same string that elsewhere means its own XML died.
        from stellars_claude_code_plugins.svg_tools.render_inspect import extract_bboxes

        for p in svg_paths:
            try:
                rendered.update(extract_bboxes([p]))
            except Exception as exc:
                render_failures[str(p)] = f"{type(exc).__name__}: {exc}"
        for path, why in render_failures.items():
            print(f"note: visual layer unavailable for {path} ({why})", file=sys.stderr)

    multi = len(svg_paths) > 1
    per_file: dict[str, tuple[list[str], list[str]]] = {}
    per_file_ran: dict[str, set[str]] = {}
    all_hard: list[str] = []
    all_soft: list[str] = []
    # The SOFT ack class, captured from the UNPREFIXED finding. Recovering it
    # afterwards meant guessing where the `[file.svg] ` prefix ended, and any
    # payload that itself starts with a bracket - `[alignment] [  2] text …` -
    # handed back its inner token: 4 ack classes became 719 across the corpus,
    # and `SOFT-  2` matches no class the gate can act on.
    soft_class: list[str] = []
    for svg_path in svg_paths:
        ran: set[str] = set()
        hard, soft = finalize(svg_path, rendered_data=rendered.get(str(svg_path)), ran=ran)
        per_file[str(svg_path)] = (hard, soft)
        per_file_ran[str(svg_path)] = ran
        prefix = f"[{svg_path.name}] " if multi else ""
        all_hard.extend(f"{prefix}{f}" for f in hard)
        all_soft.extend(f"{prefix}{f}" for f in soft)
        soft_class.extend(_layer(f) for f in soft)

    # Cross-file deck consistency (SOFT) when gating several files together.
    if multi and rendered:
        try:
            from stellars_claude_code_plugins.svg_tools.check_visual import (
                check_cross_file_consistency,
            )

            deck_findings = check_cross_file_consistency(list(rendered.values()))
        except Exception as exc:
            deck_findings = [f"[consistency] check failed: {exc}"]
        # A crashed check judged nothing, so it is HARD like every other layer's
        # crash - `run_layer` routes those to `hard` regardless of tier, and one
        # `--ack-class SOFT-CONSISTENCY` would otherwise swallow a dead checker.
        if any("] check failed" in f for f in deck_findings):
            all_hard.extend(deck_findings)
        else:
            all_soft.extend(deck_findings)
            soft_class.extend(_layer(f) for f in deck_findings)

    def _skip_reasons(svg_path) -> dict[str, str]:
        """Why the visual layer did not run on this file, when it did not.

        One source for the roster AND the clean-branch verdict - computed twice
        they can disagree, and the verdict then contradicts the roster above it.
        """
        if args.no_visual:
            return {"visual": "--no-visual"}
        if str(svg_path) in render_failures:
            return {"visual": "renderer unavailable"}
        return {}

    def _roster_skips() -> dict[str, dict[str, str]]:
        """Per file, the aspects that produced no verdict, with the cause.

        Both verdict branches read this: zero findings beside unjudged aspects
        is not a ship decision, and neither are acked SOFT findings beside
        them - same doctrine, both branches.
        """
        out: dict[str, dict[str, str]] = {}
        for svg_path in svg_paths:
            rows, _counts = build_checklist(
                svg_path,
                *per_file[str(svg_path)],
                rendered=str(svg_path) in rendered,
                ran=per_file_ran[str(svg_path)],
                skip_reasons=_skip_reasons(svg_path),
            )
            out[str(svg_path)] = {
                label: note for _g, label, status, note in rows if status == "SKIP"
            }
        return out

    def _cause_summary(skips: dict[str, str]) -> str:
        """`9 connectors the parser skipped, 1 renderer unavailable` - each
        cause once, not once per aspect; the verdict line budget is 80."""
        causes = list(skips.values())
        return ", ".join(f"{causes.count(c)} {c}" for c in dict.fromkeys(causes))

    def _print_unverified(unverified: dict[str, dict[str, str]]) -> None:
        for p, s in unverified.items():
            print(
                f"finalize {p}: NOT VERIFIED - findings acked, "
                f"{len(s)} not judged ({_cause_summary(s)})",
                file=sys.stderr,
            )

    def _print_ok(paths) -> None:
        for p in paths:
            print(
                f"finalize {p}: OK - findings acked, all aspects judged.",
                file=sys.stderr,
            )

    if args.checklist:
        # Cross-file findings belong to the deck, not to any one file, so no
        # per-file roster can carry them - and a reader of 17 clean blocks
        # concluded the deck was consistent while the gate said otherwise.
        deck = [f for f in all_soft + all_hard if f.startswith("[consistency]")]
        for svg_path in svg_paths:
            hard, soft = per_file[str(svg_path)]
            rows, counts = build_checklist(
                svg_path,
                hard,
                soft,
                rendered=str(svg_path) in rendered,
                ran=per_file_ran[str(svg_path)],
                skip_reasons=_skip_reasons(svg_path),
            )
            # Collapsed and truncated: a Playwright "install" banner is six raw
            # lines at column 0, and it would break the block's indentation in
            # the one state that means "the tool is broken, not your file".
            # The renderer's own failure already prints once as a `note:` above,
            # so it is not repeated per file here.
            # The budget is the whole line, prefix included. Bounding only the
            # message put a 119-column diagnostic under a block whose own rule
            # is 80 - in exactly the state where a wrapped roster is least
            # readable.
            diagnostics = []
            for f in hard + soft:
                if "] check failed" not in f:
                    continue
                prefix = f"{f[1 : f.index(']')]} checker crashed: "
                diagnostics.append(
                    prefix + _one_line(f.split("check failed: ", 1)[-1], 78 - len(prefix))
                )
            print(format_checklist(svg_path.name, rows, counts, diagnostics), file=sys.stderr)
            print(file=sys.stderr)
        if multi:
            crashed_deck = [f for f in deck if "] check failed" in f]
            real = [f for f in deck if "] check failed" not in f]
            if crashed_deck:
                status, note = "SKIP", "checker crashed"
            elif not rendered:
                # The cross-file checker is guarded on rendered geometry, so with
                # --no-visual it never ran - and a hand-built row with only PASS
                # and FAIL announced consistency nobody measured.
                status, note = "SKIP", "--no-visual" if args.no_visual else "no render data"
            elif real:
                status, note = "FAIL", _tier_note([(f, "SOFT") for f in real])
            elif len(rendered) < 2:
                # A cross-file check needs two files. One surviving render was
                # being compared against nothing and reported as agreement.
                status, note = (
                    "SKIP",
                    f"only {len(rendered)} of {len(svg_paths)} files rendered",
                )
            elif not _deck_subjects(rendered):
                # It ran over two or more files, and both of its comparisons had
                # zero subjects: none holds an element the checker reads as a
                # card. An empty result from an empty input is not agreement -
                # this repo's own 7-file deck was told it was mutually
                # consistent on nothing.
                status, note = "NA", "no cards to compare across files"
            else:
                status, note = "PASS", ""
            print(
                format_checklist(
                    f"deck ({len(svg_paths)} files)",
                    [("deck", "files are mutually consistent", status, note)],
                    {s: (1 if s == status else 0) for s in ("PASS", "FAIL", "NA", "SKIP")},
                ),
                file=sys.stderr,
            )
            print(file=sys.stderr)

    if not all_hard and not all_soft:
        # "OK - shippable" is a verdict over the WHOLE roster, not just the
        # findings list: zero findings beside nine unjudged aspects is not a
        # ship decision - the roster's own nag line said "these are not passes"
        # while the verdict overrode it, and `--json` carried no trace of the
        # skips at all. SKIPs the operator asked for (`--no-visual`) stay
        # shippable; an aspect unjudged for any other reason flips the verdict
        # and the exit code.
        ship = 0
        skipped = _roster_skips()
        for svg_path in svg_paths:
            unjudged = skipped[str(svg_path)]
            if not unjudged:
                print(f"finalize {svg_path}: OK - shippable.", file=sys.stderr)
                continue
            unasked = any(not note.startswith("--") for note in unjudged.values())
            if unasked:
                ship = 1
            verdict = "NOT VERIFIED" if unasked else "OK - shippable"
            print(
                f"finalize {svg_path}: {verdict} - findings clean, "
                f"{len(unjudged)} not judged ({_cause_summary(unjudged)})",
                file=sys.stderr,
            )
        if args.json:
            print(
                json.dumps(
                    {
                        "files": {
                            p: {"hard": [], "soft": [], "skipped": skipped[p]} for p in per_file
                        },
                        "totals": {"hard": 0, "soft": 0},
                    }
                )
            )
        return ship

    # Gate: HARD findings require a conscious per-token ack with reasoning.
    # SOFT findings carry a SOFT-<LAYER> class so one --ack-class flag with
    # one reason covers a whole layer instead of dozens of identical acks
    # (51 hand-typed acks on one file trained the reflex that neutralised a
    # real finding). Tokens are deterministic for (finalize args, finding).
    gate_findings = [f"HARD: {f}" for f in all_hard] + [
        f"SOFT-{cls}: {f}" for cls, f in zip(soft_class, all_soft)
    ]
    # argv=None at invocation goes through sys.argv[1:]; subprocess
    # callers pass explicit argv here so use whichever was resolved.
    cli_argv = argv if argv is not None else sys.argv[1:]
    enforce_warning_acks(gate_findings, cli_argv, args.ack_warning)

    # Gate passed - print the (now-acked) findings for the human audit
    # trail, then exit 1 on any HARD / 0 on pure SOFT.
    # The acked-SOFT branch makes the same ship decision as the clean branch,
    # so it answers to the same roster: accepted findings beside unjudged
    # aspects printed "shippable if you accept the tradeoffs", exit 0, over
    # nine aspects nobody ran. HARD findings already block, so only the
    # SOFT-only path needs the consult - but the map is built on every path,
    # so the JSON `skipped` key carries the real per-file map wherever it
    # appears instead of {} meaning "not consulted" on the HARD path alone.
    roster_skips = _roster_skips()
    unverified = {
        p: s for p, s in roster_skips.items() if any(not n.startswith("--") for n in s.values())
    }
    if args.json:
        print(
            json.dumps(
                {
                    "files": {
                        p: {"hard": h, "soft": s, "skipped": roster_skips.get(p, {})}
                        for p, (h, s) in per_file.items()
                    },
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
        # The unjudged aspects are part of the editing pass the operator is
        # planning at this line - the HARD path exits 1 either way, but
        # deferring this to the next run broke the protocol's own
        # "re-run ONCE" promise: fix the contrast, re-run, meet the skipped
        # connectors a cycle late.
        if unverified:
            _print_unverified(unverified)
    elif unverified:
        _print_unverified(unverified)
        # A mixed run owes the healthy files a verdict too - silence read as
        # "also unverified", which is the inference the roster exists to kill.
        _print_ok([p for p in svg_paths if str(p) not in unverified])
    else:
        # The uniform acked path gets the same per-file verdict - one
        # vocabulary on every branch the gate passed.
        _print_ok(svg_paths)
        print(
            "next: soft findings are stylistic nudges; shippable if you "
            "accept the tradeoffs. Otherwise fix all of them in one pass "
            "and re-run finalize once.",
            file=sys.stderr,
        )
    return 1 if (all_hard or unverified) else 0


if __name__ == "__main__":
    sys.exit(main())
