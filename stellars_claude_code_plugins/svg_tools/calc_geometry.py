#!/usr/bin/env python3
"""
SVG geometry constraint and attachment-point calculator.

Inspired by Fusion 360 sketch constraints. Computes the points and angles
Claude needs when authoring SVG infographics: midpoints, line extensions,
perpendicular projections, tangent points, intersections, evenly spaced
positions on a circle, concentric rings, and edge-snap attachment points
on rectangles and circles.

Typical workflows:

    # Where on card A's right edge should I attach a connector?
    svg-infographics geom attach --rect 20,40,150,80 --side right --pos mid

    # Tangent points from an external point to a hub circle
    svg-infographics geom tangent --circle 400,200,50 --from 100,100

    # 8 nodes evenly distributed around a hub
    svg-infographics geom evenly-spaced --center 400,200 --r 120 --count 8

    # Concentric rings for a radial diagram
    svg-infographics geom concentric --center 400,200 --radii 60,90,120,150

    # Where do two flow lines intersect?
    svg-infographics geom intersect-lines --line1 0,0,200,200 --line2 0,200,200,0

Every subcommand prints the computed point(s) plus a small SVG snippet
that visualises the result so you can paste it into your file to verify.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math

EPS = 1e-9


@dataclass(frozen=True)
class Point:
    """A 2D point in SVG coordinate space (Y grows downward)."""

    x: float
    y: float

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return f"({self.x:.2f}, {self.y:.2f})"


# ---------------------------------------------------------------------------
# Parse helpers
# ---------------------------------------------------------------------------


def _parse_point(text: str) -> Point:
    """Parse 'x,y' into a Point."""
    parts = text.replace(" ", "").split(",")
    if len(parts) != 2:
        raise ValueError(f"Expected 'x,y', got {text!r}")
    return Point(float(parts[0]), float(parts[1]))


def _parse_line(text: str) -> tuple[Point, Point]:
    """Parse 'x1,y1,x2,y2' into two Points."""
    parts = text.replace(" ", "").split(",")
    if len(parts) != 4:
        raise ValueError(f"Expected 'x1,y1,x2,y2', got {text!r}")
    nums = [float(p) for p in parts]
    return Point(nums[0], nums[1]), Point(nums[2], nums[3])


def _parse_circle(text: str) -> tuple[Point, float]:
    """Parse 'cx,cy,r' into (center Point, radius)."""
    parts = text.replace(" ", "").split(",")
    if len(parts) != 3:
        raise ValueError(f"Expected 'cx,cy,r', got {text!r}")
    return Point(float(parts[0]), float(parts[1])), float(parts[2])


def _parse_rect(text: str) -> tuple[float, float, float, float]:
    """Parse 'x,y,w,h' into a rect tuple."""
    parts = text.replace(" ", "").split(",")
    if len(parts) != 4:
        raise ValueError(f"Expected 'x,y,w,h', got {text!r}")
    return tuple(float(p) for p in parts)


def _parse_floats(text: str) -> list[float]:
    """Parse a string of floats separated by spaces and/or commas."""
    return [float(tok) for tok in text.replace(",", " ").split() if tok]


# ---------------------------------------------------------------------------
# Point and line operations
# ---------------------------------------------------------------------------


def midpoint(p1: Point, p2: Point) -> Point:
    """Midpoint of two points."""
    return Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2)


def shape_midpoint(points: list[Point]) -> tuple[Point, float]:
    """Geometric midpoint (centroid) of a closed shape defined by its vertices.

    Uses the area-weighted centroid formula for a simple polygon:
        Cx = (1/6A) * sum((x_i + x_i+1) * cross_i)
        Cy = (1/6A) * sum((y_i + y_i+1) * cross_i)
        A  = 0.5 * sum(cross_i)
        cross_i = x_i * y_i+1 - x_i+1 * y_i

    Returns (centroid, signed_area). For degenerate cases (zero area) it
    falls back to the arithmetic mean of the vertices. Use this to find
    the visual centre of any closed shape - rectangles, polygons, stars,
    hexagons, etc. - so a connector can point at the centre, or a label
    can be placed there.

    REMINDER: connectors should terminate at EDGE midpoints. Use this
    centroid function for label placement or for inside-shape annotations,
    NOT as a connector endpoint.
    """
    n = len(points)
    if n < 2:
        raise ValueError("shape_midpoint needs at least 2 points")
    if n == 2:
        return (midpoint(points[0], points[1]), 0.0)

    # Close the polygon implicitly by wrapping indices
    cx_accum = 0.0
    cy_accum = 0.0
    area_accum = 0.0
    for i in range(n):
        p = points[i]
        q = points[(i + 1) % n]
        cross = p.x * q.y - q.x * p.y
        area_accum += cross
        cx_accum += (p.x + q.x) * cross
        cy_accum += (p.y + q.y) * cross
    area = area_accum / 2
    if abs(area) < EPS:
        # Degenerate (collinear) - fall back to arithmetic mean
        mx = sum(p.x for p in points) / n
        my = sum(p.y for p in points) / n
        return (Point(mx, my), 0.0)
    cx = cx_accum / (6 * area)
    cy = cy_accum / (6 * area)
    return (Point(cx, cy), area)


def curve_midpoint(points: list[Point]) -> tuple[Point, tuple[float, float], float]:
    """Midpoint of a polyline by arc length.

    Walks along the polyline accumulating segment lengths, finds the sample
    at half of the total arc length, and returns:

      - the exact interpolated midpoint (Point on the segment containing t=0.5)
      - the unit tangent vector at that point (dx, dy)
      - the total arc length of the polyline

    This is the precise incident point for placing a label, annotation, or
    junction at the "middle" of a curved connector. Works for any polyline
    (straight-through L-chamfer corners, spline samples, Bezier samples)
    because it operates on cumulative chord lengths - no curve-type knowledge
    needed. Callers who want a Bezier midpoint can pass in the sampled
    polyline from `calc_connector`/`calc_spline`.

    REMINDER: connectors should terminate at edge MIDPOINTS of shapes. Use
    `geom attach --shape rect --side right --pos mid` to compute edge
    midpoints, and use `curve_midpoint` to find the midpoint of a connector
    path (e.g. for placing a label on it).
    """
    if len(points) < 2:
        raise ValueError("curve_midpoint needs at least 2 points")

    # Cumulative arc length at each vertex
    cum = [0.0]
    for i in range(1, len(points)):
        cum.append(cum[-1] + distance(points[i - 1], points[i]))
    total = cum[-1]
    if total == 0:
        return (points[0], (1.0, 0.0), 0.0)

    target = total / 2
    # Find segment containing the midpoint
    for i in range(1, len(points)):
        if cum[i] >= target:
            seg_start = cum[i - 1]
            seg_len = cum[i] - cum[i - 1]
            if seg_len == 0:
                continue
            t = (target - seg_start) / seg_len
            mid = lerp(points[i - 1], points[i], t)
            ux, uy = line_unit_vector(points[i - 1], points[i])
            return (mid, (ux, uy), total)

    # Shouldn't reach here
    return (points[-1], (1.0, 0.0), total)


def distance(p1: Point, p2: Point) -> float:
    """Euclidean distance between two points."""
    return math.hypot(p2.x - p1.x, p2.y - p1.y)


def lerp(p1: Point, p2: Point, t: float) -> Point:
    """Linear interpolation between two points at parameter t in [0, 1]."""
    return Point(p1.x + (p2.x - p1.x) * t, p1.y + (p2.y - p1.y) * t)


def line_unit_vector(p1: Point, p2: Point) -> tuple[float, float]:
    """Unit vector pointing from p1 to p2. Raises if points coincide."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    length = math.hypot(dx, dy)
    if length < EPS:
        raise ValueError("Cannot get unit vector for coincident points")
    return (dx / length, dy / length)


def extend_line(p1: Point, p2: Point, by: float, end: str = "end") -> Point:
    """Extend the line segment p1->p2 by `by` pixels past one of its ends.

    end="end" returns p2 + by * unit(p1 -> p2).
    end="start" returns p1 - by * unit(p1 -> p2).
    """
    ux, uy = line_unit_vector(p1, p2)
    if end == "end":
        return Point(p2.x + by * ux, p2.y + by * uy)
    if end == "start":
        return Point(p1.x - by * ux, p1.y - by * uy)
    raise ValueError(f"end must be 'start' or 'end', got {end!r}")


def perpendicular_foot(p: Point, line_p1: Point, line_p2: Point) -> Point:
    """Project point p onto the infinite line through line_p1 and line_p2."""
    dx = line_p2.x - line_p1.x
    dy = line_p2.y - line_p1.y
    denom = dx * dx + dy * dy
    if denom < EPS:
        return line_p1
    t = ((p.x - line_p1.x) * dx + (p.y - line_p1.y) * dy) / denom
    return Point(line_p1.x + t * dx, line_p1.y + t * dy)


def parallel_line_through(line_p1: Point, line_p2: Point, through: Point) -> tuple[Point, Point]:
    """Return two points defining a line parallel to line_p1->line_p2 through `through`."""
    dx = line_p2.x - line_p1.x
    dy = line_p2.y - line_p1.y
    return through, Point(through.x + dx, through.y + dy)


def perpendicular_line_through(
    line_p1: Point, line_p2: Point, through: Point
) -> tuple[Point, Point]:
    """Return two points defining a line perpendicular to line_p1->line_p2 through `through`."""
    dx = line_p2.x - line_p1.x
    dy = line_p2.y - line_p1.y
    # Perpendicular vector (rotate 90 degrees)
    return through, Point(through.x - dy, through.y + dx)


