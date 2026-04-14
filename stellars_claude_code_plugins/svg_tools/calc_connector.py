#!/usr/bin/env python3
"""
SVG connector calculator for the svg-infographics skill.

Two modes:

1. Straight-line mode (default): two endpoints, optional margin and arrowhead.
   python calc_connector.py --from 520,55 --to 590,135
   python calc_connector.py --from 520,55 --to 590,135 --margin 6 --head-size 10,5

2. Free-curve mode: 3+ waypoints, smooth PCHIP curve through them, optional
   arrowhead on either or both ends. Returns sample points, path d, trimmed
   path d (with arrowhead clearance), and per-end angle + polygon so Claude
   can decide where labels go and how to render the head.
   python calc_connector.py --waypoints "100,80 200,40 300,120 400,60" \\
       --samples 200 --arrow end --head-size 12,6

Straight-line arguments:
    --from X,Y        Source point (edge of source element)
    --to X,Y          Target point (edge of target element)
    --margin N        Padding in px to pull back from both source and target edges (default: 0)
    --head-size L,H   Arrowhead length and half-height (default: 10,5)

Free-curve arguments:
    --waypoints "X1,Y1 X2,Y2 ..."  Three or more 2D waypoints (any direction)
    --samples N                    Curve density (default: 200)
    --arrow {none,start,end,both}  Where to put arrowheads (default: none)
    --head-size L,H                Arrowhead length and half-height (default: 10,5)
    --margin N                     Trim N px of arc length from each end (default: 0)

Pill cutout mode (straight-line only):
    --cutout X,Y,W,H   If a pill label sits on the connector, provide its rect.
                        The script splits the connector into two segments with a gap
                        around the pill (adds --margin padding around the pill rect).

Output (free-curve mode):
    For each requested arrowhead end the script returns tip position, tangent
    angle (degrees), the three polygon vertices in world coordinates, the
    "stem-back" point where the visible stroke should stop, and a ready-to-use
    transform string. Also returns the full PCHIP path d, a trimmed path d
    that leaves arrowhead clearance, and the dense sample list.
"""

import argparse
import math
import sys


def calc_connector(src_x, src_y, tgt_x, tgt_y, margin=0, head_len=10, head_half_h=5):
    dx = tgt_x - src_x
    dy = tgt_y - src_y
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    full_length = math.sqrt(dx**2 + dy**2)

    # Effective length after pulling back margins from both ends
    effective_length = full_length - 2 * margin

    if effective_length <= head_len + 2:
        print(
            f"WARNING: effective length {effective_length:.1f}px too short for arrowhead",
            file=sys.stderr,
        )

    # In local (flat) coordinates:
    # - tip is at origin (0, 0) after translate
    # - stem runs from (-effective_length, 0) to (-head_len, 0)
    # - arrowhead polygon at (0,0 -head_len,-head_half_h -head_len,head_half_h)
    stem_start_local = -effective_length
    stem_end_local = -head_len

    # The <g> transform translates to the tip position (target minus margin along the line)
    tip_x = tgt_x - margin * math.cos(angle_rad)
    tip_y = tgt_y - margin * math.sin(angle_rad)

    # World coordinates of stem start (for verification)
    stem_start_world_x = tip_x + stem_start_local * math.cos(angle_rad)
    stem_start_world_y = tip_y + stem_start_local * math.sin(angle_rad)

    # World coordinates of stem end (where arrowhead back sits)
    stem_end_world_x = tip_x + stem_end_local * math.cos(angle_rad)
    stem_end_world_y = tip_y + stem_end_local * math.sin(angle_rad)

    return {
        "angle_deg": angle_deg,
        "full_length": full_length,
        "effective_length": effective_length,
        "tip_x": tip_x,
        "tip_y": tip_y,
        "stem_start_local": stem_start_local,
        "stem_end_local": stem_end_local,
        "head_len": head_len,
        "head_half_h": head_half_h,
        "stem_start_world": (stem_start_world_x, stem_start_world_y),
        "stem_end_world": (stem_end_world_x, stem_end_world_y),
    }


