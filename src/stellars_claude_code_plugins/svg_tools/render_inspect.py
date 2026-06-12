"""Element-geometry extraction for the visual checks.

Pure static extraction: an ElementTree walk that applies translate/scale
transforms and estimates text extents heuristically. No browser - the
rendering side of the visual gate is plain `render-png` (high-quality PNG
via the same approach as the markdown-export solution), which the agent
reads ONCE as the final visual pass. This module only supplies the bbox
JSON that ``check_visual.py``'s deterministic geometry checks consume.

Text extents are estimates (``len * font_size * 0.55``), so collision
findings derived from this data are SOFT - surfaced for the batch-fix
pass, never claimed as proven defects. The ``backend`` field says so.

CLI:
    svg-infographics geometry --svg file.svg [--svg file2.svg]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

_NS_RE = re.compile(r"\{[^}]*\}")

_TRANSFORM_RE = re.compile(r"(translate|scale)\(([^)]*)\)")


def _parse_simple_transform(t: str) -> tuple[float, float, float, float]:
    """(tx, ty, sx, sy) from translate()/scale() chains; other ops ignored."""
    tx = ty = 0.0
    sx = sy = 1.0
    for op, raw in _TRANSFORM_RE.findall(t or ""):
        vals = [float(v) for v in re.split(r"[,\s]+", raw.strip()) if v]
        if op == "translate":
            tx += vals[0] * sx if vals else 0.0
            ty += (vals[1] if len(vals) > 1 else 0.0) * sy
        elif op == "scale" and vals:
            sx *= vals[0]
            sy *= vals[1] if len(vals) > 1 else vals[0]
    return tx, ty, sx, sy


def _static_bbox(el: ET.Element) -> tuple[float, float, float, float] | None:
    """Local-space bbox for one element, heuristic text widths."""
    from stellars_claude_code_plugins.svg_tools.check_alignment import _path_bbox

    tag = _NS_RE.sub("", el.tag)

    def f(attr: str, default: float = 0.0) -> float:
        try:
            return float(el.get(attr, default))
        except (TypeError, ValueError):
            return default

    if tag == "rect":
        return f("x"), f("y"), f("width"), f("height")
    if tag == "circle":
        return f("cx") - f("r"), f("cy") - f("r"), 2 * f("r"), 2 * f("r")
    if tag == "ellipse":
        return f("cx") - f("rx"), f("cy") - f("ry"), 2 * f("rx"), 2 * f("ry")
    if tag == "line":
        x1, y1, x2, y2 = f("x1"), f("y1"), f("x2"), f("y2")
        return min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
    if tag in ("polyline", "polygon"):
        pts = [
            tuple(float(v) for v in p.split(","))
            for p in (el.get("points") or "").replace(";", " ").split()
            if "," in p
        ]
        if not pts:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    if tag == "path":
        bb = _path_bbox(el.get("d") or "")
        if bb is None:
            return None
        return bb.x, bb.y, bb.w, bb.h
    if tag == "text":
        content = "".join(el.itertext()).strip()
        if not content:
            return None
        fs = f("font-size", 10.0)
        est_w = len(content) * fs * 0.55
        x, y = f("x"), f("y")
        anchor = el.get("text-anchor", "start")
        if anchor == "middle":
            x -= est_w / 2
        elif anchor == "end":
            x -= est_w
        return x, y - fs * 0.85, est_w, fs
    return None


def extract_static_bboxes(svg_path: Path) -> dict:
    """ET walk with translate/scale applied and heuristic text extents."""
    text = Path(svg_path).read_text(encoding="utf-8")
    root = ET.fromstring(text)
    vb = [0.0, 0.0, 0.0, 0.0]
    if root.get("viewBox"):
        vb = [float(v) for v in root.get("viewBox", "").split()[:4]]

    elements: list[dict] = []

    def walk(el: ET.Element, tx: float, ty: float, sx: float, sy: float, parent: str | None):
        for child in el:
            tag = _NS_RE.sub("", child.tag)
            ctx, cty, csx, csy = _parse_simple_transform(child.get("transform", ""))
            ntx, nty = tx + ctx * sx, ty + cty * sy
            nsx, nsy = sx * csx, sy * csy
            child_parent = parent
            if tag == "g":
                if child.get("id"):
                    child_parent = child.get("id")
                walk(child, ntx, nty, nsx, nsy, child_parent)
                continue
            bb = _static_bbox(child)
            if bb is None:
                continue
            x, y, w, h = bb
            if w == 0 and h == 0:
                continue
            elements.append(
                {
                    "tag": tag,
                    "id": child.get("id"),
                    "classes": (child.get("class") or "").split(),
                    "parent": parent,
                    "bbox": [ntx + x * nsx, nty + y * nsy, w * nsx, h * nsy],
                    "text": "".join(child.itertext()).strip() if tag == "text" else None,
                    "anchor": child.get("text-anchor", "start") if tag == "text" else None,
                }
            )

    walk(root, 0.0, 0.0, 1.0, 1.0, None)

    # Synthesise one entry per identified icon-ish group so role checks can
    # treat the group as a unit (children carry parent=<group id> already).
    by_parent: dict[str, list[dict]] = {}
    for e in elements:
        if e["parent"]:
            by_parent.setdefault(e["parent"], []).append(e)
    for gid, members in by_parent.items():
        xs = [m["bbox"][0] for m in members]
        ys = [m["bbox"][1] for m in members]
        x2 = max(m["bbox"][0] + m["bbox"][2] for m in members)
        y2 = max(m["bbox"][1] + m["bbox"][3] for m in members)
        elements.append(
            {
                "tag": "g",
                "id": gid,
                "classes": [],
                "parent": None,
                "bbox": [min(xs), min(ys), x2 - min(xs), y2 - min(ys)],
                "text": None,
                "anchor": None,
            }
        )

    return {
        "file": str(svg_path),
        "backend": "static",
        "viewBox": vb,
        "elements": elements,
    }


def extract_bboxes(svg_paths: list[Path]) -> dict[str, dict]:
    """Bbox JSON per file (static extraction)."""
    return {str(p): extract_static_bboxes(p) for p in svg_paths}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics geometry",
        description=(
            "Extract element bboxes (static parse, transforms applied, "
            "heuristic text extents) for one or more SVGs as JSON."
        ),
    )
    parser.add_argument("--svg", action="append", required=True, help="SVG file (repeatable)")
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.svg]
    for p in paths:
        if not p.is_file():
            print(f"ERROR: svg not found: {p}", file=sys.stderr)
            return 2
    results = extract_bboxes(paths)
    print(json.dumps(results if len(paths) > 1 else results[str(paths[0])], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