def bisector_direction(p1: Point, vertex: Point, p2: Point) -> tuple[float, float]:
    """Unit vector along the angle bisector at `vertex` between rays vertex->p1 and vertex->p2."""
    u1x, u1y = line_unit_vector(vertex, p1)
    u2x, u2y = line_unit_vector(vertex, p2)
    bx = u1x + u2x
    by = u1y + u2y
    length = math.hypot(bx, by)
    if length < EPS:
        # Anti-parallel rays - bisector is perpendicular
        return (-u1y, u1x)
    return (bx / length, by / length)


# ---------------------------------------------------------------------------
# Intersections
# ---------------------------------------------------------------------------


def intersect_lines(p1: Point, p2: Point, p3: Point, p4: Point) -> Point | None:
    """Intersection point of two infinite lines, or None if parallel."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3
    x4, y4 = p4

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < EPS:
        return None

    t_num = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
    t = t_num / denom
    return Point(x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def intersect_line_circle(p1: Point, p2: Point, center: Point, radius: float) -> list[Point]:
    """Intersection points of an infinite line with a circle (0, 1, or 2 points)."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y
    fx = p1.x - center.x
    fy = p1.y - center.y

    a = dx * dx + dy * dy
    b = 2 * (fx * dx + fy * dy)
    c = fx * fx + fy * fy - radius * radius
    disc = b * b - 4 * a * c

    if disc < -EPS:
        return []
    if abs(disc) < EPS:
        t = -b / (2 * a)
        return [Point(p1.x + t * dx, p1.y + t * dy)]

    sq = math.sqrt(disc)
    t1 = (-b + sq) / (2 * a)
    t2 = (-b - sq) / (2 * a)
    return [
        Point(p1.x + t1 * dx, p1.y + t1 * dy),
        Point(p1.x + t2 * dx, p1.y + t2 * dy),
    ]


def intersect_circles(c1: Point, r1: float, c2: Point, r2: float) -> list[Point]:
    """Intersection points of two circles (0, 1, or 2 points)."""
    dx = c2.x - c1.x
    dy = c2.y - c1.y
    d = math.hypot(dx, dy)

    if d < EPS:
        return []  # concentric
    if d > r1 + r2 + EPS or d < abs(r1 - r2) - EPS:
        return []  # separate or one inside the other

    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
    h_sq = r1 * r1 - a * a
    if h_sq < 0:
        h_sq = 0
    h = math.sqrt(h_sq)

    px = c1.x + a * dx / d
    py = c1.y + a * dy / d

    if h < EPS:
        return [Point(px, py)]

    rx = -dy * (h / d)
    ry = dx * (h / d)
    return [
        Point(px + rx, py + ry),
        Point(px - rx, py - ry),
    ]


# ---------------------------------------------------------------------------
# Tangents
# ---------------------------------------------------------------------------


def tangent_points_from_external(external: Point, center: Point, radius: float) -> list[Point]:
    """Two tangent points where lines from `external` touch the circle.

    Uses the geometric construction: the tangent points lie on the circle
    of radius `sqrt(d^2 - r^2)` centered at `external` intersected with
    the original circle.
    """
    d = distance(external, center)
    if d < radius - EPS:
        return []  # external point is inside circle
    if abs(d - radius) < EPS:
        return [external]  # external point is on circle

    # Distance from external point to either tangent point
    tangent_len = math.sqrt(d * d - radius * radius)
    return intersect_circles(external, tangent_len, center, radius)


def tangent_lines_two_circles(
    c1: Point, r1: float, c2: Point, r2: float, kind: str = "external"
) -> list[tuple[Point, Point]]:
    """Tangent line segments between two circles.

    kind="external" returns the two outer tangents (lines that don't cross
    between the circles). kind="internal" returns the two inner tangents
    (which cross between them) - only exist when the circles are separate.

    Each result is a (point_on_c1, point_on_c2) pair.
    """
    d = distance(c1, c2)
    if d < EPS:
        return []

    results = []
    if kind == "external":
        # External tangents exist whenever circles are not contained
        if d < abs(r1 - r2) - EPS:
            return []
        # Construction: shrink c2 by r1 (so r2' = r2 - r1 if r2>=r1, else swap)
        # Easier: use angle method
        if abs(r1 - r2) < EPS:
            # Same radius - tangents are parallel to the center line, offset by r
            ux = (c2.x - c1.x) / d
            uy = (c2.y - c1.y) / d
            nx, ny = -uy, ux
            results.append(
                (Point(c1.x + r1 * nx, c1.y + r1 * ny), Point(c2.x + r2 * nx, c2.y + r2 * ny))
            )
            results.append(
                (Point(c1.x - r1 * nx, c1.y - r1 * ny), Point(c2.x - r2 * nx, c2.y - r2 * ny))
            )
            return results

        # Different radii: external tangents meet at the external center of similitude
        ratio = r1 / (r1 - r2)
        ex = c1.x + (c2.x - c1.x) * ratio
        ey = c1.y + (c2.y - c1.y) * ratio
        ext = Point(ex, ey)
        t1 = tangent_points_from_external(ext, c1, r1)
        t2 = tangent_points_from_external(ext, c2, r2)
        if len(t1) == 2 and len(t2) == 2:
            # Pair them by side: dot product of (t-c) vectors should match
            for tp1 in t1:
                best = min(
                    t2,
                    key=lambda tp2: (
                        ((tp1.x - c1.x) * (tp2.x - c2.x) + (tp1.y - c1.y) * (tp2.y - c2.y)) * -1
                    ),
                )
                results.append((tp1, best))
        return results

    if kind == "internal":
        if d < r1 + r2 - EPS:
            return []  # circles overlap, no internal tangents
        # Internal center of similitude
        ratio = r1 / (r1 + r2)
        ix = c1.x + (c2.x - c1.x) * ratio
        iy = c1.y + (c2.y - c1.y) * ratio
        internal = Point(ix, iy)
        t1 = tangent_points_from_external(internal, c1, r1)
        t2 = tangent_points_from_external(internal, c2, r2)
        if len(t1) == 2 and len(t2) == 2:
            for tp1 in t1:
                best = min(
                    t2,
                    key=lambda tp2: (
                        (tp1.x - c1.x) * (tp2.x - c2.x) + (tp1.y - c1.y) * (tp2.y - c2.y)
                    ),
                )
                results.append((tp1, best))
        return results

    raise ValueError(f"kind must be 'external' or 'internal', got {kind!r}")


# ---------------------------------------------------------------------------
# Polar and circle layout
# ---------------------------------------------------------------------------


def polar_to_cartesian(center: Point, r: float, angle_deg: float) -> Point:
    """Polar coordinates to SVG cartesian. Angle 0 = right, 90 = down (SVG Y-down)."""
    a = math.radians(angle_deg)
    return Point(center.x + r * math.cos(a), center.y + r * math.sin(a))


def evenly_spaced_on_circle(
    center: Point, r: float, count: int, start_angle_deg: float = 0
) -> list[Point]:
    """N points evenly distributed around a circle."""
    if count <= 0:
        return []
    return [polar_to_cartesian(center, r, start_angle_deg + 360 * i / count) for i in range(count)]


def concentric_circles(center: Point, radii: list[float]) -> list[tuple[Point, float]]:
    """Return (center, radius) pairs for each requested radius."""
    return [(center, r) for r in radii]


# ---------------------------------------------------------------------------
# Attachment points (snap to shape edge)
# ---------------------------------------------------------------------------


def rect_attachment(x: float, y: float, w: float, h: float, side: str, pos: str = "mid") -> Point:
    """Snap point on one edge of a rectangle.

    side: 'top' | 'right' | 'bottom' | 'left'
    pos:  'start' | 'mid' | 'end' (start = top-left along reading direction)
    """
    edge = {
        "top": ((x, y), (x + w, y)),
        "right": ((x + w, y), (x + w, y + h)),
        "bottom": ((x, y + h), (x + w, y + h)),
        "left": ((x, y), (x, y + h)),
    }
    if side not in edge:
        raise ValueError(f"side must be top/right/bottom/left, got {side!r}")

    p1 = Point(*edge[side][0])
    p2 = Point(*edge[side][1])
    if pos == "start":
        return p1
    if pos == "end":
        return p2
    if pos == "mid":
        return midpoint(p1, p2)
    raise ValueError(f"pos must be start/mid/end, got {pos!r}")


def rect_corner(x: float, y: float, w: float, h: float, corner: str) -> Point:
    """Corner of a rectangle. corner in {tl, tr, bl, br}."""
    corners = {
        "tl": Point(x, y),
        "tr": Point(x + w, y),
        "bl": Point(x, y + h),
        "br": Point(x + w, y + h),
    }
    if corner not in corners:
        raise ValueError(f"corner must be tl/tr/bl/br, got {corner!r}")
    return corners[corner]


def rect_center(x: float, y: float, w: float, h: float) -> Point:
    """Center of a rectangle."""
    return Point(x + w / 2, y + h / 2)


def circle_perimeter(center: Point, r: float, angle_deg: float) -> Point:
    """Point on the perimeter of a circle at angle (degrees, SVG convention)."""
    return polar_to_cartesian(center, r, angle_deg)