def calc_cutout(
    src_x,
    src_y,
    tgt_x,
    tgt_y,
    pill_x,
    pill_y,
    pill_w,
    pill_h,
    margin=0,
    padding=3,
    head_len=10,
    head_half_h=5,
):
    """Split a connector into two segments with a gap around a pill rect."""
    dx = tgt_x - src_x
    dy = tgt_y - src_y

    # Pill rect with padding
    px1, py1 = pill_x - padding, pill_y - padding
    px2, py2 = pill_x + pill_w + padding, pill_y + pill_h + padding

    # Find where the line enters and exits the padded pill rect
    # Parameterize line as P = src + t * (tgt - src), t in [0, 1]
    # Check intersection with all 4 edges
    intersections = []
    for edge_val, is_x in [(px1, True), (px2, True), (py1, False), (py2, False)]:
        if is_x:
            if dx == 0:
                continue
            t = (edge_val - src_x) / dx
        else:
            if dy == 0:
                continue
            t = (edge_val - src_y) / dy

        if 0 < t < 1:
            ix = src_x + t * dx
            iy = src_y + t * dy
            if px1 - 1 <= ix <= px2 + 1 and py1 - 1 <= iy <= py2 + 1:
                intersections.append((t, ix, iy))

    if len(intersections) < 2:
        return None  # Line doesn't cross pill

    intersections.sort(key=lambda x: x[0])
    t_enter, enter_x, enter_y = intersections[0]
    t_exit, exit_x, exit_y = intersections[-1]

    # Segment 1: source -> pill entry
    seg1 = calc_connector(
        src_x, src_y, enter_x, enter_y, margin=margin, head_len=0, head_half_h=0
    )  # No arrowhead on seg1

    # Segment 2: pill exit -> target (with arrowhead)
    seg2 = calc_connector(
        exit_x, exit_y, tgt_x, tgt_y, margin=margin, head_len=head_len, head_half_h=head_half_h
    )

    return {
        "segment1": seg1,
        "segment1_from": (src_x, src_y),
        "segment1_to": (enter_x, enter_y),
        "segment2": seg2,
        "segment2_from": (exit_x, exit_y),
        "segment2_to": (tgt_x, tgt_y),
    }


# ---------------------------------------------------------------------------
# Shared geometry helpers (polyline, PCHIP, arrowheads)
# ---------------------------------------------------------------------------


def _arrowhead_polygon_world(tip_x, tip_y, angle_rad, head_len, head_half_h):
    """Build the 3 world-space vertices of an arrowhead pointing along angle_rad.

    Local arrow shape is `tip at (0,0)`, `back at (-head_len, ±head_half_h)`,
    rotated by angle_rad (CCW) and translated to (tip_x, tip_y).
    """
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    def to_world(lx, ly):
        return (tip_x + cos_a * lx - sin_a * ly, tip_y + sin_a * lx + cos_a * ly)

    return [
        (tip_x, tip_y),
        to_world(-head_len, -head_half_h),
        to_world(-head_len, head_half_h),
    ]


def _polyline_length(points):
    """Total arc length of a polyline."""
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total += math.hypot(dx, dy)
    return total


def _polyline_to_path_d(points):
    """Convert (x, y) list to an SVG path d string with M + L commands."""
    if not points:
        return ""
    parts = [f"M{points[0][0]:.2f},{points[0][1]:.2f}"]
    for x, y in points[1:]:
        parts.append(f"L{x:.2f},{y:.2f}")
    return " ".join(parts)


def _trim_polyline(points, distance, end):
    """Walk `distance` of arc length inward from `end` and clip the polyline.

    end is "start" or "end". Returns a new list of points whose total length
    is the original minus `distance`. Used to make room for an arrowhead so
    the visible stroke does not poke through the polygon.
    """
    if distance <= 0 or len(points) < 2:
        return list(points)

    pts = list(points) if end == "end" else list(reversed(points))

    remaining = distance
    while len(pts) >= 2:
        ax, ay = pts[-1]
        bx, by = pts[-2]
        seg_dx = ax - bx
        seg_dy = ay - by
        seg_len = math.hypot(seg_dx, seg_dy)
        if seg_len == 0:
            pts.pop()
            continue
        if seg_len <= remaining:
            remaining -= seg_len
            pts.pop()
            continue
        # Trim within this segment: move the last point back by `remaining`
        ratio = remaining / seg_len
        new_x = ax - seg_dx * ratio
        new_y = ay - seg_dy * ratio
        pts[-1] = (new_x, new_y)
        break

    return pts if end == "end" else list(reversed(pts))


