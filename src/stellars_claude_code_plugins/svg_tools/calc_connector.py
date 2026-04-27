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

# Absolute import (not relative) so the module can be invoked both as
# ``python -m stellars_claude_code_plugins.svg_tools.calc_connector`` and as
# a bare script path - tests exercise both forms.
from stellars_claude_code_plugins.svg_tools._warning_gate import (
    add_ack_warning_arg,
    compute_warning_token,  # noqa: F401 - re-exported for back-compat
    enforce_warning_acks,
    parse_ack_warning_args,  # noqa: F401 - re-exported for back-compat
)


def _polygon_centroid(points):
    """Area-weighted centroid of a simple closed polygon."""
    n = len(points)
    if n < 2:
        raise ValueError("polygon needs >= 2 vertices")
    if n == 2:
        return ((points[0][0] + points[1][0]) / 2, (points[0][1] + points[1][1]) / 2)
    area_accum = 0.0
    cx_accum = 0.0
    cy_accum = 0.0
    for i in range(n):
        px, py = points[i]
        qx, qy = points[(i + 1) % n]
        cross = px * qy - qx * py
        area_accum += cross
        cx_accum += (px + qx) * cross
        cy_accum += (py + qy) * cross
    area = area_accum / 2
    if abs(area) < 1e-9:
        mx = sum(p[0] for p in points) / n
        my = sum(p[1] for p in points) / n
        return (mx, my)
    return (cx_accum / (6 * area), cy_accum / (6 * area))


def _polygon_edge_intersection(cx, cy, tx, ty, polygon):
    """Intersection of the ray (cx, cy) -> (tx, ty) with a closed polygon.

    Walks every polygon edge and finds the smallest positive parameter t
    along the ray where (cx + t*dx, cy + t*dy) lies on an edge. Returns the
    intersection point. Used to compute edge incident points for connectors
    pointing at non-rect closed shapes.
    """
    dx = tx - cx
    dy = ty - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    n = len(polygon)
    best_t = None
    best_pt = None
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        # Solve (cx + t*dx, cy + t*dy) = (x1 + s*(x2-x1), y1 + s*(y2-y1))
        ex = x2 - x1
        ey = y2 - y1
        denom = dx * (-ey) - dy * (-ex)
        if abs(denom) < 1e-12:
            continue  # parallel
        s = (dx * (cy - y1) - dy * (cx - x1)) / denom
        t = (ex * (cy - y1) - ey * (cx - x1)) / denom
        if 0 <= s <= 1 and t > 1e-9:
            if best_t is None or t < best_t:
                best_t = t
                best_pt = (cx + t * dx, cy + t * dy)
    return best_pt if best_pt is not None else (cx, cy)


def _rect_edge_intersection(cx, cy, tx, ty, rect):
    """Given a rect (x, y, w, h) and a point (tx, ty) outside it, return the
    point on the rect's perimeter where the line from the rect's centre
    (cx, cy) toward (tx, ty) exits. Used to auto-compute edge incident
    points when a caller passes a shape's bounding rect and a target.
    """
    rx, ry, rw, rh = rect
    dx = tx - cx
    dy = ty - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    # Parameterise the line from centre outward: (cx + t*dx, cy + t*dy).
    # Find the smallest t > 0 where the line meets one of the four edges.
    half_w = rw / 2
    half_h = rh / 2
    candidates = []
    if dx != 0:
        t_right = half_w / dx if dx > 0 else -half_w / dx
        t_left = -half_w / dx if dx < 0 else half_w / dx
        candidates.extend([t_right, t_left])
    if dy != 0:
        t_bottom = half_h / dy if dy > 0 else -half_h / dy
        t_top = -half_h / dy if dy < 0 else half_h / dy
        candidates.extend([t_top, t_bottom])
    t = min(t for t in candidates if t > 0)
    return (cx + t * dx, cy + t * dy)


