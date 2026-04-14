"""Identify empty regions in an SVG canvas via recursive quadtree-style
occupancy scan, then return their boundaries.

Algorithm:
  1. Divide canvas into coarse square grid.
  2. For each cell, test intersection with the list of occupied shapes
     (rects or polygons).
  3. Occupied cells subdivide 3x3 recursively up to `max_depth` levels.
  4. Union all free cells via shapely → get connected free regions
     (MultiPolygon or Polygon).
  5. For each free region, return its exterior boundary as a polygon
     vertex list. Callers can run `geom offset-polygon --direction inward`
     to inset with a standoff, or pass the vertices to `calc_spline` for
     Bezier smoothing of the boundary.

Use case: placing callouts, labels, or secondary elements on a populated
canvas without overlapping existing content. The tool tells Claude where
space is left.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys


def _intersects_any(rect, shapes):
    """True if the rect overlaps any shape in the list."""
    from shapely.geometry import Polygon, box

    r = box(rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
    for s in shapes:
        if len(s) == 4 and all(isinstance(v, (int, float)) for v in s):
            # axis-aligned rect
            sx, sy, sw, sh = s
            sbox = box(sx, sy, sx + sw, sy + sh)
            if r.intersects(sbox):
                return True
        else:
            # polygon vertex list
            poly = Polygon(s)
            if r.intersects(poly):
                return True
    return False


def find_empty_regions(
    canvas,
    shapes,
    coarse_divisions=8,
    max_depth=3,
    simplify_tolerance=2.0,
):
    """Find connected free regions in a canvas.

    Args:
        canvas: (x, y, w, h) bounding rect of the area to scan
        shapes: list of occupied shapes - each either (x, y, w, h) rect
            or [(x,y), (x,y), ...] polygon vertex list
        coarse_divisions: initial NxN grid resolution (default 8)
        max_depth: recursion depth for subdividing occupied cells (default 3)
        simplify_tolerance: Douglas-Peucker tolerance for the output polygon
            vertex list. 0 = no simplification, higher = fewer vertices.

    Returns:
        list of {"boundary": [(x, y), ...], "area": float} dicts, one per
        connected free region, sorted by area descending.
    """
    from shapely.geometry import box
    from shapely.ops import unary_union

    cx, cy, cw, ch = canvas
    cell_w = cw / coarse_divisions
    cell_h = ch / coarse_divisions

    free_boxes = []

    def scan(rect, depth):
        if not _intersects_any(rect, shapes):
            free_boxes.append(box(rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3]))
            return
        if depth >= max_depth:
            return  # fully occupied, stop recursing
        sw = rect[2] / 3
        sh = rect[3] / 3
        for i in range(3):
            for j in range(3):
                sub = (rect[0] + i * sw, rect[1] + j * sh, sw, sh)
                scan(sub, depth + 1)

    for i in range(coarse_divisions):
        for j in range(coarse_divisions):
            rect = (cx + i * cell_w, cy + j * cell_h, cell_w, cell_h)
            scan(rect, 0)

    if not free_boxes:
        return []

    union = unary_union(free_boxes)
    if union.is_empty:
        return []

    if union.geom_type == "Polygon":
        polys = [union]
    else:  # MultiPolygon
        polys = list(union.geoms)

    results = []
    for p in polys:
        if simplify_tolerance > 0:
            p = p.simplify(simplify_tolerance, preserve_topology=True)
        if p.is_empty:
            continue
        coords = [(float(x), float(y)) for x, y in p.exterior.coords]
        results.append({"boundary": coords, "area": float(p.area)})
    results.sort(key=lambda r: -r["area"])
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_literal(s):
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError) as exc:
        raise argparse.ArgumentTypeError(f"invalid literal: {exc}")


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics empty-space",
        description="Identify empty regions on a canvas via quadtree subdivision.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--canvas", type=_parse_literal, required=True,
        help="Canvas rect as '(x, y, w, h)'",
    )
    parser.add_argument(
        "--shapes", type=_parse_literal, required=True,
        help="List of occupied shapes: '[(x,y,w,h), [(x,y),...], ...]'",
    )
    parser.add_argument(
        "--coarse", type=int, default=8,
        help="Coarse grid divisions per axis (default 8)",
    )
    parser.add_argument(
        "--depth", type=int, default=3,
        help="Max subdivision depth for occupied cells (default 3)",
    )
    parser.add_argument(
        "--simplify", type=float, default=2.0,
        help="Douglas-Peucker simplify tolerance in px (default 2.0)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit JSON result only (no SVG snippet)",
    )
    parser.add_argument(
        "--stroke", default="#da8230",
        help="SVG debug stroke colour (default #da8230)",
    )
    args = parser.parse_args()

    regions = find_empty_regions(
        canvas=tuple(args.canvas),
        shapes=args.shapes,
        coarse_divisions=args.coarse,
        max_depth=args.depth,
        simplify_tolerance=args.simplify,
    )

    if args.json:
        json.dump(regions, sys.stdout, indent=2)
        print()
        return

    print(f"=== EMPTY REGIONS ({len(regions)}) ===")
    for i, r in enumerate(regions):
        print(f"[{i}] area={r['area']:.0f}px^2, {len(r['boundary'])} vertices")

    print("\n--- SVG Snippet ---\n")
    for i, r in enumerate(regions):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in r["boundary"])
        print(
            f'  <polygon points="{pts}" fill="none" stroke="{args.stroke}" '
            f'stroke-width="0.8" stroke-dasharray="4,3" opacity="0.6"/>'
        )


if __name__ == "__main__":
    main()