def _tangent_unit(points, end):
    """Unit tangent vector pointing outward at the start or end of a polyline.

    For end="end" the tangent points from the previous sample to the last
    sample (forward direction). For end="start" it points from the second
    sample back to the first (so an arrow placed at the start points away
    from the curve).
    """
    if len(points) < 2:
        return (1.0, 0.0)
    if end == "end":
        bx, by = points[-2]
        ax, ay = points[-1]
    else:
        bx, by = points[1]
        ax, ay = points[0]
    dx = ax - bx
    dy = ay - by
    length = math.hypot(dx, dy)
    if length == 0:
        return (1.0, 0.0)
    return (dx / length, dy / length)


def _pchip_slopes_1d(xs, ys):
    """PCHIP slopes for a 1D series with strictly increasing xs.

    Standard Fritsch-Carlson formula: harmonic mean of secant slopes when
    they have the same sign, zero at extrema, special-cased at endpoints.
    """
    n = len(xs)
    if n < 2:
        return [0.0] * n
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    delta = [(ys[i + 1] - ys[i]) / h[i] if h[i] != 0 else 0 for i in range(n - 1)]
    slopes = [0.0] * n

    for i in range(1, n - 1):
        if delta[i - 1] * delta[i] <= 0:
            slopes[i] = 0.0
        else:
            w1 = 2 * h[i] + h[i - 1]
            w2 = h[i] + 2 * h[i - 1]
            slopes[i] = (w1 + w2) / (w1 / delta[i - 1] + w2 / delta[i])

    # Endpoint slopes: shape-preserving one-sided estimate
    slopes[0] = (
        ((2 * h[0] + h[1]) * delta[0] - h[0] * delta[1]) / (h[0] + h[1]) if n > 2 else delta[0]
    )
    if slopes[0] * delta[0] <= 0:
        slopes[0] = 0.0
    elif n > 2 and abs(slopes[0]) > 3 * abs(delta[0]):
        slopes[0] = 3 * delta[0]

    if n > 2:
        slopes[-1] = ((2 * h[-1] + h[-2]) * delta[-1] - h[-1] * delta[-2]) / (h[-1] + h[-2])
        if slopes[-1] * delta[-1] <= 0:
            slopes[-1] = 0.0
        elif abs(slopes[-1]) > 3 * abs(delta[-1]):
            slopes[-1] = 3 * delta[-1]
    else:
        slopes[-1] = delta[-1]

    return slopes


def _pchip_eval_1d(xs, ys, slopes, query):
    """Evaluate a PCHIP at query x-values (must be in [xs[0], xs[-1]])."""
    out = []
    n = len(xs)
    seg = 0
    for q in query:
        while seg < n - 2 and q > xs[seg + 1]:
            seg += 1
        h = xs[seg + 1] - xs[seg]
        if h == 0:
            out.append(ys[seg])
            continue
        t = (q - xs[seg]) / h
        t2, t3 = t * t, t * t * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2
        out.append(
            h00 * ys[seg] + h10 * h * slopes[seg] + h01 * ys[seg + 1] + h11 * h * slopes[seg + 1]
        )
    return out


def pchip_parametric(waypoints, num_samples=200):
    """Parametric PCHIP through 2D waypoints (any direction, may loop).

    Parametrises by cumulative chord length so the curve can move in any
    direction including vertical, backward, or self-intersecting paths.
    Returns `num_samples` evenly-spaced points along the parameter domain.
    """
    n = len(waypoints)
    if n < 2:
        return [tuple(p) for p in waypoints]

    ts = [0.0]
    for i in range(1, n):
        dx = waypoints[i][0] - waypoints[i - 1][0]
        dy = waypoints[i][1] - waypoints[i - 1][1]
        ts.append(ts[-1] + math.hypot(dx, dy))
    if ts[-1] == 0:
        return [tuple(waypoints[0])] * num_samples

    xs = [p[0] for p in waypoints]
    ys = [p[1] for p in waypoints]

    if n == 2:
        # Two waypoints: just a straight line resampled.
        result = []
        for i in range(num_samples):
            t = i / (num_samples - 1) if num_samples > 1 else 0
            result.append((xs[0] + t * (xs[1] - xs[0]), ys[0] + t * (ys[1] - ys[0])))
        return result

    sx = _pchip_slopes_1d(ts, xs)
    sy = _pchip_slopes_1d(ts, ys)

    step = ts[-1] / (num_samples - 1)
    queries = [min(i * step, ts[-1]) for i in range(num_samples)]

    new_xs = _pchip_eval_1d(ts, xs, sx, queries)
    new_ys = _pchip_eval_1d(ts, ys, sy, queries)
    return list(zip(new_xs, new_ys))


