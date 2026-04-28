"""Boolean / margin operations on SVG paths.

A headless equivalent of the Path menu in Inkscape / Illustrator / Affinity:

* ``union`` (A ∪ B)               - merge filled regions
* ``intersection`` (A ∩ B)        - overlap region (optional pre-inset)
* ``difference`` (A \\ B)          - subtract (optional inflate-B-first)
* ``xor`` (A △ B)                 - symmetric difference (Exclusion)
* ``buffer``                      - inflate / deflate a shape (Inset / Outset)
* ``cutout``                      - one-step "cut B with N px breathing room
                                     around it from A"
* ``outline``                     - one-step annulus of width N around the
                                     boundary of a shape

Cutout-with-margin and outline-as-band are not standard one-button ops in any
of the desktop editors surveyed (Inkscape, Illustrator, Affinity, Figma,
Sketch, CorelDRAW) - each requires a 2-step workflow there. Bundling them
here is the main agentic value-add over a thin shapely wrapper.

Operates polygon-only via ``shapely`` (already a project dep). SVG Bezier /
Arc segments are flattened to polylines via ``_svg_paths`` before the op,
so curve-rich input round-trips as straight-segment ``M ... L ... L ... Z``.
The lossy round-trip surfaces a ``CURVE-FLATTENED`` warning through the
``_warning_gate`` so the agent has to ack it consciously; ``--tolerance``
exposes shapely's ``.simplify()`` to drop near-collinear noise.

Output mode is identical to ``calc_connector`` / ``calc_primitives``: a
diagnostic line on stdout plus a paste-ready ``<path d="...">`` snippet.
``--replace-id ID`` switches to in-place mode: the named element's ``d=``
is rewritten and the full SVG is emitted to ``--out`` or stdout.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools._svg_paths import (
    extract_xml_comments,
    find_element_by_id,
    get_element_class,
    parse_svg_source,
    path_d_from_geom,
    path_has_curves,
    polygons_from_path,
    replace_path_d_in_xml,
    sample_path_to_polylines,
)
from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    enforce_warning_acks,
)

# Operations that take 1 input, 2 inputs, or N inputs.
_SINGLE_INPUT_OPS = {"buffer", "outline"}
_DUAL_INPUT_OPS = {"cutout"}
_MULTI_INPUT_OPS = {"union", "intersection", "difference", "xor"}
_OPS_REQUIRING_MARGIN = {"buffer", "outline", "cutout"}
_OPS_IGNORING_MARGIN = {"union", "xor"}

_JOIN_STYLE_MAP = {
    "round": "round",
    "mitre": "mitre",
    "miter": "mitre",  # accept American spelling as alias
    "bevel": "bevel",
}


def boolean_op(
    op: str,
    geoms: list,
    *,
    margin: float = 0.0,
    join: str = "round",
    mitre_limit: float = 5.0,
    quad_segs: int = 16,
):
    """Dispatch to the named shapely operation.

    Returns a shapely Polygon, MultiPolygon, or empty geometry.
    """
    from shapely.ops import unary_union

    join_style = _JOIN_STYLE_MAP.get(join, "round")
    buffer_kwargs = dict(
        join_style=join_style,
        mitre_limit=mitre_limit,
        quad_segs=quad_segs,
    )

    if op == "union":
        return unary_union(geoms)

    if op == "intersection":
        if margin != 0:
            geoms = [g.buffer(-abs(margin), **buffer_kwargs) for g in geoms]
        result = geoms[0]
        for g in geoms[1:]:
            result = result.intersection(g)
        return result

    if op == "difference":
        if not geoms:
            raise ValueError("difference requires at least one input")
        if len(geoms) == 1:
            return geoms[0]
        subtrahend = unary_union(geoms[1:])
        if margin != 0:
            subtrahend = subtrahend.buffer(margin, **buffer_kwargs)
        return geoms[0].difference(subtrahend)

    if op == "xor":
        if not geoms:
            raise ValueError("xor requires at least one input")
        result = geoms[0]
        for g in geoms[1:]:
            result = result.symmetric_difference(g)
        return result

    if op == "buffer":
        if len(geoms) != 1:
            raise ValueError("buffer takes exactly one input shape")
        return geoms[0].buffer(margin, **buffer_kwargs)

    if op == "cutout":
        if len(geoms) != 2:
            raise ValueError("cutout takes exactly two input shapes (container, hole)")
        hole = geoms[1].buffer(margin, **buffer_kwargs)
        return geoms[0].difference(hole)

    if op == "outline":
        if len(geoms) != 1:
            raise ValueError("outline takes exactly one input shape")
        if margin == 0:
            raise ValueError("outline requires a non-zero --margin (band width)")
        half = margin / 2.0
        outer = geoms[0].buffer(half, **buffer_kwargs)
        inner = geoms[0].buffer(-half, **buffer_kwargs)
        return outer.difference(inner)

    raise ValueError(f"unknown op: {op!r}")


def format_result(geom) -> dict:
    """Return a diagnostic dict describing a shapely geometry."""
    if geom is None or geom.is_empty:
        return {
            "kind": "empty",
            "island_count": 0,
            "area": 0.0,
            "bbox": None,
            "path_d": "",
            "is_empty": True,
        }
    if geom.geom_type == "MultiPolygon":
        kind = "multi-polygon"
        island_count = len(list(geom.geoms))
    elif geom.geom_type == "Polygon":
        kind = "polygon"
        island_count = 1
    else:
        kind = geom.geom_type.lower()
        island_count = 1

    minx, miny, maxx, maxy = geom.bounds
    return {
        "kind": kind,
        "island_count": island_count,
        "area": float(geom.area),
        "bbox": (float(minx), float(miny), float(maxx), float(maxy)),
        "path_d": path_d_from_geom(geom),
        "is_empty": False,
    }


# ---------------------------------------------------------------------------
# Input resolution: id -> svgelements element -> shapely geometry
# ---------------------------------------------------------------------------


def _element_to_path(elem):
    """Coerce an svgelements element into an svgelements Path.

    Rect / Circle / Ellipse / Line / Polyline / Polygon expose ``d()`` (or a
    Path equivalent). Path objects pass through. Anything else returns
    ``None`` and the caller fires INPUT-DEGENERATE.
    """
    import svgelements as _se

    if isinstance(elem, _se.Path):
        return elem

    # Rect, Circle, Ellipse, Polygon, Polyline, Line all expose .d() on
    # recent svgelements versions; coerce to a Path.
    if hasattr(elem, "d") and callable(elem.d):
        try:
            d = elem.d()
            if d:
                return _se.Path(d)
        except Exception:
            pass
    # Polygon / Polyline carry a points list - build a Path manually.
    points = getattr(elem, "points", None)
    if points:
        try:
            tag = type(elem).__name__
            d_parts = [f"M {points[0][0]} {points[0][1]}"]
            for x, y in points[1:]:
                d_parts.append(f"L {x} {y}")
            if tag == "Polygon":
                d_parts.append("Z")
            return _se.Path(" ".join(d_parts))
        except Exception:
            return None
    return None


def _resolve_input_to_geom(svg_doc, element_id: str, *, tolerance):
    """Resolve one ``--ids`` argument to ``(geom, warnings)``.

    Returns ``(geom, [warning_text, ...])``. ``geom`` is None on hard failure
    (id not found, can't coerce to path); a warning is appended in that
    case so the gate fires.
    """
    warnings = []
    elem = find_element_by_id(svg_doc, element_id)
    if elem is None:
        warnings.append(f"INPUT-NOT-FOUND: no element with id={element_id!r} in source SVG")
        return None, warnings

    path = _element_to_path(elem)
    if path is None:
        warnings.append(
            f"INPUT-DEGENERATE: element id={element_id!r} could not be coerced "
            "to a path (unsupported element type)"
        )
        return None, warnings

    if path_has_curves(path):
        warnings.append(
            f"CURVE-FLATTENED: element id={element_id!r} contains Bezier or "
            "Arc segments; flattened to polyline (lossy round-trip). Tune "
            "with --tolerance to drop near-collinear noise."
        )

    # Detect open subpaths before polygon construction.
    subpaths = sample_path_to_polylines(path)
    has_open = any(not closed for _pts, closed in subpaths if len(_pts) >= 2)
    if has_open:
        warnings.append(
            f"INPUT-OPEN-PATH: element id={element_id!r} has subpath(s) "
            "without an explicit Z (close); closed implicitly with a "
            "straight segment to first point."
        )

    try:
        geom = polygons_from_path(path, tolerance=tolerance)
    except ValueError as exc:
        warnings.append(
            f"INPUT-DEGENERATE: element id={element_id!r} produced no valid polygon ({exc})."
        )
        return None, warnings

    return geom, warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svg-infographics boolean",
        description=(
            "Boolean / margin operations on SVG paths. Headless equivalent of "
            "Inkscape Path > Union/Intersection/Difference/Exclusion plus "
            "Inset / Outset / one-step cutout-with-margin and outline-as-band."
        ),
    )
    parser.add_argument(
        "--op",
        required=True,
        choices=sorted(_SINGLE_INPUT_OPS | _DUAL_INPUT_OPS | _MULTI_INPUT_OPS),
        help="Operation to perform.",
    )
    parser.add_argument(
        "--svg",
        required=True,
        type=Path,
        help="Path to source SVG file.",
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        required=True,
        metavar="ID",
        help=(
            "Element id(s) to operate on. Order matters for difference "
            "(geom[0] minus rest) and cutout (container, hole)."
        ),
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.0,
        help=(
            "Distance in user units. Sign: + grows (outset), - shrinks "
            "(inset). Required for buffer / outline / cutout."
        ),
    )
    parser.add_argument(
        "--join",
        choices=sorted(_JOIN_STYLE_MAP.keys()),
        default="round",
        help="Corner join style for buffer-based ops (default: round).",
    )
    parser.add_argument(
        "--mitre-limit",
        type=float,
        default=5.0,
        help="Mitre limit for --join mitre (default: 5.0).",
    )
    parser.add_argument(
        "--quad-segs",
        type=int,
        default=16,
        help="Round-corner sample count (default: 16).",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=None,
        help=(
            "Polyline simplification tolerance (shapely .simplify). Drops "
            "near-collinear noise from heavy curve flattening."
        ),
    )
    parser.add_argument(
        "--replace-id",
        default=None,
        metavar="ID",
        help=(
            "In-place mode: rewrite this element's d= attribute and emit the "
            "full SVG to --out (or stdout). Without this flag the tool emits "
            "only the resulting <path> snippet."
        ),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write output to file instead of stdout.",
    )
    parser.add_argument(
        "--class",
        dest="css_class",
        default=None,
        help=(
            "CSS class to apply to the emitted <path>. Defaults to the class "
            "of --replace-id's element if given, else no class."
        ),
    )
    add_ack_warning_arg(parser)
    return parser


def _validate_args(args, parser) -> None:
    op = args.op
    n_ids = len(args.ids)

    if op in _SINGLE_INPUT_OPS and n_ids != 1:
        parser.error(f"--op {op} takes exactly one --ids value (got {n_ids})")
    if op in _DUAL_INPUT_OPS and n_ids != 2:
        parser.error(f"--op {op} takes exactly two --ids values (got {n_ids})")
    if op in _MULTI_INPUT_OPS and n_ids < 2:
        parser.error(f"--op {op} requires at least two --ids values (got {n_ids})")

    if op in _OPS_REQUIRING_MARGIN and args.margin == 0:
        parser.error(f"--op {op} requires --margin (non-zero)")


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    _validate_args(args, parser)

    if not args.svg.is_file():
        print(f"ERROR: SVG file not found: {args.svg}", file=sys.stderr)
        return 1

    try:
        svg_doc, _viewbox = parse_svg_source(args.svg)
    except Exception as exc:
        print(f"ERROR: failed to parse SVG: {exc}", file=sys.stderr)
        return 1

    warnings: list[str] = []

    # Soft warning (gate-bypassed): margin ignored for ops that don't use it.
    if args.op in _OPS_IGNORING_MARGIN and args.margin != 0:
        print(
            f"NOTE: --margin {args.margin} ignored for --op {args.op}",
            file=sys.stderr,
        )

    # Resolve every id to a shapely geometry; collect input-phase warnings.
    geoms = []
    for element_id in args.ids:
        geom, w = _resolve_input_to_geom(svg_doc, element_id, tolerance=args.tolerance)
        warnings.extend(w)
        if geom is not None:
            geoms.append(geom)

    # Hard-fail early if any input did not resolve - the gate handles the
    # exit-2 for INPUT-NOT-FOUND / INPUT-DEGENERATE / INPUT-OPEN-PATH.
    if len(geoms) != len(args.ids):
        enforce_warning_acks(warnings, sys.argv[1:], args.ack_warning)
        # If we get here, every input warning was acked - but we still don't
        # have geoms, so cannot proceed. Report and exit 1.
        print(
            "ERROR: one or more inputs did not resolve to a valid shape; cannot run op.",
            file=sys.stderr,
        )
        return 1

    # MARGIN-EXCEEDS-SHAPE pre-check: warn if |margin| > 0.5 * min(bbox dim)
    # of any input.
    if args.margin != 0:
        for element_id, geom in zip(args.ids, geoms):
            minx, miny, maxx, maxy = geom.bounds
            min_dim = min(maxx - minx, maxy - miny)
            if abs(args.margin) > 0.5 * min_dim:
                warnings.append(
                    f"MARGIN-EXCEEDS-SHAPE: --margin {args.margin} exceeds "
                    f"half the smallest dimension of id={element_id!r} "
                    f"(min dim {min_dim:.2f}); result may be empty or "
                    "unexpected."
                )

    # Run the op.
    try:
        result = boolean_op(
            args.op,
            geoms,
            margin=args.margin,
            join=args.join,
            mitre_limit=args.mitre_limit,
            quad_segs=args.quad_segs,
        )
    except Exception as exc:
        print(f"ERROR: op {args.op} failed: {exc}", file=sys.stderr)
        return 1

    # Post-op warnings.
    if result is None or result.is_empty:
        if args.op in {"buffer", "outline", "cutout"} and args.margin < 0:
            warnings.append(
                f"BUFFER-COLLAPSE: --op {args.op} with --margin "
                f"{args.margin} fully erased the shape; result is empty."
            )
        else:
            warnings.append(
                f"RESULT-EMPTY: --op {args.op} produced empty geometry. "
                "Inputs may be disjoint (intersection / difference) or the "
                "margin may be too aggressive."
            )
    elif result.geom_type == "MultiPolygon":
        n = len(list(result.geoms))
        if n > 1:
            warnings.append(
                f"RESULT-MULTI-ISLAND: --op {args.op} produced {n} disconnected "
                "components; output is one <path> with multiple M...Z subpaths."
            )

    # COMMENTS-NEED-REVIEW: when rewriting in place, surface every XML
    # comment in the source so the agent reviews whether each still
    # describes the (possibly changed) surrounding structure. Comments
    # are PRESERVED in the output verbatim - the warning is review-only,
    # not a copy-paste burden.
    source_comments = []
    if args.replace_id:
        try:
            source_xml_text = args.svg.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"ERROR: failed to read SVG for in-place rewrite: {exc}", file=sys.stderr)
            return 1
        source_comments = extract_xml_comments(source_xml_text)
        if source_comments:
            n = len(source_comments)
            lines = [
                f"COMMENTS-NEED-REVIEW: source SVG contained {n} comment(s); "
                f"preserved verbatim in output but the boolean op rewrote "
                f"element id={args.replace_id!r}. Verify each comment still "
                "describes the surrounding structure; edit or delete in the "
                "output if not. Comments:"
            ]
            for c in source_comments:
                near = f" near id={c.near_id}" if c.near_id else ""
                lines.append(f"  [line ~{c.approx_line}{near}]: {c.text}")
            lines.append(
                "Ack with reason: 'comments still apply' or 'edited comments after review'."
            )
            warnings.append("\n".join(lines))

    # Gate: enforce acks. Exits 2 if anything is unacked.
    enforce_warning_acks(warnings, sys.argv[1:], args.ack_warning)

    # All clear (or all acked). Emit output.
    info = format_result(result)
    css_class = args.css_class
    if css_class is None and args.replace_id:
        target = find_element_by_id(svg_doc, args.replace_id)
        if target is not None:
            css_class = get_element_class(target)

    return _emit_output(args, info, css_class)


def _emit_output(args, info: dict, css_class: str | None) -> int:
    """Print the diagnostic + path / replace and emit. Returns exit code."""
    bbox = info["bbox"]
    bbox_str = (
        f"({bbox[0]:.3f}, {bbox[1]:.3f}, {bbox[2]:.3f}, {bbox[3]:.3f})"
        if bbox is not None
        else "(empty)"
    )
    diag = (
        f"# op={args.op}  inputs={','.join(args.ids)}  kind={info['kind']}\n"
        f"# islands={info['island_count']}  area={info['area']:.3f}  bbox={bbox_str}"
    )

    if args.replace_id:
        # Read raw XML and rewrite the d= on the named element. Comments
        # are preserved by the parser; the returned list is metadata
        # already surfaced through the gate before we reached this point.
        xml_text = args.svg.read_text(encoding="utf-8")
        try:
            new_xml, _comments = replace_path_d_in_xml(xml_text, args.replace_id, info["path_d"])
        except ValueError as exc:
            print(f"ERROR: --replace-id failed: {exc}", file=sys.stderr)
            return 1
        if args.out is not None:
            args.out.write_text(new_xml, encoding="utf-8")
            print(diag, file=sys.stderr)
            print(f"# wrote {args.out}", file=sys.stderr)
        else:
            print(diag, file=sys.stderr)
            sys.stdout.write(new_xml)
            sys.stdout.flush()
        return 0

    # Snippet mode.
    cls_attr = f' class="{css_class}"' if css_class else ""
    snippet = f'<path{cls_attr} d="{info["path_d"]}"/>'
    if args.out is not None:
        args.out.write_text(snippet + "\n", encoding="utf-8")
        print(diag, file=sys.stderr)
        print(f"# wrote {args.out}", file=sys.stderr)
    else:
        print(diag)
        print(snippet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