# ---------------------------------------------------------------------------
# Offset geometry (parallel curves at fixed standoff distance)
# ---------------------------------------------------------------------------
#
# "Offset" preserves a shape's geometry but moves it perpendicular to itself
# by a fixed distance. Useful when a label needs a standoff from a connector,
# a card needs a halo, two parallel rails need to share a route, or a polygon
# needs to be deflated/inflated for hit-testing.
#
# Side convention: "left" means visually-left when walking along the line in
# SVG screen space (where Y grows downward). "right" means visually-right.
# Internally, left perpendicular of unit (dx, dy) is (dy, -dx).


def perpendicular_normal(p1: Point, p2: Point, side: str = "left") -> tuple[float, float]:
    """Unit vector perpendicular to p1->p2, on the chosen visual side."""
    ux, uy = line_unit_vector(p1, p2)
    if side == "left":
        return (uy, -ux)
    if side == "right":
        return (-uy, ux)
    raise ValueError(f"side must be 'left' or 'right', got {side!r}")


def offset_point_from_line(
    p1: Point, p2: Point, t: float, distance: float, side: str = "left"
) -> Point:
    """Point at parameter t along p1->p2, then shifted distance px to one side.

    Useful for placing labels at a standoff from an existing connector:
    pick t (0 = start, 0.5 = mid, 1 = end) and a perpendicular distance.
    """
    base = lerp(p1, p2, t)
    nx, ny = perpendicular_normal(p1, p2, side)
    return Point(base.x + nx * distance, base.y + ny * distance)


def offset_line(p1: Point, p2: Point, distance: float, side: str = "left") -> tuple[Point, Point]:
    """Parallel line at perpendicular distance from p1->p2."""
    nx, ny = perpendicular_normal(p1, p2, side)
    dx, dy = nx * distance, ny * distance
    return Point(p1.x + dx, p1.y + dy), Point(p2.x + dx, p2.y + dy)


def offset_polyline(points: list[Point], distance: float, side: str = "left") -> list[Point]:
    """Parallel polyline at perpendicular distance from the original.

    For each interior vertex, the new vertex is the intersection of the two
    adjacent offset edges (miter join). For collinear segments the vertex
    is just the offset endpoint of the incoming edge. Endpoints are offset
    perpendicular to their adjacent edge.

    No miter limiting is applied; very sharp corners can produce vertices
    far from the original. Subdivide such corners in the input if needed.
    """
    n = len(points)
    if n < 2:
        return list(points)

    # Pre-compute offset edge endpoints for each segment
    offset_edges: list[tuple[Point, Point]] = []
    for i in range(n - 1):
        a, b = offset_line(points[i], points[i + 1], distance, side)
        offset_edges.append((a, b))

    result: list[Point] = []
    # First endpoint = offset of edge[0] start
    result.append(offset_edges[0][0])

    # Interior vertices: intersect adjacent offset edges
    for i in range(1, n - 1):
        edge_in_a, edge_in_b = offset_edges[i - 1]
        edge_out_a, edge_out_b = offset_edges[i]
        meeting = intersect_lines(edge_in_a, edge_in_b, edge_out_a, edge_out_b)
        if meeting is None:
            # Collinear adjacent segments - use the endpoint
            result.append(edge_in_b)
        else:
            result.append(meeting)

    # Last endpoint = offset of edge[-1] end
    result.append(offset_edges[-1][1])
    return result


def offset_rect(
    x: float, y: float, w: float, h: float, by: float
) -> tuple[float, float, float, float] | None:
    """Inflate (positive) or deflate (negative) a rect uniformly on all sides.

    Returns None if a negative offset would collapse the rect. Useful for
    halos around cards (positive) or hit-test shrinking (negative).
    """
    new_w = w + 2 * by
    new_h = h + 2 * by
    if new_w <= 0 or new_h <= 0:
        return None
    return (x - by, y - by, new_w, new_h)


def offset_circle(center: Point, r: float, by: float) -> tuple[Point, float] | None:
    """Inflate or deflate a circle by `by` pixels (radius change). Center stays fixed."""
    new_r = r + by
    if new_r <= 0:
        return None
    return (center, new_r)


def offset_polygon(
    points: list[Point], distance: float, direction: str = "outward"
) -> list[Point]:
    """Offset a closed polygon inward or outward.

    direction="outward" inflates the polygon, "inward" deflates it. Uses the
    same miter-intersect approach as offset_polyline. Assumes the polygon is
    given in clockwise order in SVG screen space (Y-down); for counter-clockwise
    polygons swap the side automatically.
    """
    n = len(points)
    if n < 3:
        return list(points)

    # Determine winding via signed area (SVG Y-down: negative = clockwise visually)
    area = 0.0
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        area += (b.x - a.x) * (b.y + a.y)
    is_clockwise = area > 0

    # Outward = "right" of clockwise traversal in SVG screen space
    if direction == "outward":
        side = "right" if is_clockwise else "left"
    elif direction == "inward":
        side = "left" if is_clockwise else "right"
    else:
        raise ValueError(f"direction must be 'outward' or 'inward', got {direction!r}")

    # Build offset edges around the closed loop
    offset_edges: list[tuple[Point, Point]] = []
    for i in range(n):
        a = points[i]
        b = points[(i + 1) % n]
        offset_edges.append(offset_line(a, b, distance, side))

    result: list[Point] = []
    for i in range(n):
        edge_in = offset_edges[(i - 1) % n]
        edge_out = offset_edges[i]
        meeting = intersect_lines(edge_in[0], edge_in[1], edge_out[0], edge_out[1])
        if meeting is None:
            result.append(edge_out[0])
        else:
            result.append(meeting)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_point(label: str, p: Point):
    print(f"{label}: ({p.x:.2f}, {p.y:.2f})")


def _svg_point(p: Point, color: str = "#5456f3", r: float = 3) -> str:
    return f'<circle cx="{p.x:.2f}" cy="{p.y:.2f}" r="{r}" fill="{color}"/>'


def _svg_line(p1: Point, p2: Point, color: str = "#5456f3", width: float = 1) -> str:
    return (
        f'<line x1="{p1.x:.2f}" y1="{p1.y:.2f}" '
        f'x2="{p2.x:.2f}" y2="{p2.y:.2f}" '
        f'stroke="{color}" stroke-width="{width}"/>'
    )


def _svg_circle(
    c: Point, r: float, color: str = "#5456f3", fill: str = "none", width: float = 1
) -> str:
    return (
        f'<circle cx="{c.x:.2f}" cy="{c.y:.2f}" r="{r:.2f}" '
        f'fill="{fill}" stroke="{color}" stroke-width="{width}"/>'
    )


# ---------------------------------------------------------------------------
# Alignment and distribution (multi-geometry operations)
# ---------------------------------------------------------------------------


def _parse_rects(text: str) -> list[tuple[float, float, float, float]]:
    """Parse a list of rects: '[(x,y,w,h),(x,y,w,h),...]' or 'x,y,w,h x,y,w,h ...'."""
    import ast

    text = text.strip()
    if text.startswith("["):
        items = ast.literal_eval(text)
        return [(float(r[0]), float(r[1]), float(r[2]), float(r[3])) for r in items]
    rects = []
    for chunk in text.split():
        parts = [float(v) for v in chunk.split(",")]
        rects.append((parts[0], parts[1], parts[2], parts[3]))
    return rects


def align(rects: list[tuple], edge: str) -> list[tuple]:
    """Align rects along a shared edge or centre line.

    edge: 'left', 'right', 'top', 'bottom', 'h-center', 'v-center'.
    Returns new (x, y, w, h) tuples with positions adjusted. Sizes unchanged.
    """
    if not rects:
        return []
    if edge == "left":
        target = min(r[0] for r in rects)
        return [(target, r[1], r[2], r[3]) for r in rects]
    if edge == "right":
        target = max(r[0] + r[2] for r in rects)
        return [(target - r[2], r[1], r[2], r[3]) for r in rects]
    if edge == "top":
        target = min(r[1] for r in rects)
        return [(r[0], target, r[2], r[3]) for r in rects]
    if edge == "bottom":
        target = max(r[1] + r[3] for r in rects)
        return [(r[0], target - r[3], r[2], r[3]) for r in rects]
    if edge == "h-center":
        target = sum(r[0] + r[2] / 2 for r in rects) / len(rects)
        return [(target - r[2] / 2, r[1], r[2], r[3]) for r in rects]
    if edge == "v-center":
        target = sum(r[1] + r[3] / 2 for r in rects) / len(rects)
        return [(r[0], target - r[3] / 2, r[2], r[3]) for r in rects]
    raise ValueError(f"edge must be left|right|top|bottom|h-center|v-center, got {edge!r}")