# ---------------------------------------------------------------------------
# Polyline-based connector modes (L, L-chamfer, spline)
# ---------------------------------------------------------------------------


def _build_l_polyline(src_x, src_y, tgt_x, tgt_y, first_axis):
    """Two-segment L route. first_axis='h' goes horizontal first, 'v' vertical."""
    if first_axis == "h":
        corner = (tgt_x, src_y)
    elif first_axis == "v":
        corner = (src_x, tgt_y)
    else:
        raise ValueError(f"first_axis must be 'h' or 'v', got {first_axis!r}")
    return [(src_x, src_y), corner, (tgt_x, tgt_y)]


def _build_l_chamfer_polyline(src_x, src_y, tgt_x, tgt_y, first_axis, chamfer):
    """Chamfered L: replace the 90 corner with a small diagonal cut.

    For first_axis='h' (horizontal then vertical), the corner (tgt_x, src_y)
    becomes two points: (tgt_x - chamfer*sign_x, src_y) and (tgt_x, src_y +
    chamfer*sign_y). The diagonal segment between them softens the bend.
    """
    sign_x = 1 if tgt_x >= src_x else -1
    sign_y = 1 if tgt_y >= src_y else -1
    if first_axis == "h":
        before = (tgt_x - chamfer * sign_x, src_y)
        after = (tgt_x, src_y + chamfer * sign_y)
    elif first_axis == "v":
        before = (src_x, tgt_y - chamfer * sign_y)
        after = (src_x + chamfer * sign_x, tgt_y)
    else:
        raise ValueError(f"first_axis must be 'h' or 'v', got {first_axis!r}")
    return [(src_x, src_y), before, after, (tgt_x, tgt_y)]


def _build_endpoint_info(points, end, head_len, head_half_h, draw_arrow):
    """Compute tip / tangent / angle and (optionally) arrowhead polygon for one end."""
    if end == "end":
        tip = points[-1]
    else:
        tip = points[0]

    tx, ty = _tangent_unit(points, end)
    angle_rad = math.atan2(ty, tx)
    angle_deg = math.degrees(angle_rad)

    info = {
        "tip": tip,
        "tangent": (tx, ty),
        "angle_deg": angle_deg,
        "arrow": None,
    }

    if draw_arrow:
        polygon = _arrowhead_polygon_world(tip[0], tip[1], angle_rad, head_len, head_half_h)
        stem_back = (tip[0] - tx * head_len, tip[1] - ty * head_len)
        info["arrow"] = {
            "polygon": polygon,
            "stem_back": stem_back,
            "transform": f"translate({tip[0]:.2f}, {tip[1]:.2f}) rotate({angle_deg:.2f})",
            "head_len": head_len,
            "head_half_h": head_half_h,
        }

    return info


def _build_polyline_result(mode, points, head_len, head_half_h, arrow, margin=0.0):
    """Common assembly: trims margin off each end, builds endpoint info, packs result."""
    if margin > 0:
        points = _trim_polyline(points, margin, "end")
        points = _trim_polyline(points, margin, "start")

    arrow = arrow or "none"
    arrow_start = arrow in ("start", "both")
    arrow_end = arrow in ("end", "both")

    start_info = _build_endpoint_info(points, "start", head_len, head_half_h, arrow_start)
    end_info = _build_endpoint_info(points, "end", head_len, head_half_h, arrow_end)

    # Trimmed path leaves clearance for the arrowheads
    trimmed = list(points)
    if arrow_end:
        trimmed = _trim_polyline(trimmed, head_len, "end")
    if arrow_start:
        trimmed = _trim_polyline(trimmed, head_len, "start")

    return {
        "mode": mode,
        "samples": list(points),
        "path_d": _polyline_to_path_d(points),
        "trimmed_path_d": _polyline_to_path_d(trimmed),
        "total_length": _polyline_length(points),
        "start": start_info,
        "end": end_info,
    }


