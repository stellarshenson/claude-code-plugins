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


def _is_rect(s):
    return len(s) == 4 and all(isinstance(v, (int, float)) for v in s)


def _prepare_shapes(shapes):
    """Split shapes into (rect_list, polygon_list) where rects are kept as
    plain ``(x0, y0, x2, y2)`` tuples (fast AABB overlap) and polygons are
    converted to shapely geometries once up front. Called once per scan so
    the inner loop avoids per-cell shapely constructor cost."""
    from shapely.geometry import Polygon
    rects = []
    polys = []
    for s in shapes:
        if _is_rect(s):
            sx, sy, sw, sh = s
            rects.append((sx, sy, sx + sw, sy + sh))
        else:
            polys.append(Polygon(s))
    return rects, polys


def _cell_intersects_any(rx0, ry0, rx2, ry2, rect_aabb, poly_geoms):
    """Fast overlap check: pure-Python AABB for rects, shapely for polygons.

    A cell overlaps a shape when the two axis-aligned boxes overlap, OR (for
    the polygon path) when the shapely polygon intersects the cell box.
    """
    for sx0, sy0, sx2, sy2 in rect_aabb:
        if rx0 < sx2 and sx0 < rx2 and ry0 < sy2 and sy0 < ry2:
            return True
    if poly_geoms:
        from shapely.geometry import box
        cell = box(rx0, ry0, rx2, ry2)
        for g in poly_geoms:
            if cell.intersects(g):
                return True
    return False


def _intersects_any(rect, shapes):  # legacy API, unchanged semantics
    rects, polys = _prepare_shapes(shapes)
    return _cell_intersects_any(
        rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3], rects, polys
    )


def find_empty_regions(
    canvas,
    shapes,
    coarse_divisions=8,
    max_depth=3,
    simplify_tolerance=2.0,
    tolerance=20.0,
    min_area=500.0,
):
    """Find connected free regions in a canvas.

    Args:
        canvas: (x, y, w, h) bounding rect of the area to scan
        shapes: list of occupied shapes - each either (x, y, w, h) rect
            or [(x,y), (x,y), ...] polygon vertex list
        coarse_divisions: initial NxN grid resolution (default 8)
        max_depth: recursion depth for subdividing occupied cells (default 3).
            Higher depths find smaller slivers at cost of noise.
        simplify_tolerance: Douglas-Peucker tolerance for the output polygon
            vertex list. 0 = no simplification, higher = fewer vertices.
        tolerance: safety standoff in px. Each free region is shrunk inward
            by this amount (shapely buffer with negative distance). Default
            20px - keeps callouts clear of adjacent shape edges. Set to 0
            to disable inward erosion.
        min_area: drop regions smaller than this (after erosion). Default
            500 px^2 - smaller islands can't fit a callout text bbox. Set
            to 0 to keep every region.

    Returns:
        list of {"boundary": [(x, y), ...], "area": float} dicts, one per
        connected free region, sorted by area descending. Regions that
        disappear entirely after erosion, or whose area falls below
        `min_area`, are dropped.
    """
    from shapely.geometry import box
    from shapely.ops import unary_union

    cx, cy, cw, ch = canvas
    cell_w = cw / coarse_divisions
    cell_h = ch / coarse_divisions

    # Prepare shapes once: keep rects as plain AABB tuples and convert any
    # polygon shapes to shapely once. The hot path inside `scan` does
    # pure-Python AABB overlap for rects and only touches shapely when the
    # shape list contains real polygons.
    rect_aabb, poly_geoms = _prepare_shapes(shapes)

    free_rects = []  # (x0, y0, x2, y2)

    def scan(x0, y0, x2, y2, depth):
        if not _cell_intersects_any(x0, y0, x2, y2, rect_aabb, poly_geoms):
            free_rects.append((x0, y0, x2, y2))
            return
        if depth >= max_depth:
            return  # fully occupied, stop recursing
        sw = (x2 - x0) / 3
        sh = (y2 - y0) / 3
        for i in range(3):
            for j in range(3):
                sx0 = x0 + i * sw
                sy0 = y0 + j * sh
                scan(sx0, sy0, sx0 + sw, sy0 + sh, depth + 1)

    for i in range(coarse_divisions):
        for j in range(coarse_divisions):
            scan(
                cx + i * cell_w,
                cy + j * cell_h,
                cx + (i + 1) * cell_w,
                cy + (j + 1) * cell_h,
                0,
            )

    if not free_rects:
        return []

    # Build shapely boxes once for the union (unary_union still needs them).
    union = unary_union([box(x0, y0, x2, y2) for x0, y0, x2, y2 in free_rects])
    if union.is_empty:
        return []

    if tolerance > 0:
        union = union.buffer(-tolerance, join_style=2)
        if union.is_empty:
            return []

    if union.geom_type == "Polygon":
        polys = [union]
    elif union.geom_type == "MultiPolygon":
        polys = list(union.geoms)
    else:
        return []

    results = []
    for p in polys:
        if simplify_tolerance > 0:
            p = p.simplify(simplify_tolerance, preserve_topology=True)
        if p.is_empty or p.area < min_area:
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
        help="Max subdivision depth for occupied cells (default 3). "
             "Higher depths find smaller slivers at cost of noise.",
    )
    parser.add_argument(
        "--simplify", type=float, default=2.0,
        help="Douglas-Peucker simplify tolerance in px (default 2.0)",
    )
    parser.add_argument(
        "--tolerance", type=float, default=20.0,
        help="Inward standoff in px shrinking every free region (default 20, "
             "minimum recommended for callouts). 0 disables.",
    )
    parser.add_argument(
        "--min-area", type=float, default=500.0,
        help="Drop regions smaller than this in px^2 after erosion "
             "(default 500). Smaller islands cannot fit a callout text bbox. "
             "Set 0 to keep every region.",
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

    if args.tolerance < 20.0:
        print(
            f"WARNING: --tolerance {args.tolerance} is below the 20px minimum "
            "recommended for callouts; leaders may clip adjacent shapes.",
            file=sys.stderr,
        )

    regions = find_empty_regions(
        canvas=tuple(args.canvas),
        shapes=args.shapes,
        coarse_divisions=args.coarse,
        max_depth=args.depth,
        simplify_tolerance=args.simplify,
        tolerance=args.tolerance,
        min_area=args.min_area,
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