def distribute(rects: list[tuple], axis: str, mode: str = "center") -> list[tuple]:
    """Space rects evenly along an axis.

    axis: 'h' (horizontal) or 'v' (vertical).
    mode: 'center' (equal centroid spacing), 'gap' (equal gaps between edges).
    Returns new (x, y, w, h) tuples with positions adjusted. Sizes unchanged.
    Rects sorted by current position along the axis before distributing.
    """
    if len(rects) < 3:
        return list(rects)  # need >=3 to distribute

    if axis == "h":
        indexed = sorted(enumerate(rects), key=lambda ir: ir[1][0])
    else:
        indexed = sorted(enumerate(rects), key=lambda ir: ir[1][1])

    result = [None] * len(rects)

    if mode == "center":
        if axis == "h":
            centers = [r[0] + r[2] / 2 for _, r in indexed]
            start, end = centers[0], centers[-1]
            step = (end - start) / (len(indexed) - 1)
            for k, (orig_i, r) in enumerate(indexed):
                new_cx = start + k * step
                result[orig_i] = (new_cx - r[2] / 2, r[1], r[2], r[3])
        else:
            centers = [r[1] + r[3] / 2 for _, r in indexed]
            start, end = centers[0], centers[-1]
            step = (end - start) / (len(indexed) - 1)
            for k, (orig_i, r) in enumerate(indexed):
                new_cy = start + k * step
                result[orig_i] = (r[0], new_cy - r[3] / 2, r[2], r[3])
    elif mode == "gap":
        if axis == "h":
            total_width = sum(r[2] for _, r in indexed)
            first_left = indexed[0][1][0]
            last_right = indexed[-1][1][0] + indexed[-1][1][2]
            total_space = last_right - first_left - total_width
            gap = total_space / (len(indexed) - 1) if len(indexed) > 1 else 0
            cursor = first_left
            for orig_i, r in indexed:
                result[orig_i] = (cursor, r[1], r[2], r[3])
                cursor += r[2] + gap
        else:
            total_height = sum(r[3] for _, r in indexed)
            first_top = indexed[0][1][1]
            last_bottom = indexed[-1][1][1] + indexed[-1][1][3]
            total_space = last_bottom - first_top - total_height
            gap = total_space / (len(indexed) - 1) if len(indexed) > 1 else 0
            cursor = first_top
            for orig_i, r in indexed:
                result[orig_i] = (r[0], cursor, r[2], r[3])
                cursor += r[3] + gap
    else:
        raise ValueError(f"mode must be 'center' or 'gap', got {mode!r}")

    return result


def stack(rects: list[tuple], axis: str, gap: float = 10.0, anchor: str = "start") -> list[tuple]:
    """Stack rects sequentially along an axis with a fixed gap.

    axis: 'h' (left-to-right) or 'v' (top-to-bottom).
    gap: pixels between adjacent edges.
    anchor: 'start' (first rect stays, others follow) or 'center' (centre the stack).
    Returns new (x, y, w, h) tuples.
    """
    if not rects:
        return []

    if axis == "h":
        if anchor == "center":
            total = sum(r[2] for r in rects) + gap * (len(rects) - 1)
            cx = sum(r[0] + r[2] / 2 for r in rects) / len(rects)
            cursor = cx - total / 2
        else:
            cursor = rects[0][0]
        new = []
        for r in rects:
            new.append((cursor, r[1], r[2], r[3]))
            cursor += r[2] + gap
        return new
    elif axis == "v":
        if anchor == "center":
            total = sum(r[3] for r in rects) + gap * (len(rects) - 1)
            cy = sum(r[1] + r[3] / 2 for r in rects) / len(rects)
            cursor = cy - total / 2
        else:
            cursor = rects[0][1]
        new = []
        for r in rects:
            new.append((r[0], cursor, r[2], r[3]))
            cursor += r[3] + gap
        return new
    raise ValueError(f"axis must be 'h' or 'v', got {axis!r}")


def cmd_align(args):
    rects = _parse_rects(args.rects)
    result = align(rects, args.edge)
    import json

    print(json.dumps({"aligned": [list(r) for r in result], "edge": args.edge}))


def cmd_distribute(args):
    rects = _parse_rects(args.rects)
    result = distribute(rects, args.axis, args.mode)
    import json

    print(
        json.dumps(
            {"distributed": [list(r) for r in result], "axis": args.axis, "mode": args.mode}
        )
    )


def cmd_stack(args):
    rects = _parse_rects(args.rects)
    result = stack(rects, args.axis, args.gap, args.anchor)
    import json

    print(json.dumps({"stacked": [list(r) for r in result], "axis": args.axis, "gap": args.gap}))


# ---------------------------------------------------------------------------
# CLI command implementations (point/line/circle operations)
# ---------------------------------------------------------------------------


def cmd_midpoint(args):
    p1 = _parse_point(args.p1)
    p2 = _parse_point(args.p2)
    m = midpoint(p1, p2)
    _print_point("Midpoint", m)
    print(f"Distance:  {distance(p1, p2):.2f}")
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_point(m, "#5456f3", 3))


def cmd_curve_midpoint(args):
    """Arc-length midpoint of a polyline (open curve). Use for label
    placement or for finding the precise midpoint incident on a connector."""
    import ast as _ast

    if not args.points:
        raise SystemExit("curve-midpoint requires --points [(x,y),(x,y),...]")
    raw = _ast.literal_eval(args.points)
    pts = [Point(float(p[0]), float(p[1])) for p in raw]
    mid, tangent, total = curve_midpoint(pts)
    _print_point("Midpoint", mid)
    print(f"Tangent:   ({tangent[0]:.4f}, {tangent[1]:.4f})")
    print(f"Angle:     {math.degrees(math.atan2(tangent[1], tangent[0])):.1f} deg")
    print(f"Total arc: {total:.2f} px")
    print("\n--- SVG ---")
    d = "M" + " L".join(f"{p.x},{p.y}" for p in pts)
    print(f'<path d="{d}" stroke="#999" fill="none" stroke-width="0.5"/>')
    print(_svg_point(mid, "#5456f3", 3))


def cmd_shape_midpoint(args):
    """Centroid of a closed shape polygon. Use when a connector's source
    or target is a closed shape (any polygon, not just a rect) and you
    need the centre to compute a connect-from-centre direction."""
    import ast as _ast

    if not args.points:
        raise SystemExit("shape-midpoint requires --points [(x,y),(x,y),...]")
    raw = _ast.literal_eval(args.points)
    pts = [Point(float(p[0]), float(p[1])) for p in raw]
    centroid, area = shape_midpoint(pts)
    _print_point("Centroid", centroid)
    print(f"Signed area: {area:.2f} px^2")
    print("\n--- SVG ---")
    d = "M" + " L".join(f"{p.x},{p.y}" for p in pts) + " Z"
    print(f'<path d="{d}" stroke="#999" fill="#5456f3" fill-opacity="0.1" stroke-width="0.5"/>')
    print(_svg_point(centroid, "#5456f3", 3))


def cmd_extend(args):
    p1, p2 = _parse_line(args.line)
    new_end = extend_line(p1, p2, args.by, args.end)
    _print_point("Original start", p1)
    _print_point("Original end  ", p2)
    _print_point(f"Extended {args.end} by {args.by}", new_end)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    if args.end == "end":
        print(_svg_line(p2, new_end, "#5456f3", 1.5))
    else:
        print(_svg_line(p1, new_end, "#5456f3", 1.5))


def cmd_at(args):
    p1, p2 = _parse_line(args.line)
    p = lerp(p1, p2, args.t)
    _print_point(f"Point at t={args.t}", p)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_point(p, "#5456f3", 3))


def cmd_perpendicular(args):
    p = _parse_point(args.point)
    p1, p2 = _parse_line(args.line)
    foot = perpendicular_foot(p, p1, p2)
    _print_point("Foot", foot)
    print(f"Distance:  {distance(p, foot):.2f}")
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_line(p, foot, "#5456f3", 1))
    print(_svg_point(foot, "#5456f3", 3))


def cmd_parallel(args):
    p1, p2 = _parse_line(args.line)
    through = _parse_point(args.through)
    a, b = parallel_line_through(p1, p2, through)
    _print_point("Through point", a)
    _print_point("Parallel direction point", b)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_line(a, b, "#5456f3", 1.2))


def cmd_perpendicular_line(args):
    p1, p2 = _parse_line(args.line)
    through = _parse_point(args.through)
    a, b = perpendicular_line_through(p1, p2, through)
    _print_point("Through point", a)
    _print_point("Perpendicular direction point", b)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_line(a, b, "#5456f3", 1.2))


def cmd_tangent(args):
    center, r = _parse_circle(args.circle)
    ext = _parse_point(getattr(args, "from"))
    points = tangent_points_from_external(ext, center, r)
    if not points:
        print(
            f"No tangent: external point is inside circle (d={distance(ext, center):.2f}, r={r:.2f})"
        )
        return
    if len(points) == 1:
        print("External point lies on circle - single tangent point")
        _print_point("Tangent point", points[0])
    else:
        _print_point("Tangent point 1", points[0])
        _print_point("Tangent point 2", points[1])
    print("\n--- SVG ---")
    print(_svg_circle(center, r, "#999", "none", 0.5))
    print(_svg_point(ext, "#999", 3))
    for tp in points:
        print(_svg_line(ext, tp, "#5456f3", 1))
        print(_svg_point(tp, "#5456f3", 3))


def cmd_tangent_circles(args):
    c1, r1 = _parse_circle(args.c1)
    c2, r2 = _parse_circle(args.c2)
    pairs = tangent_lines_two_circles(c1, r1, c2, r2, kind=args.kind)
    if not pairs:
        print(f"No {args.kind} tangents exist for these circles")
        return
    for i, (a, b) in enumerate(pairs, 1):
        print(f"Tangent {i}:")
        _print_point("  on c1", a)
        _print_point("  on c2", b)
    print("\n--- SVG ---")
    print(_svg_circle(c1, r1, "#999", "none", 0.5))
    print(_svg_circle(c2, r2, "#999", "none", 0.5))
    for a, b in pairs:
        print(_svg_line(a, b, "#5456f3", 1))
        print(_svg_point(a, "#5456f3", 2))
        print(_svg_point(b, "#5456f3", 2))