def calc_l(
    src_x, src_y, tgt_x, tgt_y, first_axis="h", margin=0.0, head_len=10, head_half_h=5, arrow="end"
):
    """Two-segment axis-aligned L connector."""
    pts = _build_l_polyline(src_x, src_y, tgt_x, tgt_y, first_axis)
    return _build_polyline_result("l", pts, head_len, head_half_h, arrow, margin)


def calc_l_chamfer(
    src_x,
    src_y,
    tgt_x,
    tgt_y,
    first_axis="h",
    chamfer=4.0,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
):
    """Chamfered L connector with diagonal corner cut."""
    pts = _build_l_chamfer_polyline(src_x, src_y, tgt_x, tgt_y, first_axis, chamfer)
    return _build_polyline_result("l-chamfer", pts, head_len, head_half_h, arrow, margin)


def calc_spline(waypoints, samples=200, margin=0.0, head_len=10, head_half_h=5, arrow="end"):
    """Free PCHIP spline through 2D waypoints. Waypoints may go in any direction."""
    if len(waypoints) < 2:
        raise ValueError("Spline connector needs at least 2 waypoints")
    pts = pchip_parametric(waypoints, num_samples=samples)
    return _build_polyline_result("spline", pts, head_len, head_half_h, arrow, margin)


def format_polyline_svg(result, stroke_color="#5456f3", stroke_width="1.2", opacity="0.4"):
    """Render an L / L-chamfer / spline result as a ready-to-paste SVG snippet."""
    lines = [
        f"  <!-- {result['mode']} connector: "
        f"len={result['total_length']:.0f}px "
        f"start_angle={result['start']['angle_deg']:.1f}deg "
        f"end_angle={result['end']['angle_deg']:.1f}deg -->",
        f'  <path d="{result["trimmed_path_d"]}" fill="none" '
        f'stroke="{stroke_color}" stroke-width="{stroke_width}" '
        f'opacity="{opacity}" stroke-linejoin="round" stroke-linecap="round"/>',
    ]

    for end_name in ("start", "end"):
        end = result[end_name]
        if end["arrow"] is None:
            continue
        poly_pts = " ".join(f"{px:.2f},{py:.2f}" for px, py in end["arrow"]["polygon"])
        lines.append(f'  <polygon points="{poly_pts}" fill="{stroke_color}" opacity="0.6"/>')

    return "\n".join(lines)


