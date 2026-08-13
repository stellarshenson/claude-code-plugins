"""Workflow status: infer the build phase of an SVG and say what's next.

Stateless - everything is inferred from the file itself, so any agent (or
a fresh session) can ask "where am I, what's next" instead of re-reading
the workflow docs and re-running steps that already passed. This is what
makes the 6-phase workflow dynamic: completed gates are detected, not
remembered.

Gates, in order:

1. **scaffold** - file exists, parses, carries the grid comment, the
   topology comment, a ``<style>`` block with dark-mode overrides and the
   five canonical layers (``svg-infographics scaffold`` emits all of it)
2. **author** - placeholder cards replaced with real content; the nodes
   layer holds shapes
3. **content** - text present in the content layer; the file description
   comment is filled in (not the scaffold placeholder)
4. **finalize** - the consolidated validator gate reports no HARD findings

Connectors are reported as information, not gated - not every image
needs them.

Usage:
    svg-infographics workflow --svg file.svg [--json]
"""

import argparse
import json as _json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from stellars_claude_code_plugins.svg_tools._layers import CANONICAL_LAYERS

_SVG_NS = "http://www.w3.org/2000/svg"


def _strip_ns_tree(root: ET.Element) -> ET.Element:
    for elem in root.iter():
        if elem.tag.startswith(f"{{{_SVG_NS}}}"):
            elem.tag = elem.tag[len(_SVG_NS) + 2 :]
    return root


_SHAPE_TAGS = {"rect", "circle", "ellipse", "path", "polygon", "polyline", "line"}


def inspect_svg(svg_path: Path) -> dict:
    """Collect the workflow-relevant facts about ``svg_path``.

    Returns a dict of raw signals; ``phase_report`` turns them into the
    gate checklist + current phase.
    """
    facts: dict = {"file": str(svg_path), "exists": svg_path.exists()}
    if not facts["exists"]:
        return facts

    raw = svg_path.read_text(encoding="utf-8", errors="replace")
    facts["has_grid_comment"] = "=== GRID" in raw
    facts["has_topology_comment"] = ("=== LAYOUT TOPOLOGY" in raw) or ("TOPOLOGY:" in raw)
    # Via the CSS parser: a whole-file substring test did not even require
    # `: dark`, and counted the words appearing in an XML comment.
    from stellars_claude_code_plugins.svg_tools.check_css import has_dark_block

    facts["has_dark_mode"] = has_dark_block(raw)
    facts["description_placeholder"] = "<short role description>" in raw
    # A description comment is any comment BEFORE the <svg> root carrying
    # a "Shows:" line (house format). The scaffold emits one with
    # placeholders; authored files fill it in.
    head = raw.split("<svg", 1)[0]
    facts["has_description_comment"] = "Shows:" in head

    try:
        root = _strip_ns_tree(ET.fromstring(raw))
        facts["parses"] = True
    except ET.ParseError as exc:
        facts["parses"] = False
        facts["parse_error"] = str(exc)
        return facts

    top_groups = [g for g in list(root) if g.tag == "g"]
    top_ids = [g.get("id") for g in top_groups]
    facts["layers_present"] = [n for n in CANONICAL_LAYERS if n in top_ids]
    facts["layers_missing"] = [n for n in CANONICAL_LAYERS if n not in top_ids]

    def _layer(name: str):
        for g in top_groups:
            if g.get("id") == name:
                return g
        return None

    placeholders = [el for el in root.iter() if el.get("data-placeholder") == "true"]
    facts["placeholders"] = len(placeholders)

    nodes = _layer("nodes")
    facts["nodes_shapes"] = (
        sum(1 for el in nodes.iter() if el.tag in _SHAPE_TAGS) if nodes is not None else 0
    )
    connectors = _layer("connectors")
    facts["connector_paths"] = (
        sum(1 for el in connectors.iter() if el.tag in ("path", "polyline", "line"))
        if connectors is not None
        else 0
    )
    content = _layer("content")
    texts_anywhere = sum(1 for el in root.iter() if el.tag == "text")
    facts["content_texts"] = (
        sum(1 for el in content.iter() if el.tag == "text") if content is not None else 0
    )
    facts["texts_total"] = texts_anywhere
    return facts


def _finalize_counts(svg_path: Path) -> tuple[int, int]:
    """HARD / SOFT finding counts from the consolidated finalize gate
    (static checks only - no browser render)."""
    from stellars_claude_code_plugins.svg_tools.finalize import finalize

    hard, soft = finalize(svg_path, rendered_data=None)
    return len(hard), len(soft)