def cmd_intersect_lines(args):
    p1, p2 = _parse_line(args.line1)
    p3, p4 = _parse_line(args.line2)
    pt = intersect_lines(p1, p2, p3, p4)
    if pt is None:
        print("Lines are parallel - no intersection")
        return
    _print_point("Intersection", pt)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_line(p3, p4, "#999", 0.5))
    print(_svg_point(pt, "#5456f3", 3))


def cmd_intersect_line_circle(args):
    p1, p2 = _parse_line(args.line)
    center, r = _parse_circle(args.circle)
    pts = intersect_line_circle(p1, p2, center, r)
    if not pts:
        print("Line does not intersect circle")
        return
    for i, pt in enumerate(pts, 1):
        _print_point(f"Intersection {i}", pt)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_circle(center, r, "#999", "none", 0.5))
    for pt in pts:
        print(_svg_point(pt, "#5456f3", 3))


def cmd_intersect_circles(args):
    c1, r1 = _parse_circle(args.c1)
    c2, r2 = _parse_circle(args.c2)
    pts = intersect_circles(c1, r1, c2, r2)
    if not pts:
        print("Circles do not intersect")
        return
    for i, pt in enumerate(pts, 1):
        _print_point(f"Intersection {i}", pt)
    print("\n--- SVG ---")
    print(_svg_circle(c1, r1, "#999", "none", 0.5))
    print(_svg_circle(c2, r2, "#999", "none", 0.5))
    for pt in pts:
        print(_svg_point(pt, "#5456f3", 3))


def cmd_polar(args):
    center = _parse_point(args.center)
    pt = polar_to_cartesian(center, args.r, args.angle)
    _print_point("Cartesian", pt)
    print("\n--- SVG ---")
    print(_svg_line(center, pt, "#999", 0.5))
    print(_svg_point(pt, "#5456f3", 3))


def cmd_evenly_spaced(args):
    center = _parse_point(args.center)
    pts = evenly_spaced_on_circle(center, args.r, args.count, args.start_angle)
    for i, pt in enumerate(pts):
        _print_point(f"Point {i}", pt)
    print("\n--- SVG ---")
    print(_svg_circle(center, args.r, "#999", "none", 0.5))
    for pt in pts:
        print(_svg_point(pt, "#5456f3", 4))


def cmd_concentric(args):
    center = _parse_point(args.center)
    radii = _parse_floats(args.radii)
    print(f"Center: ({center.x:.2f}, {center.y:.2f})")
    for r in radii:
        print(f"Radius: {r}")
    print("\n--- SVG ---")
    for r in radii:
        print(_svg_circle(center, r, "#5456f3", "none", 1))


def cmd_attach(args):
    if args.shape == "rect":
        x, y, w, h = _parse_rect(args.geometry)
        if args.side == "center":
            pt = rect_center(x, y, w, h)
        elif args.side in ("tl", "tr", "bl", "br"):
            pt = rect_corner(x, y, w, h, args.side)
        else:
            pt = rect_attachment(x, y, w, h, args.side, args.pos)
        _print_point("Attachment", pt)
        print("\n--- SVG ---")
        print(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="none" stroke="#999" stroke-width="0.5"/>'
        )
        print(_svg_point(pt, "#5456f3", 3))
    elif args.shape == "circle":
        center, r = _parse_circle(args.geometry)
        if args.side == "center":
            pt = center
        else:
            pt = circle_perimeter(center, r, args.angle)
        _print_point("Attachment", pt)
        print("\n--- SVG ---")
        print(_svg_circle(center, r, "#999", "none", 0.5))
        print(_svg_point(pt, "#5456f3", 3))
    else:
        raise ValueError(f"shape must be rect or circle, got {args.shape!r}")


def cmd_offset_line(args):
    p1, p2 = _parse_line(args.line)
    new_p1, new_p2 = offset_line(p1, p2, args.distance, args.side)
    _print_point("Original start", p1)
    _print_point("Original end  ", p2)
    _print_point("Offset start  ", new_p1)
    _print_point("Offset end    ", new_p2)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_line(new_p1, new_p2, "#5456f3", 1.5))


def cmd_offset_polyline(args):
    nums = _parse_floats(args.points)
    if len(nums) % 2 != 0 or len(nums) < 4:
        raise ValueError("--points must contain >= 2 pairs of numbers")
    pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    offset = offset_polyline(pts, args.distance, args.side)
    print(f"Offset polyline ({len(offset)} points):")
    for i, p in enumerate(offset):
        _print_point(f"  v{i}", p)
    print("\n--- SVG ---")
    orig_d = "M" + " L".join(f"{p.x:.2f},{p.y:.2f}" for p in pts)
    new_d = "M" + " L".join(f"{p.x:.2f},{p.y:.2f}" for p in offset)
    print(f'<path d="{orig_d}" fill="none" stroke="#999" stroke-width="0.5"/>')
    print(f'<path d="{new_d}" fill="none" stroke="#5456f3" stroke-width="1.5"/>')


def cmd_offset_rect(args):
    x, y, w, h = _parse_rect(args.rect)
    result = offset_rect(x, y, w, h, args.by)
    if result is None:
        print(f"Offset of {args.by} would collapse the rect ({w}x{h})")
        return
    nx, ny, nw, nh = result
    print(f"Original: x={x} y={y} w={w} h={h}")
    print(f"Offset:   x={nx} y={ny} w={nw} h={nh}")
    print("\n--- SVG ---")
    print(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
        f'fill="none" stroke="#999" stroke-width="0.5"/>'
    )
    print(
        f'<rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" '
        f'fill="none" stroke="#5456f3" stroke-width="1.5"/>'
    )


def cmd_offset_circle(args):
    center, r = _parse_circle(args.circle)
    result = offset_circle(center, r, args.by)
    if result is None:
        print(f"Offset of {args.by} would collapse the circle (r={r})")
        return
    _, new_r = result
    print(f"Original radius: {r}")
    print(f"Offset radius:   {new_r}")
    print("\n--- SVG ---")
    print(_svg_circle(center, r, "#999", "none", 0.5))
    print(_svg_circle(center, new_r, "#5456f3", "none", 1.5))


def cmd_offset_polygon(args):
    nums = _parse_floats(args.points)
    if len(nums) % 2 != 0 or len(nums) < 6:
        raise ValueError("--points must contain >= 3 pairs of numbers")
    pts = [Point(nums[i], nums[i + 1]) for i in range(0, len(nums), 2)]
    offset = offset_polygon(pts, args.distance, args.direction)
    print(f"{args.direction.title()} offset polygon ({len(offset)} vertices):")
    for i, p in enumerate(offset):
        _print_point(f"  v{i}", p)
    print("\n--- SVG ---")
    orig = " ".join(f"{p.x:.2f},{p.y:.2f}" for p in pts)
    new = " ".join(f"{p.x:.2f},{p.y:.2f}" for p in offset)
    print(f'<polygon points="{orig}" fill="none" stroke="#999" stroke-width="0.5"/>')
    print(f'<polygon points="{new}" fill="none" stroke="#5456f3" stroke-width="1.5"/>')


def cmd_offset_point(args):
    """Offset a point a perpendicular distance from a reference line."""
    p1, p2 = _parse_line(args.line)
    pt = offset_point_from_line(p1, p2, args.t, args.distance, args.side)
    _print_point(f"Standoff (t={args.t}, d={args.distance}, side={args.side})", pt)
    print("\n--- SVG ---")
    print(_svg_line(p1, p2, "#999", 0.5))
    print(_svg_point(pt, "#5456f3", 3))


def cmd_bisector(args):
    p1 = _parse_point(args.p1)
    vertex = _parse_point(args.vertex)
    p2 = _parse_point(args.p2)
    bx, by = bisector_direction(p1, vertex, p2)
    far = Point(vertex.x + bx * 50, vertex.y + by * 50)
    print(f"Bisector unit vector: ({bx:.4f}, {by:.4f})")
    angle = math.degrees(math.atan2(by, bx))
    print(f"Bisector angle:       {angle:.2f} degrees")
    _print_point("50px along bisector", far)
    print("\n--- SVG ---")
    print(_svg_line(vertex, p1, "#999", 0.5))
    print(_svg_line(vertex, p2, "#999", 0.5))
    print(_svg_line(vertex, far, "#5456f3", 1.2))


def _parse_polygon_arg(s):
    """Parse polygon as a Python literal '[(x,y),(x,y),...]' or 'x,y x,y ...'."""
    import ast

    s = s.strip()
    if s.startswith("["):
        return [tuple(p) for p in ast.literal_eval(s)]
    pts = []
    for tok in s.split():
        parts = tok.replace(",", " ").split()
        pts.append((float(parts[0]), float(parts[1])))
    return pts


def _build_shapely_geom(inner):
    from shapely.geometry import (
        LineString,
    )
    from shapely.geometry import (
        Point as SPoint,
    )
    from shapely.geometry import (
        Polygon as SPolygon,
    )
    from shapely.geometry import (
        box as sbox,
    )

    kind, data = inner
    if kind == "point":
        return SPoint(data[0], data[1])
    if kind == "bbox":
        x, y, w, h = data
        return sbox(x, y, x + w, y + h)
    if kind == "line":
        return LineString([data[0], data[1]])
    if kind == "polyline":
        return LineString(data)
    if kind == "polygon":
        return SPolygon(data)
    raise ValueError(f"unknown geometry kind: {kind}")