def format_svg(c, stroke_color="#5456f3", stroke_width="1.2", opacity="0.4"):
    """Generate ready-to-paste SVG snippet."""
    tip_x = c["tip_x"]
    tip_y = c["tip_y"]
    angle = c["angle_deg"]
    s_start = c["stem_start_local"]
    s_end = c["stem_end_local"]
    hl = c["head_len"]
    hh = c["head_half_h"]

    lines = []
    lines.append(f"  <!-- Connector: angle={angle:.1f}deg len={c['effective_length']:.0f}px -->")

    if hl > 0:
        lines.append(f'  <g transform="translate({tip_x:.1f}, {tip_y:.1f}) rotate({angle:.1f})">')
        lines.append(
            f'    <line x1="{s_start:.0f}" y1="0" x2="{s_end:.0f}" y2="0"'
            f' stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )
        lines.append(
            f'    <polygon points="0,0 -{hl},{-hh} -{hl},{hh}"'
            f' fill="{stroke_color}" opacity="0.6"/>'
        )
        lines.append("  </g>")
    else:
        # Stem only (no arrowhead) - for cutout segment 1
        lines.append(
            f'  <line x1="{c["stem_start_world"][0]:.1f}" y1="{c["stem_start_world"][1]:.1f}"'
            f' x2="{tip_x:.1f}" y2="{tip_y:.1f}"'
            f' stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    return "\n".join(lines)


_CONNECTOR_DESCRIPTION = """\
SVG connector calculator. Computes the path geometry, arrowhead polygon,
and tangent angle for a connector between elements - never hand-author
connector geometry, always run this tool.

Modes:

  straight    One straight line between two points. Stem + arrowhead built
              with a translate+rotate transform. Supports --cutout for pill
              labels sitting on the line.
              Use for: simple direct arrows between adjacent cards.

  l           Two-segment axis-aligned right-angle route. Pick which axis
              to walk first with --first-axis h|v.
              Use for: straight-then-turn connectors aligned to the grid.

  l-chamfer   L route with the 90 corner replaced by a small diagonal cut
              (--chamfer 4). Smoother visual than a sharp L.
              Use for: any direction-changing connector in finished SVGs
              (default rule: prefer this over plain L).

  spline      Smooth PCHIP curve through 3+ waypoints. Monotone, no
              overshoot, returns dense sample list + arrowhead polygons +
              tangent angles at each end.
              Use for: organic flow paths, decision boundaries, fork/merge
              manifolds, anything a designer would draw freehand.

Every mode supports --arrow {none,start,end,both}, --head-size L,H,
--margin (trims arc length from each end), --color/--width/--opacity, and
returns the trimmed path d (with arrowhead clearance baked in) so the
visible stroke never pokes through the polygon.
"""


def main():
    parser = argparse.ArgumentParser(
        description=_CONNECTOR_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["straight", "l", "l-chamfer", "spline"],
        default="straight",
        help="Connector style: straight | l | l-chamfer | spline (default: straight)",
    )
    parser.add_argument("--from", dest="src", help="Source point X,Y (straight/l/l-chamfer)")
    parser.add_argument("--to", dest="tgt", help="Target point X,Y (straight/l/l-chamfer)")
    parser.add_argument(
        "--waypoints", default=None, help='Spline waypoints "x1,y1 x2,y2 ..." (spline mode)'
    )
    parser.add_argument(
        "--samples", type=int, default=200, help="Spline interpolation samples (default: 200)"
    )
    parser.add_argument(
        "--first-axis",
        choices=["h", "v"],
        default="h",
        help="L mode first axis: 'h'=horizontal then vertical, 'v'=vice versa (default: h)",
    )
    parser.add_argument(
        "--chamfer", type=float, default=4.0, help="L-chamfer corner cut size in px (default: 4)"
    )
    parser.add_argument(
        "--arrow",
        choices=["none", "start", "end", "both"],
        default="end",
        help="Where to place arrowheads in l/l-chamfer/spline modes (default: end)",
    )
    parser.add_argument("--margin", type=float, default=0, help="Edge margin in px (default: 0)")
    parser.add_argument(
        "--head-size", default="10,5", help="Arrowhead length,half-height (default: 10,5)"
    )
    parser.add_argument(
        "--cutout", default=None, help="Pill rect X,Y,W,H for cutout gap (straight only)"
    )
    parser.add_argument("--color", default="#5456f3", help="Stroke colour (default: #5456f3)")
    parser.add_argument("--width", default="1.2", help="Stroke width (default: 1.2)")
    parser.add_argument("--opacity", default="0.4", help="Stroke opacity (default: 0.4)")
    args = parser.parse_args()

    head_len, head_half_h = map(float, args.head_size.split(","))

    if args.mode == "straight" and args.waypoints is None:
        if args.src is None or args.tgt is None:
            parser.error("--from and --to are required in straight mode")
        src_x, src_y = map(float, args.src.split(","))
        tgt_x, tgt_y = map(float, args.tgt.split(","))

        if args.cutout:
            px, py, pw, ph = map(float, args.cutout.split(","))
            result = calc_cutout(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                px,
                py,
                pw,
                ph,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
            )
            if result is None:
                print("Line does not cross pill rect - no cutout needed")
                c = calc_connector(
                    src_x,
                    src_y,
                    tgt_x,
                    tgt_y,
                    margin=args.margin,
                    head_len=head_len,
                    head_half_h=head_half_h,
                )
                print_result(c, args)
            else:
                print("=== CUTOUT MODE: two segments ===\n")
                print(
                    f"Segment 1: ({result['segment1_from'][0]:.1f},{result['segment1_from'][1]:.1f})"
                    f" -> ({result['segment1_to'][0]:.1f},{result['segment1_to'][1]:.1f})"
                )
                print(
                    f"Segment 2: ({result['segment2_from'][0]:.1f},{result['segment2_from'][1]:.1f})"
                    f" -> ({result['segment2_to'][0]:.1f},{result['segment2_to'][1]:.1f})"
                )
                print("\n--- SVG Snippet ---\n")
                print(format_svg(result["segment1"], args.color, args.width, args.opacity))
                print(format_svg(result["segment2"], args.color, args.width, args.opacity))
        else:
            c = calc_connector(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
            )
            print_result(c, args)
        return

    # New polyline-based modes
    if args.mode == "spline" or args.waypoints is not None:
        if args.waypoints is None:
            parser.error("--waypoints is required in spline mode")
        waypoints = _parse_waypoints(args.waypoints)
        result = calc_spline(
            waypoints,
            samples=args.samples,
            margin=args.margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=args.arrow,
        )
    else:
        if args.src is None or args.tgt is None:
            parser.error(f"--from and --to are required in {args.mode} mode")
        src_x, src_y = map(float, args.src.split(","))
        tgt_x, tgt_y = map(float, args.tgt.split(","))
        if args.mode == "l":
            result = calc_l(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                first_axis=args.first_axis,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
            )
        else:  # l-chamfer
            result = calc_l_chamfer(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                first_axis=args.first_axis,
                chamfer=args.chamfer,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
            )

    print_polyline_result(result, args)


def _parse_waypoints(text):
    """Parse '"x1,y1 x2,y2 ..."' into a list of (x, y) tuples."""
    out = []
    for token in text.replace(",", " ").split():
        out.append(float(token))
    if len(out) < 4 or len(out) % 2 != 0:
        raise ValueError(f"--waypoints must contain >= 2 pairs of numbers, got {len(out)} numbers")
    return [(out[i], out[i + 1]) for i in range(0, len(out), 2)]


def print_polyline_result(result, args):
    """Print diagnostic output for L / L-chamfer / spline connectors."""
    print(f"=== {result['mode'].upper()} CONNECTOR ===")
    print(f"Samples:          {len(result['samples'])}")
    print(f"Total length:     {result['total_length']:.1f}px")
    print("")
    for end_name in ("start", "end"):
        end = result[end_name]
        tip = end["tip"]
        print(f"--- {end_name.upper()} ---")
        print(f"Tip:              ({tip[0]:.1f}, {tip[1]:.1f})")
        print(f"Tangent:          ({end['tangent'][0]:.3f}, {end['tangent'][1]:.3f})")
        print(f"Angle:            {end['angle_deg']:.1f} degrees")
        if end["arrow"]:
            arr = end["arrow"]
            poly = arr["polygon"]
            poly_str = " ".join(f"({p[0]:.1f},{p[1]:.1f})" for p in poly)
            print(f"Arrow polygon:    {poly_str}")
            print(f"Stem-back point:  ({arr['stem_back'][0]:.1f}, {arr['stem_back'][1]:.1f})")
            print(f"Transform:        {arr['transform']}")
        else:
            print("Arrow:            (none)")
        print("")

    print("=== PATH (full) ===")
    print(result["path_d"])
    print("")
    print("=== PATH (trimmed for arrowhead clearance) ===")
    print(result["trimmed_path_d"])
    print("")
    print("--- SVG Snippet ---")
    print()
    print(format_polyline_svg(result, args.color, args.width, args.opacity))


def print_result(c, args):
    print("=== CONNECTOR ===")
    print(f"Source:           ({c['stem_start_world'][0]:.1f}, {c['stem_start_world'][1]:.1f})")
    print(f"Target (tip):     ({c['tip_x']:.1f}, {c['tip_y']:.1f})")
    print(f"Angle:            {c['angle_deg']:.1f} degrees")
    print(f"Full length:      {c['full_length']:.1f}px")
    print(f"Effective length: {c['effective_length']:.1f}px")
    print("")
    print("=== TRANSFORM ===")
    print(f"translate({c['tip_x']:.1f}, {c['tip_y']:.1f}) rotate({c['angle_deg']:.1f})")
    print("")
    print("=== LOCAL COORDINATES (flat, pre-rotation) ===")
    print(f"Stem:     x1={c['stem_start_local']:.0f}  x2={c['stem_end_local']:.0f}  y=0")
    print(
        f'Head:     points="0,0 -{c["head_len"]},{-c["head_half_h"]:.0f} -{c["head_len"]},{c["head_half_h"]:.0f}"'
    )
    print("")
    print("=== WORLD COORDINATES (after rotation, for verification) ===")
    print(f"Stem start: ({c['stem_start_world'][0]:.1f}, {c['stem_start_world'][1]:.1f})")
    print(f"Stem end:   ({c['stem_end_world'][0]:.1f}, {c['stem_end_world'][1]:.1f})")
    print(f"Tip:        ({c['tip_x']:.1f}, {c['tip_y']:.1f})")
    print("")
    print("--- SVG Snippet ---\n")
    print(format_svg(c, args.color, args.width, args.opacity))


if __name__ == "__main__":
    main()