def calc_connector(
    src_x=None,
    src_y=None,
    tgt_x=None,
    tgt_y=None,
    margin=0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    start_dir=None,
    end_dir=None,
    src_rect=None,
    tgt_rect=None,
    src_polygon=None,
    tgt_polygon=None,
):
    """Straight-line connector. Unified polyline output.

    REMINDER: connectors typically terminate at the MIDPOINT of a shape's edge
    (use `geom attach --side right|left|top|bottom --pos mid`). When the
    caller passes a whole shape (src_rect/tgt_rect for axis-aligned rects, or
    src_polygon/tgt_polygon for arbitrary closed polygons) the tool computes
    the centre-to-centre line and intersects it with the shape's perimeter -
    giving the correct edge incident point automatically.
    """
    # Resolve source and target centres from explicit coords OR shape geometry.
    # Rects are axis-aligned (x, y, w, h); polygons are closed vertex lists.
    if src_polygon is not None:
        sx_c, sy_c = _polygon_centroid(src_polygon)
    elif src_rect is not None:
        sx_c = src_rect[0] + src_rect[2] / 2
        sy_c = src_rect[1] + src_rect[3] / 2
    else:
        sx_c = sy_c = None
    if tgt_polygon is not None:
        tx_c, ty_c = _polygon_centroid(tgt_polygon)
    elif tgt_rect is not None:
        tx_c = tgt_rect[0] + tgt_rect[2] / 2
        ty_c = tgt_rect[1] + tgt_rect[3] / 2
    else:
        tx_c = ty_c = None

    # Default each endpoint to the shape centre if no explicit coord was passed
    if src_x is None or src_y is None:
        if sx_c is None:
            raise ValueError("src_x/src_y required unless src_rect or src_polygon is given")
        src_x = sx_c if src_x is None else src_x
        src_y = sy_c if src_y is None else src_y
    if tgt_x is None or tgt_y is None:
        if tx_c is None:
            raise ValueError("tgt_x/tgt_y required unless tgt_rect or tgt_polygon is given")
        tgt_x = tx_c if tgt_x is None else tgt_x
        tgt_y = ty_c if tgt_y is None else tgt_y

    # Auto-edge: intersect the centre-to-target ray with the shape perimeter
    # to compute the true edge incident point. Polygons and rects each use
    # their own intersection routine.
    if src_polygon is not None:
        src_x, src_y = _polygon_edge_intersection(sx_c, sy_c, tgt_x, tgt_y, src_polygon)
    elif src_rect is not None:
        src_x, src_y = _rect_edge_intersection(sx_c, sy_c, tgt_x, tgt_y, src_rect)
    if tgt_polygon is not None:
        tgt_x, tgt_y = _polygon_edge_intersection(tx_c, ty_c, src_x, src_y, tgt_polygon)
    elif tgt_rect is not None:
        tgt_x, tgt_y = _rect_edge_intersection(tx_c, ty_c, src_x, src_y, tgt_rect)

    return _build_polyline_result(
        "straight",
        [(src_x, src_y), (tgt_x, tgt_y)],
        head_len,
        head_half_h,
        arrow,
        margin,
        standoff=standoff,
    )


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

    # Segment 1: source -> pill entry (no arrowhead)
    seg1 = calc_connector(
        src_x,
        src_y,
        enter_x,
        enter_y,
        margin=margin,
        head_len=head_len,
        head_half_h=head_half_h,
        arrow="none",
    )

    # Segment 2: pill exit -> target (arrowhead on end)
    seg2 = calc_connector(
        exit_x,
        exit_y,
        tgt_x,
        tgt_y,
        margin=margin,
        head_len=head_len,
        head_half_h=head_half_h,
        arrow="end",
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


# ---------------------------------------------------------------------------
# Compass-direction annotations on connector endpoints
# ---------------------------------------------------------------------------

# 16 compass directions. In SVG coordinates y increases downward, so:
#   North = (0, -1)  (up)
#   South = (0, +1)  (down)
#   East  = (+1, 0)  (right)
#   West  = (-1, 0)  (left)
# Compound directions are unit vectors at the appropriate angle.
# Angle 0 is north, increasing clockwise (like a real compass).
_COMPASS_ANGLES = {
    "N": 0,
    "NNE": 22.5,
    "NE": 45,
    "ENE": 67.5,
    "E": 90,
    "ESE": 112.5,
    "SE": 135,
    "SSE": 157.5,
    "S": 180,
    "SSW": 202.5,
    "SW": 225,
    "WSW": 247.5,
    "W": 270,
    "WNW": 292.5,
    "NW": 315,
    "NNW": 337.5,
}


def _direction_to_unit_vector(direction):
    """Convert a direction spec to a unit vector (dx, dy) in SVG coordinates.

    Accepts:
      - None -> returns None (no direction constraint)
      - compass string ("N", "NNE", "NE", ...) case-insensitive
      - numeric angle in degrees measured clockwise from north
        (0=N, 90=E, 180=S, 270=W)

    Returns (dx, dy) unit vector or None.
    """
    if direction is None:
        return None
    if isinstance(direction, str):
        key = direction.strip().upper()
        if key not in _COMPASS_ANGLES:
            raise ValueError(
                f"unknown compass direction {direction!r}; "
                f"use one of {sorted(_COMPASS_ANGLES)} or a numeric angle"
            )
        angle_deg = _COMPASS_ANGLES[key]
    elif isinstance(direction, (int, float)):
        angle_deg = float(direction) % 360
    else:
        raise ValueError(f"direction must be a compass string or numeric angle, got {direction!r}")
    angle_rad = math.radians(angle_deg)
    # Angle 0 = north = (0, -1); clockwise: E=(1,0), S=(0,1), W=(-1,0)
    dx = math.sin(angle_rad)
    dy = -math.cos(angle_rad)
    return (dx, dy)


def _unpack_point_with_direction(point):
    """Split a 2-tuple, 3-tuple, or dict into ((x, y), direction).

    Accepts:
      - (x, y)                 -> ((x, y), None)
      - (x, y, "N")            -> ((x, y), "N")
      - (x, y, 45.0)           -> ((x, y), 45.0)
      - {"xy": (x, y), "dir": "NE"}  -> ((x, y), "NE")
    """
    if isinstance(point, dict):
        xy = point["xy"]
        direction = point.get("dir")
        return (float(xy[0]), float(xy[1])), direction
    if len(point) == 2:
        return (float(point[0]), float(point[1])), None
    if len(point) == 3:
        return (float(point[0]), float(point[1])), point[2]
    raise ValueError(f"point must be (x, y) or (x, y, direction), got {point!r}")


def _apply_direction_to_l(src, tgt, direction_in, direction_out):
    """Infer first_axis from the start direction.

    N/S -> v (vertical first), E/W -> h (horizontal first), diagonal -> dominant.
    When no direction is given, fall back to the default inference from geometry.
    """
    unit = _direction_to_unit_vector(direction_in)
    if unit is None:
        return _infer_first_axis(src[0], src[1], tgt[0], tgt[1])
    if abs(unit[0]) >= abs(unit[1]):
        return "h"
    return "v"


def _apply_direction_to_spline(src, tgt, direction_in, direction_out, offset=24.0):
    """Inject implicit PCHIP control points at offsets along the given directions.

    Returns a new waypoint list: [src, injected_in?, injected_out?, tgt]. The
    injected points are a fixed distance along the direction unit vector,
    forcing the curve to leave (or enter) the endpoint tangent to the
    specified direction.
    """
    pts = [src]
    uin = _direction_to_unit_vector(direction_in)
    uout = _direction_to_unit_vector(direction_out)
    if uin is not None:
        pts.append((src[0] + uin[0] * offset, src[1] + uin[1] * offset))
    if uout is not None:
        pts.append((tgt[0] - uout[0] * offset, tgt[1] - uout[1] * offset))
    pts.append(tgt)
    return pts


def _infer_first_axis(src_x, src_y, tgt_x, tgt_y):
    """Pick 'h' or 'v' for an L segment based on which delta is larger.

    If the horizontal distance dominates, the route goes horizontal first
    (the long side comes first) and turns vertical near the target.
    """
    return "h" if abs(tgt_x - src_x) >= abs(tgt_y - src_y) else "v"


# Direction -> 4-edge mapping for rect edge-midpoints. Key = compass letter,
# value = edge name ("right"/"left"/"top"/"bottom"). Anything outside the
# cardinal set (NE, NNE, 45, ...) is rejected by the L resolver because an
# L-route can only leave/enter a rect on one of four axis-aligned edges.
_CARDINAL_EDGE = {"E": "right", "W": "left", "N": "top", "S": "bottom"}


def _rect_edge_midpoint(rect, edge):
    """Return the midpoint of the named edge of an axis-aligned rect.

    rect is (x, y, w, h), edge is "right"/"left"/"top"/"bottom".
    """
    rx, ry, rw, rh = rect
    if edge == "right":
        return (rx + rw, ry + rh / 2)
    if edge == "left":
        return (rx, ry + rh / 2)
    if edge == "top":
        return (rx + rw / 2, ry)
    if edge == "bottom":
        return (rx + rw / 2, ry + rh)
    raise ValueError(f"unknown edge {edge!r}")


def _rect_edge_slide_range(rect, edge):
    """Return the sliding range for an axis-aligned rect edge as (axis, lo, hi).

    For horizontal edges (left / right) the sliding axis is 'y' and the
    range is [rect.top, rect.bottom] - the y coordinate can move anywhere
    along that edge. For vertical edges (top / bottom) the sliding axis
    is 'x' with range [rect.left, rect.right]. Used by the straight-line
    collapse heuristic to decide whether src and tgt can be slid to a
    shared coordinate.
    """
    rx, ry, rw, rh = rect
    if edge in ("right", "left"):
        return ("y", ry, ry + rh)
    if edge in ("top", "bottom"):
        return ("x", rx, rx + rw)
    raise ValueError(f"unknown edge {edge!r}")


def _rect_edge_point_at(rect, edge, coord):
    """Return a point on the named rect edge with the sliding axis set
    to ``coord``. Complements _rect_edge_midpoint for the straight-line
    slide resolver.
    """
    rx, ry, rw, rh = rect
    if edge == "right":
        return (rx + rw, coord)
    if edge == "left":
        return (rx, coord)
    if edge == "top":
        return (coord, ry)
    if edge == "bottom":
        return (coord, ry + rh)
    raise ValueError(f"unknown edge {edge!r}")


def _direction_to_cardinal(direction):
    """Coerce a direction spec to one of 'E'/'W'/'N'/'S' (or None).

    Accepts compass strings (cardinal only for L) and numeric angles
    (snapped to nearest cardinal). Non-cardinal compass keys (NNE, NE,
    ENE, ...) and off-axis angles return None so the caller can fall
    back to the geometry inference with a warning.
    """
    if direction is None:
        return None
    if isinstance(direction, str):
        key = direction.strip().upper()
        if key in _CARDINAL_EDGE:
            return key
        return None
    if isinstance(direction, (int, float)):
        angle = float(direction) % 360
        # Snap to nearest cardinal if within 1 degree, else reject.
        for deg, card in ((0, "N"), (90, "E"), (180, "S"), (270, "W"), (360, "N")):
            if abs(angle - deg) <= 1.0:
                return card
        return None
    return None


def _resolve_l_endpoints_from_rects(
    src_rect,
    tgt_rect,
    src_x,
    src_y,
    tgt_x,
    tgt_y,
    start_dir,
    end_dir,
    warnings,
    straight_tolerance=20.0,
):
    """Edge-aware endpoint + first-axis resolution for L / L-chamfer routes.

    When a rect is supplied WITH a cardinal direction, the connector's
    exit / entry point snaps to the midpoint of the matching edge and the
    first-axis is locked to that direction's axis. Missing directions fall
    back to geometric inference and append a warning to ``warnings``.

    Cardinal semantics:
      - ``start_dir`` is the direction the connector LEAVES the src
        (E/W => horizontal exit, N/S => vertical exit).
      - ``end_dir`` is the direction the connector is still MOVING when it
        arrives at the tgt. S means "moving south into tgt" which means
        it enters from the TOP edge; E means "moving east into tgt" so it
        enters from the LEFT edge; and so on (inverse mapping).

    Straight-line collapse (``straight_tolerance`` px): when both
    endpoints expose a sliding axis along the SAME cardinal, and their
    natural midpoints differ by less than the tolerance, both endpoints
    are slid along their edges to a shared coordinate so the route
    degenerates to a single straight line. This avoids the "twisted
    start" artefact where a tiny first leg + chamfer + standoff leaves
    the connector exiting through a diagonal bevel. Raw point endpoints
    count as "not movable"; when the rect endpoint can hit the raw
    point's coordinate within the tolerance and the rect's edge extent,
    the rect side slides.

    Returns (src_x, src_y, tgt_x, tgt_y, first_axis). ``first_axis`` is
    ``None`` when no direction was given (caller uses geometric inference).
    """
    # Entry-edge inverse map: end_dir tells the direction of travel at
    # tgt, so the entry edge is opposite to that direction.
    entry_edge = {"E": "left", "W": "right", "N": "bottom", "S": "top"}
    exit_edge = {"E": "right", "W": "left", "N": "top", "S": "bottom"}

    start_card = _direction_to_cardinal(start_dir)
    end_card = _direction_to_cardinal(end_dir)

    resolved_src = (src_x, src_y)
    resolved_tgt = (tgt_x, tgt_y)

    # Pass 1: resolve each endpoint to its natural position (rect edge
    # midpoint when the direction is cardinal, geometry inference
    # otherwise, raw coord if no rect).
    if src_rect is not None:
        if start_card is not None:
            resolved_src = _rect_edge_midpoint(src_rect, exit_edge[start_card])
        else:
            warnings.append(
                "L route: src_rect supplied without cardinal start_dir; "
                "endpoint inferred from centre-to-target ray — route may "
                "run parallel to an edge. Pass --start_dir E|W|N|S to snap."
            )
            sx_c = src_rect[0] + src_rect[2] / 2
            sy_c = src_rect[1] + src_rect[3] / 2
            resolved_src = _rect_edge_intersection(
                sx_c, sy_c, resolved_tgt[0], resolved_tgt[1], src_rect
            )

    if tgt_rect is not None:
        if end_card is not None:
            resolved_tgt = _rect_edge_midpoint(tgt_rect, entry_edge[end_card])
        else:
            warnings.append(
                "L route: tgt_rect supplied without cardinal end_dir; "
                "endpoint inferred from centre-to-source ray — route may "
                "run parallel to an edge. Pass --end_dir E|W|N|S to snap."
            )
            tx_c = tgt_rect[0] + tgt_rect[2] / 2
            ty_c = tgt_rect[1] + tgt_rect[3] / 2
            resolved_tgt = _rect_edge_intersection(
                tx_c, ty_c, resolved_src[0], resolved_src[1], tgt_rect
            )

    # Pass 2: straight-line collapse. Try to slide both endpoints along
    # their edges so the route degenerates to a single cardinal segment
    # with no corner. Requires:
    #   - both directions are cardinal and on the SAME axis (both E/W
    #     or both N/S), OR one endpoint is a raw point whose coordinate
    #     projects onto the rect's movable edge
    #   - the natural midpoint difference is <= straight_tolerance
    #   - the rect's edge extent contains the slide target
    if straight_tolerance is not None and straight_tolerance > 0:
        src_slide = None  # (axis, lo, hi) if src side can slide
        tgt_slide = None
        if src_rect is not None and start_card is not None:
            src_slide = _rect_edge_slide_range(src_rect, exit_edge[start_card])
        if tgt_rect is not None and end_card is not None:
            tgt_slide = _rect_edge_slide_range(tgt_rect, entry_edge[end_card])

        # Case A: BOTH endpoints are movable on the same axis.
        if src_slide is not None and tgt_slide is not None and src_slide[0] == tgt_slide[0]:
            axis = src_slide[0]
            idx = 1 if axis == "y" else 0
            diff = abs(resolved_src[idx] - resolved_tgt[idx])
            if diff <= straight_tolerance:
                lo = max(src_slide[1], tgt_slide[1])
                hi = min(src_slide[2], tgt_slide[2])
                if lo <= hi:
                    # Bias the shared target toward the smaller range's
                    # midpoint (clamped to the intersection) so the
                    # smaller-geometry endpoint slides as little as
                    # possible - shifting an anchor on a larger edge is
                    # visually less noticeable than shifting it on a
                    # small one.
                    src_width = src_slide[2] - src_slide[1]
                    tgt_width = tgt_slide[2] - tgt_slide[1]
                    if src_width <= tgt_width:
                        preferred = (src_slide[1] + src_slide[2]) / 2.0
                    else:
                        preferred = (tgt_slide[1] + tgt_slide[2]) / 2.0
                    target = max(lo, min(hi, preferred))
                    resolved_src = _rect_edge_point_at(src_rect, exit_edge[start_card], target)
                    resolved_tgt = _rect_edge_point_at(tgt_rect, entry_edge[end_card], target)

        # Case B: only src is movable, tgt is a raw point. Snap src's
        # slide coord to the tgt raw coord when it lands inside the
        # src edge extent AND the natural difference is within tolerance.
        elif src_slide is not None and tgt_rect is None:
            axis, lo, hi = src_slide
            idx = 1 if axis == "y" else 0
            natural_src = resolved_src[idx]
            raw_tgt = resolved_tgt[idx]
            if abs(natural_src - raw_tgt) <= straight_tolerance and lo <= raw_tgt <= hi:
                resolved_src = _rect_edge_point_at(src_rect, exit_edge[start_card], raw_tgt)

        # Case C: only tgt is movable, src is a raw point.
        elif tgt_slide is not None and src_rect is None:
            axis, lo, hi = tgt_slide
            idx = 1 if axis == "y" else 0
            natural_tgt = resolved_tgt[idx]
            raw_src = resolved_src[idx]
            if abs(natural_tgt - raw_src) <= straight_tolerance and lo <= raw_src <= hi:
                resolved_tgt = _rect_edge_point_at(tgt_rect, entry_edge[end_card], raw_src)

    # First-axis from direction: E/W => horizontal first, N/S => vertical.
    # Only locked when START direction is known; otherwise left None so
    # the downstream builder falls back to geometric inference.
    first_axis = None
    if start_card is not None:
        first_axis = "h" if start_card in ("E", "W") else "v"

    return resolved_src[0], resolved_src[1], resolved_tgt[0], resolved_tgt[1], first_axis


def _build_l_polyline(src_x, src_y, tgt_x, tgt_y, first_axis=None):
    """Two-segment L route. first_axis='h' goes horizontal first, 'v' vertical.

    When first_axis is None, it is inferred per segment from geometry
    (dominant axis first). Collinear pairs degenerate to a two-point polyline.
    """
    if src_x == tgt_x or src_y == tgt_y:
        return [(src_x, src_y), (tgt_x, tgt_y)]
    if first_axis is None:
        first_axis = _infer_first_axis(src_x, src_y, tgt_x, tgt_y)
    if first_axis == "h":
        corner = (tgt_x, src_y)
    elif first_axis == "v":
        corner = (src_x, tgt_y)
    else:
        raise ValueError(f"first_axis must be 'h' or 'v' or None, got {first_axis!r}")
    return [(src_x, src_y), corner, (tgt_x, tgt_y)]


def _build_l_chamfer_polyline(src_x, src_y, tgt_x, tgt_y, first_axis=None, chamfer=4.0):
    """Chamfered L: replace the 90 corner with a small diagonal cut.

    When first_axis is None, it is inferred per segment from geometry
    (dominant axis first). Collinear pairs (Δx=0 or Δy=0) fall back to a
    straight two-point polyline with no corner to chamfer.
    """
    dx = tgt_x - src_x
    dy = tgt_y - src_y
    if dx == 0 or dy == 0:
        return [(src_x, src_y), (tgt_x, tgt_y)]

    if first_axis is None:
        first_axis = _infer_first_axis(src_x, src_y, tgt_x, tgt_y)

    sign_x = 1 if dx >= 0 else -1
    sign_y = 1 if dy >= 0 else -1
    if first_axis == "h":
        before = (tgt_x - chamfer * sign_x, src_y)
        after = (tgt_x, src_y + chamfer * sign_y)
    elif first_axis == "v":
        before = (src_x, tgt_y - chamfer * sign_y)
        after = (src_x + chamfer * sign_x, tgt_y)
    else:
        raise ValueError(f"first_axis must be 'h' or 'v' or None, got {first_axis!r}")
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


def _bbox_of(points, extras=()):
    """Axis-aligned bounding box over a list of points plus any extras.

    `extras` is an iterable of (x, y) pairs (e.g. arrowhead polygon vertices)
    that should be included in the bbox but are not part of the main polyline.
    Returns (x, y, w, h) or None for empty input.
    """
    xs = [p[0] for p in points] + [e[0] for e in extras]
    ys = [p[1] for p in points] + [e[1] for e in extras]
    if not xs:
        return None
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


DEFAULT_STANDOFF = 1.0  # default 1px gap between stroke and endpoint


def _zero_standoff_warning(standoff):
    """Return a warning string if ``standoff`` is zero on either end.

    Zero standoff makes the connector stroke touch the shape edge, which
    reads as a drawing glitch (the line blurs into the border). Project
    minimum is >= 2px. Caller can still ship zero-standoff on purpose by
    acking the warning via ``--ack-warning TOKEN=reason``.
    """
    if standoff is None:
        return None
    if isinstance(standoff, (int, float)):
        if float(standoff) == 0.0:
            return (
                "WARNING: --standoff 0 puts the connector stroke directly on "
                "the shape edge. Project minimum is >= 2px. Ack with a "
                "reason if flush endpoint is intentional."
            )
        return None
    try:
        a, b = standoff
    except (TypeError, ValueError):
        return None
    if float(a) == 0.0 and float(b) == 0.0:
        return (
            "WARNING: --standoff 0,0 puts both endpoints flush on shape "
            "edges. Project minimum is >= 2px each side. Ack if intentional."
        )
    if float(a) == 0.0:
        return (
            "WARNING: --standoff start-side is 0 (connector stroke on source "
            "edge). Project minimum is >= 2px. Ack if intentional."
        )
    if float(b) == 0.0:
        return (
            "WARNING: --standoff end-side is 0 (connector stroke on target "
            "edge). Project minimum is >= 2px. Ack if intentional."
        )
    return None


def _resolve_standoff(standoff, margin):
    """Return (start_trim, end_trim) from the standoff/margin inputs.

    standoff takes precedence:
      - scalar -> (standoff, standoff)
      - 2-tuple (a, b) -> (a, b)
      - None  -> uses margin if >0, else the module-level DEFAULT_STANDOFF
        so every connector leaves a tiny 1px gap to its endpoints by default
    """
    if standoff is None:
        if margin and margin > 0:
            return (float(margin), float(margin))
        return (DEFAULT_STANDOFF, DEFAULT_STANDOFF)
    if isinstance(standoff, (int, float)):
        return (float(standoff), float(standoff))
    if isinstance(standoff, (tuple, list)) and len(standoff) == 2:
        return (float(standoff[0]), float(standoff[1]))
    raise ValueError(f"standoff must be a number or 2-tuple (start, end), got {standoff!r}")


def _build_polyline_result(
    mode,
    points,
    head_len,
    head_half_h,
    arrow,
    margin=0.0,
    controls=None,
    warnings=None,
    standoff=None,
):
    """Common assembly: trims standoff from each end, builds endpoint info, packs result.

    Every polyline result carries:
      - mode, shape-independent samples / path_d / trimmed_path_d
      - total_length
      - start / end endpoint info (tip, tangent, angle, arrowhead polygon if any)
      - bbox  : axis-aligned (x, y, w, h) over samples + arrowhead polygons
      - warnings : list of non-fatal messages collected during construction
      - controls : echoed back (empty list if none supplied)
      - standoff : (start_trim, end_trim) applied during construction

    `standoff` is a scalar or 2-tuple. When set it overrides `margin`, letting
    callers specify independent start and end trims. Scalar standoff is the
    same as the legacy scalar margin.
    """
    warnings = list(warnings) if warnings else []

    start_trim, end_trim = _resolve_standoff(standoff, margin)
    if end_trim > 0:
        points = _trim_polyline(points, end_trim, "end")
    if start_trim > 0:
        points = _trim_polyline(points, start_trim, "start")

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

    # bbox includes arrowhead polygon vertices so callers can measure the full
    # visible footprint of the connector (useful for collision and layout checks).
    extras = []
    if start_info["arrow"] is not None:
        extras.extend(start_info["arrow"]["polygon"])
    if end_info["arrow"] is not None:
        extras.extend(end_info["arrow"]["polygon"])
    bbox = _bbox_of(points, extras=extras)

    total_length = _polyline_length(points)

    # Minimum-strand warning - a strand that is shorter than the arrowhead clearance
    # is likely a degenerate endpoint pair. Always reported, non-fatal.
    min_required = head_len + 2
    if arrow != "none" and total_length < min_required:
        msg = (
            f"{mode} connector is only {total_length:.1f}px - shorter than "
            f"arrowhead clearance ({min_required:.1f}px). Endpoints may be too close."
        )
        warnings.append(msg)
        print(f"WARNING: {msg}", file=sys.stderr)

    return {
        "mode": mode,
        "samples": list(points),
        "path_d": _polyline_to_path_d(points),
        "trimmed_path_d": _polyline_to_path_d(trimmed),
        "total_length": total_length,
        "start": start_info,
        "end": end_info,
        "bbox": bbox,
        "controls": list(controls) if controls else [],
        "standoff": (start_trim, end_trim),
        "warnings": warnings,
    }


CONTROL_SOFT_CAP = 5


def _check_soft_cap(controls, label):
    """Non-fatal warning if controls exceed the soft cap. Always printed to stderr."""
    if controls and len(controls) > CONTROL_SOFT_CAP:
        msg = (
            f"{label}: {len(controls)} control points exceed soft cap of {CONTROL_SOFT_CAP}. "
            f"Consider splitting into multiple strands."
        )
        print(f"WARNING: {msg}", file=sys.stderr)
        return [msg]
    return []


def _thread_l_controls(
    src,
    dst,
    controls,
    chamfer=None,
    start_dir=None,
    end_dir=None,
    first_reserve=0.0,
    last_reserve=0.0,
):
    """Build a single orthogonal polyline through [src, *controls, dst] and
    optionally chamfer every 90 degree corner in a global pass.

    The old implementation glued a separate 1-bend L per segment and then
    concatenated them. That produced three artefacts on multi-elbow routes:
    only the first elbow of each L was chamfered (inter-segment joins stayed
    sharp); start_dir / end_dir were ignored because each segment re-inferred
    its own first_axis; and the chamfer bevel could overshoot when the
    segment's dominant delta was smaller than the chamfer radius.

    This version builds ONE continuous sharp polyline first - locking the
    first segment's first_axis from start_dir and the last segment's from
    end_dir - then runs a single chamfer pass that bevels every 90 degree
    vertex. The bevel is clamped per corner to half the shorter adjacent
    segment so two adjacent bevels never overlap and near-colinear segments
    degrade gracefully to sharp corners.

    Parameters
    ----------
    src, dst : tuple[float, float]
        Endpoints (world coordinates).
    controls : list[tuple[float, float]] | None
        Interior waypoints the polyline must pass through in order.
    chamfer : float | None
        Bevel radius in world units. None or <= 0 leaves corners sharp.
    start_dir : str | None
        Cardinal 'E' / 'W' / 'N' / 'S' locking the first segment's exit
        axis (E/W -> horizontal exit, N/S -> vertical exit).
    end_dir : str | None
        Cardinal direction of motion INTO the target. N/S means the last
        leg is vertical (so the elbow before it is horizontal); E/W means
        the last leg is horizontal.
    first_reserve : float
        Minimum axial length that must survive on the first segment after
        chamfering. Used by the caller to reserve room for standoff +
        arrowhead clearance so the start-arrow's tangent stays aligned
        with the first cardinal leg instead of eating into a bevel.
    last_reserve : float
        Same reservation for the last segment. Without this, a short last
        leg combined with a large chamfer leaves the end-arrow's trim
        walking into the bevel and the arrow tangent diverges from the
        last-leg cardinal direction.
    """
    anchors = [src, *(controls or []), dst]
    n_segments = len(anchors) - 1

    start_card = _direction_to_cardinal(start_dir)
    end_card = _direction_to_cardinal(end_dir)

    # Step 1: build a sharp orthogonal polyline by inserting at most one
    # corner per inter-anchor segment. A segment that already shares an
    # axis (dx=0 or dy=0) collapses to a straight line with no corner.
    pts: list = [anchors[0]]
    for i in range(n_segments):
        ax, ay = anchors[i]
        bx, by = anchors[i + 1]
        if ax == bx or ay == by:
            pts.append((bx, by))
            continue

        first_axis = None
        if i == 0 and start_card is not None:
            # start_dir locks the first leg's axis - E/W leave horizontal,
            # N/S leave vertical - so the route exits the src perpendicular
            # to its edge even when the first waypoint is near-colinear.
            first_axis = "h" if start_card in ("E", "W") else "v"
        if i == n_segments - 1 and end_card is not None:
            # end_dir describes the LAST leg's direction of motion. N/S
            # means the last leg is vertical, so the corner before it is
            # horizontal (first_axis='h'); mirror for E/W.
            first_axis = "h" if end_card in ("N", "S") else "v"
        if first_axis is None:
            first_axis = _infer_first_axis(ax, ay, bx, by)

        corner = (bx, ay) if first_axis == "h" else (ax, by)
        pts.append(corner)
        pts.append((bx, by))

    # Step 2: drop consecutive duplicates (happens when a corner coincides
    # with an anchor because one of the deltas was zero but the caller still
    # supplied a direction lock).
    dedup: list = [pts[0]]
    for p in pts[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    pts = dedup

    # Step 3: straighten runs of collinear vertices. Consecutive anchors
    # that share a direction (e.g. two auto-route waypoints on the same
    # horizontal line) should appear as one segment with no mid-vertex.
    def _sgn(v):
        return 0 if v == 0 else (1 if v > 0 else -1)

    if len(pts) >= 3:
        straight: list = [pts[0]]
        for i in range(1, len(pts) - 1):
            prev = straight[-1]
            cur = pts[i]
            nxt = pts[i + 1]
            d1 = (_sgn(cur[0] - prev[0]), _sgn(cur[1] - prev[1]))
            d2 = (_sgn(nxt[0] - cur[0]), _sgn(nxt[1] - cur[1]))
            if d1 == d2:
                continue
            straight.append(cur)
        straight.append(pts[-1])
        pts = straight

    if chamfer is None or chamfer <= 0 or len(pts) < 3:
        return pts

    # Step 4: global chamfer pass. Every interior vertex is a 90 degree
    # corner (guaranteed by Steps 1-3), so bevel each one with a radius
    # clamped to half the shorter adjacent segment length. The first and
    # last interior corners additionally reserve `first_reserve` /
    # `last_reserve` of axial length on the outer segment so the eventual
    # standoff + arrowhead clearance stays on the cardinal leg rather
    # than crossing into a diagonal bevel.
    last_corner_idx = len(pts) - 2
    chamfered: list = [pts[0]]
    for i in range(1, len(pts) - 1):
        prev = pts[i - 1]
        corner = pts[i]
        nxt = pts[i + 1]
        dx_in = corner[0] - prev[0]
        dy_in = corner[1] - prev[1]
        dx_out = nxt[0] - corner[0]
        dy_out = nxt[1] - corner[1]
        len_in = abs(dx_in) + abs(dy_in)  # one of the deltas is 0
        len_out = abs(dx_out) + abs(dy_out)
        eff = min(float(chamfer), len_in / 2.0, len_out / 2.0)
        if i == 1 and first_reserve > 0:
            # Reserve first_reserve on the incoming (first) axial segment.
            eff = min(eff, max(0.0, len_in - float(first_reserve)))
        if i == last_corner_idx and last_reserve > 0:
            # Reserve last_reserve on the outgoing (last) axial segment.
            eff = min(eff, max(0.0, len_out - float(last_reserve)))
        if eff <= 0.5:
            chamfered.append(corner)
            continue
        # Axis-aligned unit vectors (one component is zero by construction).
        uin = (_sgn(dx_in), _sgn(dy_in))
        uout = (_sgn(dx_out), _sgn(dy_out))
        before = (corner[0] - uin[0] * eff, corner[1] - uin[1] * eff)
        after = (corner[0] + uout[0] * eff, corner[1] + uout[1] * eff)
        chamfered.append(before)
        chamfered.append(after)
    chamfered.append(pts[-1])

    return chamfered


def _auto_route_l_waypoints(
    src,
    tgt,
    start_dir=None,
    end_dir=None,
    svg=None,
    container_id=None,
    cell_size=10,
    margin_px=5,
    first_stem_reserve=0.0,
    last_stem_reserve=0.0,
):
    """Grid A* router that returns intermediate elbow waypoints avoiding
    obstacles in the SVG. Returns a list of (x, y) tuples (may be empty if
    a single 1-bend L already clears obstacles) or None if no path is
    routable at the current cell size.

    Algorithm: rasterise every SVG element as an obstacle, erode by
    ``margin_px``, downsample to ``cell_size``-spaced cells via centre
    sampling, run 4-connected A* from src cell to tgt cell with Manhattan
    heuristic, reconstruct the path, drop collinear interior cells, and
    return the resulting elbow points (first and last are dropped - those
    are src / tgt themselves).

    ``first_stem_reserve`` / ``last_stem_reserve`` create "stem zones"
    near src and tgt where A* turns pay a heavy extra penalty. This
    discourages the router from placing its last corner close to tgt
    (or its first corner close to src) so the final and initial
    cardinal legs are long enough to accommodate standoff + arrowhead
    clearance + a visible stem. The reserves are in world pixels and
    converted to Manhattan cell distances internally.
    """
    if svg is None:
        return None

    import heapq

    import numpy as np
    from scipy import ndimage as ndi

    from .calc_empty_space import (
        _container_interior_surrogates,
        _element_to_surrogates,
        _is_canvas_background,
        _parse_svg_source,
        _rasterise_surrogates,
    )

    try:
        import svgelements as _se
    except ImportError:
        return None

    svg_doc, viewbox = _parse_svg_source(svg)
    cx, cy, cw, ch = viewbox

    container_elem = None
    if container_id is not None:
        container_elem = svg_doc.get_element_by_id(container_id)
        if container_elem is None:
            return None

    # Rasterise all obstacles. Skip the container itself if pinned, and
    # always skip full-canvas background plates - otherwise a single
    # bg-plate rect marks every pixel as an obstacle and the router
    # reports "unroutable".
    surrogates: list = []

    def walk(node):
        if node is not container_elem and not _is_canvas_background(node, viewbox):
            surrogates.extend(_element_to_surrogates(node))
        if isinstance(node, _se.Group):
            for child in node:
                walk(child)

    walk(svg_doc)

    obstacle_mask = _rasterise_surrogates(viewbox, surrogates)
    free_mask = ~obstacle_mask

    if container_elem is not None:
        interior = _container_interior_surrogates(container_elem)
        container_mask = _rasterise_surrogates(viewbox, interior)
        free_mask = free_mask & container_mask

    # Erode so the route stays a few pixels clear of obstacles
    if margin_px > 0:
        padded = np.zeros((free_mask.shape[0] + 2, free_mask.shape[1] + 2), dtype=bool)
        padded[1:-1, 1:-1] = free_mask
        dist = ndi.distance_transform_edt(padded)
        free_mask = dist[1:-1, 1:-1] > margin_px

    # Downsample: sample the centre pixel of every cell_size-wide cell
    step = max(1, int(cell_size))
    H, W = free_mask.shape
    gh = H // step
    gw = W // step
    if gh < 2 or gw < 2:
        return None
    half = step // 2
    grid = free_mask[half::step, half::step][:gh, :gw]

    def world_to_cell(x, y):
        gx = int((x - cx) // step)
        gy = int((y - cy) // step)
        return (max(0, min(gh - 1, gy)), max(0, min(gw - 1, gx)))

    def cell_to_world(r, c):
        return (cx + (c + 0.5) * step, cy + (r + 0.5) * step)

    src_cell = world_to_cell(*src)
    tgt_cell = world_to_cell(*tgt)
    if src_cell == tgt_cell:
        return []

    # Force a 1-cell halo around src / tgt to be free so A* can enter and
    # exit. Without this the erosion halo around the endpoint rects would
    # trap the router - a 5 px erosion typically blocks every cell directly
    # adjacent to a rect edge even though that cell is geometrically free.
    forced_free: set = set()
    for anchor in (src_cell, tgt_cell):
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                cell = (anchor[0] + dr, anchor[1] + dc)
                if 0 <= cell[0] < gh and 0 <= cell[1] < gw:
                    forced_free.add(cell)

    def is_free(cell):
        if cell in forced_free:
            return True
        return bool(grid[cell[0], cell[1]])

    # Directions: N, S, W, E as (dr, dc) deltas. The None sentinel is used
    # as the "incoming direction" at the src so the first step is not
    # penalised as a turn.
    _DIRS = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    # A* state = (cell, incoming_direction). Adding the incoming direction
    # lets us apply a turn penalty: moving in a different direction than
    # the last step costs extra, so long straight runs beat staircases.
    # ``TURN_PENALTY`` is measured in grid cells; 4 keeps the heuristic
    # admissible because Manhattan distance doesn't account for detours.
    TURN_PENALTY = 4

    # Stem zones: turning inside a Manhattan radius of ``stem_cells``
    # around src or tgt costs an extra ``STEM_TURN_PENALTY`` on top of
    # the normal turn penalty. This discourages A* from placing corners
    # near the endpoints, producing long cardinal legs that can absorb
    # standoff + arrowhead clearance + a visible stem. The penalty is
    # large enough to dominate normal path cost within the zone but not
    # so large that an obstacle-forced turn makes the whole path
    # unroutable - A* still finds SOMETHING, just more expensive.
    STEM_TURN_PENALTY = 100
    import math as _math

    # Convert world-unit reserves to Manhattan cell radii, then add ONE
    # cell of headroom. The extra cell covers two things:
    #   (a) the cell-to-world quantisation error - A* measures distance
    #       between cell CENTRES, but the threader measures distance to
    #       real_src / real_tgt which can be up to cell_size/2 off on
    #       each axis, so a "4 cell" A* reserve is only 35 world units
    #       when real_tgt is offset 5 px from its cell centre;
    #   (b) the chamfer bevel width - for the final bevel to render at
    #       its full radius, the last cardinal leg must be >= reserve +
    #       chamfer long.
    # One extra cell (= cell_size world units) is enough to cover both
    # in the common case (cell_size 10, chamfer <= 5). For larger
    # chamfers the caller can drop cell_size to 5 or 8 to gain precision.
    first_stem_cells = (
        int(_math.ceil(float(first_stem_reserve) / float(step))) + 1
        if first_stem_reserve and first_stem_reserve > 0
        else 0
    )
    last_stem_cells = (
        int(_math.ceil(float(last_stem_reserve) / float(step))) + 1
        if last_stem_reserve and last_stem_reserve > 0
        else 0
    )

    start_state = (src_cell, None)
    openq: list = [(heuristic(src_cell, tgt_cell), 0, start_state)]
    came_from: dict = {start_state: None}
    g_score: dict = {start_state: 0}
    counter = 0
    goal_state = None

    while openq:
        _, _, current = heapq.heappop(openq)
        cur_cell, cur_dir = current
        if cur_cell == tgt_cell:
            goal_state = current
            break
        for d in _DIRS:
            nr = cur_cell[0] + d[0]
            nc = cur_cell[1] + d[1]
            if not (0 <= nr < gh and 0 <= nc < gw):
                continue
            nb_cell = (nr, nc)
            if not is_free(nb_cell):
                continue
            step_cost = 1
            if cur_dir is not None and d != cur_dir:
                step_cost += TURN_PENALTY
                # Extra penalty for turns inside the stem zone - the
                # Manhattan distance is measured at the CURRENT cell
                # (where the turn originates) so the radius captures
                # every cell whose corner would eat into the stem.
                if last_stem_cells > 0:
                    tdist = abs(cur_cell[0] - tgt_cell[0]) + abs(cur_cell[1] - tgt_cell[1])
                    if tdist < last_stem_cells:
                        step_cost += STEM_TURN_PENALTY
                if first_stem_cells > 0:
                    sdist = abs(cur_cell[0] - src_cell[0]) + abs(cur_cell[1] - src_cell[1])
                    if sdist < first_stem_cells:
                        step_cost += STEM_TURN_PENALTY
            nb_state = (nb_cell, d)
            tentative = g_score[current] + step_cost
            if nb_state not in g_score or tentative < g_score[nb_state]:
                g_score[nb_state] = tentative
                came_from[nb_state] = current
                counter += 1
                heapq.heappush(
                    openq,
                    (tentative + heuristic(nb_cell, tgt_cell), counter, nb_state),
                )

    if goal_state is None:
        return None

    # Reconstruct cell path from tgt back to src (drop the direction tag)
    cells: list = []
    cur = goal_state
    while cur is not None:
        cells.append(cur[0])
        cur = came_from[cur]
    cells.reverse()

    # Drop collinear interior cells so only direction-change vertices remain
    corners: list = [cells[0]]
    for i in range(1, len(cells) - 1):
        p = cells[i - 1]
        c = cells[i]
        n = cells[i + 1]
        d1 = (c[0] - p[0], c[1] - p[1])
        d2 = (n[0] - c[0], n[1] - c[1])
        if d1 != d2:
            corners.append(c)
    corners.append(cells[-1])

    if len(corners) <= 2:
        # Path is a single run - no elbows needed beyond the 1-bend L.
        return []

    # Interior corners become the waypoints threaded through _thread_l_controls.
    waypoints = [cell_to_world(r, c) for r, c in corners[1:-1]]

    # Cell-center snap: the A* returns waypoints at cell centers which
    # do NOT exactly match real_src / real_tgt coordinates. When the
    # threader builds the final L-segment from the last waypoint to
    # real_tgt with end_dir cardinal, it INSERTS a corner at
    # ``(real_tgt.x, waypoint.y)`` for E/W or ``(waypoint.x, real_tgt.y)``
    # for N/S. That inserted corner is at a DIFFERENT world position
    # from the A* cell center, and its distance to real_tgt is typically
    # a few pixels shorter than A* thought - directly eating into the
    # stem reserve and squashing the last chamfer bevel.
    #
    # Fix: before returning, snap the last waypoint's non-cardinal axis
    # to real_tgt's cardinal coord so the threader does NOT insert an
    # extra corner. The waypoint becomes the last true corner, and A*'s
    # cell-distance calculation for the reserve matches the threader's
    # real-world len_out. Same symmetric snap for the first waypoint
    # against real_src under start_dir. This eliminates the coordinate
    # system mismatch between A* cells and threader world coords.
    start_card = _direction_to_cardinal(start_dir)
    end_card = _direction_to_cardinal(end_dir)
    if waypoints and start_card is not None:
        wx, wy = waypoints[0]
        if start_card in ("E", "W"):
            # First cardinal leg is horizontal; waypoint must share src.y
            waypoints[0] = (wx, float(src[1]))
        else:
            # First cardinal leg is vertical; waypoint must share src.x
            waypoints[0] = (float(src[0]), wy)
    if waypoints and end_card is not None:
        wx, wy = waypoints[-1]
        if end_card in ("E", "W"):
            # Last cardinal leg is horizontal; waypoint must share tgt.y
            waypoints[-1] = (wx, float(tgt[1]))
        else:
            # Last cardinal leg is vertical; waypoint must share tgt.x
            waypoints[-1] = (float(tgt[0]), wy)

    return waypoints


def calc_l(
    src_x=None,
    src_y=None,
    tgt_x=None,
    tgt_y=None,
    controls=None,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    start_dir=None,
    end_dir=None,
    src_rect=None,
    tgt_rect=None,
    auto_route=False,
    svg=None,
    container_id=None,
    route_cell_size=10,
    route_margin=5,
    straight_tolerance=20.0,
    stem_min=20.0,
):
    """Axis-aligned L connector, sharp corners.

    When ``src_rect`` / ``tgt_rect`` are supplied WITH cardinal ``start_dir`` /
    ``end_dir``, the tool snaps endpoints to the midpoint of the edge that
    matches the direction and locks the first-axis accordingly — no
    parallel-to-edge artefacts. Without directions the tool falls back to
    geometric inference and emits a warning.

    ``start_dir`` is the direction the connector LEAVES the source (E/W =>
    horizontal exit, N/S => vertical exit). ``end_dir`` is the direction
    the connector is still MOVING when it arrives at the target — so S
    means "moving south into tgt", entering via the TOP edge.

    ``straight_tolerance`` (default 20 px) controls the straight-line
    collapse heuristic. When both endpoints can slide along their edges
    to a shared coordinate and their natural midpoint difference is
    within this tolerance, the L degenerates to a single straight
    segment with no corner - removing the "twisted start" artefact that
    a tiny first leg + chamfer + standoff produces. Set to 0 to disable.

    ``auto_route=True`` runs grid A* on the SVG's obstacle bitmap and
    automatically picks multi-elbow waypoints that avoid collisions. The
    caller must also pass ``svg`` (path/string/bytes). ``container_id``
    restricts routing to the interior of that element; ``route_cell_size``
    (default 10 px) controls A* resolution vs. speed; ``route_margin``
    (default 5 px) is the clearance from obstacles. On failure the tool
    falls back to the 1-bend L and emits a warning.
    """
    warnings = _check_soft_cap(controls, "calc_l controls")

    if src_rect is not None or tgt_rect is not None:
        if src_x is None or src_y is None:
            src_x = src_y = 0.0
        if tgt_x is None or tgt_y is None:
            tgt_x = tgt_y = 0.0
        src_x, src_y, tgt_x, tgt_y, first_axis = _resolve_l_endpoints_from_rects(
            src_rect,
            tgt_rect,
            src_x,
            src_y,
            tgt_x,
            tgt_y,
            start_dir,
            end_dir,
            warnings,
            straight_tolerance=straight_tolerance,
        )
    else:
        if src_x is None or src_y is None or tgt_x is None or tgt_y is None:
            raise ValueError("calc_l requires src_x/src_y/tgt_x/tgt_y or src_rect/tgt_rect")

    # Compute stem reserves even for the sharp L so the auto-router
    # keeps its corners far enough from src / tgt to leave a clean
    # stem for standoff + arrowhead clearance + stem_min visible px.
    start_trim, end_trim = _resolve_standoff(standoff, margin)
    arrow_start = (arrow or "none") in ("start", "both")
    arrow_end = (arrow or "none") in ("end", "both")
    first_stem = start_trim + (float(head_len) if arrow_start else 0.0) + float(stem_min)
    last_stem = end_trim + (float(head_len) if arrow_end else 0.0) + float(stem_min)

    if auto_route and not controls:
        auto_wp = _auto_route_l_waypoints(
            (src_x, src_y),
            (tgt_x, tgt_y),
            start_dir=start_dir,
            end_dir=end_dir,
            svg=svg,
            container_id=container_id,
            cell_size=route_cell_size,
            margin_px=route_margin,
            first_stem_reserve=first_stem,
            last_stem_reserve=last_stem,
        )
        if auto_wp is None:
            msg = "calc_l auto_route failed - falling back to 1-bend L"
            warnings.append(msg)
            print(f"WARNING: {msg}", file=sys.stderr)
        else:
            controls = auto_wp
            _check_soft_cap(controls, "calc_l auto_route controls")

    # Route BOTH 1-bend and multi-elbow cases through _thread_l_controls
    # so end_dir is always honored on the last segment (the direct
    # _build_l_polyline path ignores end_dir because first_axis is locked
    # from start_dir only).
    pts = _thread_l_controls(
        (src_x, src_y),
        (tgt_x, tgt_y),
        controls or [],
        chamfer=None,
        start_dir=start_dir,
        end_dir=end_dir,
    )
    return _build_polyline_result(
        "l",
        pts,
        head_len,
        head_half_h,
        arrow,
        margin,
        controls=controls,
        warnings=warnings,
        standoff=standoff,
    )


def calc_l_chamfer(
    src_x=None,
    src_y=None,
    tgt_x=None,
    tgt_y=None,
    controls=None,
    chamfer=4.0,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    start_dir=None,
    end_dir=None,
    src_rect=None,
    tgt_rect=None,
    auto_route=False,
    svg=None,
    container_id=None,
    route_cell_size=10,
    route_margin=5,
    straight_tolerance=20.0,
    stem_min=20.0,
):
    """Chamfered L connector. Same edge-aware semantics as ``calc_l``.

    Pass ``src_rect`` / ``tgt_rect`` plus cardinal ``start_dir`` / ``end_dir``
    to snap endpoints to edge midpoints and lock the first axis — this is
    the canonical way to avoid the vertical-along-edge artefact. Without
    directions, geometry inference runs and a warning is emitted.

    ``straight_tolerance`` (default 20 px) controls the straight-line
    collapse heuristic - see ``calc_l`` for details. ``stem_min`` (default
    20 px) reserves a clean cardinal stem of at least that many pixels
    behind each arrowhead after standoff + head_len clearance. When the
    geometry can't accommodate the reservation, the outer corner's bevel
    clamps to 0 (sharp corner) and a warning is emitted so the caller
    knows the guarantee couldn't be honored.

    ``auto_route=True`` runs grid A* on the SVG's obstacle bitmap and
    automatically picks multi-elbow waypoints that avoid collisions.
    Requires ``svg``; ``container_id`` clips routing to one element;
    ``route_cell_size`` / ``route_margin`` tune resolution and clearance.
    Failure falls back to 1-bend L with a warning.
    """
    warnings = _check_soft_cap(controls, "calc_l_chamfer controls")

    if src_rect is not None or tgt_rect is not None:
        if src_x is None or src_y is None:
            src_x = src_y = 0.0
        if tgt_x is None or tgt_y is None:
            tgt_x = tgt_y = 0.0
        src_x, src_y, tgt_x, tgt_y, first_axis = _resolve_l_endpoints_from_rects(
            src_rect,
            tgt_rect,
            src_x,
            src_y,
            tgt_x,
            tgt_y,
            start_dir,
            end_dir,
            warnings,
            straight_tolerance=straight_tolerance,
        )
    else:
        if src_x is None or src_y is None or tgt_x is None or tgt_y is None:
            raise ValueError(
                "calc_l_chamfer requires src_x/src_y/tgt_x/tgt_y or src_rect/tgt_rect"
            )

    # Reserve standoff + head_len + stem_min on each outer segment so
    # (a) the trim for arrowhead clearance never walks into a chamfer
    # bevel - otherwise the line end lands on a diagonal and the arrow
    # tangent diverges from end_dir - and (b) there is always at least
    # ``stem_min`` px of clean cardinal stem behind each arrowhead when
    # the geometry allows. Compute reserves once and pass them into BOTH
    # the auto-router (as stem-zone turn penalty radii) and the threader
    # (as chamfer bevel clamps) so router corners stay far enough from
    # endpoints that the threader can honor the visible-stem guarantee.
    start_trim, end_trim = _resolve_standoff(standoff, margin)
    arrow_start = (arrow or "none") in ("start", "both")
    arrow_end = (arrow or "none") in ("end", "both")
    first_reserve = start_trim + (float(head_len) if arrow_start else 0.0) + float(stem_min)
    last_reserve = end_trim + (float(head_len) if arrow_end else 0.0) + float(stem_min)

    if auto_route and not controls:
        auto_wp = _auto_route_l_waypoints(
            (src_x, src_y),
            (tgt_x, tgt_y),
            start_dir=start_dir,
            end_dir=end_dir,
            svg=svg,
            container_id=container_id,
            cell_size=route_cell_size,
            margin_px=route_margin,
            first_stem_reserve=first_reserve,
            last_stem_reserve=last_reserve,
        )
        if auto_wp is None:
            msg = "calc_l_chamfer auto_route failed - falling back to 1-bend L"
            warnings.append(msg)
            print(f"WARNING: {msg}", file=sys.stderr)
        else:
            controls = auto_wp
            _check_soft_cap(controls, "calc_l_chamfer auto_route controls")

    # Route BOTH 1-bend and multi-elbow cases through _thread_l_controls
    # so end_dir is always honored on the last segment and the chamfer
    # pass can apply the reserves to the outer corners.
    pts = _thread_l_controls(
        (src_x, src_y),
        (tgt_x, tgt_y),
        controls or [],
        chamfer=chamfer,
        start_dir=start_dir,
        end_dir=end_dir,
        first_reserve=first_reserve,
        last_reserve=last_reserve,
    )

    # If the geometry could not accommodate stem_min behind the arrows,
    # emit a non-fatal warning so the caller knows the stem target was
    # missed. Look at the final / initial cardinal leg of the post-
    # chamfer polyline: we need (leg length) >= head_len + stem_min for
    # the arrowhead to sit on a clean cardinal stem of at least stem_min.
    if stem_min and stem_min > 0 and len(pts) >= 2:

        def _axis_leg_length(points, end):
            """Length of the last (or first) maximal axis-aligned run.

            Walks from the specified endpoint inward, accumulating
            segment lengths as long as each segment is axis-aligned AND
            shares the same cardinal axis as the first step. Stops at
            the first diagonal (bevel) or direction change (corner).
            """
            if end == "end":
                seq = list(reversed(points))
            else:
                seq = list(points)
            if len(seq) < 2:
                return 0.0
            dx0 = seq[1][0] - seq[0][0]
            dy0 = seq[1][1] - seq[0][1]
            if dx0 != 0 and dy0 != 0:
                return 0.0  # first step is diagonal, no cardinal stem
            axis0 = "h" if dy0 == 0 else "v"
            total = abs(dx0) + abs(dy0)
            for i in range(2, len(seq)):
                dx = seq[i][0] - seq[i - 1][0]
                dy = seq[i][1] - seq[i - 1][1]
                if dx != 0 and dy != 0:
                    break  # diagonal bevel
                axis = "h" if dy == 0 else "v"
                if axis != axis0:
                    break  # direction change (corner)
                total += abs(dx) + abs(dy)
            return total

        # Stem-too-short warnings. A bend that lands right at (or 1-2px from)
        # the arrowhead or the source endpoint looks unprofessional - the
        # arrow appears to emerge mid-corner. Two severity tiers:
        #   - visible < 3px  -> CRITICAL (bend ON the arrow tip)
        #   - visible < stem_min -> CONSIDER (stem too short, raise geometry)
        if arrow_end:
            leg = _axis_leg_length(pts, "end")
            visible = leg - end_trim - float(head_len)
            if visible + 0.5 < 3.0:
                msg = (
                    f"CONSIDER (snap rule): bend {max(0.0, visible):.1f}px "
                    f"from end arrow; arrow emerges mid-corner. "
                    f"Extend approach leg."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)
            elif visible + 0.5 < float(stem_min):
                msg = (
                    f"CONSIDER (snap rule): end stem {max(0.0, visible):.1f}px "
                    f"(< stem_min={stem_min}). Lengthen final leg."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)
        if arrow_start:
            leg = _axis_leg_length(pts, "start")
            visible = leg - start_trim - float(head_len)
            if visible + 0.5 < 3.0:
                msg = (
                    f"CONSIDER (snap rule): bend {max(0.0, visible):.1f}px "
                    f"from start arrow; arrow emerges mid-corner. "
                    f"Extend first leg."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)
            elif visible + 0.5 < float(stem_min):
                msg = (
                    f"CONSIDER (snap rule): start stem {max(0.0, visible):.1f}px "
                    f"(< stem_min={stem_min}). Lengthen first leg."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)
    return _build_polyline_result(
        "l-chamfer",
        pts,
        head_len,
        head_half_h,
        arrow,
        margin,
        controls=controls,
        warnings=warnings,
        standoff=standoff,
    )


def calc_spline(
    waypoints,
    samples=200,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    controls=None,
    standoff=None,
    start_dir=None,
    end_dir=None,
    direction_offset=24.0,
    tangent_magnitude=None,
):
    """Spline connector. PCHIP through waypoints OR cubic Bezier with tangent vectors.

    REMINDER: endpoint waypoints must be on shape EDGES, not centres (use `geom attach`).
    """
    warnings = _check_soft_cap(controls, "calc_spline controls")
    if len(waypoints) < 2:
        raise ValueError("Spline connector needs at least 2 waypoints")
    src = tuple(waypoints[0])
    dst = tuple(waypoints[-1])
    u_in = _direction_to_unit_vector(start_dir)
    u_out = _direction_to_unit_vector(end_dir)

    if (u_in is not None or u_out is not None) and not controls:
        # Cubic Bezier with explicit tangent vectors. Tangent magnitude
        # controls curve bowing: longer tangent = more dramatic curve, shorter
        # tangent = straighter line. Callers can pass `tangent_magnitude` as
        # either an absolute pixel distance or a fraction of the endpoint
        # chord length. Default = 50% of chord length which gives the
        # graceful S shape of a Sankey diagram.
        dx = dst[0] - src[0]
        dy = dst[1] - src[1]
        chord_len = max(math.hypot(dx, dy), 1.0)
        if tangent_magnitude is None:
            tangent_mag = chord_len * 0.5
        else:
            tangent_mag = float(tangent_magnitude)

        # If only one direction is specified, mirror it for the other end.
        dir_in = u_in if u_in is not None else u_out
        dir_out = u_out if u_out is not None else u_in
        p1 = (src[0] + dir_in[0] * tangent_mag, src[1] + dir_in[1] * tangent_mag)
        p2 = (dst[0] - dir_out[0] * tangent_mag, dst[1] - dir_out[1] * tangent_mag)
        pts = _sample_cubic_bezier(src, p1, p2, dst, num=samples)
    elif controls:
        # Controls provided -> PCHIP through waypoints (no direction injection,
        # caller is explicitly driving the curve shape).
        wps = [src, *[tuple(c) for c in controls], dst]
        pts = pchip_parametric(wps, num_samples=samples)
    else:
        # Pure waypoint spline, no directions, no controls.
        pts = pchip_parametric(list(waypoints), num_samples=samples)

    return _build_polyline_result(
        "spline",
        pts,
        head_len,
        head_half_h,
        arrow,
        margin,
        controls=controls,
        warnings=warnings,
        standoff=standoff,
    )


def _sample_cubic_bezier(p0, p1, p2, p3, num=60):
    """Sample a cubic Bezier curve using the bezier library.

    Tangent at t=0 is 3*(p1 - p0) direction, at t=1 is 3*(p3 - p2) direction -
    guaranteed by construction of the Bernstein basis. The library handles
    the vectorised Bernstein evaluation with numpy under the hood.
    """
    import bezier
    import numpy as np

    nodes = np.asfortranarray(
        [
            [p0[0], p1[0], p2[0], p3[0]],
            [p0[1], p1[1], p2[1], p3[1]],
        ]
    )
    curve = bezier.Curve.from_nodes(nodes)
    ts = np.linspace(0.0, 1.0, num)
    xy = curve.evaluate_multi(ts)  # shape (2, num)
    return [(float(xy[0, i]), float(xy[1, i])) for i in range(num)]


# ---------------------------------------------------------------------------
# Manifold mode: N starts converge through merge points, flow along a shared
# spine, then fork out to M ends. Each start has its own merge point (can
# coincide) and each end has its own fork point (can coincide). Every strand -
# start-to-merge, spine, fork-to-end - uses the selected shape.
# ---------------------------------------------------------------------------


def _calc_single_strand(
    src,
    dst,
    shape,
    chamfer,
    samples,
    margin,
    head_len,
    head_half_h,
    arrow,
    controls=None,
    standoff=None,
    start_dir=None,
    end_dir=None,
    tangent_magnitude=None,
):
    """Dispatch to the right single-strand builder based on `shape`.

    Returns a polyline-shaped result (same contract as calc_l / calc_spline).
    first_axis is inferred per segment from geometry - no global flag.
    `start_dir` / `end_dir` are optional compass-or-angle direction hints
    applied at the endpoints.
    """
    sx, sy = src
    dx, dy = dst
    if shape == "straight":
        if controls:
            raise ValueError("straight shape does not accept controls; use spline or l-chamfer")
        return calc_connector(
            sx,
            sy,
            dx,
            dy,
            margin=margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=arrow,
            standoff=standoff,
            start_dir=start_dir,
            end_dir=end_dir,
        )
    if shape == "l":
        return calc_l(
            sx,
            sy,
            dx,
            dy,
            controls=controls,
            margin=margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=arrow,
            standoff=standoff,
            start_dir=start_dir,
            end_dir=end_dir,
        )
    if shape == "l-chamfer":
        return calc_l_chamfer(
            sx,
            sy,
            dx,
            dy,
            controls=controls,
            chamfer=chamfer,
            margin=margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=arrow,
            standoff=standoff,
            start_dir=start_dir,
            end_dir=end_dir,
        )
    if shape == "spline":
        return calc_spline(
            [(sx, sy), (dx, dy)],
            samples=samples,
            controls=controls,
            margin=margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=arrow,
            standoff=standoff,
            start_dir=start_dir,
            end_dir=end_dir,
            tangent_magnitude=tangent_magnitude,
        )
    raise ValueError(f"shape must be straight|l|l-chamfer|spline, got {shape!r}")


def _centroid(points):
    n = len(points)
    return (sum(p[0] for p in points) / n, sum(p[1] for p in points) / n)


def _unique_in_order(points, tol=0.01):
    """De-duplicate adjacent waypoints within a small tolerance."""
    out = []
    for p in points:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > tol:
            out.append(tuple(p))
    return out


def _resolve_tension(tension):
    """Return (tension_start, tension_end) from scalar or 2-tuple."""
    if isinstance(tension, (int, float)):
        return (float(tension), float(tension))
    if isinstance(tension, (tuple, list)) and len(tension) == 2:
        return (float(tension[0]), float(tension[1]))
    raise ValueError(f"tension must be a number in [0, 1] or a 2-tuple, got {tension!r}")


def _single_convergence_points(n, point):
    """Return a list of N copies of the same convergence point.

    Legacy canonical-manifold model: every start strand converges at exactly
    spine_start and every end strand diverges from exactly spine_end. Kept
    for backward compatibility. The default for new manifolds is
    _distributed_convergence_points (snapping rules), which slides each
    merge/fork point along the spine to its perpendicular projection.
    """
    return [tuple(point)] * n


def _project_onto_spine(point, spine_start, spine_end):
    """Perpendicular projection of `point` onto the spine segment.

    Returns the projection clamped to the segment [spine_start, spine_end]
    along with the fractional t in [0, 1] describing where on the spine the
    projection landed. t=0 means "at spine_start", t=1 means "at spine_end";
    interior t values denote T-junctions.
    """
    sx, sy = spine_start[0], spine_start[1]
    ex, ey = spine_end[0], spine_end[1]
    vx, vy = ex - sx, ey - sy
    length_sq = vx * vx + vy * vy
    if length_sq < 1e-9:
        return (sx, sy), 0.0
    px, py = point[0], point[1]
    t = ((px - sx) * vx + (py - sy) * vy) / length_sq
    t = max(0.0, min(1.0, t))
    return (sx + t * vx, sy + t * vy), t


def _snap_to_grid(coord, grid):
    """Snap a scalar coordinate to the nearest multiple of `grid`.

    Returns `coord` unchanged if grid <= 0. Used by the snapping rules to
    land merge/fork points on clean pixel boundaries.
    """
    if not grid or grid <= 0:
        return coord
    return round(coord / grid) * grid


def _distributed_convergence_points(
    points,
    spine_start,
    spine_end,
    snap_grid=0,
):
    """Slide each point onto the spine via perpendicular projection.

    This is the core of the manifold snapping rules:

    * **Align snap**: each merge/fork point is projected perpendicularly onto
      the spine line, then clamped to the [spine_start, spine_end] segment.
      Interior projections produce T-junctions; projections at the endpoints
      degenerate to the legacy single-convergence behaviour.
    * **Grid snap**: when `snap_grid > 0`, the projection's coordinate along
      the spine axis is snapped to the nearest grid line (horizontal spines
      snap X, vertical spines snap Y, diagonal spines snap the parametric t).
      This keeps connectors landing on clean integer pixel boundaries.

    Returns a list of (snapped_point, t) tuples parallel to `points`, where
    t in [0, 1] is the fractional distance along the spine. Callers use t
    to decide whether the strand endpoint is a T-junction (0 < t < 1) or a
    true spine-endpoint convergence (t==0 or t==1).
    """
    orientation = _spine_orientation(
        (spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])
    )
    out = []
    for p in points:
        proj, t = _project_onto_spine(p, spine_start, spine_end)
        if snap_grid and snap_grid > 0:
            if orientation == "horizontal":
                snapped_x = _snap_to_grid(proj[0], snap_grid)
                proj, t = _project_onto_spine((snapped_x, proj[1]), spine_start, spine_end)
            elif orientation == "vertical":
                snapped_y = _snap_to_grid(proj[1], snap_grid)
                proj, t = _project_onto_spine((proj[0], snapped_y), spine_start, spine_end)
            else:
                snapped_x = _snap_to_grid(proj[0], snap_grid)
                snapped_y = _snap_to_grid(proj[1], snap_grid)
                proj, t = _project_onto_spine((snapped_x, snapped_y), spine_start, spine_end)
        out.append((proj, t))
    return out


def _middle_alignment_hint(points, spine_start, spine_end, label):
    """Snap-rule hint: odd count + middle point off-axis => suggest spine realignment.

    When a manifold has an odd number of starts (or ends) and the MIDDLE
    point's perpendicular distance to the spine line is nonzero, the spine
    is not running through the natural "centre" of the fan. Moving the
    spine so it passes through the middle point produces a visually
    balanced manifold where the central strand flows straight through.

    Returns a telegram-style "CONSIDER: ..." string or None.
    """
    n = len(points)
    if n < 3 or n % 2 == 0:
        return None
    mid = points[n // 2]
    # Only fire the hint when the middle point's projection lands AT a spine
    # endpoint (t=0 or t=1). That's the case where the middle strand feeds
    # into the spine from outside the spine's axis range, and realigning the
    # spine perpendicular axis makes the middle strand a clean straight line.
    # For T-junction geometry (interior projection), the strand is already
    # perpendicular and no realignment is warranted.
    _, t_mid = _project_onto_spine(mid, spine_start, spine_end)
    if 0.01 < t_mid < 0.99:
        return None
    orientation = _spine_orientation(
        (spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])
    )
    if orientation == "horizontal":
        target_y = mid[1]
        current_y = spine_start[1]
        offset = abs(target_y - current_y)
        if offset < 0.5:
            return None
        return (
            f"CONSIDER (snap rule): odd {label} ({n}); middle off-axis "
            f"by {offset:.1f}px. Move spine to y={target_y:.0f} "
            f"for straight-through middle strand."
        )
    if orientation == "vertical":
        target_x = mid[0]
        current_x = spine_start[0]
        offset = abs(target_x - current_x)
        if offset < 0.5:
            return None
        return (
            f"CONSIDER (snap rule): odd {label} ({n}); middle off-axis "
            f"by {offset:.1f}px. Move spine to x={target_x:.0f} "
            f"for straight-through middle strand."
        )
    # Diagonal spine: perpendicular distance to infinite line.
    vx = spine_end[0] - spine_start[0]
    vy = spine_end[1] - spine_start[1]
    vlen = math.hypot(vx, vy)
    if vlen < 1e-9:
        return None
    nx, ny = -vy / vlen, vx / vlen  # unit normal
    offset = abs((mid[0] - spine_start[0]) * nx + (mid[1] - spine_start[1]) * ny)
    if offset < 0.5:
        return None
    return (
        f"CONSIDER (snap rule): odd {label} ({n}); middle {offset:.1f}px "
        f"off diagonal spine. Shift spine_start/spine_end "
        f"so line crosses middle point."
    )


# --------------------------------------------------------------------------
# Near-spine alignment tunables (externalise-ready).
#
# These are the numeric thresholds that govern when the manifold builder
# emits a "your endpoint is close enough to the spine to be aligned"
# recommendation and when `--snap-tolerance` is accepted. Keep them as
# named constants so a future config wiring (yaml / env var) can override
# without code changes.
# --------------------------------------------------------------------------

# Offsets strictly below this are considered already aligned (rounding
# noise) and no warning fires. Pure cleanliness floor.
SPINE_OFFSET_MIN_PX = 0.5

# Offsets above this are considered intentional kinks (the agent wanted
# an L-bend on purpose). The recommendation band is (MIN, MAX] inclusive.
SPINE_OFFSET_MAX_RECOMMEND_PX = 30.0

# Extra tolerance when checking whether a snapped endpoint still lands
# inside a declared target bbox. Absorbs rounding from shape edges.
SPINE_SNAP_BBOX_TOLERANCE_PX = 0.5


def _spine_offset_and_snap(
    points,
    spine_start,
    spine_end,
    label,
    shapes,
    snap_tolerance,
    shape,
    max_recommend=SPINE_OFFSET_MAX_RECOMMEND_PX,
):
    """Detect near-spine endpoints and optionally snap them onto the axis.

    Walks every endpoint (``starts`` or ``ends``) and measures its
    perpendicular offset to the spine axis. In the "reasonable alignment"
    band (0.5 px < offset <= ``max_recommend``) the endpoint is a
    candidate for elbow-free routing - sliding it onto the spine axis
    turns the L / L-chamfer strand into a single clean segment.

    Three outcomes per endpoint:

    1. ``snap_tolerance > 0`` AND geometry supplied AND snap would stay
       inside the declared bbox -> silently align (endpoint coord is
       rewritten in the returned list; no warning).
    2. ``snap_tolerance > 0`` AND geometry supplied BUT snap would leave
       the bbox -> no align; warning explains the geometry block.
    3. Everything else (detection only, or snap requested without
       geometry) -> no align; passive "alignment possible" warning with
       the exact command + geometry reminder.

    Scope restriction: only fires when ``shape`` is ``"l"`` or
    ``"l-chamfer"``. Straight / spline strands absorb offsets naturally
    and don't produce visible kinks.

    Args:
        points: list of ``(x, y)`` endpoints (starts or ends).
        spine_start / spine_end: spine axis segment.
        label: ``"starts"`` or ``"ends"`` (used in warning text).
        shapes: optional list of ``(x, y, w, h)`` bboxes, one per point,
            or None. When present, gates auto-snap with a bbox
            containment check.
        snap_tolerance: float; 0 disables auto-snap, >0 enables it when
            geometry allows.
        shape: manifold strand shape (``"straight"``, ``"l"``,
            ``"l-chamfer"``, ``"spline"``).
        max_recommend: upper bound of the "reasonable alignment" band;
            offsets beyond this are considered intentional kinks and
            get no warning.

    Returns:
        ``(new_points, warnings)``. ``new_points`` has snapped coords
        where applicable; the original list is returned unchanged for
        non-L shapes or when no snaps fire. ``warnings`` is a list of
        CONSIDER-style strings ready to append to the manifold result.
    """
    if shape not in ("l", "l-chamfer", "L-chamfer"):
        return list(points), []
    orientation = _spine_orientation(
        (spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])
    )
    new_points = list(points)
    warnings_out: list[str] = []
    noun = label[:-1]  # "ends" -> "end", "starts" -> "start"
    flag_shapes = f"--{noun}-shapes"

    for i, pt in enumerate(points):
        if orientation == "horizontal":
            target = spine_start[1]
            offset = abs(pt[1] - target)
            axis_str = f"y={target:.0f}"
            snapped = (pt[0], target)
        elif orientation == "vertical":
            target = spine_start[0]
            offset = abs(pt[0] - target)
            axis_str = f"x={target:.0f}"
            snapped = (target, pt[1])
        else:
            # Diagonal: perpendicular distance, no simple snap target.
            vx = spine_end[0] - spine_start[0]
            vy = spine_end[1] - spine_start[1]
            vlen = math.hypot(vx, vy)
            if vlen < 1e-9:
                continue
            nx, ny = -vy / vlen, vx / vlen
            offset = abs((pt[0] - spine_start[0]) * nx + (pt[1] - spine_start[1]) * ny)
            axis_str = "spine axis"
            snapped = None  # snap on diagonals is ambiguous; skip auto-align

        if offset < SPINE_OFFSET_MIN_PX or offset > max_recommend:
            continue

        bbox = shapes[i] if shapes and i < len(shapes) and shapes[i] is not None else None

        if snap_tolerance > 0 and offset <= snap_tolerance and snapped is not None:
            if bbox is not None:
                bx, by, bw, bh = bbox
                tol = SPINE_SNAP_BBOX_TOLERANCE_PX
                if (
                    bx - tol <= snapped[0] <= bx + bw + tol
                    and by - tol <= snapped[1] <= by + bh + tol
                ):
                    # Snap is safe - rewrite point silently.
                    new_points[i] = snapped
                    continue
                # Geometry blocks.
                warnings_out.append(
                    f"CONSIDER: {label} strand {i + 1} at "
                    f"({pt[0]:.0f},{pt[1]:.0f}) is {offset:.1f}px off spine "
                    f"({axis_str}); target bbox {bbox} prevents alignment - "
                    f"snapped {axis_str} falls outside the target's snappable "
                    f"edge. Move target upstream or widen the target."
                )
                continue
            # snap-tolerance set but no geometry provided.
            warnings_out.append(
                f"CONSIDER: {label} strand {i + 1} at "
                f"({pt[0]:.0f},{pt[1]:.0f}) is {offset:.1f}px off spine "
                f"({axis_str}); --snap-tolerance set but {flag_shapes} missing - "
                f"cannot verify snap stays on the target edge. Supply "
                f'{flag_shapes} "x,y,w,h x,y,w,h ..." and re-run.'
            )
            continue

        # Passive recommendation (no snap requested).
        if snapped is None:
            warnings_out.append(
                f"CONSIDER: {label} strand {i + 1} at "
                f"({pt[0]:.0f},{pt[1]:.0f}) is {offset:.1f}px off the diagonal "
                f"spine. Alignment would require moving the endpoint onto the "
                f"spine line; auto-snap not supported on diagonal spines."
            )
        else:
            warnings_out.append(
                f"CONSIDER: {label} strand {i + 1} at "
                f"({pt[0]:.0f},{pt[1]:.0f}) is {offset:.1f}px off spine "
                f"({axis_str}). Alignment possible - rerun with "
                f'`--snap-tolerance 30` (and supply {flag_shapes} "x,y,w,h ..." '
                f"so the tool can verify the snap lands on a valid target edge)."
            )
    return new_points, warnings_out


def _endpoint_clearance_hints(points_with_t, spine_start, spine_end, label, min_fraction=0.05):
    """Snap-rule hint: merge/fork too close to spine endpoint = no room to route.

    When a merge/fork point's t is within `min_fraction` of 0 or 1, the
    strand has effectively zero room to leave the spine-endpoint region
    before being forced into a chamfer. Returns a list of telegram-style
    CONSIDER hints, one per too-close point.
    """
    hints = []
    spine_len = math.hypot(spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])
    for i, (_, t) in enumerate(points_with_t):
        if t < min_fraction and t > 0.0001:
            hints.append(
                f"CONSIDER (snap rule): {label}[{i}] sits {t * spine_len:.1f}px "
                f"from spine_start (t={t:.2f}). Spread merges along spine "
                f"or extend spine_start."
            )
        elif t > 1.0 - min_fraction and t < 0.9999:
            hints.append(
                f"CONSIDER (snap rule): {label}[{i}] sits {(1 - t) * spine_len:.1f}px "
                f"from spine_end (t={t:.2f}). Spread forks along spine "
                f"or extend spine_end."
            )
    return hints


def _organic_relaxation(
    strands_samples,
    iterations=250,
    repulsion=60.0,
    step=0.4,
    stiffness=0.5,
    convergence_threshold=0.1,
    min_distance=3.0,
):
    """Vectorised Fruchterman-Reingold layout for manifold strands.

    Each strand is a chain of sample points; its first and last points are
    pinned at the source and merge/fork endpoints. Every interior point feels:

      1. **Spring force** (Laplacian-style pull toward its two neighbours on
         the same strand). Keeps the chain connected. Stiffness scales k.

      2. **Bell-weighted repulsion** from every point on every OTHER strand.
         The repulsion is damped by a bell curve sin(pi*t) along each strand's
         arc parameter, so points near the pinned endpoints (t~0 or t~1) feel
         almost no repulsion while midsection points (t~0.5) feel the full
         force. This is critical for the canonical manifold: all N start
         strands share the same merge point, so their near-merge samples are
         close to each other by design. Without the bell weighting, the
         near-merge region would explode outward under enormous repulsion.

    Fully vectorised via numpy + scipy.spatial.distance.cdist (one BLAS call
    per iteration for all pairwise distances). Early exit when max per-iter
    displacement falls below `convergence_threshold`. No post-force PCHIP -
    the relaxed coordinates ARE the output.
    """
    import numpy as np
    from scipy.spatial.distance import cdist

    if len(strands_samples) < 2:
        return [list(s) for s in strands_samples]

    sizes = [len(s) for s in strands_samples]
    offsets = np.concatenate([[0], np.cumsum(sizes)])
    n_total = int(offsets[-1])

    pts = np.concatenate([np.asarray(s, dtype=float) for s in strands_samples], axis=0)

    strand_id = np.zeros(n_total, dtype=np.int32)
    for i, (off, sz) in enumerate(zip(offsets[:-1], sizes)):
        strand_id[off : off + sz] = i

    # Pin FOUR samples per strand: the two endpoints plus the samples
    # adjacent to them. The initial curve places the adjacent samples at
    # the direction-injection positions from the PCHIP waypoint list, so
    # freezing both pairs locks the tangent direction at each endpoint.
    # The solver can only move the true interior (index 2 through -3).
    fixed_mask = np.zeros(n_total, dtype=bool)
    for off, sz in zip(offsets[:-1], sizes):
        fixed_mask[off] = True
        fixed_mask[off + sz - 1] = True
        if sz >= 5:
            fixed_mask[off + 1] = True
            fixed_mask[off + sz - 2] = True

    interior_slices = []
    for off, sz in zip(offsets[:-1], sizes):
        # Interior spring indices start at +2 to account for the pinned
        # tangent-constraint sample at +1. Similarly end at -2 rather than -1.
        if sz >= 6:
            lo, hi = off + 2, off + sz - 2
            interior_slices.append((lo, hi, off + 1, off + 3, off + sz - 1))
        elif sz >= 3:
            # Fallback for very short strands: only pin endpoints
            interior_slices.append((off + 1, off + sz - 1, off, off + 2, off + sz))

    # Bell-curve weight per point: sin(pi * t) where t is normalised position
    # on each strand. t=0 at start, t=1 at end, t=0.5 at midpoint.
    # At endpoints the weight is 0 (no repulsion, preserving convergence).
    # At midpoint the weight is 1 (full repulsion, fanning out).
    weights_1d = np.zeros(n_total, dtype=float)
    for off, sz in zip(offsets[:-1], sizes):
        if sz >= 2:
            ts = np.linspace(0.0, 1.0, sz)
            weights_1d[off : off + sz] = np.sin(np.pi * ts)

    stiffness_clamped = max(0.0, min(1.0, float(stiffness)))
    spring_k = 0.3 + 0.7 * stiffness_clamped

    same_strand_mask = strand_id[:, None] == strand_id[None, :]

    for it in range(iterations):
        d = cdist(pts, pts)
        d_safe = np.where((d > min_distance) & (~same_strand_mask), d, np.inf)
        # Inverse-square magnitude (gentler than inverse-cube); direction is
        # (p_i - p_j) / d_ij. So the force is repulsion * (p_i - p_j) / d^3.
        inv_cube = 1.0 / (d_safe * d_safe * d_safe)
        # Bell weighting on both indices: force_ij = w_i * w_j * ...
        # This kills repulsion near pinned endpoints of either strand.
        weight_pair = weights_1d[:, None] * weights_1d[None, :]
        weighted = inv_cube * weight_pair
        delta = pts[:, None, :] - pts[None, :, :]
        repel_force = repulsion * (delta * weighted[:, :, None]).sum(axis=1)

        # Spring force: Laplacian of each strand's chain
        spring_force = np.zeros_like(pts)
        for a, b, lo, hi, end in interior_slices:
            interior = pts[a:b]
            prev_ = pts[lo : lo + (b - a)]
            next_ = pts[hi : hi + (b - a)]
            spring_force[a:b] = spring_k * (prev_ + next_ - 2 * interior)

        force = repel_force + spring_force
        force[fixed_mask] = 0
        disp = force * step
        pts = pts + disp

        max_disp = float(np.linalg.norm(disp, axis=1).max())
        if max_disp < convergence_threshold:
            break

    out = []
    for off, sz in zip(offsets[:-1], sizes):
        out.append([tuple(p) for p in pts[off : off + sz]])
    return out


def _spine_orientation(direction):
    """Classify a spine direction vector as 'horizontal', 'vertical', or 'diagonal'.

    Horizontal: |dx| dominates by at least 3:1 over |dy|.
    Vertical:   |dy| dominates by at least 3:1 over |dx|.
    Diagonal:   anything else.
    """
    dx, dy = abs(direction[0]), abs(direction[1])
    if dx >= 3 * dy:
        return "horizontal"
    if dy >= 3 * dx:
        return "vertical"
    return "diagonal"


def _compute_elbow_alignment(merge_points, orientation, spine_start):
    """Pick a single coordinate where every start-strand elbow should align.

    For horizontal spines we align on the X-axis (all elbows share the same x);
    for vertical spines we align on Y. The chosen coordinate is the median of
    the merge-point projections onto the aligned axis, biased toward spine_start
    when the spread is narrow (guarantees a clean rail running up to the trunk).
    For diagonal spines we fall back to spine_start.x (still acceptable visually
    and simpler to reason about than a rotated rail).
    """
    if not merge_points:
        return None
    if orientation == "horizontal":
        xs = sorted(m[0] for m in merge_points)
        return xs[len(xs) // 2]  # median x
    if orientation == "vertical":
        ys = sorted(m[1] for m in merge_points)
        return ys[len(ys) // 2]  # median y
    # Diagonal: align on spine_start's dominant axis
    return spine_start[0]


def _inject_alignment_control(src, merge, align_value, orientation, existing_controls):
    """Prepend an alignment control point onto an existing controls list.

    For horizontal orientation, the alignment injects a turn at (align_value, src.y)
    which forces the strand to run horizontally to align_value, then turn vertical
    to reach the merge point. For vertical orientation, (src.x, align_value).
    """
    if orientation == "horizontal":
        injected = (align_value, src[1])
    elif orientation == "vertical":
        injected = (src[0], align_value)
    else:
        injected = (align_value, src[1])  # diagonal fallback uses horizontal rule
    # Skip injection if it would be degenerate (already on the line)
    if abs(injected[0] - src[0]) < 0.5 and abs(injected[1] - src[1]) < 0.5:
        return list(existing_controls or [])
    return [injected] + list(existing_controls or [])


def calc_manifold(
    starts,
    ends,
    spine_start,
    spine_end,
    shape="l-chamfer",
    tension=0.75,
    merge_points=None,
    fork_points=None,
    spine_controls=None,
    start_controls=None,
    end_controls=None,
    align_elbows=False,
    organic=None,
    organic_iterations=25,
    organic_repulsion=60.0,
    organic_segments=5,
    chamfer=4.0,
    samples=200,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    snap_grid=0,
    strict=False,
    start_shapes=None,
    end_shapes=None,
    snap_tolerance=0.0,
):
    """Build a manifold connector.

    REMINDER: starts, ends, spine_start, spine_end must be on shape EDGES,
    not centres (use `geom attach` to compute edge anchors).

    Topology:
        N starts -> inferred/specified merge points -> spine_start ->
            spine (with optional spine_controls) -> spine_end ->
            inferred/specified fork points -> M ends

    Parameters:
        starts, ends       Lists of (x, y). Required.
        spine_start        (x, y). Required. Where all start strands converge.
        spine_end          (x, y). Required. Where fork strands diverge from.
        shape              One of "straight", "l", "l-chamfer", "spline".
        tension            Scalar in [0,1] or 2-tuple (start_tension, end_tension).
                           Default 0.75 (stiff). Controls how merge/fork points
                           fan out AND how stiff the S-curves are. 0 = collapse
                           at spine endpoint (floppy, strands cross easily);
                           1 = full perpendicular projection (rigid, maximum
                           separation). Increase toward 1.0 when strands cross
                           or curve backward. Use (start, end) tuple for
                           asymmetric stiffness.
        merge_points       Optional list (one per start) to override inference.
        fork_points        Optional list (one per end) to override inference.
        spine_controls     Optional list of waypoints for the spine connector.
        start_controls     Optional list-of-lists, one inner list per start.
        end_controls       Optional list-of-lists, one inner list per end.
        chamfer            L-chamfer corner cut size.
        samples            PCHIP density for spline shape.
        margin / standoff  Endpoint trims (standoff overrides margin).
        head_len, head_half_h, arrow  Arrowhead config for end strands.

    Returns a dict with start_strands, spine, end_strands, bbox, warnings, etc.
    """
    # --- Input validation ---
    if not starts or not ends:
        raise ValueError("Manifold needs at least one start and one end")
    if shape not in ("straight", "l", "l-chamfer", "spline"):
        raise ValueError(f"shape must be straight|l|l-chamfer|spline, got {shape!r}")

    # Unpack direction-annotated points. Each start/end/spine endpoint can be
    # (x, y) or (x, y, direction) where direction is a compass string or
    # numeric angle. Directions are propagated into the relevant sub-strands:
    # start directions constrain the first segment of start strands; end
    # directions constrain the final approach of end strands. Spine start/end
    # directions constrain the spine's own endpoint tangents.
    spine_start, spine_start_dir = _unpack_point_with_direction(spine_start)
    spine_end, spine_end_dir = _unpack_point_with_direction(spine_end)
    starts_dirs = [_unpack_point_with_direction(p) for p in starts]
    starts = [sd[0] for sd in starts_dirs]
    start_directions = [sd[1] for sd in starts_dirs]
    ends_dirs = [_unpack_point_with_direction(p) for p in ends]
    ends = [ed[0] for ed in ends_dirs]
    end_directions = [ed[1] for ed in ends_dirs]

    N = len(starts)
    M = len(ends)
    t_start, t_end = _resolve_tension(tension)
    if not (0 <= t_start <= 1) or not (0 <= t_end <= 1):
        raise ValueError(f"tension components must be in [0, 1], got ({t_start}, {t_end})")

    warnings = []

    # --- Merge point inference via perpendicular projection ---
    spine_direction = (spine_end[0] - spine_start[0], spine_end[1] - spine_start[1])

    # Compute the spine's flow direction as a numeric compass angle so we can
    # pass it to sub-strands as a default direction constraint. The rule is:
    # a strand connecting to the spine inherits the spine's flow direction at
    # the point of attachment, unless its merge/fork point carries an explicit
    # direction override.
    _sp_len = math.hypot(spine_direction[0], spine_direction[1])
    if _sp_len > 0:
        _sp_dx, _sp_dy = spine_direction[0] / _sp_len, spine_direction[1] / _sp_len
        # Compass angle: N=0 clockwise. dx=unit_x, dy=unit_y in SVG coords.
        spine_flow_angle_deg = math.degrees(math.atan2(_sp_dx, -_sp_dy)) % 360
    else:
        spine_flow_angle_deg = None
    # Snapping rules (two layers - hints always fire, geometry is opt-out):
    #   1. GEOMETRY layer (disabled by `strict=True`):
    #      - Project each merge/fork onto the spine segment (align snap).
    #      - Grid-snap the projection when `snap_grid > 0`.
    #      - Interior t in (0, 1) -> T-junction strand routing.
    #   2. HINT layer (ALWAYS on):
    #      - CONSIDER (snap rule): ... telegram-style best-practice hints.
    #
    # `strict=True` means "apply caller's geometry literally" - layer 1 is
    # skipped, but layer 2 still fires so Claude sees the aesthetic suggestions
    # even when strict keeps the literal placement.
    apply_geometry_snap = not strict
    emit_hints = True

    # Near-spine alignment detection + opt-in snap. Only fires on
    # L / L-chamfer strands where the offset produces a visible kink.
    # Rewrites starts/ends in place when snap is safe; otherwise just
    # collects CONSIDER-style warnings. Runs BEFORE merge/fork inference
    # so snapped coords propagate through the rest of the build.
    if emit_hints and shape in ("l", "l-chamfer", "L-chamfer"):
        starts, spine_snap_warnings_s = _spine_offset_and_snap(
            starts,
            spine_start,
            spine_end,
            "starts",
            start_shapes,
            snap_tolerance,
            shape,
        )
        for hint in spine_snap_warnings_s:
            warnings.append(hint)
            print(hint, file=sys.stderr)
        ends, spine_snap_warnings_e = _spine_offset_and_snap(
            ends,
            spine_start,
            spine_end,
            "ends",
            end_shapes,
            snap_tolerance,
            shape,
        )
        for hint in spine_snap_warnings_e:
            warnings.append(hint)
            print(hint, file=sys.stderr)

    merge_ts = [0.0] * N
    if merge_points is None:
        if apply_geometry_snap:
            distributed = _distributed_convergence_points(
                starts, spine_start, spine_end, snap_grid=snap_grid
            )
            merge_points = [pt for pt, _ in distributed]
            merge_ts = [t for _, t in distributed]
        else:
            merge_points = _single_convergence_points(N, spine_start)
        merge_directions = [None] * N
    else:
        merges_dirs = [_unpack_point_with_direction(p) for p in merge_points]
        merge_points = [md[0] for md in merges_dirs]
        merge_directions = [md[1] for md in merges_dirs]
        if len(merge_points) != N:
            raise ValueError(f"merge_points length ({len(merge_points)}) must match starts ({N})")
        # Record t for each caller-provided merge point so T-junction detection
        # still applies.
        merge_ts = [_project_onto_spine(mp, spine_start, spine_end)[1] for mp in merge_points]
    fork_ts = [1.0] * M
    if fork_points is None:
        if apply_geometry_snap:
            distributed = _distributed_convergence_points(
                ends, spine_start, spine_end, snap_grid=snap_grid
            )
            fork_points = [pt for pt, _ in distributed]
            fork_ts = [t for _, t in distributed]
        else:
            fork_points = _single_convergence_points(M, spine_end)
        fork_directions = [None] * M
    else:
        forks_dirs = [_unpack_point_with_direction(p) for p in fork_points]
        fork_points = [fd[0] for fd in forks_dirs]
        fork_directions = [fd[1] for fd in forks_dirs]
        if len(fork_points) != M:
            raise ValueError(f"fork_points length ({len(fork_points)}) must match ends ({M})")
        fork_ts = [_project_onto_spine(fp, spine_start, spine_end)[1] for fp in fork_points]

    # --- Snap-rule best-practice hints (telegram style "CONSIDER: ...") ---
    # Hints always fire when snap_rules is on, even under --strict, so the
    # caller sees aesthetic suggestions without geometry being auto-adjusted.
    if emit_hints:
        # Hints analyse the CALLER's original points (starts, ends), not the
        # auto-projected ones, so --strict gets the same guidance as default.
        for hint in _endpoint_clearance_hints(
            [(p, _project_onto_spine(p, spine_start, spine_end)[1]) for p in starts],
            spine_start,
            spine_end,
            "starts",
        ):
            warnings.append(hint)
            print(hint, file=sys.stderr)
        for hint in _endpoint_clearance_hints(
            [(p, _project_onto_spine(p, spine_start, spine_end)[1]) for p in ends],
            spine_start,
            spine_end,
            "ends",
        ):
            warnings.append(hint)
            print(hint, file=sys.stderr)
        middle_hint_start = _middle_alignment_hint(starts, spine_start, spine_end, "starts")
        if middle_hint_start:
            warnings.append(middle_hint_start)
            print(middle_hint_start, file=sys.stderr)
        middle_hint_end = _middle_alignment_hint(ends, spine_start, spine_end, "ends")
        if middle_hint_end:
            warnings.append(middle_hint_end)
            print(middle_hint_end, file=sys.stderr)

    # --- Controls list normalisation ---
    if start_controls is None:
        start_controls = [[] for _ in range(N)]
    elif len(start_controls) != N:
        raise ValueError(f"start_controls length ({len(start_controls)}) must match starts ({N})")
    if end_controls is None:
        end_controls = [[] for _ in range(M)]
    elif len(end_controls) != M:
        raise ValueError(f"end_controls length ({len(end_controls)}) must match ends ({M})")
    if spine_controls is None:
        spine_controls = []

    # --- Elbow alignment for L / L-chamfer manifolds ---
    # When align_elbows=True, all start-strand elbows share one coordinate
    # (and same for end strands). Only applies to L-family shapes because
    # "elbow" is meaningful for orthogonal routing; splines ignore the flag.
    aligned_start_controls = [list(c) if c else [] for c in start_controls]
    aligned_end_controls = [list(c) if c else [] for c in end_controls]
    if align_elbows and shape in ("l", "l-chamfer"):
        orientation = _spine_orientation(spine_direction)
        align_merge = _compute_elbow_alignment(merge_points, orientation, spine_start)
        align_fork = _compute_elbow_alignment(fork_points, orientation, spine_end)
        for i in range(N):
            if aligned_start_controls[i]:
                continue  # caller supplied controls - don't second-guess them
            aligned_start_controls[i] = _inject_alignment_control(
                starts[i],
                merge_points[i],
                align_merge,
                orientation,
                None,
            )
        for j in range(M):
            if aligned_end_controls[j]:
                continue
            aligned_end_controls[j] = _inject_alignment_control(
                ends[j],
                fork_points[j],
                align_fork,
                orientation,
                None,
            )

    # --- Build sub-strands ---
    # Each start strand runs from starts[i] to spine_start, passing through
    # merge_points[i] as an intermediate waypoint. This keeps the spine's
    # start as a single convergence point where every strand terminates
    # cleanly, while the merge point shapes the curve along the way.
    # At tension=0 merge_points[i] coincides with spine_start and the strand
    # is a direct curve; at tension=1 the merge point is the full
    # perpendicular projection, bulging the strand outward before converging.
    start_strands = []
    convergence_strands = [None] * N  # retained for API compatibility, always None

    # Tension -> Bezier tangent magnitude scaling. Low tension = floppy
    # = long tangent vectors = dramatic bow. High tension = stiff = short
    # tangent vectors = curve hugs the straight line. The scaling is
    # proportional to the endpoint chord length (computed per-strand below
    # via the default behaviour when tangent_magnitude=None), but we pre-
    # compute a multiplier per side so each strand's tangent mag is
    # chord_len * tension_multiplier.
    def _tension_to_tangent_mult(t):
        # tension=0 -> 0.9 (very floppy), tension=1 -> 0.2 (stiff)
        return 0.9 - 0.7 * t

    tangent_mult_start = _tension_to_tangent_mult(t_start)
    tangent_mult_end = _tension_to_tangent_mult(t_end)

    # Per-strand standoff: a manifold must read as ONE continuous connector,
    # so inner junctions (start-strand end at merge/spine, spine endpoints,
    # end-strand start at fork/spine) MUST have zero standoff. Otherwise the
    # default 1px trim leaves visible gaps where strands meet. Outer endpoints
    # still honour the caller's standoff / margin.
    inner_stub = 0.0

    # Perpendicular-to-spine direction (as compass angle) for T-junction
    # strands. A T-junction strand's last segment must approach the spine
    # at 90 degrees so the junction reads as a clean tee, not a chamfered
    # elbow. Two perpendicular directions exist; the builder below picks
    # whichever points from the strand's source toward the spine.
    def _perpendicular_approach_angle(src):
        if _sp_len <= 0:
            return None
        # Spine normal (rotate spine unit by 90 degrees, both signs)
        nx1, ny1 = -_sp_dy, _sp_dx
        nx2, ny2 = _sp_dy, -_sp_dx
        # Pick the normal that points from src toward the spine (i.e. the
        # one whose dot product with (spine_projection - src) is positive).
        proj, _ = _project_onto_spine(src, spine_start, spine_end)
        vx = proj[0] - src[0]
        vy = proj[1] - src[1]
        dot1 = vx * nx1 + vy * ny1
        dot2 = vx * nx2 + vy * ny2
        if dot1 >= dot2:
            return math.degrees(math.atan2(nx1, -ny1)) % 360
        return math.degrees(math.atan2(nx2, -ny2)) % 360

    # T-junction threshold: anything strictly interior counts. We use a tiny
    # epsilon so a distributed point that landed exactly on spine_start
    # (t=0.0) keeps the legacy convergence routing.
    T_JUNCTION_EPS = 1e-4

    # T-junction middle detection (GEOMETRIC, not index-based):
    #
    # At a merge or fork point, each strand bends from its along-spine leg to
    # its perpendicular-to-spine leg. Those bend points align on a shared
    # "merge line" perpendicular to the spine. A strand is a T-JUNCTION MIDDLE
    # when it has peer strands on BOTH sides of it along that merge line -
    # i.e., the trunk extends past its bend point in both perpendicular
    # directions. The extremes of the cluster (top-most and bottom-most
    # perpendicular positions) are L-JUNCTION ENDS, not T-junctions.
    #
    # Middle strands drop their chamfer: a chamfered bend at a T-junction
    # creates a visible bump against the perpendicular trunk, whereas a sharp
    # L at the extreme tips of the cluster reads clean.
    #
    # Clusters of <3 strands have no middle (every member is an extreme by
    # sort), so chamfer stays on for everyone. The spine endpoint itself is
    # added to the sort so that a small cluster anchored by the spine still
    # has a "middle" when the spine sits between peer bends.
    def _detect_middle_indices(points, spine_dir, spine_endpoint):
        n = len(points)
        if n < 3:
            return set()
        sp_mag = math.hypot(spine_dir[0], spine_dir[1])
        if sp_mag < 1e-9:
            return set()
        # Unit vector perpendicular to the spine direction
        perp = (-spine_dir[1] / sp_mag, spine_dir[0] / sp_mag)

        def project(p):
            return p[0] * perp[0] + p[1] * perp[1]

        # Sort strand positions with the spine endpoint injected so a cluster
        # anchored by the spine counts the spine as a trunk landmark.
        # Use a sort key that only compares projected positions (not the
        # strand index) to avoid "NoneType < int" on ties.
        labelled = [(project(p), i) for i, p in enumerate(points)]
        labelled.append((project(spine_endpoint), None))
        labelled.sort(key=lambda t: t[0])
        # Extremes are the smallest and largest along the trunk axis.
        extremes = set()
        for lab in labelled:
            if lab[1] is not None:
                extremes.add(lab[1])
                break
        for lab in reversed(labelled):
            if lab[1] is not None:
                extremes.add(lab[1])
                break
        return {i for i in range(n) if i not in extremes}

    middle_start_indices = (
        set() if strict else _detect_middle_indices(starts, spine_direction, spine_start)
    )
    middle_end_indices = (
        set() if strict else _detect_middle_indices(ends, spine_direction, spine_end)
    )

    # Outer-side standoffs: caller's `standoff` / `margin` applied to the
    # original source of start strands and the original target of end strands.
    # Default behaviour is SYMMETRIC - the start and end sides use the same
    # standoff value. Callers who want an asymmetric gap pass a 2-tuple via
    # `standoff` explicitly; the tool does not auto-scale one side to
    # compensate for arrowhead clearance.
    _outer_start_trim, _outer_end_trim = _resolve_standoff(standoff, margin)
    start_strand_standoff = (_outer_start_trim, inner_stub)
    end_strand_standoff = (inner_stub, _outer_end_trim)
    spine_standoff = (inner_stub, inner_stub)

    for i in range(N):
        user_controls = list(aligned_start_controls[i]) if aligned_start_controls[i] else []
        t_i = merge_ts[i]
        is_tjunction = apply_geometry_snap and T_JUNCTION_EPS < t_i < 1.0 - T_JUNCTION_EPS
        if is_tjunction:
            # Strand terminates at merge_points[i] on the spine. No chamfer at
            # that end - the tee is formed by the spine passing through the
            # strand's endpoint. We approach perpendicular to the spine.
            strand_end_dir = (
                merge_directions[i]
                if merge_directions[i] is not None
                else _perpendicular_approach_angle(starts[i])
            )
            all_controls = user_controls if user_controls else None
            _chord = math.hypot(
                merge_points[i][0] - starts[i][0], merge_points[i][1] - starts[i][1]
            )
            strand_tangent_mag = _chord * tangent_mult_start
            # T-junction strands must meet the spine cleanly: no chamfer
            # anywhere in the strand path. A chamfer at the spine-facing end
            # creates a visible bump against the spine line (the user's
            # "middle connector with chamfer" complaint). A chamfer at an
            # interior bend would also look wrong against a clean tee, so
            # we set chamfer=0 for the whole strand.
            # `strict=True` opts out of this aesthetic rule and keeps the
            # caller's chamfer value even at T-junctions.
            t_junction_chamfer = chamfer if strict else 0.0
            strand = _calc_single_strand(
                starts[i],
                merge_points[i],
                shape,
                t_junction_chamfer,
                samples,
                margin,
                head_len,
                head_half_h,
                arrow="none",
                controls=all_controls,
                standoff=start_strand_standoff,
                start_dir=start_directions[i],
                end_dir=strand_end_dir,
                tangent_magnitude=strand_tangent_mag,
            )
        else:
            # Endpoint convergence at spine_start (t<=eps or t>=1-eps).
            # For L-chamfer / L shapes the end direction is left UNCONSTRAINED
            # (None) so the router picks the natural two-bend path honouring
            # only start_dir. Forcing end_dir to the spine flow would conflict
            # with start_dir on diagonally-offset endpoints and reverse the
            # routing. Splines still get the spine flow as a tangent hint.
            include_merge = shape != "straight" and merge_points[i] != spine_start
            all_controls = [*user_controls, merge_points[i]] if include_merge else user_controls
            if merge_directions[i] is not None:
                strand_end_dir = merge_directions[i]
            elif shape in ("l", "l-chamfer"):
                strand_end_dir = None
            else:
                strand_end_dir = spine_flow_angle_deg
            _chord = math.hypot(spine_start[0] - starts[i][0], spine_start[1] - starts[i][1])
            strand_tangent_mag = _chord * tangent_mult_start
            # T-junction middle detection: if this strand is NOT at the
            # extreme perpendicular position of the cluster, it's a middle
            # connector at a T-junction formed by its peers. Drop the chamfer
            # so the tee reads clean.
            if i in middle_start_indices:
                effective_chamfer = 0.0
                hint = (
                    f"HINT: start[{i}] chamfer dropped; T-junction middle "
                    f"(peers on both sides of merge trunk)."
                )
                warnings.append(hint)
                print(hint, file=sys.stderr)
            else:
                effective_chamfer = chamfer
            strand = _calc_single_strand(
                starts[i],
                spine_start,
                shape,
                effective_chamfer,
                samples,
                margin,
                head_len,
                head_half_h,
                arrow="none",
                controls=all_controls if all_controls else None,
                standoff=start_strand_standoff,
                start_dir=start_directions[i],
                end_dir=strand_end_dir,
                tangent_magnitude=strand_tangent_mag,
            )
        start_strands.append(strand)
        warnings.extend(strand["warnings"])

    # Spine: spine_start -> spine_end (with spine_controls, no arrow).
    # Both endpoints meet inner strands so standoff=0 both sides.
    spine = _calc_single_strand(
        spine_start,
        spine_end,
        shape,
        chamfer,
        samples,
        margin,
        head_len,
        head_half_h,
        arrow="none",
        controls=spine_controls if spine_controls else None,
        standoff=spine_standoff,
        start_dir=spine_start_dir,
        end_dir=spine_end_dir,
    )
    warnings.extend(spine["warnings"])

    # End strands run from spine_end to ends[j], passing through fork_points[j]
    # as an intermediate waypoint. Same principle as start strands: every
    # strand leaves the spine's single endpoint cleanly.
    end_strands = []
    divergence_strands = [None] * M  # retained for API compatibility

    # Perpendicular-from-spine direction (as compass angle) for T-junction
    # end strands. The strand leaves the spine at fork_points[j] heading
    # perpendicular toward ends[j]; mirror of the start-side helper.
    def _perpendicular_departure_angle(dst):
        if _sp_len <= 0:
            return None
        nx1, ny1 = -_sp_dy, _sp_dx
        nx2, ny2 = _sp_dy, -_sp_dx
        proj, _ = _project_onto_spine(dst, spine_start, spine_end)
        vx = dst[0] - proj[0]
        vy = dst[1] - proj[1]
        dot1 = vx * nx1 + vy * ny1
        dot2 = vx * nx2 + vy * ny2
        if dot1 >= dot2:
            return math.degrees(math.atan2(nx1, -ny1)) % 360
        return math.degrees(math.atan2(nx2, -ny2)) % 360

    for j in range(M):
        user_controls = list(aligned_end_controls[j]) if aligned_end_controls[j] else []
        t_j = fork_ts[j]
        is_tjunction = apply_geometry_snap and T_JUNCTION_EPS < t_j < 1.0 - T_JUNCTION_EPS
        if is_tjunction:
            # Strand departs from fork_points[j] on the spine, heading
            # perpendicular to the spine. No chamfer at the spine-facing end.
            strand_start_dir = (
                fork_directions[j]
                if fork_directions[j] is not None
                else _perpendicular_departure_angle(ends[j])
            )
            all_controls = user_controls if user_controls else None
            _chord_e = math.hypot(ends[j][0] - fork_points[j][0], ends[j][1] - fork_points[j][1])
            strand_tangent_mag_e = _chord_e * tangent_mult_end
            # T-junction fork strands: no chamfer (symmetric with start-side
            # T-junction rule - the middle connectors must meet the spine at
            # a clean tee, no bumps). `strict=True` overrides and keeps the
            # caller's chamfer value.
            t_junction_chamfer = chamfer if strict else 0.0
            strand = _calc_single_strand(
                fork_points[j],
                ends[j],
                shape,
                t_junction_chamfer,
                samples,
                margin,
                head_len,
                head_half_h,
                arrow=arrow,
                controls=all_controls,
                standoff=end_strand_standoff,
                start_dir=strand_start_dir,
                end_dir=end_directions[j],
                tangent_magnitude=strand_tangent_mag_e,
            )
        else:
            # Endpoint convergence at spine_end (t>=1-eps or t<=eps). Same
            # reasoning as start-side: for L / L-chamfer shapes, leave the
            # strand's start direction UNCONSTRAINED so the router can honour
            # end_dir without fighting the spine-flow default.
            include_fork = shape != "straight" and fork_points[j] != spine_end
            all_controls = [fork_points[j], *user_controls] if include_fork else user_controls
            if fork_directions[j] is not None:
                strand_start_dir = fork_directions[j]
            elif shape in ("l", "l-chamfer"):
                strand_start_dir = None
            else:
                strand_start_dir = spine_flow_angle_deg
            _chord_e = math.hypot(ends[j][0] - spine_end[0], ends[j][1] - spine_end[1])
            strand_tangent_mag_e = _chord_e * tangent_mult_end
            if j in middle_end_indices:
                effective_chamfer = 0.0
                hint = (
                    f"HINT: end[{j}] chamfer dropped; T-junction middle "
                    f"(peers on both sides of fork trunk)."
                )
                warnings.append(hint)
                print(hint, file=sys.stderr)
            else:
                effective_chamfer = chamfer
            strand = _calc_single_strand(
                spine_end,
                ends[j],
                shape,
                effective_chamfer,
                samples,
                margin,
                head_len,
                head_half_h,
                arrow=arrow,
                controls=all_controls if all_controls else None,
                standoff=end_strand_standoff,
                start_dir=strand_start_dir,
                end_dir=end_directions[j],
                tangent_magnitude=strand_tangent_mag_e,
            )
        end_strands.append(strand)
        warnings.extend(strand["warnings"])

    # --- Organic relaxation for spline shape (optional) ---
    # Cubic Bezier curves already produce clean tangent-constrained shapes
    # deterministically - no force simulation needed for the standard case.
    # Organic mode is off by default and only kicks in if the caller
    # explicitly requests it.
    should_organic = organic if organic is not None else False
    if should_organic:
        # Run relaxation over the union of start strands + spine + end strands.
        # Fixed endpoints of each strand are preserved automatically by the
        # algorithm (only interior points move).
        strand_list = start_strands + [spine] + end_strands
        original_samples = [list(s["samples"]) for s in strand_list]
        # Couple stiffness to the average manifold tension: stiffer strands
        # under higher tension resist perpendicular bowing. Tension has two
        # interpretations in a manifold - fan-out spread (where strands start
        # and end) AND stiffness (how much they bow in between). Both are
        # governed by the same parameter.
        avg_tension = (t_start + t_end) / 2
        relaxed_samples = _organic_relaxation(
            original_samples,
            iterations=organic_iterations,
            repulsion=organic_repulsion,
            stiffness=avg_tension,
        )
        # Rebuild each strand's path_d / trimmed_path_d / bbox from relaxed samples.
        # Arrowheads must be recomputed because the tangent at the strand endpoint
        # changes when the samples move under relaxation.
        for strand, new_samples in zip(strand_list, relaxed_samples):
            strand["samples"] = new_samples
            strand["path_d"] = _polyline_to_path_d(new_samples)

            # Rebuild start/end info from the relaxed samples
            arrow_start = strand["start"]["arrow"] is not None
            arrow_end = strand["end"]["arrow"] is not None
            new_start_info = _build_endpoint_info(
                new_samples, "start", head_len, head_half_h, arrow_start
            )
            new_end_info = _build_endpoint_info(
                new_samples, "end", head_len, head_half_h, arrow_end
            )
            strand["start"] = new_start_info
            strand["end"] = new_end_info

            # Re-trim for arrowhead clearance if an arrow is present
            trimmed = new_samples
            if arrow_end:
                trimmed = _trim_polyline(trimmed, head_len, "end")
            if arrow_start:
                trimmed = _trim_polyline(trimmed, head_len, "start")
            strand["trimmed_path_d"] = _polyline_to_path_d(trimmed)

            # Refresh bbox to include the new arrowhead polygon vertices
            extras = []
            if new_start_info["arrow"] is not None:
                extras.extend(new_start_info["arrow"]["polygon"])
            if new_end_info["arrow"] is not None:
                extras.extend(new_end_info["arrow"]["polygon"])
            strand["bbox"] = _bbox_of(new_samples, extras=extras)

    # --- bbox: union over all strands and arrowhead polygons ---
    all_bboxes = [s["bbox"] for s in start_strands + end_strands + [spine]]
    all_bboxes.extend(s["bbox"] for s in convergence_strands + divergence_strands if s is not None)
    xs = [bb[0] for bb in all_bboxes if bb] + [bb[0] + bb[2] for bb in all_bboxes if bb]
    ys = [bb[1] for bb in all_bboxes if bb] + [bb[1] + bb[3] for bb in all_bboxes if bb]
    manifold_bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    # --- Concatenated path strings ---
    def _collect_d(key):
        parts = [s[key] for s in start_strands]
        parts.extend(s[key] for s in convergence_strands if s is not None)
        parts.append(spine[key])
        parts.extend(s[key] for s in divergence_strands if s is not None)
        parts.extend(s[key] for s in end_strands)
        return " ".join(parts)

    # --- Post-build quality checks ---

    # 1. Strand crossing detection: check if any start strands cross each
    #    other or any end strands cross each other. Crossing strands are a
    #    visual defect - the fix is to move the merge/fork point or increase
    #    tension so the fan-out is wider and strands separate cleanly.
    def _check_strand_crossings(strands, label):
        """Detect pairwise intersections among a list of strand results.

        Telegram-style WARNING. Crossings are real defects, not hints.
        """
        try:
            from shapely.geometry import LineString
        except ImportError:
            return
        lines = []
        for s in strands:
            pts = s.get("samples", [])
            if len(pts) >= 2:
                lines.append(LineString([(float(x), float(y)) for x, y in pts]))
            else:
                lines.append(None)
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                if lines[i] is None or lines[j] is None:
                    continue
                if lines[i].crosses(lines[j]):
                    tens = t_start if label == "start" else t_end
                    anchor = "merge" if label == "start" else "fork"
                    msg = (
                        f"WARNING: manifold {label} strands {i}/{j} CROSS. "
                        f"Increase tension (now {tens:.2f}) "
                        f"or move {anchor} points further apart on spine."
                    )
                    warnings.append(msg)
                    print(msg, file=sys.stderr)

    _check_strand_crossings(start_strands, "start")
    _check_strand_crossings(end_strands, "end")

    # 2. Backward-curve detection: any sample moving against the spine flow
    #    direction, which happens when bezier S-curves overshoot (too-low
    #    tension) or when endpoint directions force a loop. Caught for both
    #    l-chamfer and spline shapes because it reads raw samples post-build.
    #    Telegram-style CONSIDER hint: tells the caller which knob to turn.
    if _sp_len > 0:
        flow_unit = (_sp_dx, _sp_dy)

        def _check_backward(strands, label):
            side_tension = t_start if label == "start" else t_end
            for i, s in enumerate(strands):
                pts = s.get("samples", [])
                if len(pts) < 3:
                    continue
                max_back = 0.0
                back_k = None
                for k in range(1, len(pts)):
                    dx = pts[k][0] - pts[k - 1][0]
                    dy = pts[k][1] - pts[k - 1][1]
                    dot = dx * flow_unit[0] + dy * flow_unit[1]
                    if dot < max_back:
                        max_back = dot
                        back_k = k
                if max_back < -2.0:
                    msg = (
                        f"CONSIDER (snap rule): manifold {label} strand {i} "
                        f"bends BACKWARD against spine flow ({-max_back:.1f}px "
                        f"at sample {back_k}); tension {side_tension:.2f} "
                        f"too loose. Raise tension toward 1.0 or narrow "
                        f"endpoint spread."
                    )
                    warnings.append(msg)
                    print(msg, file=sys.stderr)

        _check_backward(start_strands, "start")
        _check_backward(end_strands, "end")
        # Spine itself can overshoot when spine_controls / direction hints
        # push it against its own flow.
        pts = spine.get("samples", [])
        if len(pts) >= 3:
            max_back = 0.0
            back_k = None
            for k in range(1, len(pts)):
                dx = pts[k][0] - pts[k - 1][0]
                dy = pts[k][1] - pts[k - 1][1]
                dot = dx * flow_unit[0] + dy * flow_unit[1]
                if dot < max_back:
                    max_back = dot
                    back_k = k
            if max_back < -2.0:
                msg = (
                    f"CONSIDER (snap rule): manifold SPINE bends BACKWARD "
                    f"against its own flow ({-max_back:.1f}px at sample {back_k}). "
                    f"Remove conflicting spine_controls or straighten "
                    f"spine_start_dir / spine_end_dir hints."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)

    # 3. Flow-chain twist detection: the topology is
    #       starts[i] -> merge[i] -> spine_start -> spine_end -> fork[j] -> ends[j]
    #    and every link should have a positive dot product with the spine flow
    #    direction. A negative dot means a source sits AHEAD of its merge point,
    #    or an end sits BEHIND its fork - something is reversed or miswired.
    #    The SPINE direction is the reference; everything downstream follows it.
    if _sp_len > 0:
        flow_unit = (_sp_dx, _sp_dy)
        # Use perpendicular tolerance rather than exact zero: a start that
        # sits 1-2px forward of its merge (e.g. due to grid snapping) is not
        # twisted, but a start 50px past its merge definitely is.
        twist_threshold = -3.0

        for i in range(N):
            dx = merge_points[i][0] - starts[i][0]
            dy = merge_points[i][1] - starts[i][1]
            dot = dx * flow_unit[0] + dy * flow_unit[1]
            if dot < twist_threshold:
                msg = (
                    f"WARNING: TWIST start[{i}] {-dot:.1f}px ahead of merge "
                    f"along flow. Swap coords or flip spine."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)

        for j in range(M):
            dx = ends[j][0] - fork_points[j][0]
            dy = ends[j][1] - fork_points[j][1]
            dot = dx * flow_unit[0] + dy * flow_unit[1]
            if dot < twist_threshold:
                msg = (
                    f"WARNING: TWIST end[{j}] {-dot:.1f}px behind fork "
                    f"along flow. Swap coords or flip spine."
                )
                warnings.append(msg)
                print(msg, file=sys.stderr)

        # Centroid sanity: overall starts-to-ends direction must match spine flow.
        sx = sum(p[0] for p in starts) / N
        sy = sum(p[1] for p in starts) / N
        ex = sum(p[0] for p in ends) / M
        ey = sum(p[1] for p in ends) / M
        centroid_flow = (ex - sx) * flow_unit[0] + (ey - sy) * flow_unit[1]
        if centroid_flow < -10.0:
            msg = (
                f"WARNING: FLOW REVERSED starts centroid {-centroid_flow:.1f}px "
                f"downstream of ends. Swap starts/ends or flip spine."
            )
            warnings.append(msg)
            print(msg, file=sys.stderr)

    return {
        "mode": "manifold",
        "shape": shape,
        "n_starts": N,
        "n_ends": M,
        "starts": starts,
        "ends": ends,
        "spine_start": spine_start,
        "spine_end": spine_end,
        "spine_direction": spine_direction,
        "tension": (t_start, t_end),
        "organic": bool(should_organic),
        "merge_points": merge_points,
        "fork_points": fork_points,
        "start_strands": start_strands,
        "convergence_strands": convergence_strands,
        "spine": spine,
        "divergence_strands": divergence_strands,
        "end_strands": end_strands,
        "all_paths_d": _collect_d("path_d"),
        "all_trimmed_d": _collect_d("trimmed_path_d"),
        "bbox": manifold_bbox,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Collision detection using shapely. Works on polyline results directly.
# ---------------------------------------------------------------------------


def _polyline_to_linestring(result_or_samples):
    """Turn a polyline result dict OR a raw samples list into a LineString."""
    from shapely.geometry import LineString

    if isinstance(result_or_samples, dict):
        samples = result_or_samples.get("samples") or []
    else:
        samples = list(result_or_samples)
    if len(samples) < 2:
        return None
    return LineString([(float(x), float(y)) for x, y in samples])


def detect_collisions(connectors, tolerance=0.0, labels=None):
    """Pairwise collision detection over a list of polyline connectors.

    Args:
        connectors: list of polyline result dicts (as returned by calc_l,
            calc_spline, calc_connector, or manifold sub-strands) OR raw
            samples lists. Must contain at least 2 items.
        tolerance: padding in pixels. Each line is buffered by tolerance/2
            on both sides before the intersection test, so two connectors
            register as colliding when their stroke centres come within
            `tolerance` pixels. tolerance=0 is a strict crossing check.
        labels: optional list of string labels, one per connector, used in
            the result instead of numeric indices. Defaults to "0", "1", ...

    Returns a list of collision dicts:
        {
          "a": label_a, "b": label_b,
          "type": "crossing" | "near-miss" | "touching",
          "points": [(x, y), ...],     # intersection coords (may be empty
                                       # for near-miss at the minimum distance)
          "min_distance": float,       # unbuffered distance between the lines
        }

    Uses shapely (LineString.intersects / intersection / distance / buffer).
    """

    if len(connectors) < 2:
        return []
    if labels is None:
        labels = [str(i) for i in range(len(connectors))]
    if len(labels) != len(connectors):
        raise ValueError(
            f"labels length ({len(labels)}) must match connectors ({len(connectors)})"
        )

    lines = [_polyline_to_linestring(c) for c in connectors]
    collisions = []
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            la, lb = lines[i], lines[j]
            if la is None or lb is None:
                continue
            min_dist = float(la.distance(lb))
            # Classify:
            if la.intersects(lb):
                inter = la.intersection(lb)
                pts = _extract_points(inter)
                # If the only intersection is a shared endpoint, call it touching
                endpoint_share = any(
                    _point_eq(p, la.coords[0])
                    or _point_eq(p, la.coords[-1])
                    or _point_eq(p, lb.coords[0])
                    or _point_eq(p, lb.coords[-1])
                    for p in pts
                )
                if endpoint_share and len(pts) == 1:
                    ctype = "touching"
                else:
                    ctype = "crossing"
                collisions.append(
                    {
                        "a": labels[i],
                        "b": labels[j],
                        "type": ctype,
                        "points": pts,
                        "min_distance": min_dist,
                    }
                )
            elif tolerance > 0 and min_dist <= tolerance:
                # Near-miss: buffered versions would overlap.
                # Report the nearest-pair points (one on each line).
                nearest_pt_a = la.interpolate(la.project(lb.centroid))
                nearest_pt_b = lb.interpolate(lb.project(la.centroid))
                collisions.append(
                    {
                        "a": labels[i],
                        "b": labels[j],
                        "type": "near-miss",
                        "points": [
                            (float(nearest_pt_a.x), float(nearest_pt_a.y)),
                            (float(nearest_pt_b.x), float(nearest_pt_b.y)),
                        ],
                        "min_distance": min_dist,
                    }
                )
    return collisions


def _extract_points(geom):
    """Flatten a shapely intersection geometry into a list of (x, y) tuples."""
    from shapely.geometry import (
        GeometryCollection,
        LineString,
        MultiLineString,
        MultiPoint,
        Point,
    )

    if geom.is_empty:
        return []
    if isinstance(geom, Point):
        return [(float(geom.x), float(geom.y))]
    if isinstance(geom, MultiPoint):
        return [(float(p.x), float(p.y)) for p in geom.geoms]
    if isinstance(geom, LineString):
        # Two overlapping segments - report the midpoint
        mid = geom.interpolate(0.5, normalized=True)
        return [(float(mid.x), float(mid.y))]
    if isinstance(geom, (MultiLineString, GeometryCollection)):
        out = []
        for g in geom.geoms:
            out.extend(_extract_points(g))
        return out
    return []


def _point_eq(p1, p2, tol=1e-6):
    return abs(p1[0] - p2[0]) < tol and abs(p1[1] - p2[1]) < tol


def format_manifold_svg(result, stroke_color="#5456f3", stroke_width="1.2", opacity="0.4"):
    """Render a manifold result as a paste-ready SVG block.

    Emits each sub-strand as its own <path> (trimmed) plus <polygon> arrowheads
    where present, wrapped in a single <g> for logical grouping.
    """
    lines = [
        f"  <!-- manifold connector: shape={result['shape']} "
        f"starts={result['n_starts']} ends={result['n_ends']} -->",
        f'  <g class="manifold-connector" '
        f'fill="none" stroke="{stroke_color}" stroke-width="{stroke_width}" '
        f'opacity="{opacity}" stroke-linejoin="round" stroke-linecap="round">',
    ]

    def emit_strand(strand, label):
        lines.append(f"    <!-- {label} -->")
        lines.append(f'    <path d="{strand["trimmed_path_d"]}"/>')
        for end_name in ("start", "end"):
            end = strand[end_name]
            if end["arrow"] is None:
                continue
            poly_pts = " ".join(f"{px:.2f},{py:.2f}" for px, py in end["arrow"]["polygon"])
            lines.append(
                f'    <polygon points="{poly_pts}" fill="{stroke_color}" stroke="none" opacity="0.6"/>'
            )

    for i, strand in enumerate(result["start_strands"]):
        emit_strand(strand, f"start {i}: start_point -> merge_point")
    emit_strand(result["spine"], "spine: merge_anchor -> fork_anchor")
    for j, strand in enumerate(result["end_strands"]):
        emit_strand(strand, f"end {j}: fork_point -> end_point")

    lines.append("  </g>")
    return "\n".join(lines)


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


def format_svg(result, stroke_color="#5456f3", stroke_width="1.2", opacity="0.4"):
    """Backwards-compatible alias - straight/l/l-chamfer/spline all use the polyline renderer."""
    return format_polyline_svg(result, stroke_color, stroke_width, opacity)


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
              Use for: organic flow paths, decision boundaries, score
              trajectories, anything a designer would draw freehand.

  manifold    N starts converge through per-start merge points, flow along
              a shared spine, then fork out to M ends through per-end fork
              points. Every strand (start-to-merge, spine, fork-to-end)
              uses the same --shape (straight|l|l-chamfer|spline).
              Merge and fork points can coincide (strict junction) or be
              scattered (staggered manifold).
              Use for: hub/spoke fan-ins, many-to-one aggregators, one-to-
              many broadcasts, pipeline trunks with multiple inputs/outputs.

Every mode supports --arrow {none,start,end,both}, --head-size L,H,
--margin (trims arc length from each end), --color/--width/--opacity, and
returns the trimmed path d (with arrowhead clearance baked in) so the
visible stroke never pokes through the polygon.
"""


_LINEAR_DIRECTION_MAP = {
    "forward": "end",
    "reverse": "start",
    "both": "both",
    "none": "none",
}
_MANIFOLD_DIRECTION_MAP = {
    "sources-to-sinks": "end",
    "sinks-to-sources": "start",
    "both": "both",
    "none": "none",
}


def _resolve_direction_flag(args, parser):
    """Map --direction (semantic) to --arrow (mechanical), and collect pre-
    dispatch warnings for the ack gate.

    Returns a list of warning strings (empty when everything is declared).
    Caller merges these with result['warnings'] before the gate so
    direction-omission and underconstrained-routing warnings also require
    acknowledgement.
    """
    pre_warnings = []
    is_manifold = args.mode == "manifold"
    direction_map = _MANIFOLD_DIRECTION_MAP if is_manifold else _LINEAR_DIRECTION_MAP
    if args.direction is not None:
        if args.direction not in direction_map:
            parser.error(
                f"--direction {args.direction!r} invalid for mode={args.mode!r}; "
                f"expected one of {sorted(direction_map)}"
            )
        args.arrow = direction_map[args.direction]
    else:
        # No explicit direction. Collect the warning - the gate will print
        # it and require an ack before the SVG is emitted.
        valid = sorted(direction_map)
        pre_warnings.append(
            f"WARNING: --direction not declared on mode={args.mode!r}. "
            f"Arrowhead placement defaults to --arrow={args.arrow!r} which "
            f"follows input point order, not semantic intent. Declare "
            f"--direction explicitly; expected one of {valid}."
        )

    # L / L-chamfer underconstrained routing warning.
    if args.mode in ("l", "l-chamfer", "L-chamfer"):
        src_polygon = getattr(args, "src_polygon", None)
        tgt_polygon = getattr(args, "tgt_polygon", None)
        has_start_dir = getattr(args, "start_dir", None) is not None
        has_end_dir = getattr(args, "end_dir", None) is not None
        has_src_rect = args.src_rect is not None or src_polygon is not None
        has_tgt_rect = args.tgt_rect is not None or tgt_polygon is not None
        has_geometry = has_src_rect and has_tgt_rect
        has_both_dirs = has_start_dir and has_end_dir
        if not has_geometry and not has_both_dirs:
            pre_warnings.append(
                f"WARNING: mode={args.mode!r} without --start-dir + --end-dir OR "
                "--src-rect + --tgt-rect. Router must infer which axis to leave "
                "each endpoint on, and the guess is frequently wrong for "
                "non-trivial layouts - route will likely look garbage. "
                "Declare either (a) both directions or (b) both shape rects."
            )

    return pre_warnings


def main():
    parser = argparse.ArgumentParser(
        description=_CONNECTOR_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["straight", "l", "l-chamfer", "L-chamfer", "spline", "manifold"],
        default="straight",
        help="Connector style: straight | l | l-chamfer | spline | manifold (default: straight)",
    )
    parser.add_argument("--from", dest="src", help="Source point X,Y (straight/l/l-chamfer)")
    parser.add_argument("--to", dest="tgt", help="Target point X,Y (straight/l/l-chamfer)")
    parser.add_argument(
        "--waypoints", default=None, help='Spline waypoints "x1,y1 x2,y2 ..." (spline mode)'
    )
    parser.add_argument(
        "--starts",
        default=None,
        help='Manifold start points, literal form: "[(x1,y1),(x2,y2),...]" or legacy "x1,y1 x2,y2"',
    )
    parser.add_argument(
        "--ends",
        default=None,
        help="Manifold end points, literal or legacy form (one per end)",
    )
    parser.add_argument(
        "--spine-start",
        default=None,
        help='Manifold spine start point "(x,y)" - required for manifold mode',
    )
    parser.add_argument(
        "--spine-end",
        default=None,
        help='Manifold spine end point "(x,y)" - required for manifold mode',
    )
    parser.add_argument(
        "--merge-points",
        default=None,
        help="Optional merge points (one per start) - overrides tension inference",
    )
    parser.add_argument(
        "--fork-points",
        default=None,
        help="Optional fork points (one per end) - overrides tension inference",
    )
    parser.add_argument(
        "--spine-controls",
        default=None,
        help='Spine control waypoints "[(x1,y1),(x2,y2),...]" (optional)',
    )
    parser.add_argument(
        "--start-controls",
        default=None,
        help='Per-start control groups "[[(x,y),...], [], ...]" (optional, N groups)',
    )
    parser.add_argument(
        "--end-controls",
        default=None,
        help='Per-end control groups "[[(x,y),...], [], ...]" (optional, M groups)',
    )
    parser.add_argument(
        "--tension",
        default="0.5",
        help="Manifold tension scalar or (start,end) tuple in [0,1]. Default 0.5",
    )
    parser.add_argument(
        "--align-elbows",
        action="store_true",
        help="For L / L-chamfer manifolds: force all start-strand elbows to share "
        "one coordinate (and similarly for end strands). Algorithm picks the "
        "alignment axis from the spine orientation. No effect on spline shapes.",
    )
    parser.add_argument(
        "--snap-grid",
        type=float,
        default=0.0,
        help="Grid-snap merge/fork coords to nearest N px along spine axis. "
        "0 = off. Align snap (perpendicular projection onto spine) runs "
        "alongside when a manifold is built.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Literal mode: apply caller geometry exactly as given. No endpoint "
        "sliding onto spine, no grid snap, chamfer kept at T-junctions. "
        "Snap-rule CONSIDER hints still fire (they are guidance, never auto-fix).",
    )
    parser.add_argument(
        "--snap-tolerance",
        type=float,
        default=0.0,
        dest="snap_tolerance",
        help="L / L-chamfer manifold only: auto-slide endpoints whose "
        "perpendicular offset to the spine is <= N px onto the spine axis "
        "so the strand becomes kink-free. Requires --start-shapes or "
        f"--end-shapes to verify the snap stays inside the target bbox. "
        f"Default 0 = detection warnings only. Recommendation band is "
        f"(0.5, {SPINE_OFFSET_MAX_RECOMMEND_PX:.0f}] px; offsets above "
        f"{SPINE_OFFSET_MAX_RECOMMEND_PX:.0f} px are treated as intentional "
        "kinks and NOT flagged.",
    )
    parser.add_argument(
        "--start-shapes",
        default=None,
        help="Manifold only: space-separated bboxes 'x,y,w,h x,y,w,h ...' "
        "for each start endpoint (same order as --starts). Gates "
        "--snap-tolerance: a snap only fires when the shifted coord "
        "still lies inside the declared bbox.",
    )
    parser.add_argument(
        "--end-shapes",
        default=None,
        help="Manifold only: space-separated bboxes 'x,y,w,h x,y,w,h ...' "
        "for each end endpoint (same order as --ends). Gates "
        "--snap-tolerance: a snap only fires when the shifted coord "
        "still lies inside the declared bbox.",
    )
    parser.add_argument(
        "--organic",
        choices=["auto", "on", "off"],
        default="auto",
        help="Organic spline relaxation: auto (on for spline without controls), "
        "on (force relaxation), off (force straight). Uses pairwise inverse-square "
        'repulsion between strand sample points for a braided, "pulled-apart" look.',
    )
    parser.add_argument(
        "--organic-iterations",
        type=int,
        default=25,
        help="Organic relaxation iteration count (default: 25)",
    )
    parser.add_argument(
        "--organic-repulsion",
        type=float,
        default=60.0,
        help="Organic relaxation force strength (default: 60)",
    )
    parser.add_argument(
        "--organic-segments",
        type=int,
        default=5,
        help="Number of PCHIP segments per organic strand (anchors = segments+1). "
        "More segments = finer control, more computation. Default: 5",
    )
    parser.add_argument(
        "--standoff",
        default=None,
        help="Endpoint standoff scalar or (start,end) tuple - overrides --margin",
    )
    parser.add_argument(
        "--controls",
        default=None,
        help='Control waypoints for non-manifold modes "[(x,y),(x,y),...]"',
    )
    parser.add_argument(
        "--shape",
        choices=["straight", "l", "l-chamfer", "L-chamfer", "spline"],
        default="L-chamfer",
        help="Strand shape for manifold mode (default: l-chamfer)",
    )
    parser.add_argument(
        "--samples", type=int, default=200, help="Spline interpolation samples (default: 200)"
    )
    parser.add_argument(
        "--chamfer", type=float, default=4.0, help="L-chamfer corner cut size in px (default: 4)"
    )
    parser.add_argument(
        "--start-dir",
        default=None,
        help="Direction hint at the source endpoint: compass string (N/NE/NNW/...) or "
        "numeric degrees clockwise from north. Constrains L first-axis or injects "
        "a spline tangent control point.",
    )
    parser.add_argument(
        "--end-dir",
        default=None,
        help="Direction hint at the target endpoint, same format as --start-dir.",
    )
    parser.add_argument(
        "--src-rect",
        default=None,
        help="Source shape bounding rect as 'x,y,w,h'. For l/l-chamfer modes, "
        "combine with --start-dir E|W|N|S to snap the exit point to the edge "
        "midpoint. Missing direction falls back to centre-to-target ray and "
        "emits a warning.",
    )
    parser.add_argument(
        "--tgt-rect",
        default=None,
        help="Target shape bounding rect as 'x,y,w,h'. Combine with --end-dir "
        "to snap the entry point to the edge midpoint.",
    )
    parser.add_argument(
        "--arrow",
        choices=["none", "start", "end", "both"],
        default="end",
        help="Where to place arrowheads in l/l-chamfer/spline modes (default: end)",
    )
    parser.add_argument(
        "--direction",
        default=None,
        help=(
            "Semantic arrow direction; maps to --arrow per mode. "
            "For straight/l/l-chamfer/spline: "
            "forward|reverse|both|none. For manifold: "
            "sources-to-sinks|sinks-to-sources|both|none. When omitted, "
            "the tool proceeds with --arrow defaults but emits a stderr "
            "warning - arrow direction is a deliberate choice, not a "
            "geometry accident."
        ),
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
    parser.add_argument(
        "--auto-route",
        action="store_true",
        help="Run grid A* on the SVG obstacle bitmap to pick multi-elbow "
        "waypoints that avoid collisions. Requires --svg. Falls back to "
        "1-bend L with a warning if unroutable.",
    )
    parser.add_argument(
        "--svg",
        default=None,
        help="SVG file path for --auto-route. Required when --auto-route is set.",
    )
    parser.add_argument(
        "--container-id",
        default=None,
        help="Clip auto-route to the interior of the element with this id "
        "(must be a closed shape; groups rejected). Used only with --auto-route.",
    )
    parser.add_argument(
        "--route-cell-size",
        type=float,
        default=10.0,
        help="A* grid cell size in px (default: 10). Smaller = higher "
        "fidelity + slower. Used only with --auto-route.",
    )
    parser.add_argument(
        "--route-margin",
        type=float,
        default=5.0,
        help="Obstacle clearance in px for the routing free-mask (default: 5). "
        "Used only with --auto-route.",
    )
    parser.add_argument(
        "--straight-tolerance",
        type=float,
        default=20.0,
        help="Straight-line collapse tolerance in px (default: 20). When "
        "both L endpoints can slide along their cardinal edges to a "
        "shared coordinate within this tolerance, the L degenerates to "
        "a single straight segment. Slide bias favours the smaller "
        "geometry so the larger rect absorbs the displacement. Set to "
        "0 to disable the collapse heuristic.",
    )
    parser.add_argument(
        "--stem-min",
        type=float,
        default=20.0,
        help="Minimum visible cardinal stem behind each arrowhead in px "
        "(default: 20). Reserved via A* stem-zone turn penalty + "
        "waypoint snap + chamfer clamp. When the geometry can't honour "
        "the target, the tool emits a non-fatal warning with the "
        "achieved stem length. Set to 0 to disable the reservation.",
    )
    add_ack_warning_arg(parser)
    args = parser.parse_args()

    pre_warnings = _resolve_direction_flag(args, parser)

    head_len, head_half_h = map(float, args.head_size.split(","))

    if args.mode == "straight" and args.waypoints is None:
        src_rect = _parse_rect(args.src_rect) if args.src_rect else None
        tgt_rect = _parse_rect(args.tgt_rect) if args.tgt_rect else None
        if args.src is not None:
            src_x, src_y = _parse_point(args.src)
        else:
            src_x = src_y = None
        if args.tgt is not None:
            tgt_x, tgt_y = _parse_point(args.tgt)
        else:
            tgt_x = tgt_y = None
        if src_rect is None and (src_x is None or src_y is None):
            parser.error("--from or --src-rect is required in straight mode")
        if tgt_rect is None and (tgt_x is None or tgt_y is None):
            parser.error("--to or --tgt-rect is required in straight mode")
        straight_standoff = _parse_standoff(args.standoff) if args.standoff else None
        _zero_warn = _zero_standoff_warning(straight_standoff)
        if _zero_warn:
            pre_warnings.append(_zero_warn)

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
                c = calc_connector(
                    src_x,
                    src_y,
                    tgt_x,
                    tgt_y,
                    margin=args.margin,
                    head_len=head_len,
                    head_half_h=head_half_h,
                    standoff=straight_standoff,
                )
                enforce_warning_acks(
                    pre_warnings + list(c.get("warnings", [])),
                    sys.argv[1:],
                    args.ack_warning,
                )
                print("Line does not cross pill rect - no cutout needed")
                print_result(c, args)
            else:
                combined = list(result.get("warnings", []))
                combined += list(result.get("segment1", {}).get("warnings", []))
                combined += list(result.get("segment2", {}).get("warnings", []))
                enforce_warning_acks(pre_warnings + combined, sys.argv[1:], args.ack_warning)
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
                print(
                    format_polyline_svg(result["segment1"], args.color, args.width, args.opacity)
                )
                print(
                    format_polyline_svg(result["segment2"], args.color, args.width, args.opacity)
                )
        else:
            c = calc_connector(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                standoff=straight_standoff,
                src_rect=src_rect,
                tgt_rect=tgt_rect,
            )
            enforce_warning_acks(
                pre_warnings + list(c.get("warnings", [])),
                sys.argv[1:],
                args.ack_warning,
            )
            print_result(c, args)
        return

    # Accept both "L-chamfer" (preferred; 'l' is easy to mistake for '1') and
    # "l-chamfer" (legacy). Normalize to the lowercase form used internally
    # for dispatch and style keys.
    if hasattr(args, "shape") and args.shape == "L-chamfer":
        args.shape = "l-chamfer"
    if args.mode == "L-chamfer":
        args.mode = "l-chamfer"

    # Manifold mode: N starts + M ends + required spine start/end + optional tension/controls
    if args.mode == "manifold":
        if not all([args.starts, args.ends, args.spine_start, args.spine_end]):
            parser.error("manifold mode requires --starts, --ends, --spine-start, --spine-end")
        starts = _parse_point_list(args.starts)
        ends = _parse_point_list(args.ends)
        spine_start = _parse_point(args.spine_start)
        spine_end = _parse_point(args.spine_end)
        merge_points = _parse_point_list(args.merge_points) if args.merge_points else None
        fork_points = _parse_point_list(args.fork_points) if args.fork_points else None
        spine_controls = _parse_point_list(args.spine_controls) if args.spine_controls else None
        start_controls = _parse_point_groups(args.start_controls) if args.start_controls else None
        end_controls = _parse_point_groups(args.end_controls) if args.end_controls else None
        tension = _parse_tension(args.tension)
        standoff = _parse_standoff(args.standoff) if args.standoff else None
        _zero_warn = _zero_standoff_warning(standoff)
        if _zero_warn:
            pre_warnings.append(_zero_warn)
        result = calc_manifold(
            starts=starts,
            ends=ends,
            spine_start=spine_start,
            spine_end=spine_end,
            shape=args.shape,
            tension=tension,
            merge_points=merge_points,
            fork_points=fork_points,
            spine_controls=spine_controls,
            start_controls=start_controls,
            end_controls=end_controls,
            align_elbows=args.align_elbows,
            organic={"auto": None, "on": True, "off": False}[args.organic],
            organic_iterations=args.organic_iterations,
            organic_repulsion=args.organic_repulsion,
            organic_segments=args.organic_segments,
            chamfer=args.chamfer,
            samples=args.samples,
            margin=args.margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=args.arrow,
            standoff=standoff,
            # --strict disables geometry modification (sliding, grid snap).
            # Hints always fire.
            snap_grid=0.0 if args.strict else args.snap_grid,
            strict=args.strict,
            start_shapes=_parse_shape_list(args.start_shapes),
            end_shapes=_parse_shape_list(args.end_shapes),
            snap_tolerance=args.snap_tolerance,
        )
        enforce_warning_acks(
            pre_warnings + list(result.get("warnings", [])),
            sys.argv[1:],
            args.ack_warning,
        )
        print_manifold_result(result, args)
        return

    controls = _parse_point_list(args.controls) if args.controls else None
    standoff = _parse_standoff(args.standoff) if args.standoff else None
    _zero_warn = _zero_standoff_warning(standoff)
    if _zero_warn:
        pre_warnings.append(_zero_warn)

    # New polyline-based modes
    if args.mode == "spline" or args.waypoints is not None:
        if args.waypoints is None:
            parser.error("--waypoints is required in spline mode")
        waypoints = _parse_waypoints(args.waypoints)
        # A PCHIP spline needs at least 3 waypoints to actually curve -
        # two points degenerate to a straight line, which is what other
        # modes are for. Fail loudly with guidance instead of silently
        # producing a line.
        if len(waypoints) < 3:
            parser.error(
                f"--mode spline needs at least 3 waypoints to produce a curve; "
                f"got {len(waypoints)}. Two-point paths should use --mode straight, "
                f"or add a middle control point: --waypoints 'x1,y1 xmid,ymid x2,y2'."
            )
        result = calc_spline(
            waypoints,
            samples=args.samples,
            margin=args.margin,
            head_len=head_len,
            head_half_h=head_half_h,
            arrow=args.arrow,
            controls=controls,
            standoff=standoff,
        )
    else:
        src_rect = _parse_rect(args.src_rect) if args.src_rect else None
        tgt_rect = _parse_rect(args.tgt_rect) if args.tgt_rect else None
        if args.src is not None:
            src_x, src_y = _parse_point(args.src)
        else:
            src_x = src_y = None
        if args.tgt is not None:
            tgt_x, tgt_y = _parse_point(args.tgt)
        else:
            tgt_x = tgt_y = None
        # --from/--to required unless a matching rect is provided for each side.
        if src_rect is None and (src_x is None or src_y is None):
            parser.error(f"--from or --src-rect is required in {args.mode} mode")
        if tgt_rect is None and (tgt_x is None or tgt_y is None):
            parser.error(f"--to or --tgt-rect is required in {args.mode} mode")
        if args.auto_route and args.svg is None:
            parser.error("--auto-route requires --svg")
        if args.mode == "l":
            result = calc_l(
                src_x=src_x,
                src_y=src_y,
                tgt_x=tgt_x,
                tgt_y=tgt_y,
                controls=controls,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
                standoff=standoff,
                start_dir=args.start_dir,
                end_dir=args.end_dir,
                src_rect=src_rect,
                tgt_rect=tgt_rect,
                auto_route=args.auto_route,
                svg=args.svg,
                container_id=args.container_id,
                route_cell_size=args.route_cell_size,
                route_margin=args.route_margin,
                straight_tolerance=args.straight_tolerance,
                stem_min=args.stem_min,
            )
        else:  # l-chamfer
            result = calc_l_chamfer(
                src_x=src_x,
                src_y=src_y,
                tgt_x=tgt_x,
                tgt_y=tgt_y,
                controls=controls,
                chamfer=args.chamfer,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
                standoff=standoff,
                start_dir=args.start_dir,
                end_dir=args.end_dir,
                src_rect=src_rect,
                tgt_rect=tgt_rect,
                auto_route=args.auto_route,
                svg=args.svg,
                container_id=args.container_id,
                route_cell_size=args.route_cell_size,
                route_margin=args.route_margin,
                straight_tolerance=args.straight_tolerance,
                stem_min=args.stem_min,
            )

    enforce_warning_acks(
        pre_warnings + list(result.get("warnings", [])),
        sys.argv[1:],
        args.ack_warning,
    )
    print_polyline_result(result, args)


def _parse_waypoints(text):
    """Parse '"x1,y1 x2,y2 ..."' into a list of (x, y) tuples.

    Accepts legacy space-separated form AND Python/JSON literal form:
      "100,80 200,40 300,120"      (legacy)
      "[(100,80),(200,40),(300,120)]"  (literal)
      "[[100,80],[200,40],[300,120]]"  (JSON-style)
    """
    import ast as _ast

    text = text.strip()
    if text.startswith(("[", "(")):
        parsed = _ast.literal_eval(text)
        return [tuple(p) for p in parsed]
    # Legacy space-separated
    out = []
    for token in text.replace(",", " ").split():
        out.append(float(token))
    if len(out) < 4 or len(out) % 2 != 0:
        raise ValueError(
            f"--waypoints must contain >= 2 pairs of numbers, got {len(out)} numbers. "
            f"For --mode spline you need >= 3 pairs (waypoints) to get a curve."
        )
    return [(out[i], out[i + 1]) for i in range(0, len(out), 2)]


def _parse_point_list(text):
    """Parse a point list from a literal or legacy space-separated string."""
    import ast as _ast

    text = text.strip()
    if text.startswith(("[", "(")):
        parsed = _ast.literal_eval(text)
        return [tuple(p) for p in parsed]
    out = []
    for token in text.replace(",", " ").split():
        out.append(float(token))
    if len(out) < 2 or len(out) % 2 != 0:
        raise ValueError(f"point list must contain >= 1 pair of numbers, got {len(out)} numbers")
    return [(out[i], out[i + 1]) for i in range(0, len(out), 2)]


def _parse_point(text):
    """Parse a single (x, y) point. Accepts literal '(x,y)' or 'x,y'."""
    import ast as _ast

    text = text.strip()
    if text.startswith(("[", "(")):
        parsed = _ast.literal_eval(text)
        return (float(parsed[0]), float(parsed[1]))
    parts = [float(t) for t in text.replace(",", " ").split()]
    if len(parts) != 2:
        raise ValueError(f"point must have exactly 2 numbers, got {len(parts)}")
    return (parts[0], parts[1])


def _parse_shape_list(text):
    """Parse 'x,y,w,h x,y,w,h ...' into a list of 4-tuples, or None.

    Used by --start-shapes / --end-shapes on manifold mode. Empty / None
    input returns None so the caller can treat missing geometry as "no
    bbox provided" and skip the snap safety check.
    """
    if not text:
        return None
    chunks = text.replace(";", " ").split()
    out = []
    for chunk in chunks:
        nums = [float(x) for x in chunk.split(",") if x]
        if len(nums) != 4:
            raise ValueError(
                f"shape list chunk {chunk!r} must be 'x,y,w,h' (4 comma-separated floats)"
            )
        out.append(tuple(nums))
    return out or None


def _parse_rect(text):
    """Parse 'x,y,w,h' (or literal '(x,y,w,h)') into a 4-tuple of floats."""
    import ast as _ast

    text = text.strip()
    if text.startswith(("[", "(")):
        parsed = _ast.literal_eval(text)
        return (float(parsed[0]), float(parsed[1]), float(parsed[2]), float(parsed[3]))
    parts = [float(t) for t in text.replace(",", " ").split()]
    if len(parts) != 4:
        raise ValueError(f"rect must have exactly 4 numbers (x,y,w,h), got {len(parts)}")
    return (parts[0], parts[1], parts[2], parts[3])


def _parse_point_groups(text):
    """Parse a list-of-lists of points (one group per sub-connector).

    Example literal:
      "[[(150,100),(200,150)], [], [(150,300)], [(200,400),(180,380)]]"
    """
    import ast as _ast

    parsed = _ast.literal_eval(text)
    return [[tuple(p) for p in group] for group in parsed]


def _parse_tension(text):
    """Parse a tension scalar or 2-tuple."""
    import ast as _ast

    text = text.strip()
    if text.startswith(("[", "(")):
        parsed = _ast.literal_eval(text)
        return (float(parsed[0]), float(parsed[1]))
    return float(text)


def _parse_standoff(text):
    """Parse a standoff scalar or 2-tuple."""
    return _parse_tension(text)


def print_manifold_result(result, args):
    """Print diagnostic output for a manifold connector (tension model)."""
    print("=== MANIFOLD CONNECTOR ===")
    print(f"Shape:            {result['shape']}")
    print(f"Starts:           {result['n_starts']}")
    print(f"Ends:             {result['n_ends']}")
    print(f"Spine start:      ({result['spine_start'][0]:.1f}, {result['spine_start'][1]:.1f})")
    print(f"Spine end:        ({result['spine_end'][0]:.1f}, {result['spine_end'][1]:.1f})")
    print(f"Tension:          {result['tension']}")
    bb = result["bbox"]
    print(f"BBox:             x={bb[0]:.1f} y={bb[1]:.1f} w={bb[2]:.1f} h={bb[3]:.1f}")
    if result["warnings"]:
        print(f"Warnings:         {len(result['warnings'])}")
        for w in result["warnings"]:
            print(f"  - {w}")
    print("")

    for i, strand in enumerate(result["start_strands"]):
        src = result["starts"][i]
        merge = result["merge_points"][i]
        print(
            f"--- start {i}: ({src[0]:.1f},{src[1]:.1f}) "
            f"-> merge ({merge[0]:.1f},{merge[1]:.1f})  "
            f"len={strand['total_length']:.1f}px ---"
        )
        print(f"  d: {strand['trimmed_path_d']}")

    print("")
    print(
        f"--- spine: ({result['spine_start'][0]:.1f},{result['spine_start'][1]:.1f}) "
        f"-> ({result['spine_end'][0]:.1f},{result['spine_end'][1]:.1f})  "
        f"len={result['spine']['total_length']:.1f}px ---"
    )
    print(f"  d: {result['spine']['trimmed_path_d']}")
    print("")

    for j, strand in enumerate(result["end_strands"]):
        fork = result["fork_points"][j]
        dst = result["ends"][j]
        arrow_info = ""
        if strand["end"]["arrow"] is not None:
            arrow_info = f"  arrow angle={strand['end']['angle_deg']:.1f}deg"
        print(
            f"--- end {j}: fork ({fork[0]:.1f},{fork[1]:.1f}) "
            f"-> ({dst[0]:.1f},{dst[1]:.1f})  "
            f"len={strand['total_length']:.1f}px{arrow_info} ---"
        )
        print(f"  d: {strand['trimmed_path_d']}")

    print("")
    print("--- SVG Snippet ---\n")
    print(format_manifold_svg(result, args.color, args.width, args.opacity))


def print_polyline_result(result, args):
    """Print diagnostic output for L / L-chamfer / spline connectors."""
    print(f"=== {result['mode'].upper()} CONNECTOR ===")
    print(f"Samples:          {len(result['samples'])}")
    print(f"Total length:     {result['total_length']:.1f}px")
    if result.get("warnings"):
        print("Warnings:")
        for w in result["warnings"]:
            print(f"  ! {w}")
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


def print_result(result, args):
    """Straight-mode output. The result is a polyline-shaped dict - same printer
    as l/l-chamfer/spline - so the diagnostic output is consistent across modes.
    """
    print_polyline_result(result, args)


if __name__ == "__main__":
    main()