def geometry_in_polygon(inner, polygon):
    """Containment and convex-safety report for `inner` inside closed `polygon`.

    Supports any inner geometry type passed as a (kind, data) tuple:

      - ``('point', (x, y))`` - a single point
      - ``('bbox', (x, y, w, h))`` - an axis-aligned rectangle
      - ``('line', ((x1, y1), (x2, y2)))`` - a single segment
      - ``('polyline', [(x, y), ...])`` - an open polyline or curve sample
      - ``('polygon', [(x, y), ...])`` - a closed polygon vertex list

    Returns a dictionary with three fields:

      - ``contained``: True iff every point of `inner` lies inside the outer
        polygon or on its boundary (``shapely.covers``). This is the classic
        "is X inside Y" test and is sufficient for a convex outer polygon.

      - ``convex_safe``: True iff the CONVEX HULL of `inner` is also covered
        by the outer polygon. This is the stricter test: when the outer
        polygon is concave, two inner points can both lie inside while the
        straight line between them exits through a concave notch and re-enters.
        ``convex_safe=True`` guarantees that any straight line between any two
        points of `inner` stays fully inside the outer polygon. Equivalent to
        saying "the tightest convex cover of `inner` fits in the outer".

      - ``exit_segments``: list of ``(start, end)`` point pairs whose straight
        line is NOT contained in the outer polygon. When the inner geometry is
        a line / polyline / polygon the function enumerates every pair of
        vertices and reports which ones fail. When the inner is a bbox the
        four corners are used. Empty when ``convex_safe`` is True.

    Typical use in the callout-placement workflow: pass the candidate text
    bbox as ``inner`` and an empty-space island boundary as ``polygon``.
    ``contained=True`` means the text visually lands on free space; adding
    ``convex_safe=True`` means a leader drawn between any two corners (or any
    two sample points of a more complex inner shape) stays inside the island
    too - useful when the island is an L-shape or horseshoe.
    """
    from shapely.geometry import LineString
    from shapely.geometry import Polygon as SPolygon
    from shapely.geometry.base import BaseGeometry

    outer = SPolygon(polygon)
    geom = _build_shapely_geom(inner)
    contained = outer.covers(geom)

    hull = geom.convex_hull
    if isinstance(hull, BaseGeometry):
        convex_safe = outer.covers(hull)
    else:
        convex_safe = False

    exit_segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    if not convex_safe and geom.geom_type in (
        "LineString",
        "Polygon",
        "MultiPoint",
        "Point",
    ):
        kind = inner[0]
        if kind in ("line", "polyline"):
            pts = list(geom.coords)
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    seg = LineString([pts[i], pts[j]])
                    if not outer.covers(seg):
                        exit_segments.append((pts[i], pts[j]))
        elif kind == "polygon":
            pts = list(geom.exterior.coords)
            for i in range(len(pts)):
                for j in range(i + 1, len(pts)):
                    seg = LineString([pts[i], pts[j]])
                    if not outer.covers(seg):
                        exit_segments.append((pts[i], pts[j]))
        elif kind == "bbox":
            x, y, w, h = inner[1]
            corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
            for i in range(4):
                for j in range(i + 1, 4):
                    seg = LineString([corners[i], corners[j]])
                    if not outer.covers(seg):
                        exit_segments.append((corners[i], corners[j]))

    return {
        "contained": bool(contained),
        "convex_safe": bool(convex_safe),
        "exit_segments": exit_segments,
    }


def rect_ray_exit(rect, from_point):
    """Perimeter intersection point of a ray from rect centre toward an external point.

    Given an axis-aligned rectangle ``rect = (x, y, w, h)`` and a point
    ``from_point = (px, py)``, extend the ray that starts at the centre of the
    rectangle and passes through `from_point`. Return the single point where
    that ray exits the rectangle perimeter.

    Use case: leader anchor computation. Given a callout text bbox and a
    leader target, inflate the bbox by the standoff, then call this function
    with `from_point = target` to obtain the point on the inflated bbox edge
    that faces the target. The leader should start at `from_point` and end at
    the returned perimeter point; the small gap between the returned point
    and the true bbox perimeter IS the standoff.

    Assumes `from_point` lies outside the rect (or at worst on its boundary).
    If `from_point` coincides with the rect centre the function raises.
    """
    x, y, w, h = rect
    cx, cy = x + w / 2.0, y + h / 2.0
    dx, dy = from_point[0] - cx, from_point[1] - cy
    if dx == 0 and dy == 0:
        raise ValueError("from_point coincides with rect centre")
    ts = []
    if dx != 0:
        ts.append((x - cx) / dx)
        ts.append((x + w - cx) / dx)
    if dy != 0:
        ts.append((y - cy) / dy)
        ts.append((y + h - cy) / dy)
    candidates = []
    for t in ts:
        if t <= 0:
            continue
        px = cx + t * dx
        py = cy + t * dy
        if x - 1e-9 <= px <= x + w + 1e-9 and y - 1e-9 <= py <= y + h + 1e-9:
            candidates.append((t, px, py))
    if not candidates:
        raise ValueError("ray does not exit rect (geometry degenerate)")
    candidates.sort(key=lambda c: c[0])
    _, px, py = candidates[0]
    return (px, py)


def cmd_rect_edge(args):
    parts = [float(t) for t in args.rect.replace(",", " ").split()]
    if len(parts) != 4:
        raise ValueError("--rect expects 'x,y,w,h'")
    rect = tuple(parts)
    fp = _parse_point(getattr(args, "from"))
    px, py = rect_ray_exit(rect, (fp.x, fp.y))
    cx, cy = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
    print(f"Rect centre: ({cx:.2f}, {cy:.2f})")
    print(f"Ray toward:  ({fp.x:.2f}, {fp.y:.2f})")
    print(f"Edge point:  ({px:.2f}, {py:.2f})")


def cmd_contains(args):
    polygon = _parse_polygon_arg(args.polygon)
    from shapely.geometry import Polygon as SPolygon

    outer = SPolygon(polygon)
    print(f"Outer: {len(polygon)} vertices, area={outer.area:.1f}")

    def _report(label, inner):
        res = geometry_in_polygon(inner, polygon)
        cflag = "YES" if res["contained"] else "NO"
        sflag = "YES" if res["convex_safe"] else "NO"
        print(f"{label}: contained={cflag}  convex-safe={sflag}")
        for s, e in res["exit_segments"][:3]:
            print(f"  exit: {s} -> {e}")
        if len(res["exit_segments"]) > 3:
            print(f"  ... +{len(res['exit_segments']) - 3} more exits")

    tested = 0
    if args.point is not None:
        pt = _parse_point(args.point)
        _report(f"Point ({pt.x:.2f},{pt.y:.2f})", ("point", (pt.x, pt.y)))
        tested += 1
    if args.bbox is not None:
        parts = [float(t) for t in args.bbox.replace(",", " ").split()]
        if len(parts) != 4:
            raise ValueError("--bbox expects 'x,y,w,h'")
        _report(f"BBox {tuple(parts)}", ("bbox", tuple(parts)))
        tested += 1
    if args.line is not None:
        parts = [float(t) for t in args.line.replace(",", " ").split()]
        if len(parts) != 4:
            raise ValueError("--line expects 'x1,y1,x2,y2'")
        line = ((parts[0], parts[1]), (parts[2], parts[3]))
        _report(f"Line {line[0]}->{line[1]}", ("line", line))
        tested += 1
    if args.polyline is not None:
        pts = _parse_polygon_arg(args.polyline)
        _report(f"Polyline ({len(pts)} pts)", ("polyline", pts))
        tested += 1
    if args.inner_polygon is not None:
        pts = _parse_polygon_arg(args.inner_polygon)
        _report(f"Inner polygon ({len(pts)} verts)", ("polygon", pts))
        tested += 1
    if tested == 0:
        print("(no geometry; use --point / --bbox / --line / --polyline / --inner-polygon)")


_TOP_DESCRIPTION = """\
Geometry calculator for SVG infographics. Fusion-360-style sketch
operations: attachment points, midpoints, tangents, intersections,
parallel/perpendicular construction, polar layout, and parallel offsets.

All angles are in degrees, SVG convention (Y grows downward, angle 0 = +X,
angle 90 = +Y/down). Every command prints the computed value(s) plus a
small SVG verification snippet you can paste into a file to inspect.

When to reach for which subcommand:

  Connector source/target on a card edge .... attach
  Mid / end / corner of a card .............. attach
  Point on circle perimeter at angle ........ attach (--shape circle)
  Junction or label position on a span ...... midpoint, at
  Pull a line N px past its endpoint ........ extend
  Drop a perpendicular foot ................. perpendicular
  Tangent connector to a hub circle ......... tangent
  Tangent rails between two hub circles ..... tangent-circles
  "Where do these two flow lines meet?" ..... intersect-lines
  Line clipped by a circle .................. intersect-line-circle
  Two circles meeting (Venn / radical) ...... intersect-circles
  N nodes around a hub (radial diagram) ..... evenly-spaced
  Rings around a center (target / sonar) .... concentric
  Polar -> SVG cartesian point .............. polar
  Bisect an angle for arrow placement ....... bisector
  Parallel / perpendicular construction line. parallel, perpendicular-line
  Halo / shadow / inflate a card ............ offset-rect
  Bigger / smaller concentric of a circle ... offset-circle
  Parallel rail / channel along a line ...... offset-line
  Parallel rail along an L-route or path .... offset-polyline
  Inflate / deflate a closed polygon ........ offset-polygon
  Label standoff perpendicular to a line .... offset-point
  Is a point / bbox inside a closed polygon. contains
  Callout leader anchor on text bbox edge .. rect-edge
"""

