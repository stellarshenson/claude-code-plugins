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


def _thread_l_controls(src, dst, controls, chamfer=None):
    """Build an orthogonal polyline from src to dst, visiting each control in
    order as a corner. Each segment's first_axis is inferred from its own
    geometry (dominant delta first). When chamfer is not None, corners get
    the chamfered cut; when None, sharp corners.

    Zero controls degenerates to a single L-segment (current behaviour).
    """
    waypoints = [src, *controls, dst]
    result = [waypoints[0]]
    for i in range(len(waypoints) - 1):
        a = waypoints[i]
        b = waypoints[i + 1]
        if chamfer is None:
            seg = _build_l_polyline(a[0], a[1], b[0], b[1], first_axis=None)
        else:
            seg = _build_l_chamfer_polyline(
                a[0], a[1], b[0], b[1], first_axis=None, chamfer=chamfer
            )
        # Drop the first point of each segment except the very first, to avoid
        # duplicating the join between consecutive segments.
        result.extend(seg[1:])
    return result


def calc_l(
    src_x,
    src_y,
    tgt_x,
    tgt_y,
    controls=None,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    start_dir=None,
    end_dir=None,
):
    """Axis-aligned L connector, sharp corners. First axis inferred from geometry.

    REMINDER: endpoints must be on shape EDGES, not centres (use `geom attach`).
    """
    warnings = _check_soft_cap(controls, "calc_l controls")
    first_axis = None
    if start_dir is not None:
        first_axis = _apply_direction_to_l((src_x, src_y), (tgt_x, tgt_y), start_dir, end_dir)
    if controls:
        pts = _thread_l_controls((src_x, src_y), (tgt_x, tgt_y), controls, chamfer=None)
    else:
        pts = _build_l_polyline(src_x, src_y, tgt_x, tgt_y, first_axis=first_axis)
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
    src_x,
    src_y,
    tgt_x,
    tgt_y,
    controls=None,
    chamfer=4.0,
    margin=0.0,
    head_len=10,
    head_half_h=5,
    arrow="end",
    standoff=None,
    start_dir=None,
    end_dir=None,
):
    """Chamfered L connector. Same direction semantics as calc_l.

    REMINDER: endpoints must be on shape EDGES, not centres (use `geom attach`).
    """
    warnings = _check_soft_cap(controls, "calc_l_chamfer controls")
    first_axis = None
    if start_dir is not None:
        first_axis = _apply_direction_to_l((src_x, src_y), (tgt_x, tgt_y), start_dir, end_dir)
    if controls:
        pts = _thread_l_controls((src_x, src_y), (tgt_x, tgt_y), controls, chamfer=chamfer)
    else:
        pts = _build_l_chamfer_polyline(
            src_x, src_y, tgt_x, tgt_y, first_axis=first_axis, chamfer=chamfer
        )
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

    In the canonical manifold model every start strand converges at exactly
    the same merge point (= spine_start) and every end strand diverges from
    exactly the same fork point (= spine_end). There is no "distribution"
    along the spine - the spine has a single start and a single end, and
    the strands all terminate there, tangent to the spine direction.
    """
    return [tuple(point)] * n


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
    tension=0.5,
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
                           Controls how merge/fork points fan out. 0 = collapse
                           at spine endpoint, 1 = full perpendicular projection
                           of each start/end onto the merge/fork line.
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
    if merge_points is None:
        # Canonical model: merge point is ONE point at spine_start.
        # Every start strand converges here, tangent to the spine direction.
        # Tension/bundling is resolved via the force simulation, not by
        # distributing merge points along the spine.
        merge_points = _single_convergence_points(N, spine_start)
        merge_directions = [None] * N
    else:
        merges_dirs = [_unpack_point_with_direction(p) for p in merge_points]
        merge_points = [md[0] for md in merges_dirs]
        merge_directions = [md[1] for md in merges_dirs]
        if len(merge_points) != N:
            raise ValueError(f"merge_points length ({len(merge_points)}) must match starts ({N})")
    if fork_points is None:
        # Canonical model: fork point is ONE point at spine_end. Every end
        # strand diverges from here, tangent to the spine direction.
        fork_points = _single_convergence_points(M, spine_end)
        fork_directions = [None] * M
    else:
        forks_dirs = [_unpack_point_with_direction(p) for p in fork_points]
        fork_points = [fd[0] for fd in forks_dirs]
        fork_directions = [fd[1] for fd in forks_dirs]
        if len(fork_points) != M:
            raise ValueError(f"fork_points length ({len(fork_points)}) must match ends ({M})")

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

    for i in range(N):
        user_controls = list(aligned_start_controls[i]) if aligned_start_controls[i] else []
        include_merge = shape != "straight" and merge_points[i] != spine_start
        all_controls = [*user_controls, merge_points[i]] if include_merge else user_controls
        strand_end_dir = (
            merge_directions[i] if merge_directions[i] is not None else spine_flow_angle_deg
        )
        # Compute tangent magnitude from start-side tension and this strand's
        # source -> merge chord length.
        _chord = math.hypot(spine_start[0] - starts[i][0], spine_start[1] - starts[i][1])
        strand_tangent_mag = _chord * tangent_mult_start
        strand = _calc_single_strand(
            starts[i],
            spine_start,
            shape,
            chamfer,
            samples,
            margin,
            head_len,
            head_half_h,
            arrow="none",
            controls=all_controls if all_controls else None,
            standoff=standoff,
            start_dir=start_directions[i],
            end_dir=strand_end_dir,
            tangent_magnitude=strand_tangent_mag,
        )
        start_strands.append(strand)
        warnings.extend(strand["warnings"])

    # Spine: spine_start -> spine_end (with spine_controls, no arrow)
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
        standoff=standoff,
        start_dir=spine_start_dir,
        end_dir=spine_end_dir,
    )
    warnings.extend(spine["warnings"])

    # End strands run from spine_end to ends[j], passing through fork_points[j]
    # as an intermediate waypoint. Same principle as start strands: every
    # strand leaves the spine's single endpoint cleanly.
    end_strands = []
    divergence_strands = [None] * M  # retained for API compatibility
    for j in range(M):
        user_controls = list(aligned_end_controls[j]) if aligned_end_controls[j] else []
        include_fork = shape != "straight" and fork_points[j] != spine_end
        all_controls = [fork_points[j], *user_controls] if include_fork else user_controls
        # Start-direction rule: a strand leaving spine_end inherits the
        # spine's flow direction unless the fork point has an explicit override.
        strand_start_dir = (
            fork_directions[j] if fork_directions[j] is not None else spine_flow_angle_deg
        )
        _chord_e = math.hypot(ends[j][0] - spine_end[0], ends[j][1] - spine_end[1])
        strand_tangent_mag_e = _chord_e * tangent_mult_end
        strand = _calc_single_strand(
            spine_end,
            ends[j],
            shape,
            chamfer,
            samples,
            margin,
            head_len,
            head_half_h,
            arrow=arrow,
            controls=all_controls if all_controls else None,
            standoff=standoff,
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


def main():
    parser = argparse.ArgumentParser(
        description=_CONNECTOR_DESCRIPTION,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=["straight", "l", "l-chamfer", "spline", "manifold"],
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
        choices=["straight", "l", "l-chamfer", "spline"],
        default="l-chamfer",
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
        src_x, src_y = _parse_point(args.src)
        tgt_x, tgt_y = _parse_point(args.tgt)
        straight_standoff = _parse_standoff(args.standoff) if args.standoff else None

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
                    standoff=straight_standoff,
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
            )
            print_result(c, args)
        return

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
        )
        print_manifold_result(result, args)
        return

    controls = _parse_point_list(args.controls) if args.controls else None
    standoff = _parse_standoff(args.standoff) if args.standoff else None

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
            controls=controls,
            standoff=standoff,
        )
    else:
        if args.src is None or args.tgt is None:
            parser.error(f"--from and --to are required in {args.mode} mode")
        src_x, src_y = _parse_point(args.src)
        tgt_x, tgt_y = _parse_point(args.tgt)
        if args.mode == "l":
            result = calc_l(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                controls=controls,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
                standoff=standoff,
            )
        else:  # l-chamfer
            result = calc_l_chamfer(
                src_x,
                src_y,
                tgt_x,
                tgt_y,
                controls=controls,
                chamfer=args.chamfer,
                margin=args.margin,
                head_len=head_len,
                head_half_h=head_half_h,
                arrow=args.arrow,
                standoff=standoff,
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
        raise ValueError(f"--waypoints must contain >= 2 pairs of numbers, got {len(out)} numbers")
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