def phase_report(svg_path: Path, run_finalize: bool = True) -> dict:
    """Gate checklist + current phase + next actions for ``svg_path``."""
    facts = inspect_svg(svg_path)
    gates: list[dict] = []

    def gate(name, ok, detail, next_action=None):
        gates.append({"gate": name, "ok": bool(ok), "detail": detail, "next": next_action})

    if not facts["exists"]:
        gate(
            "scaffold",
            False,
            "file does not exist",
            "svg-infographics scaffold --format <preset> --out "
            f"{facts['file']} (see scaffold --list)",
        )
        return {"facts": facts, "gates": gates, "phase": "scaffold"}

    if not facts.get("parses", False):
        gate(
            "scaffold",
            False,
            f"XML does not parse: {facts.get('parse_error', '?')}",
            f"fix the XML, then `svg-infographics validate --svg {facts['file']}`",
        )
        return {"facts": facts, "gates": gates, "phase": "scaffold"}

    scaffold_bits = {
        "grid comment": facts["has_grid_comment"],
        "topology comment": facts["has_topology_comment"],
        "dark-mode CSS": facts["has_dark_mode"],
        "five layers": not facts["layers_missing"],
    }
    scaffold_ok = all(scaffold_bits.values())
    missing_bits = [k for k, v in scaffold_bits.items() if not v]
    gate(
        "scaffold",
        scaffold_ok,
        "grid + topology + dark CSS + layers present"
        if scaffold_ok
        else f"missing: {', '.join(missing_bits)}"
        + (f" (layers: {', '.join(facts['layers_missing'])})" if facts["layers_missing"] else ""),
        None
        if scaffold_ok
        else "regenerate via `svg-infographics scaffold` or add the missing pieces",
    )

    authored = facts["nodes_shapes"] > 0 and facts["placeholders"] == 0
    if facts["placeholders"]:
        detail = f"{facts['placeholders']} scaffold placeholder(s) remain"
        next_action = (
            "replace data-placeholder groups with real cards (keep the ids); "
            "place inner elements via `empty-space --container-id`"
        )
    elif facts["nodes_shapes"] == 0:
        detail = "nodes layer is empty"
        next_action = 'author the structural shapes into <g id="nodes">'
    else:
        detail = f"{facts['nodes_shapes']} shape(s) in nodes layer"
        next_action = None
    gate("author", authored, detail, next_action)

    content_ok = facts["content_texts"] > 0 and not facts["description_placeholder"]
    if facts["content_texts"] == 0:
        detail = "no text in content layer"
        next_action = 'add titles/labels to <g id="content"> (CSS classes, unicode glyphs)'
    elif facts["description_placeholder"]:
        detail = "file description comment still carries scaffold placeholders"
        next_action = "fill in the description comment (filename / Shows / Intent / Theme)"
    else:
        detail = f"{facts['content_texts']} text node(s), description comment filled"
        next_action = None
    gate("content", content_ok, detail, next_action)

    hard = soft = None
    if run_finalize:
        try:
            hard, soft = _finalize_counts(svg_path)
        except Exception as exc:  # pragma: no cover - defensive
            hard, soft = -1, -1
            gate("finalize", False, f"finalize crashed: {exc}", None)
    if hard is not None and hard >= 0:
        gate(
            "finalize",
            hard == 0,
            f"{hard} HARD / {soft} SOFT finding(s)",
            None
            if hard == 0
            else f"svg-infographics finalize {facts['file']} - fix every HARD finding "
            "in ONE pass, re-run once",
        )

    phase = "ship"
    for g in gates:
        if not g["ok"]:
            phase = g["gate"]
            break

    report = {
        "facts": facts,
        "gates": gates,
        "phase": phase,
        "info": {
            "connectors": facts.get("connector_paths", 0),
        },
    }
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics workflow",
        description=(
            "Infer the build phase of an SVG (scaffold / author / content / "
            "finalize / ship) from the file itself and print the next "
            "actions. Stateless - run any time to see what is already done "
            "and what remains; no step needs to be repeated to find out."
        ),
    )
    parser.add_argument("--svg", required=True, help="SVG file to inspect")
    parser.add_argument(
        "--no-finalize",
        action="store_true",
        help="Skip the finalize validator sweep (faster; phase may report 'ship' prematurely)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    report = phase_report(Path(args.svg), run_finalize=not args.no_finalize)

    if args.json:
        _json.dump(report, sys.stdout, indent=2)
        print()
        return 0

    print(f"=== WORKFLOW STATUS: {args.svg} ===")
    for g in report["gates"]:
        mark = "x" if g["ok"] else " "
        print(f"[{mark}] {g['gate']:<9} {g['detail']}")
        if g["next"]:
            print(f"          next: {g['next']}")
    conn = report["info"]["connectors"] if "info" in report else 0
    print(f"    info: {conn} connector path(s) in connectors layer")
    print(f"PHASE: {report['phase']}")
    if report["phase"] == "ship":
        print("Ready: render PNG readback (`render-png <file> out.png --mode both`), deliver.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