_EXAMPLES = """\
Examples:

  # Right-edge midpoint of a card (use as connector source)
  geom attach --shape rect --geometry 20,40,150,80 --side right --pos mid

  # Tangent points from an external point to a hub circle
  geom tangent --circle 400,200,50 --from 100,100

  # 8 nodes evenly distributed around a hub
  geom evenly-spaced --center 400,200 --r 120 --count 8

  # Concentric rings for a radial scorecard
  geom concentric --center 400,200 --radii 60,90,120,150

  # Where do two flow lines intersect?
  geom intersect-lines --line1 0,0,200,200 --line2 0,200,200,0

  # 5px halo around a card outline
  geom offset-rect --rect 50,50,100,80 --by 5

  # Parallel rail 8px to the right of an L-route
  geom offset-polyline --points "0,0 100,0 100,100" --distance 8 --side right

  # Label standoff: 12px above the midpoint of a connector
  geom offset-point --line 100,100,300,100 --t 0.5 --distance 12 --side left
"""


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics geom",
        description=_TOP_DESCRIPTION,
        epilog=_EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(
        dest="cmd",
        required=True,
        title="subcommands",
        metavar="SUBCOMMAND",
    )

    # ----------------------------------------------------------------------
    # Point and line operations
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "midpoint",
        help="Midpoint of two points. Use for label position between two cards or junction of two arrows.",
        description="Compute the midpoint between two points and the distance between them.",
    )
    p.add_argument("--p1", required=True, help="First point as 'x,y'")
    p.add_argument("--p2", required=True, help="Second point as 'x,y'")
    p.set_defaults(func=cmd_midpoint)

    p = sub.add_parser(
        "curve-midpoint",
        help="Arc-length midpoint of an open polyline (curved connector, Bezier samples, L-route). Returns midpoint + tangent + total arc length.",
        description="Walks a polyline accumulating segment lengths and returns the exact point at arc-length/2 with the tangent direction at that point. Use for labels on connectors or precise midpoint incident on a curved path.",
    )
    p.add_argument(
        "--points", required=True, help='Polyline as a Python literal: "[(x1,y1),(x2,y2),...]"'
    )
    p.set_defaults(func=cmd_curve_midpoint)

    p = sub.add_parser(
        "shape-midpoint",
        help="Centroid of a closed shape (any polygon). Use when a connector is pointing at a non-rect closed shape and you need its centre for direction inference.",
        description="Computes the area-weighted centroid of a closed polygon defined by its vertices. Returns the centroid point and the signed area. For rectangles, circles, stars, hexagons and any other closed polygon the caller passes as a vertex list.",
    )
    p.add_argument(
        "--points",
        required=True,
        help='Closed polygon vertices as a literal: "[(x1,y1),(x2,y2),...]"',
    )
    p.set_defaults(func=cmd_shape_midpoint)

    p = sub.add_parser(
        "extend",
        help="Push a line endpoint N px farther along its own direction. Use to extend a stem past a card edge or hit a junction.",
        description="Move a line endpoint N pixels past its current position along the line direction.",
    )
    p.add_argument("--line", required=True, help="Line as 'x1,y1,x2,y2'")
    p.add_argument("--by", type=float, required=True, help="Pixels to extend by (positive)")
    p.add_argument(
        "--end", choices=["start", "end"], default="end", help="Which end to push (default: end)"
    )
    p.set_defaults(func=cmd_extend)

    p = sub.add_parser(
        "at",
        help="Point at parameter t in [0,1] along a line. Use for label positions, fractional waypoints, even spacing along an existing edge.",
        description="Linear interpolation point along a line at parameter t (0=start, 1=end).",
    )
    p.add_argument("--line", required=True, help="Line as 'x1,y1,x2,y2'")
    p.add_argument("--t", type=float, required=True, help="Parameter in [0, 1]")
    p.set_defaults(func=cmd_at)

    p = sub.add_parser(
        "perpendicular",
        help="Foot of the perpendicular from a point onto a line. Use to drop a callout marker onto a connector or measure shortest distance.",
        description="Project a point onto an infinite line and return the closest point + distance.",
    )
    p.add_argument("--point", required=True, help="External point as 'x,y'")
    p.add_argument("--line", required=True, help="Line as 'x1,y1,x2,y2'")
    p.set_defaults(func=cmd_perpendicular)

    p = sub.add_parser(
        "parallel",
        help="Parallel line through a point. Use to build a second flow rail or guide line that copies an existing direction.",
        description="Construct a line parallel to a reference line that passes through a chosen point.",
    )
    p.add_argument("--line", required=True, help="Reference line as 'x1,y1,x2,y2'")
    p.add_argument("--through", required=True, help="Point the new line must pass through 'x,y'")
    p.set_defaults(func=cmd_parallel)

    p = sub.add_parser(
        "perpendicular-line",
        help="Perpendicular line through a point. Use to construct cross-bars, axis ticks, or T-junctions normal to an existing line.",
        description="Construct a line perpendicular to a reference line that passes through a chosen point.",
    )
    p.add_argument("--line", required=True, help="Reference line as 'x1,y1,x2,y2'")
    p.add_argument("--through", required=True, help="Point the new line must pass through 'x,y'")
    p.set_defaults(func=cmd_perpendicular_line)

    p = sub.add_parser(
        "bisector",
        help="Unit vector along the angle bisector at a vertex. Use to centre an arrow or label inside a fork or merge.",
        description="Compute the angle bisector direction at a vertex between two rays.",
    )
    p.add_argument("--p1", required=True, help="First ray endpoint 'x,y'")
    p.add_argument("--vertex", required=True, help="Common vertex 'x,y'")
    p.add_argument("--p2", required=True, help="Second ray endpoint 'x,y'")
    p.set_defaults(func=cmd_bisector)

    p = sub.add_parser(
        "rect-edge",
        help="Perimeter intersection of ray from rect centre toward an external point. Use for callout leader anchor: inflate text bbox by standoff, pass inflated rect + leader target, get anchor on bbox edge facing target.",
        description="Given rect (x,y,w,h) and from-point p, extend ray rect_center->p until it exits the rect and return the exit point. Used to terminate a callout leader one standoff short of the text bbox.",
    )
    p.add_argument("--rect", required=True, help="Rect 'x,y,w,h'")
    p.add_argument("--from", dest="from", required=True, help="External point 'x,y'")
    p.set_defaults(func=cmd_rect_edge)

    p = sub.add_parser(
        "contains",
        help="Is inner geometry (point/bbox/line/polyline/polygon) inside outer polygon? Reports contained + convex-safe (catches concave re-entry).",
        description="Two checks. contained: all inner points inside outer. convex-safe: convex hull of inner also covered - when false, some line between two inner points exits concave outer. For callout bbox / leader / decorative shape validation inside empty-space islands.",
    )
    p.add_argument("--polygon", required=True, help='Outer polygon "[(x,y),...]" or "x,y x,y ..."')
    p.add_argument("--point", help="Inner 'x,y'")
    p.add_argument("--bbox", help="Inner 'x,y,w,h'")
    p.add_argument("--line", help="Inner 'x1,y1,x2,y2'")
    p.add_argument("--polyline", help='Inner "[(x,y),...]"')
    p.add_argument("--inner-polygon", help='Inner closed "[(x,y),...]"')
    p.set_defaults(func=cmd_contains)

    # ----------------------------------------------------------------------
    # Tangents
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "tangent",
        help="Two tangent points from an external point to a circle. Use to route a connector to a hub circle without poking through it.",
        description="Find the two tangent points where lines from an external point touch a circle.",
    )
    p.add_argument("--circle", required=True, help="Circle as 'cx,cy,r'")
    p.add_argument("--from", dest="from", required=True, help="External point 'x,y'")
    p.set_defaults(func=cmd_tangent)

    p = sub.add_parser(
        "tangent-circles",
        help="Tangent line pairs between two circles (external or internal). Use for belts, rails, or pipes flowing between two circular nodes.",
        description="Build the tangent lines that touch two circles. External=outer rails, internal=crossing rails.",
    )
    p.add_argument("--c1", required=True, help="First circle 'cx,cy,r'")
    p.add_argument("--c2", required=True, help="Second circle 'cx,cy,r'")
    p.add_argument(
        "--kind",
        choices=["external", "internal"],
        default="external",
        help="external = outer (non-crossing), internal = crossing between circles",
    )
    p.set_defaults(func=cmd_tangent_circles)

    # ----------------------------------------------------------------------
    # Intersections
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "intersect-lines",
        help="Intersection point of two lines (None if parallel). Use to find where two flow lines cross or where a guide meets an edge.",
        description="Find the unique intersection point of two infinite lines, or report parallel.",
    )
    p.add_argument("--line1", required=True, help="First line 'x1,y1,x2,y2'")
    p.add_argument("--line2", required=True, help="Second line 'x1,y1,x2,y2'")
    p.set_defaults(func=cmd_intersect_lines)

    p = sub.add_parser(
        "intersect-line-circle",
        help="0/1/2 intersection points of a line with a circle. Use to clip a connector to a hub or place a marker where a line enters a region.",
        description="Find the 0, 1, or 2 points where an infinite line meets a circle.",
    )
    p.add_argument("--line", required=True, help="Line 'x1,y1,x2,y2'")
    p.add_argument("--circle", required=True, help="Circle 'cx,cy,r'")
    p.set_defaults(func=cmd_intersect_line_circle)

    p = sub.add_parser(
        "intersect-circles",
        help="0/1/2 intersection points of two circles. Use for Venn diagrams, radical lines, and crescent shapes.",
        description="Find the 0, 1, or 2 points where two circles meet.",
    )
    p.add_argument("--c1", required=True, help="First circle 'cx,cy,r'")
    p.add_argument("--c2", required=True, help="Second circle 'cx,cy,r'")
    p.set_defaults(func=cmd_intersect_circles)

    # ----------------------------------------------------------------------
    # Polar layout
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "polar",
        help="Single polar coordinate to cartesian. Use for one-off radial placements like a clock hand tip or a radial label.",
        description="Convert (radius, angle) around a center into an SVG (x, y) point.",
    )
    p.add_argument("--center", required=True, help="Origin 'cx,cy'")
    p.add_argument("--r", type=float, required=True, help="Radius")
    p.add_argument(
        "--angle", type=float, required=True, help="Angle in degrees (0=right, 90=down)"
    )
    p.set_defaults(func=cmd_polar)

    p = sub.add_parser(
        "evenly-spaced",
        help="N points evenly distributed around a circle. Use for hub-and-spoke layouts, radial menus, gear teeth, dial markers.",
        description="Place N points at equal angular spacing on a circle, optionally rotated by start-angle.",
    )
    p.add_argument("--center", required=True, help="Center 'cx,cy'")
    p.add_argument("--r", type=float, required=True, help="Radius")
    p.add_argument("--count", type=int, required=True, help="How many points")
    p.add_argument(
        "--start-angle",
        type=float,
        default=0,
        help="Angle of the first point in degrees (default: 0 = right)",
    )
    p.set_defaults(func=cmd_evenly_spaced)

    p = sub.add_parser(
        "concentric",
        help="Concentric circles at given radii. Use for sonar/target/scorecard rings, capability heatmaps, dartboards.",
        description="Emit SVG for several circles sharing a center but with different radii.",
    )
    p.add_argument("--center", required=True, help="Common center 'cx,cy'")
    p.add_argument("--radii", required=True, help="Comma-separated radii e.g. '20,40,60'")
    p.set_defaults(func=cmd_concentric)

    # ----------------------------------------------------------------------
    # Offset / parallel geometry (preserves shape, shifts perpendicular)
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "offset-line",
        help="Parallel line at perpendicular distance. Use for double rails, side channels, or shadow lines along a connector.",
        description="Translate a line perpendicular to itself by a fixed distance. Side relative to walking direction.",
    )
    p.add_argument("--line", required=True, help="Original line 'x1,y1,x2,y2'")
    p.add_argument("--distance", type=float, required=True, help="Perpendicular offset in px")
    p.add_argument(
        "--side",
        choices=["left", "right"],
        default="left",
        help="Visual side: left = up-of-direction in SVG, right = down-of-direction",
    )
    p.set_defaults(func=cmd_offset_line)

    p = sub.add_parser(
        "offset-polyline",
        help="Parallel polyline with mitered corners. Use for parallel rails along an L-route, multi-segment flow channels, thick borders.",
        description="Offset every edge of a polyline perpendicularly and meet adjacent edges at mitered intersections.",
    )
    p.add_argument(
        "--points",
        required=True,
        help='Polyline vertices as "x1,y1 x2,y2 ..." (space or comma separated)',
    )
    p.add_argument("--distance", type=float, required=True, help="Perpendicular offset in px")
    p.add_argument(
        "--side",
        choices=["left", "right"],
        default="left",
        help="Visual side relative to walking direction",
    )
    p.set_defaults(func=cmd_offset_polyline)

    p = sub.add_parser(
        "offset-rect",
        help="Inflate (positive) or deflate (negative) a rect uniformly. Use for halos, shadows, padding boxes, hit-test shrinks.",
        description="Grow or shrink a rect equally on all four sides. Returns None if a negative offset would collapse it.",
    )
    p.add_argument("--rect", required=True, help="Rect 'x,y,w,h'")
    p.add_argument(
        "--by",
        type=float,
        required=True,
        help="Pixels to grow each side (positive=halo, negative=shrink)",
    )
    p.set_defaults(func=cmd_offset_rect)

    p = sub.add_parser(
        "offset-circle",
        help="Inflate or deflate a circle. Use for halos around hubs, smaller concentric ring, target rings tied to a base radius.",
        description="Add or subtract from a circle's radius keeping the centre fixed.",
    )
    p.add_argument("--circle", required=True, help="Circle 'cx,cy,r'")
    p.add_argument(
        "--by",
        type=float,
        required=True,
        help="Pixels to add to radius (positive=halo, negative=shrink)",
    )
    p.set_defaults(func=cmd_offset_circle)

    p = sub.add_parser(
        "offset-polygon",
        help="Inflate or deflate a closed polygon. Use for halos around irregular shapes, padding around hit areas, layered ring polygons.",
        description="Outward = inflate, inward = deflate. Auto-detects polygon winding.",
    )
    p.add_argument("--points", required=True, help='Polygon vertices as "x1,y1 x2,y2 ..."')
    p.add_argument("--distance", type=float, required=True, help="Offset distance in px")
    p.add_argument(
        "--direction",
        choices=["outward", "inward"],
        default="outward",
        help="outward = inflate, inward = deflate",
    )
    p.set_defaults(func=cmd_offset_polygon)

    p = sub.add_parser(
        "offset-point",
        help="Point at parameter t along a line, shifted perpendicular by N px. Use for label standoffs above/below a connector.",
        description="Pick a fractional position along a line then offset perpendicularly to one side.",
    )
    p.add_argument("--line", required=True, help="Reference line 'x1,y1,x2,y2'")
    p.add_argument("--t", type=float, required=True, help="Parameter in [0, 1] along the line")
    p.add_argument("--distance", type=float, required=True, help="Perpendicular standoff in px")
    p.add_argument(
        "--side",
        choices=["left", "right"],
        default="left",
        help="Visual side relative to walking direction",
    )
    p.set_defaults(func=cmd_offset_point)

    # ----------------------------------------------------------------------
    # Attachment points (snap to a shape)
    # ----------------------------------------------------------------------
    p = sub.add_parser(
        "attach",
        help="Snap point on a card edge or circle perimeter. THE workhorse for placing connector endpoints exactly on shape boundaries.",
        description=(
            "Get an exact point on a shape boundary so connectors land cleanly.\n"
            "  rect:   --side top|right|bottom|left   plus --pos start|mid|end\n"
            "          --side tl|tr|bl|br             (corners)\n"
            "          --side center                  (rect center)\n"
            "  circle: --side perimeter --angle DEG\n"
            "          --side center"
        ),
    )
    p.add_argument("--shape", choices=["rect", "circle"], required=True, help="rect or circle")
    p.add_argument("--geometry", required=True, help="rect: 'x,y,w,h'   circle: 'cx,cy,r'")
    p.add_argument(
        "--side",
        default="center",
        help="rect: top|right|bottom|left|tl|tr|bl|br|center   circle: perimeter|center",
    )
    p.add_argument(
        "--pos",
        choices=["start", "mid", "end"],
        default="mid",
        help="Position along edge for rect sides (default: mid)",
    )
    p.add_argument(
        "--angle",
        type=float,
        default=0,
        help="Perimeter angle in degrees for circle perimeter (default: 0)",
    )
    p.set_defaults(func=cmd_attach)

    # ------------------------------------------------------------------
    # Alignment and distribution
    # ------------------------------------------------------------------
    p = sub.add_parser(
        "align",
        help="Align multiple rects along a shared edge or centre. Like Figma's align toolbar.",
        description=(
            "Align a list of rects to a common edge or centre line.\n"
            "  edge: left | right | top | bottom | h-center | v-center"
        ),
    )
    p.add_argument(
        "--rects",
        required=True,
        help="List of rects: '[(x,y,w,h),(x,y,w,h),...]' or 'x,y,w,h x,y,w,h ...'",
    )
    p.add_argument(
        "--edge",
        required=True,
        choices=["left", "right", "top", "bottom", "h-center", "v-center"],
        help="Edge or centre to align to",
    )
    p.set_defaults(func=cmd_align)

    p = sub.add_parser(
        "distribute",
        help="Space rects evenly along an axis. Equal centroid spacing or equal gap between edges.",
    )
    p.add_argument(
        "--rects",
        required=True,
        help="List of rects: '[(x,y,w,h),(x,y,w,h),...]'",
    )
    p.add_argument("--axis", required=True, choices=["h", "v"], help="Distribution axis")
    p.add_argument(
        "--mode",
        default="center",
        choices=["center", "gap"],
        help="'center' = equal centroid spacing, 'gap' = equal gaps between edges (default: center)",
    )
    p.set_defaults(func=cmd_distribute)

    p = sub.add_parser(
        "stack",
        help="Stack rects sequentially with a fixed gap. h-stack or v-stack.",
    )
    p.add_argument(
        "--rects",
        required=True,
        help="List of rects: '[(x,y,w,h),(x,y,w,h),...]'",
    )
    p.add_argument("--axis", required=True, choices=["h", "v"], help="Stack direction")
    p.add_argument("--gap", type=float, default=10.0, help="Pixels between edges (default: 10)")
    p.add_argument(
        "--anchor",
        default="start",
        choices=["start", "center"],
        help="'start' = first rect stays, 'center' = centre the stack (default: start)",
    )
    p.set_defaults(func=cmd_stack)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
