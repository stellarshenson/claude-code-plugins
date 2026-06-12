"""SVG primitive geometry generator.

Generates exact coordinates and SVG snippets for geometric primitives.
Helps Claude agents place elements with pixel-precise coordinates
instead of approximating positions.

2D: rectangle, square, ellipse, circle, diamond, hexagon, star, arc
3D: cube, cuboid, cylinder, sphere, plane
Curves: spline (PCHIP interpolation)
Layout: axis (x, y, xy, xyz with ticks)

Uses shapely for precise geometric computations (buffer, centroid,
intersection, bounding box).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
import re
import sys

from shapely.geometry import Polygon as ShapelyPolygon
from shapely.geometry import box as shapely_box

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Point:
    x: float
    y: float

    def __repr__(self):
        return f"({self.x}, {self.y})"


@dataclass
class PrimitiveResult:
    """Result of primitive generation."""

    kind: str
    anchors: dict[str, Point]  # named anchor points (center, top, bottom-left, etc.)
    svg: str  # ready-to-paste SVG snippet
    path_d: str = ""  # raw path data if applicable


# ---------------------------------------------------------------------------
# PCHIP interpolation (pure Python, no scipy)
# ---------------------------------------------------------------------------


def _pchip_slopes(xs: list[float], ys: list[float]) -> list[float]:
    """Fritsch-Carlson PCHIP slopes. Preserves monotonicity between knots."""
    n = len(xs)
    if n < 2:
        return [0.0] * n

    deltas = [
        (ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) if xs[i + 1] != xs[i] else 0.0
        for i in range(n - 1)
    ]
    slopes = [0.0] * n
    slopes[0] = deltas[0]
    slopes[-1] = deltas[-1]

    for i in range(1, n - 1):
        if deltas[i - 1] * deltas[i] <= 0:
            slopes[i] = 0.0
        else:
            w1 = 2 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2 * (xs[i] - xs[i - 1])
            slopes[i] = (w1 + w2) / (w1 / deltas[i - 1] + w2 / deltas[i])

    return slopes


def pchip_interpolate(
    xs: list[float],
    ys: list[float],
    num_samples: int = 50,
) -> list[Point]:
    """Interpolate through control points using PCHIP.

    Returns evenly spaced points along the interpolated curve.
    Preserves monotonicity - no overshooting.

    Args:
        xs: X coordinates (must be strictly increasing)
        ys: Y coordinates
        num_samples: Number of output points (default 50)
    """
    n = len(xs)
    if n < 2:
        return [Point(xs[0], ys[0])] if n == 1 else []
    if n != len(ys):
        raise ValueError(f"xs ({n}) and ys ({len(ys)}) must have same length")

    slopes = _pchip_slopes(xs, ys)
    result = []
    x_min, x_max = xs[0], xs[-1]
    step = (x_max - x_min) / (num_samples - 1) if num_samples > 1 else 0

    seg_idx = 0
    for i in range(num_samples):
        x = min(x_min + i * step, x_max)
        while seg_idx < n - 2 and x > xs[seg_idx + 1]:
            seg_idx += 1

        h = xs[seg_idx + 1] - xs[seg_idx]
        if h == 0:
            result.append(Point(round(x, 2), round(ys[seg_idx], 2)))
            continue

        t = (x - xs[seg_idx]) / h
        t2, t3 = t * t, t * t * t
        h00 = 2 * t3 - 3 * t2 + 1
        h10 = t3 - 2 * t2 + t
        h01 = -2 * t3 + 3 * t2
        h11 = t3 - t2

        y = (
            h00 * ys[seg_idx]
            + h10 * h * slopes[seg_idx]
            + h01 * ys[seg_idx + 1]
            + h11 * h * slopes[seg_idx + 1]
        )
        result.append(Point(round(x, 2), round(y, 2)))

    return result


def points_to_svg_path(points: list[Point], closed: bool = False) -> str:
    """Convert points to SVG path data using L commands."""
    if not points:
        return ""
    parts = [f"M{points[0].x},{points[0].y}"]
    for p in points[1:]:
        parts.append(f"L{p.x},{p.y}")
    if closed:
        parts.append("Z")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Primitive generators
# ---------------------------------------------------------------------------


def gen_rect(
    x: float, y: float, w: float, h: float, r: float = 0, accent: str = ""
) -> PrimitiveResult:
    """Rectangle with optional rounded corners and accent bar."""
    anchors = {
        "top-left": Point(x, y),
        "top-right": Point(x + w, y),
        "bottom-left": Point(x, y + h),
        "bottom-right": Point(x + w, y + h),
        "center": Point(x + w / 2, y + h / 2),
        "top-center": Point(x + w / 2, y),
        "bottom-center": Point(x + w / 2, y + h),
        "left-center": Point(x, y + h / 2),
        "right-center": Point(x + w, y + h / 2),
    }

    if r > 0:
        # Flat-top, rounded-bottom card (infographic standard)
        d = (
            f"M{x},{y} H{x + w} V{y + h - r} "
            f"Q{x + w},{y + h} {x + w - r},{y + h} "
            f"H{x + r} Q{x},{y + h} {x},{y + h - r} Z"
        )
        svg = f'<path d="{d}" fill="{{accent}}" fill-opacity="0.04" stroke="{{accent}}" stroke-width="1"/>'
        if accent:
            svg += (
                f'\n<rect x="{x}" y="{y}" width="{w}" height="5" fill="{{accent}}" opacity="0.6"/>'
            )
    else:
        svg = f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>'
        d = ""

    return PrimitiveResult("rect", anchors, svg, d)


def gen_square(x: float, y: float, size: float, r: float = 0) -> PrimitiveResult:
    """Square (rect with equal sides)."""
    return gen_rect(x, y, size, size, r)


def gen_circle(cx: float, cy: float, r: float) -> PrimitiveResult:
    """Circle with cardinal and diagonal anchors."""
    anchors = {
        "center": Point(cx, cy),
        "top": Point(cx, cy - r),
        "bottom": Point(cx, cy + r),
        "left": Point(cx - r, cy),
        "right": Point(cx + r, cy),
        "top-left": Point(cx - r * 0.707, cy - r * 0.707),
        "top-right": Point(cx + r * 0.707, cy - r * 0.707),
        "bottom-left": Point(cx - r * 0.707, cy + r * 0.707),
        "bottom-right": Point(cx + r * 0.707, cy + r * 0.707),
    }
    svg = f'<circle cx="{cx}" cy="{cy}" r="{r}"/>'
    return PrimitiveResult("circle", anchors, svg)


def gen_ellipse(cx: float, cy: float, rx: float, ry: float) -> PrimitiveResult:
    """Ellipse with cardinal anchors."""
    anchors = {
        "center": Point(cx, cy),
        "top": Point(cx, cy - ry),
        "bottom": Point(cx, cy + ry),
        "left": Point(cx - rx, cy),
        "right": Point(cx + rx, cy),
    }
    svg = f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}"/>'
    return PrimitiveResult("ellipse", anchors, svg)


def gen_diamond(cx: float, cy: float, w: float, h: float) -> PrimitiveResult:
    """Diamond (rhombus) centered at (cx, cy)."""
    top = Point(cx, cy - h / 2)
    right = Point(cx + w / 2, cy)
    bottom = Point(cx, cy + h / 2)
    left = Point(cx - w / 2, cy)

    anchors = {
        "center": Point(cx, cy),
        "top": top,
        "right": right,
        "bottom": bottom,
        "left": left,
    }
    vertices = f"{top.x},{top.y} {right.x},{right.y} {bottom.x},{bottom.y} {left.x},{left.y}"
    svg = f'<polygon points="{vertices}"/>'
    return PrimitiveResult("diamond", anchors, svg)


def gen_hexagon(cx: float, cy: float, r: float, flat_top: bool = True) -> PrimitiveResult:
    """Regular hexagon. Uses shapely for precise vertex computation.

    Args:
        flat_top: True for flat-top orientation, False for pointy-top
    """
    offset = 0 if flat_top else 30
    pts = []
    anchors = {"center": Point(cx, cy)}

    for i in range(6):
        angle = math.radians(60 * i + offset)
        px = round(cx + r * math.cos(angle), 2)
        py = round(cy + r * math.sin(angle), 2)
        pts.append(Point(px, py))
        anchors[f"v{i}"] = pts[-1]

    # Named anchors for flat-top: left, right, top-left, top-right, bottom-left, bottom-right
    if flat_top:
        anchors["right"] = pts[0]
        anchors["top-right"] = pts[5]
        anchors["top-left"] = pts[4]
        anchors["left"] = pts[3]
        anchors["bottom-left"] = pts[2]
        anchors["bottom-right"] = pts[1]

    # Use shapely for precise area and centroid verification
    poly = ShapelyPolygon([(p.x, p.y) for p in pts])
    anchors["area"] = Point(round(poly.area, 2), 0)  # area stored in x

    vertices = " ".join(f"{p.x},{p.y}" for p in pts)
    svg = f'<polygon points="{vertices}"/>'
    return PrimitiveResult("hexagon", anchors, svg)


def gen_star(
    cx: float, cy: float, outer_r: float, inner_r: float = 0, points: int = 5
) -> PrimitiveResult:
    """Regular star polygon. Inner radius defaults to outer_r * 0.4.

    Args:
        points: Number of star points (default: 5)
        inner_r: Inner radius (default: outer_r * 0.4)
    """
    if inner_r == 0:
        inner_r = outer_r * 0.4

    anchors = {"center": Point(cx, cy)}
    pts = []

    for i in range(points * 2):
        angle = math.radians(90 + 360 * i / (points * 2))
        r = outer_r if i % 2 == 0 else inner_r
        px = round(cx + r * math.cos(angle), 2)
        py = round(cy - r * math.sin(angle), 2)  # SVG y-axis inverted
        pts.append(Point(px, py))
        if i % 2 == 0:
            anchors[f"tip{i // 2}"] = pts[-1]
        else:
            anchors[f"valley{i // 2}"] = pts[-1]

    anchors["top"] = pts[0]  # first tip at 12 o'clock

    vertices = " ".join(f"{p.x},{p.y}" for p in pts)
    svg = f'<polygon points="{vertices}"/>'
    return PrimitiveResult("star", anchors, svg)


def gen_arc(
    cx: float, cy: float, r: float, start_angle: float, end_angle: float
) -> PrimitiveResult:
    """Circular arc sector (pie slice). Angles in degrees, 0 = right, CCW.

    Returns anchor points for the arc endpoints and midpoint.
    """
    sa = math.radians(start_angle)
    ea = math.radians(end_angle)
    mid_a = (sa + ea) / 2

    start_pt = Point(round(cx + r * math.cos(sa), 2), round(cy - r * math.sin(sa), 2))
    end_pt = Point(round(cx + r * math.cos(ea), 2), round(cy - r * math.sin(ea), 2))
    mid_pt = Point(round(cx + r * math.cos(mid_a), 2), round(cy - r * math.sin(mid_a), 2))

    # Large arc flag
    sweep = end_angle - start_angle
    if sweep < 0:
        sweep += 360
    large_arc = 1 if sweep > 180 else 0

    anchors = {
        "center": Point(cx, cy),
        "start": start_pt,
        "end": end_pt,
        "mid": mid_pt,
        "label": Point(
            round(cx + r * 0.6 * math.cos(mid_a), 2), round(cy - r * 0.6 * math.sin(mid_a), 2)
        ),
    }

    # SVG arc: A rx ry x-rotation large-arc-flag sweep-flag x y
    # sweep-flag 0 for CCW in SVG coords (y inverted)
    d = f"M{cx},{cy} L{start_pt.x},{start_pt.y} A{r},{r} 0 {large_arc},0 {end_pt.x},{end_pt.y} Z"
    svg = f'<path d="{d}"/>'
    return PrimitiveResult("arc", anchors, svg, d)


def gen_cube(
    x: float, y: float, w: float, h: float, depth: float = 0, mode: str = "fill"
) -> PrimitiveResult:
    """Isometric cube. Depth defaults to w*0.4.

    Args:
        mode: "fill" for 3-face shaded cube, "wire" for wireframe edges only
    """
    if depth == 0:
        depth = w * 0.4
    dx = depth * 0.866  # cos(30)
    dy = depth * 0.5  # sin(30)

    # 8 vertices (front face + back face offset by dx, -dy)
    fl = Point(x, y)  # front-top-left
    fr = Point(x + w, y)  # front-top-right
    fbr = Point(x + w, y + h)  # front-bottom-right
    fbl = Point(x, y + h)  # front-bottom-left
    bl = Point(x + dx, y - dy)
    br = Point(x + w + dx, y - dy)
    bbr = Point(x + w + dx, y + h - dy)
    bbl = Point(x + dx, y + h - dy)  # hidden back-bottom-left (dashed in wire mode)

    anchors = {
        "front-top-left": fl,
        "front-top-right": fr,
        "front-bottom-left": fbl,
        "front-bottom-right": fbr,
        "back-top-left": bl,
        "back-top-right": br,
        "back-bottom-left": bbl,
        "back-bottom-right": bbr,
        "center": Point(x + w / 2 + dx / 2, y + h / 2 - dy / 2),
    }

    if mode == "wire":
        visible = [
            # Front face
            f"M{fl.x},{fl.y} L{fr.x},{fr.y} L{fbr.x},{fbr.y} L{fbl.x},{fbl.y} Z",
            # Top face
            f"M{fl.x},{fl.y} L{bl.x},{bl.y} L{br.x},{br.y} L{fr.x},{fr.y} Z",
            # Right face
            f"M{fr.x},{fr.y} L{br.x},{br.y} L{bbr.x},{bbr.y} L{fbr.x},{fbr.y} Z",
        ]
        # Hidden edges emanate from bbl (back-bottom-left corner). Three edges:
        # bbl-bl (vertical), bbl-bbr (back-bottom horizontal), bbl-fbl (depth diagonal)
        hidden = [
            f"M{bbl.x},{bbl.y} L{bl.x},{bl.y}",
            f"M{bbl.x},{bbl.y} L{bbr.x},{bbr.y}",
            f"M{bbl.x},{bbl.y} L{fbl.x},{fbl.y}",
        ]
        svg = "\n".join(
            f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="1"/>' for d in visible
        )
        svg += "\n" + "\n".join(
            f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="0.7" '
            f'stroke-dasharray="2,2" opacity="0.55"/>'
            for d in hidden
        )
    else:
        # Three visible faces with different opacities
        top_d = f"M{fl.x},{fl.y} L{bl.x},{bl.y} L{br.x},{br.y} L{fr.x},{fr.y} Z"
        right_d = f"M{fr.x},{fr.y} L{br.x},{br.y} L{bbr.x},{bbr.y} L{fbr.x},{fbr.y} Z"
        front_d = f"M{fl.x},{fl.y} L{fr.x},{fr.y} L{fbr.x},{fbr.y} L{fbl.x},{fbl.y} Z"
        svg = (
            f'<path d="{front_d}" fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{top_d}" fill="{{accent}}" fill-opacity="0.15"/>\n'
            f'<path d="{right_d}" fill="{{accent}}" fill-opacity="0.04"/>'
        )

    return PrimitiveResult("cube", anchors, svg)


def gen_cylinder(
    cx: float, cy: float, rx: float, ry: float, h: float, mode: str = "fill"
) -> PrimitiveResult:
    """Cylinder with elliptical top and bottom faces.

    Args:
        cx, cy: Center of top ellipse
        rx, ry: Radii of the ellipses
        h: Height (distance from top to bottom center)
        mode: "fill" for shaded, "wire" for wireframe
    """
    anchors = {
        "top-center": Point(cx, cy),
        "bottom-center": Point(cx, cy + h),
        "top-left": Point(cx - rx, cy),
        "top-right": Point(cx + rx, cy),
        "bottom-left": Point(cx - rx, cy + h),
        "bottom-right": Point(cx + rx, cy + h),
        "center": Point(cx, cy + h / 2),
    }

    # Top ellipse arc: A rx,ry 0 1,0 (full sweep)
    top_arc = f"M{cx - rx},{cy} A{rx},{ry} 0 1,0 {cx + rx},{cy} A{rx},{ry} 0 1,0 {cx - rx},{cy}"
    # Body: left side down, bottom arc, right side up, top arc
    body_d = (
        f"M{cx - rx},{cy} L{cx - rx},{cy + h} "
        f"A{rx},{ry} 0 0,0 {cx + rx},{cy + h} "
        f"L{cx + rx},{cy} A{rx},{ry} 0 0,1 {cx - rx},{cy} Z"
    )

    if mode == "wire":
        # Visible: top ellipse (full), body silhouette (left + right verticals +
        # front half of bottom ellipse). Hidden: back half of bottom ellipse,
        # back half of top ellipse already included in the full top arc.
        svg = (
            # Left vertical
            f'<path d="M{cx - rx},{cy} L{cx - rx},{cy + h}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            # Right vertical
            f'<path d="M{cx + rx},{cy} L{cx + rx},{cy + h}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            # Full top ellipse (visible)
            f'<path d="{top_arc}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            # Front (visible) half of bottom ellipse: solid
            f'<path d="M{cx - rx},{cy + h} A{rx},{ry} 0 0,0 {cx + rx},{cy + h}" '
            f'fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            # Back (hidden) half of bottom ellipse: dashed
            f'<path d="M{cx - rx},{cy + h} A{rx},{ry} 0 0,1 {cx + rx},{cy + h}" '
            f'fill="none" stroke="{{accent}}" stroke-width="0.7" '
            f'stroke-dasharray="2,2" opacity="0.55"/>'
        )
    else:
        svg = (
            f'<path d="{body_d}" fill="{{accent}}" fill-opacity="0.06" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{top_arc}" fill="{{accent}}" fill-opacity="0.12" stroke="{{accent}}" stroke-width="1"/>'
        )

    return PrimitiveResult("cylinder", anchors, svg)


def gen_sphere(cx: float, cy: float, r: float, mode: str = "fill") -> PrimitiveResult:
    """Sphere rendered as a circle with shading ellipses for 3D effect.

    Args:
        cx, cy: Center
        r: Radius
        mode: "fill" for shaded sphere, "wire" for wireframe with latitude/longitude
    """
    anchors = {
        "center": Point(cx, cy),
        "top": Point(cx, cy - r),
        "bottom": Point(cx, cy + r),
        "left": Point(cx - r, cy),
        "right": Point(cx + r, cy),
    }

    if mode == "wire":
        # Main circle
        parts = [
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{{accent}}" stroke-width="1"/>'
        ]
        # Equator ellipse (horizontal)
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r * 0.3}" '
            f'fill="none" stroke="{{accent}}" stroke-width="0.5" opacity="0.5"/>'
        )
        # Meridian ellipse (vertical)
        parts.append(
            f'<ellipse cx="{cx}" cy="{cy}" rx="{r * 0.3}" ry="{r}" '
            f'fill="none" stroke="{{accent}}" stroke-width="0.5" opacity="0.5"/>'
        )
        svg = "\n".join(parts)
    else:
        # Shaded sphere: base circle + highlight ellipse offset top-left
        hx = cx - r * 0.25
        hy = cy - r * 0.25
        hr = r * 0.35
        parts = [
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{{accent}}" fill-opacity="0.08" '
            f'stroke="{{accent}}" stroke-width="1"/>',
            f'<ellipse cx="{hx}" cy="{hy}" rx="{hr}" ry="{hr * 0.8}" '
            f'fill="{{accent}}" fill-opacity="0.12"/>',
        ]
        svg = "\n".join(parts)

    return PrimitiveResult("sphere", anchors, svg)


def gen_cuboid(
    x: float, y: float, w: float, h: float, d: float, mode: str = "fill"
) -> PrimitiveResult:
    """Isometric cuboid (box with independent width, height, depth).

    Like cube but with different width, height, and depth.

    Args:
        x, y: Front-top-left corner
        w: Width (horizontal)
        h: Height (vertical)
        d: Depth (into page, isometric projection at 30 degrees)
    """
    dx = d * 0.866  # cos(30)
    dy = d * 0.5  # sin(30)

    fl = Point(x, y)
    fr = Point(x + w, y)
    fbr = Point(x + w, y + h)
    fbl = Point(x, y + h)
    bl = Point(x + dx, y - dy)
    br = Point(x + w + dx, y - dy)
    bbr = Point(x + w + dx, y + h - dy)
    bbl = Point(x + dx, y + h - dy)  # hidden back-bottom-left

    anchors = {
        "front-top-left": fl,
        "front-top-right": fr,
        "front-bottom-left": fbl,
        "front-bottom-right": fbr,
        "back-top-left": bl,
        "back-top-right": br,
        "back-bottom-left": bbl,
        "back-bottom-right": bbr,
        "center": Point(x + w / 2 + dx / 2, y + h / 2 - dy / 2),
        "front-center": Point(x + w / 2, y + h / 2),
        "top-center": Point(x + w / 2 + dx / 2, y - dy / 2),
    }

    front_d = f"M{fl.x},{fl.y} L{fr.x},{fr.y} L{fbr.x},{fbr.y} L{fbl.x},{fbl.y} Z"
    top_d = f"M{fl.x},{fl.y} L{bl.x},{bl.y} L{br.x},{br.y} L{fr.x},{fr.y} Z"
    right_d = f"M{fr.x},{fr.y} L{br.x},{br.y} L{bbr.x},{bbr.y} L{fbr.x},{fbr.y} Z"

    if mode == "wire":
        visible = [front_d, top_d, right_d]
        hidden = [
            f"M{bbl.x},{bbl.y} L{bl.x},{bl.y}",
            f"M{bbl.x},{bbl.y} L{bbr.x},{bbr.y}",
            f"M{bbl.x},{bbl.y} L{fbl.x},{fbl.y}",
        ]
        svg = "\n".join(
            f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="1"/>' for d in visible
        )
        svg += "\n" + "\n".join(
            f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="0.7" '
            f'stroke-dasharray="2,2" opacity="0.55"/>'
            for d in hidden
        )
    else:
        svg = (
            f'<path d="{front_d}" fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{top_d}" fill="{{accent}}" fill-opacity="0.15"/>\n'
            f'<path d="{right_d}" fill="{{accent}}" fill-opacity="0.04"/>'
        )

    return PrimitiveResult("cuboid", anchors, svg)


def gen_plane(
    x: float, y: float, w: float, h: float, tilt: float = 30, mode: str = "fill"
) -> PrimitiveResult:
    """Isometric plane (flat surface tilted into the page).

    A parallelogram representing a flat surface in pseudo-3D. A flat plane
    has no truly hidden edges (all four outline segments are visible from
    an isometric viewpoint), so ``wire`` mode simply emits the outline
    without fill, matching the visual language of the other 3D primitives.

    Args:
        x, y: Front-left corner
        w: Width (horizontal extent)
        h: Depth (into page, projected at tilt angle)
        tilt: Projection angle in degrees (default: 30)
        mode: ``"fill"`` for shaded parallelogram, ``"wire"`` for outline only
    """
    rad = math.radians(tilt)
    dx = h * math.cos(rad)
    dy = h * math.sin(rad)

    fl = Point(x, y)  # front-left
    fr = Point(x + w, y)  # front-right
    br = Point(x + w + dx, y - dy)  # back-right
    bl = Point(x + dx, y - dy)  # back-left

    anchors = {
        "front-left": fl,
        "front-right": fr,
        "back-left": bl,
        "back-right": br,
        "center": Point(x + w / 2 + dx / 2, y - dy / 2),
        "front-center": Point(x + w / 2, y),
        "back-center": Point(x + w / 2 + dx, y - dy),
    }

    d = f"M{fl.x},{fl.y} L{fr.x},{fr.y} L{br.x:.1f},{br.y:.1f} L{bl.x:.1f},{bl.y:.1f} Z"
    if mode == "wire":
        svg = f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="1"/>'
    else:
        svg = f'<path d="{d}" fill="{{accent}}" fill-opacity="0.06" stroke="{{accent}}" stroke-width="1"/>'

    return PrimitiveResult("plane", anchors, svg, d)


def gen_axis(
    origin_x: float,
    origin_y: float,
    length: float,
    axes: str = "xy",
    tick_spacing: float = 0,
    tick_count: int = 0,
    labels: bool = True,
) -> PrimitiveResult:
    """Generate coordinate axes with optional ticks and labels.

    Args:
        origin_x, origin_y: Origin point
        length: Axis length in pixels
        axes: "x", "y", "xy", or "xyz" (xyz adds isometric z-axis)
        tick_spacing: Pixels between ticks (0 = auto from tick_count)
        tick_count: Number of ticks per axis (0 = no ticks)
        labels: Whether to add axis labels
    """
    TICK_LEN = 4
    ARROW_LEN = 8
    anchors = {"origin": Point(origin_x, origin_y)}
    parts = []

    if tick_count > 0 and tick_spacing == 0:
        tick_spacing = length / (tick_count + 1)

    # X-axis (rightward)
    if "x" in axes:
        x_end = origin_x + length
        anchors["x-end"] = Point(x_end, origin_y)
        # Axis line stops at the BACK of the arrowhead so the line does not
        # protrude through the triangle.
        parts.append(
            f'<line x1="{origin_x}" y1="{origin_y}" x2="{x_end - ARROW_LEN}" y2="{origin_y}" '
            f'stroke="{{accent}}" stroke-width="1"/>'
        )
        # Arrow triangle: tip at (x_end, origin_y), base at x_end-ARROW_LEN.
        parts.append(
            f'<polygon points="{x_end},{origin_y} '
            f"{x_end - ARROW_LEN},{origin_y - 3} "
            f'{x_end - ARROW_LEN},{origin_y + 3}" fill="{{accent}}"/>'
        )
        # Ticks
        if tick_spacing > 0:
            tx = origin_x + tick_spacing
            i = 0
            while tx < x_end - ARROW_LEN:
                anchors[f"x-tick-{i}"] = Point(tx, origin_y)
                parts.append(
                    f'<line x1="{tx}" y1="{origin_y - TICK_LEN}" '
                    f'x2="{tx}" y2="{origin_y + TICK_LEN}" '
                    f'stroke="{{accent}}" stroke-width="0.5"/>'
                )
                tx += tick_spacing
                i += 1
        if labels:
            parts.append(
                f'<text x="{x_end + 6}" y="{origin_y + 4}" font-size="9" '
                f'class="fg-3" font-family="Segoe UI, Arial, sans-serif">x</text>'
            )

    # Y-axis (upward)
    if "y" in axes:
        y_end = origin_y - length
        anchors["y-end"] = Point(origin_x, y_end)
        # Line stops at arrow back (y_end + ARROW_LEN) so the axis does not
        # stab through the triangle.
        parts.append(
            f'<line x1="{origin_x}" y1="{origin_y}" x2="{origin_x}" y2="{y_end + ARROW_LEN}" '
            f'stroke="{{accent}}" stroke-width="1"/>'
        )
        parts.append(
            f'<polygon points="{origin_x},{y_end} '
            f"{origin_x - 3},{y_end + ARROW_LEN} "
            f'{origin_x + 3},{y_end + ARROW_LEN}" fill="{{accent}}"/>'
        )
        if tick_spacing > 0:
            ty = origin_y - tick_spacing
            i = 0
            while ty > y_end + ARROW_LEN:
                anchors[f"y-tick-{i}"] = Point(origin_x, ty)
                parts.append(
                    f'<line x1="{origin_x - TICK_LEN}" y1="{ty}" '
                    f'x2="{origin_x + TICK_LEN}" y2="{ty}" '
                    f'stroke="{{accent}}" stroke-width="0.5"/>'
                )
                ty -= tick_spacing
                i += 1
        if labels:
            parts.append(
                f'<text x="{origin_x - 10}" y="{y_end - 4}" font-size="9" '
                f'text-anchor="middle" class="fg-3" '
                f'font-family="Segoe UI, Arial, sans-serif">y</text>'
            )

    # Z-axis (isometric: 30 degrees down-left from origin)
    if "z" in axes:
        z_dx = length * 0.866  # cos(30)
        z_dy = length * 0.5  # sin(30)
        z_end_x = origin_x - z_dx
        z_end_y = origin_y + z_dy
        anchors["z-end"] = Point(z_end_x, z_end_y)
        # Line stops ARROW_LEN short of z_end along the axis direction so the
        # line does not protrude through the arrowhead. Unit vector origin->z_end
        # is (-0.866, 0.5); back-of-arrow = z_end shifted ARROW_LEN back toward origin.
        z_back_x = z_end_x + ARROW_LEN * 0.866
        z_back_y = z_end_y - ARROW_LEN * 0.5
        parts.append(
            f'<line x1="{origin_x}" y1="{origin_y}" '
            f'x2="{z_back_x:.1f}" y2="{z_back_y:.1f}" '
            f'stroke="{{accent}}" stroke-width="1"/>'
        )
        # Arrow: back direction is from tip toward origin (opposite of axis
        # forward direction). Forward is atan2(z_dy, -z_dx); back is
        # atan2(-z_dy, z_dx). Offsetting back-points along the BACK angle
        # places them correctly on the tip's trailing side.
        back_angle = math.atan2(-z_dy, z_dx)
        ax = z_end_x + ARROW_LEN * math.cos(back_angle - 0.35)
        ay = z_end_y + ARROW_LEN * math.sin(back_angle - 0.35)
        bx = z_end_x + ARROW_LEN * math.cos(back_angle + 0.35)
        by = z_end_y + ARROW_LEN * math.sin(back_angle + 0.35)
        parts.append(
            f'<polygon points="{z_end_x:.1f},{z_end_y:.1f} '
            f'{ax:.1f},{ay:.1f} {bx:.1f},{by:.1f}" fill="{{accent}}"/>'
        )
        if tick_spacing > 0:
            unit_x = -z_dx / length
            unit_y = z_dy / length
            perp_x = -unit_y
            perp_y = unit_x
            i = 0
            d = tick_spacing
            while d < length - ARROW_LEN:
                tx = origin_x + unit_x * d
                ty = origin_y + unit_y * d
                anchors[f"z-tick-{i}"] = Point(round(tx, 1), round(ty, 1))
                parts.append(
                    f'<line x1="{tx + perp_x * TICK_LEN:.1f}" y1="{ty + perp_y * TICK_LEN:.1f}" '
                    f'x2="{tx - perp_x * TICK_LEN:.1f}" y2="{ty - perp_y * TICK_LEN:.1f}" '
                    f'stroke="{{accent}}" stroke-width="0.5"/>'
                )
                d += tick_spacing
                i += 1
        if labels:
            parts.append(
                f'<text x="{z_end_x - 8}" y="{z_end_y + 12}" font-size="9" '
                f'class="fg-3" font-family="Segoe UI, Arial, sans-serif">z</text>'
            )

    svg = "\n".join(parts)
    return PrimitiveResult(f"axis-{axes}", anchors, svg)


def gen_spline(
    control_points: list[tuple[float, float]], num_samples: int = 50, closed: bool = False
) -> PrimitiveResult:
    """Smooth spline through control points via PCHIP interpolation.

    Args:
        control_points: List of (x, y) tuples. X must be strictly increasing.
        num_samples: Interpolation density (default 50)
        closed: Whether to close the path
    """
    xs = [p[0] for p in control_points]
    ys = [p[1] for p in control_points]

    points = pchip_interpolate(xs, ys, num_samples=num_samples)
    path_d = points_to_svg_path(points, closed=closed)

    anchors = {
        "start": points[0] if points else Point(0, 0),
        "end": points[-1] if points else Point(0, 0),
        "mid": points[len(points) // 2] if points else Point(0, 0),
    }
    # Add control points as anchors
    for i, (x, y) in enumerate(control_points):
        anchors[f"cp{i}"] = Point(x, y)

    svg = f'<path d="{path_d}" fill="none" stroke="{{accent}}" stroke-width="2"/>'
    return PrimitiveResult("spline", anchors, svg, path_d)


def gen_gear(
    x: float, y: float, outer_r: float, inner_r: float = 0, teeth: int = 12, mode: str = "filled"
) -> PrimitiveResult:
    """Toothed gear wheel centered at (x, y).

    Each tooth is a trapezoid: two base vertices on the inner circle and two
    tip vertices on the outer circle. Teeth are evenly spaced over 360 degrees.

    Args:
        x, y: Centre of the gear
        outer_r: Outer (tip) radius
        inner_r: Inner (root) radius (default: outer_r * 0.7)
        teeth: Number of teeth (default: 12)
        mode: "filled" for a filled polygon, "outline" for stroke-only path
    """
    if inner_r == 0:
        inner_r = outer_r * 0.7

    tooth_angle = 2 * math.pi / teeth
    half_tooth = tooth_angle * 0.25  # half-width of each tooth tip

    pts = []
    for i in range(teeth):
        base_angle = tooth_angle * i
        # Base-left on inner circle
        pts.append(
            Point(
                round(x + inner_r * math.cos(base_angle - half_tooth), 2),
                round(y + inner_r * math.sin(base_angle - half_tooth), 2),
            )
        )
        # Tip-left on outer circle
        pts.append(
            Point(
                round(x + outer_r * math.cos(base_angle - half_tooth), 2),
                round(y + outer_r * math.sin(base_angle - half_tooth), 2),
            )
        )
        # Tip-right on outer circle
        pts.append(
            Point(
                round(x + outer_r * math.cos(base_angle + half_tooth), 2),
                round(y + outer_r * math.sin(base_angle + half_tooth), 2),
            )
        )
        # Base-right on inner circle
        pts.append(
            Point(
                round(x + inner_r * math.cos(base_angle + half_tooth), 2),
                round(y + inner_r * math.sin(base_angle + half_tooth), 2),
            )
        )

    anchors = {
        "centre": Point(x, y),
        "top": Point(x, y - outer_r),
        "right": Point(x + outer_r, y),
        "bottom": Point(x, y + outer_r),
        "left": Point(x - outer_r, y),
    }

    vertices = " ".join(f"{p.x},{p.y}" for p in pts)
    if mode == "filled":
        svg = f'<polygon points="{vertices}" fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>'
    else:
        d = "M" + " L".join(f"{p.x},{p.y}" for p in pts) + " Z"
        svg = f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="1"/>'

    return PrimitiveResult("gear", anchors, svg)


def gen_pyramid(
    x: float, y: float, base_w: float, height: float, mode: str = "filled"
) -> PrimitiveResult:
    """Isometric 3D pyramid with three visible faces. Apex at top.

    Uses pseudo-3D projection: apex above the base centre, base-back
    recessed upward at 60% of the height to simulate depth.

    Args:
        x, y: Top-left corner of the bounding box
        base_w: Width of the base
        height: Height from base to apex
        mode: "filled" for shaded faces, "wire" for outline with dashed hidden edges
    """
    apex = Point(x + base_w / 2, y)
    base_left = Point(x, y + height)
    base_right = Point(x + base_w, y + height)
    base_back = Point(x + base_w / 2, y + height * 0.6)

    anchors = {
        "apex": apex,
        "base-left": base_left,
        "base-right": base_right,
        "base-back": base_back,
        "centre": Point(x + base_w / 2, y + height * 0.7),
    }

    face_left = f"M{apex.x},{apex.y} L{base_left.x},{base_left.y} L{base_back.x},{base_back.y} Z"
    face_right = (
        f"M{apex.x},{apex.y} L{base_right.x},{base_right.y} L{base_back.x},{base_back.y} Z"
    )
    face_back = f"M{base_left.x},{base_left.y} L{base_right.x},{base_right.y} L{base_back.x},{base_back.y} Z"

    if mode == "wire":
        svg = (
            f'<path d="{face_left}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{face_right}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="M{base_back.x},{base_back.y} L{apex.x},{apex.y}" '
            f'fill="none" stroke="{{accent}}" stroke-width="0.7" stroke-dasharray="2,2" opacity="0.55"/>'
        )
    else:
        svg = (
            f'<path d="{face_left}" fill="{{accent}}" fill-opacity="0.15" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{face_right}" fill="{{accent}}" fill-opacity="0.10" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{face_back}" fill="{{accent}}" fill-opacity="0.05"/>'
        )

    return PrimitiveResult("pyramid", anchors, svg)


def gen_cloud(
    x: float, y: float, w: float, h: float, lobes: int = 5, mode: str = "filled"
) -> PrimitiveResult:
    """Cloud shape built from a cubic-bezier closed path scaled to (x, y, w, h).

    The path uses a 5-lobe cloud template with control points scaled
    proportionally to w and h. The `lobes` parameter adjusts the number of
    bumps by repeating the top-arc segment pattern.

    Args:
        x, y: Top-left corner of the bounding box
        w, h: Width and height of the bounding box
        lobes: Number of top bumps (default: 5; values 3-7 work well)
        mode: "filled" for filled cloud, "outline" for stroke-only path
    """
    # Base 5-lobe template scaled to (w, h).  The bottom is flat-ish at 0.7*h.
    # Additional lobes duplicate the middle bump arc segment.
    extra = max(0, lobes - 5)
    lobe_w = w / (5 + extra)

    # Build the top arc as a series of bump arcs (cubic bezier per lobe).
    # Start: left side entry at (0.15*w, 0.35*h)
    # Each lobe adds one cubic bump of width lobe_w rising to ~0.05*h above y.
    parts = [f"M{x + 0.2 * w:.2f},{y + 0.7 * h:.2f}"]
    # Left ramp up
    parts.append(
        f"C{x + 0.05 * w:.2f},{y + 0.7 * h:.2f} "
        f"{x:.2f},{y + 0.45 * h:.2f} "
        f"{x + 0.15 * w:.2f},{y + 0.35 * h:.2f}"
    )
    # Top lobes: each lobe spans lobe_w, centre rises to y + 0.05*h
    lobe_count = 5 + extra
    for i in range(lobe_count):
        lx0 = x + 0.15 * w + i * lobe_w
        lx1 = lx0 + lobe_w
        lmid = (lx0 + lx1) / 2
        parts.append(
            f"C{lx0:.2f},{y:.2f} {lmid:.2f},{y - 0.05 * h:.2f} {lx1:.2f},{y + 0.05 * h:.2f}"
        )
    # Right ramp down
    parts.append(
        f"C{x + w:.2f},{y + 0.35 * h:.2f} "
        f"{x + w:.2f},{y + 0.6 * h:.2f} "
        f"{x + 0.8 * w:.2f},{y + 0.7 * h:.2f}"
    )
    parts.append("Z")
    d = " ".join(parts)

    anchors = {
        "centre": Point(x + w / 2, y + h / 2),
        "top": Point(x + w / 2, y),
        "right": Point(x + w, y + h * 0.6),
        "bottom": Point(x + w / 2, y + h * 0.7),
        "left": Point(x, y + h * 0.6),
    }

    if mode == "filled":
        svg = f'<path d="{d}" fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>'
    else:
        svg = f'<path d="{d}" fill="none" stroke="{{accent}}" stroke-width="1"/>'

    return PrimitiveResult("cloud", anchors, svg, d)


def gen_document(
    x: float, y: float, w: float, h: float, fold: float = 0, mode: str = "filled"
) -> PrimitiveResult:
    """Rectangle with a folded corner (dog-ear) at the top-right.

    The main body is a pentagon with the top-right corner cut diagonally.
    A small triangle overlaid at the fold represents the curled flap.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        fold: Size of the fold triangle (default: min(w, h) * 0.2)
        mode: "filled" for shaded document, "outline" for stroke-only
    """
    if fold == 0:
        fold = min(w, h) * 0.2

    # Main body: top-left -> (top-right minus fold) -> diagonal -> down -> bottom-right -> bottom-left
    body_d = f"M{x},{y} L{x + w - fold},{y} L{x + w},{y + fold} L{x + w},{y + h} L{x},{y + h} Z"
    # Fold flap triangle
    flap_d = f"M{x + w - fold},{y} L{x + w - fold},{y + fold} L{x + w},{y + fold} Z"

    anchors = {
        "top-left": Point(x, y),
        "top-right": Point(x + w - fold, y),
        "bottom-left": Point(x, y + h),
        "bottom-right": Point(x + w, y + h),
        "centre": Point(x + w / 2, y + h / 2),
        "fold": Point(x + w, y + fold),
    }

    if mode == "filled":
        svg = (
            f'<path d="{body_d}" fill="{{accent}}" fill-opacity="0.06" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{flap_d}" fill="{{accent}}" fill-opacity="0.12" stroke="{{accent}}" stroke-width="0.7"/>'
        )
    else:
        svg = (
            f'<path d="{body_d}" fill="none" stroke="{{accent}}" stroke-width="1"/>\n'
            f'<path d="{flap_d}" fill="none" stroke="{{accent}}" stroke-width="0.7" stroke-dasharray="2,2"/>'
        )

    return PrimitiveResult("document", anchors, svg, body_d)


# ---------------------------------------------------------------------------
# Speech bubble + callout spike
# ---------------------------------------------------------------------------


def _polygon_to_path_d(poly: ShapelyPolygon, decimals: int = 2) -> str:
    """Convert a shapely Polygon's exterior to an SVG path `d=` (M/L ... Z)."""
    coords = list(poly.exterior.coords)
    if len(coords) < 3:
        return ""
    # shapely closes the ring with a duplicate first vertex; drop it.
    if coords[0] == coords[-1]:
        coords = coords[:-1]
    parts = [f"M{coords[0][0]:.{decimals}f},{coords[0][1]:.{decimals}f}"]
    parts.extend(f"L{x:.{decimals}f},{y:.{decimals}f}" for x, y in coords[1:])
    parts.append("Z")
    return " ".join(parts)


def _ellipse_polygon(
    cx: float, cy: float, rx: float, ry: float, segments: int = 96
) -> ShapelyPolygon:
    """Approximate an ellipse as a closed shapely Polygon with `segments` vertices."""
    pts = [
        (
            cx + rx * math.cos(2 * math.pi * i / segments),
            cy + ry * math.sin(2 * math.pi * i / segments),
        )
        for i in range(segments)
    ]
    return ShapelyPolygon(pts)


def _rounded_rect_polygon(
    bx1: float, by1: float, bx2: float, by2: float, rx: float, ry: float, corner_segs: int = 16
) -> ShapelyPolygon:
    """Rounded rectangle with possibly-elliptical (rx != ry) corners.

    Built by walking the perimeter clockwise: 4 straight edges + 4 quarter-
    ellipses. ``rx`` is the horizontal radius (clamped to (bx2-bx1)/2) and
    ``ry`` the vertical radius (clamped to (by2-by1)/2). Falls back to a
    plain rectangle when both radii collapse to 0.
    """
    rx = max(0.0, min(rx, (bx2 - bx1) / 2))
    ry = max(0.0, min(ry, (by2 - by1) / 2))
    if rx == 0 and ry == 0:
        return shapely_box(bx1, by1, bx2, by2)
    pts: list[tuple[float, float]] = []
    # Top edge (left -> right), then top-right quarter (rotating from -90deg to 0deg).
    pts.append((bx1 + rx, by1))
    pts.append((bx2 - rx, by1))
    cx_r, cy_r = bx2 - rx, by1 + ry  # top-right corner centre
    for i in range(1, corner_segs + 1):
        t = (i / corner_segs) * (math.pi / 2)
        pts.append((cx_r + rx * math.sin(t), cy_r - ry * math.cos(t)))
    # Right edge (top -> bottom).
    pts.append((bx2, by2 - ry))
    cx_r, cy_r = bx2 - rx, by2 - ry  # bottom-right centre
    for i in range(1, corner_segs + 1):
        t = (i / corner_segs) * (math.pi / 2)
        pts.append((cx_r + rx * math.cos(t), cy_r + ry * math.sin(t)))
    # Bottom edge (right -> left).
    pts.append((bx1 + rx, by2))
    cx_r, cy_r = bx1 + rx, by2 - ry  # bottom-left centre
    for i in range(1, corner_segs + 1):
        t = (i / corner_segs) * (math.pi / 2)
        pts.append((cx_r - rx * math.sin(t), cy_r + ry * math.cos(t)))
    # Left edge (bottom -> top).
    pts.append((bx1, by1 + ry))
    cx_r, cy_r = bx1 + rx, by1 + ry  # top-left centre
    for i in range(1, corner_segs + 1):
        t = (i / corner_segs) * (math.pi / 2)
        pts.append((cx_r - rx * math.cos(t), cy_r - ry * math.sin(t)))
    return ShapelyPolygon(pts)


def _ellipse_perimeter_intersect(
    cx: float, cy: float, rx: float, ry: float, tip_x: float, tip_y: float
) -> tuple[float, float]:
    """Return the point on the ellipse boundary on the ray from (cx,cy) to (tip)."""
    dx = tip_x - cx
    dy = tip_y - cy
    if dx == 0 and dy == 0:
        # degenerate: tip == centre. Pick a deterministic point on the right.
        return (cx + rx, cy)
    # Parametric ray: (cx + t*dx, cy + t*dy). Plug into ellipse equation:
    #   ((t*dx)/rx)^2 + ((t*dy)/ry)^2 = 1
    a = (dx / rx) ** 2 + (dy / ry) ** 2
    t = 1.0 / math.sqrt(a)
    return (cx + t * dx, cy + t * dy)


def gen_speech_bubble(
    x: float,
    y: float,
    w: float,
    h: float,
    tip_x: float | None = None,
    tip_y: float | None = None,
    shape: str = "soft-rect",
    corner_radius: float = 12.0,
    rx: float | None = None,
    ry: float | None = None,
    spike_base_width: float = 20.0,
    spike_anchor: str = "auto",
    text_padding: float = 10.0,
    text_padding_x: float | None = None,
    text_padding_y: float | None = None,
    element_id: str | None = None,
    mode: str = "filled",
) -> tuple[PrimitiveResult, list[str]]:
    """Speech bubble: rect / soft-rect / ellipse body, optionally merged with a callout spike.

    When ``tip_x`` and ``tip_y`` are both supplied, a triangular spike is added
    with apex at ``(tip_x, tip_y)`` and base on the bubble perimeter; body and
    spike are unioned via shapely so the result is a single closed ``<path>``
    with one fill and one stroke (no seam line). When the tip is unset, just
    the body is emitted - a plain quote box / rounded card with no callout.

    Args:
        x, y: top-left of the body bounding box.
        w, h: body bounding-box dimensions.
        tip_x, tip_y: where the spike apex points. Both must be set to get a
            spike; leave both unset for a bubble without a callout.
        shape: ``"rect"`` (sharp corners), ``"soft-rect"`` (rounded), or
            ``"ellipse"`` (oval body).
        corner_radius: uniform corner radius for ``soft-rect``; clamped to
            ``min(w, h) / 2``. Used when neither ``rx`` nor ``ry`` is set.
        rx, ry: non-uniform corner radii for ``soft-rect`` (elliptical corners).
            Either one alone defaults the other to itself; setting both gives
            elliptical corners. Both are clamped to ``w/2`` / ``h/2``.
        spike_base_width: width of the spike base along the bubble edge.
        spike_anchor: ``"auto"`` picks the nearest edge for rect / soft-rect
            and the ellipse perimeter point on the centre->tip ray for
            ellipse. Explicit ``"top"`` / ``"bottom"`` / ``"left"`` /
            ``"right"`` overrides edge selection for rect / soft-rect only.
        text_padding: uniform inset for the ``text-area`` anchor rectangle.
        text_padding_x, text_padding_y: per-axis overrides of ``text_padding``.
        element_id: when set, the emitted ``<path>`` gets ``id="<element_id>"``
            so the agent can target it via ``--replace-id`` in the boolean tool.
        mode: ``"filled"`` or ``"outline"``.

    Returns:
        ``(PrimitiveResult, list[str])`` - the result and any warnings
        (``TIP-INSIDE-BUBBLE``, ``SPIKE-BASE-CLAMPED``,
        ``CORNER-RADIUS-CLAMPED``, ``ELLIPSE-ANCHOR-OVERRIDDEN``,
        ``TIP-INCOMPLETE``).
    """
    warnings: list[str] = []

    if shape not in ("rect", "soft-rect", "ellipse"):
        raise ValueError(f"shape must be rect / soft-rect / ellipse, got {shape!r}")
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive")
    if spike_base_width <= 0:
        raise ValueError("spike_base_width must be positive")

    # Tip handling: both unset => no spike; exactly one set => warn + ignore.
    has_tip = tip_x is not None and tip_y is not None
    if (tip_x is None) ^ (tip_y is None):
        warnings.append(
            "TIP-INCOMPLETE: both --tip-x and --tip-y must be supplied to attach a spike; "
            "treating as no-tip and emitting body only"
        )

    # ----- build body polygon -----
    bx1, by1, bx2, by2 = x, y, x + w, y + h
    cx, cy = (bx1 + bx2) / 2, (by1 + by2) / 2
    # Effective corner radii; the spike base must land on the straight edge
    # segment between the corner arcs, not on the bounding-box corners.
    corner_rx = corner_ry = 0.0

    if shape == "rect":
        body = shapely_box(bx1, by1, bx2, by2)
    elif shape == "soft-rect":
        # Non-uniform rx/ry path: explicit elliptical corners.
        if rx is not None or ry is not None:
            eff_rx = rx if rx is not None else (ry if ry is not None else corner_radius)
            eff_ry = ry if ry is not None else eff_rx
            rx_max, ry_max = w / 2, h / 2
            if eff_rx > rx_max:
                warnings.append(f"CORNER-RADIUS-CLAMPED: rx={eff_rx} clamped to {rx_max:.2f}")
                eff_rx = rx_max
            if eff_ry > ry_max:
                warnings.append(f"CORNER-RADIUS-CLAMPED: ry={eff_ry} clamped to {ry_max:.2f}")
                eff_ry = ry_max
            body = _rounded_rect_polygon(bx1, by1, bx2, by2, eff_rx, eff_ry)
            corner_rx, corner_ry = eff_rx, eff_ry
        else:
            r_max = min(w, h) / 2
            r = corner_radius
            if r > r_max:
                warnings.append(
                    f"CORNER-RADIUS-CLAMPED: corner_radius={corner_radius} clamped to {r_max:.2f}"
                )
                r = r_max
            if r <= 0:
                body = shapely_box(bx1, by1, bx2, by2)
            else:
                # Inset rectangle, then outset by r with rounded joins.
                inner = shapely_box(bx1 + r, by1 + r, bx2 - r, by2 - r)
                body = inner.buffer(r, quad_segs=16, join_style=1)
                corner_rx = corner_ry = r
    else:  # ellipse
        body = _ellipse_polygon(cx, cy, w / 2, h / 2)

    # ----- decide whether the spike is feasible -----
    spike_polygon = None
    spike_anchor_used = None
    spike_base_l = None
    spike_base_r = None

    if has_tip:
        tip_inside = body.contains(_tiny_point(tip_x, tip_y))
        if tip_inside:
            warnings.append(
                f"TIP-INSIDE-BUBBLE: tip ({tip_x}, {tip_y}) lies inside the body; "
                "spike suppressed. Place the tip outside the body to attach a spike."
            )
        else:
            spike_polygon, spike_anchor_used, spike_base_l, spike_base_r, more = _build_spike(
                shape=shape,
                bx1=bx1,
                by1=by1,
                bx2=bx2,
                by2=by2,
                cx=cx,
                cy=cy,
                w=w,
                h=h,
                tip_x=tip_x,
                tip_y=tip_y,
                spike_base_width=spike_base_width,
                anchor_request=spike_anchor,
                corner_rx=corner_rx,
                corner_ry=corner_ry,
            )
            warnings.extend(more)

    # ----- union body + spike -----
    if spike_polygon is not None:
        merged = body.union(spike_polygon)
    else:
        merged = body

    # merged may be a MultiPolygon if spike is detached; take the largest piece.
    if merged.geom_type == "MultiPolygon":
        merged = max(merged.geoms, key=lambda p: p.area)

    path_d = _polygon_to_path_d(merged)

    # ----- anchors -----
    anchors: dict[str, Point] = {
        "centre": Point(cx, cy),
        "top": Point(cx, by1),
        "bottom": Point(cx, by2),
        "left": Point(bx1, cy),
        "right": Point(bx2, cy),
    }
    if has_tip:
        anchors["tip"] = Point(tip_x, tip_y)
    # Text area: inset by `text_padding` (or per-axis overrides). Ellipse keeps
    # its inscribed-rect approximation (0.7 factor) since axis padding doesn't
    # map cleanly to an oval inscribed bounds.
    tpx = text_padding_x if text_padding_x is not None else text_padding
    tpy = text_padding_y if text_padding_y is not None else text_padding
    if shape == "ellipse":
        tx, ty = bx1 + w * 0.15, by1 + h * 0.15
        tw, th = w * 0.70, h * 0.70
    else:
        tx, ty = bx1 + tpx, by1 + tpy
        tw, th = max(0, w - 2 * tpx), max(0, h - 2 * tpy)
    anchors["text-top-left"] = Point(tx, ty)
    anchors["text-bottom-right"] = Point(tx + tw, ty + th)
    if spike_base_l is not None and spike_base_r is not None:
        anchors["spike-base-l"] = Point(*spike_base_l)
        anchors["spike-base-r"] = Point(*spike_base_r)

    # ----- emit SVG -----
    id_attr = f' id="{element_id}"' if element_id else ""
    if mode == "filled":
        svg = f'<path{id_attr} d="{path_d}" fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>'
    else:
        svg = f'<path{id_attr} d="{path_d}" fill="none" stroke="{{accent}}" stroke-width="1"/>'

    kind = f"speech-{shape}"
    if spike_anchor_used is not None:
        kind += f"+spike-{spike_anchor_used}"

    return PrimitiveResult(kind, anchors, svg, path_d), warnings


def _tiny_point(x: float, y: float) -> ShapelyPolygon:
    """Tiny triangle proxy for shapely point-in-polygon (avoids Point import churn)."""
    eps = 1e-6
    return ShapelyPolygon([(x, y), (x + eps, y), (x, y + eps)])


def _build_spike(
    *,
    shape: str,
    bx1: float,
    by1: float,
    bx2: float,
    by2: float,
    cx: float,
    cy: float,
    w: float,
    h: float,
    tip_x: float,
    tip_y: float,
    spike_base_width: float,
    anchor_request: str,
    corner_rx: float = 0.0,
    corner_ry: float = 0.0,
) -> tuple[ShapelyPolygon, str, tuple[float, float], tuple[float, float], list[str]]:
    """Build the spike triangle. Returns (polygon, anchor_used, base_l, base_r, warnings).

    ``corner_rx`` / ``corner_ry`` are the body's effective corner radii: the
    spike base is clamped to the straight edge segment between the corner
    arcs, otherwise the base lands on the bounding-box corner where the body
    has already curved away and the union outline backtracks over the arc.
    """
    warnings: list[str] = []
    half = spike_base_width / 2

    if shape in ("rect", "soft-rect"):
        # Decide anchor side.
        if anchor_request == "auto":
            # Pick side whose outward distance to tip is largest positive.
            dists = {
                "top": by1 - tip_y,
                "bottom": tip_y - by2,
                "left": bx1 - tip_x,
                "right": tip_x - bx2,
            }
            anchor = max(dists, key=dists.get)
        elif anchor_request in ("top", "bottom", "left", "right"):
            anchor = anchor_request
        else:
            raise ValueError(
                f"spike_anchor must be auto / top / bottom / left / right for {shape}, got {anchor_request!r}"
            )

        if anchor in ("top", "bottom"):
            edge_y = by1 if anchor == "top" else by2
            # Clamp base centre x so the base sits on the straight segment
            # between the corner arcs (corner_rx wide on each side).
            min_cx = bx1 + corner_rx + half
            max_cx = bx2 - corner_rx - half
            if min_cx > max_cx:
                # Straight segment too short for the requested base width.
                warnings.append(
                    f"SPIKE-BASE-CLAMPED: spike_base_width={spike_base_width} exceeds the "
                    "straight edge segment between the corner arcs; clamping"
                )
                base_cx = (bx1 + bx2) / 2
                half_effective = min(half, max((bx2 - bx1) / 2 - corner_rx, 0.0))
                if half_effective <= 0:
                    # Fully-rounded edge (pill): no straight segment exists;
                    # fall back to the bbox clamp rather than a degenerate base.
                    half_effective = min(half, (bx2 - bx1) / 2)
            else:
                base_cx = max(min_cx, min(max_cx, tip_x))
                half_effective = half
            base_l = (base_cx - half_effective, edge_y)
            base_r = (base_cx + half_effective, edge_y)
        else:  # left / right
            edge_x = bx1 if anchor == "left" else bx2
            min_cy = by1 + corner_ry + half
            max_cy = by2 - corner_ry - half
            if min_cy > max_cy:
                warnings.append(
                    f"SPIKE-BASE-CLAMPED: spike_base_width={spike_base_width} exceeds the "
                    "straight edge segment between the corner arcs; clamping"
                )
                base_cy = (by1 + by2) / 2
                half_effective = min(half, max((by2 - by1) / 2 - corner_ry, 0.0))
                if half_effective <= 0:
                    half_effective = min(half, (by2 - by1) / 2)
            else:
                base_cy = max(min_cy, min(max_cy, tip_y))
                half_effective = half
            base_l = (edge_x, base_cy - half_effective)
            base_r = (edge_x, base_cy + half_effective)

        spike = ShapelyPolygon([base_l, base_r, (tip_x, tip_y)])
        return spike, anchor, base_l, base_r, warnings

    # Ellipse: anchor is the perimeter point on the centre->tip ray. Manual
    # side anchors don't apply geometrically; if requested, warn and override.
    if anchor_request not in ("auto",):
        warnings.append(
            f"ELLIPSE-ANCHOR-OVERRIDDEN: anchor={anchor_request!r} not meaningful for ellipse; "
            "using the perimeter point on the centre-to-tip ray instead"
        )
    rx, ry = w / 2, h / 2
    px, py = _ellipse_perimeter_intersect(cx, cy, rx, ry, tip_x, tip_y)
    # Tangent direction perpendicular to the radial (centre->tip) line.
    dx, dy = tip_x - cx, tip_y - cy
    length = math.hypot(dx, dy)
    if length == 0:
        # Degenerate (tip at centre) — should be caught upstream as tip-inside.
        tnx, tny = 1.0, 0.0
    else:
        # Perpendicular: rotate (dx,dy)/length by 90deg.
        tnx, tny = -dy / length, dx / length
    base_l = (px - half * tnx, py - half * tny)
    base_r = (px + half * tnx, py + half * tny)
    spike = ShapelyPolygon([base_l, base_r, (tip_x, tip_y)])
    return spike, "ellipse-radial", base_l, base_r, warnings


# ---------------------------------------------------------------------------
# Thought bubble (lobed cloud + trail of decreasing bubbles)
# ---------------------------------------------------------------------------


def gen_thought_bubble(
    x: float,
    y: float,
    w: float,
    h: float,
    tip_x: float | None = None,
    tip_y: float | None = None,
    lobes: int = 5,
    trail_bubbles: int = 3,
    trail_r_start: float = 0.0,
    trail_r_end: float = 0.0,
    text_padding: float = 12.0,
    text_padding_x: float | None = None,
    text_padding_y: float | None = None,
    element_id: str | None = None,
    mode: str = "filled",
) -> tuple[PrimitiveResult, list[str]]:
    """Thought bubble: lobed cloud body + (optional) trail of small ellipses to the tip.

    The trail bubbles are kept visually distinct (separate ``<ellipse>``
    elements, NOT unioned with the body) - that's what makes a thought
    bubble read as a thought bubble. The whole thing is wrapped in a ``<g>``
    so callers can apply transforms or class names once. When the tip is
    unset, just the cloud body is emitted (no trail).

    Args:
        x, y, w, h: body bounding box.
        tip_x, tip_y: where the thought trail terminates (the "thinker"
            position). Both must be set to get a trail; leave both unset for
            a bare cloud body.
        lobes: number of cloud lobes (default 5; passed to gen_cloud).
        trail_bubbles: number of small bubbles in the trail (default 3;
            0 disables the trail entirely even when tip is supplied).
        trail_r_start: radius of the first (largest) trail bubble; default
            ``min(w, h) * 0.08`` (~6 px on a 80 px-tall bubble).
        trail_r_end: radius of the last (smallest) trail bubble; default
            ``trail_r_start * 0.35``.
        text_padding: uniform inset for the text-area anchor.
        text_padding_x, text_padding_y: per-axis overrides of ``text_padding``.
        element_id: when set, the outer ``<g>`` gets ``id="<element_id>"``.
        mode: ``"filled"`` or ``"outline"``.

    Returns: ``(PrimitiveResult, warnings)``. Warnings: ``TIP-INSIDE-BUBBLE``
    when the tip falls inside the body bbox (trail suppressed); ``TIP-INCOMPLETE``
    when only one of tip_x / tip_y is provided.
    """
    warnings: list[str] = []
    if w <= 0 or h <= 0:
        raise ValueError("width and height must be positive")
    if trail_bubbles < 0:
        raise ValueError("trail_bubbles must be >= 0")

    has_tip = tip_x is not None and tip_y is not None
    if (tip_x is None) ^ (tip_y is None):
        warnings.append(
            "TIP-INCOMPLETE: both --tip-x and --tip-y must be supplied to attach a trail; "
            "treating as no-tip and emitting cloud body only"
        )

    # Body: reuse gen_cloud verbatim so we don't fork the lobed-path code.
    body = gen_cloud(x, y, w, h, lobes=lobes, mode=mode)

    # Decide whether the trail is feasible. Use the body's bounding box for
    # the inside test (cheap + good enough; the cloud roughly fills the bbox).
    bx1, by1, bx2, by2 = x, y, x + w, y + h
    tip_inside = has_tip and (bx1 <= tip_x <= bx2) and (by1 <= tip_y <= by2)

    anchors: dict[str, Point] = dict(body.anchors)
    if has_tip:
        anchors["tip"] = Point(tip_x, tip_y)
    # Text area inscribed inside the cloud (cloud body is ~0.7h tall + lobes
    # eat the top quarter; inset more aggressively than for soft-rect).
    tpx = text_padding_x if text_padding_x is not None else text_padding
    tpy = text_padding_y if text_padding_y is not None else text_padding
    tx = bx1 + max(tpx, w * 0.10)
    ty = by1 + max(tpy, h * 0.20)
    tw = max(0.0, w - 2 * max(tpx, w * 0.10))
    th = max(0.0, h * 0.70 - 2 * tpy)
    anchors["text-top-left"] = Point(tx, ty)
    anchors["text-bottom-right"] = Point(tx + tw, ty + th)

    trail_svgs: list[str] = []

    if not has_tip or tip_inside or trail_bubbles == 0:
        if tip_inside:
            warnings.append(
                f"TIP-INSIDE-BUBBLE: tip ({tip_x}, {tip_y}) lies inside the body bbox; "
                "thought trail suppressed. Place the tip outside the body."
            )
    else:
        # Pick the body-bbox edge midpoint closest to the tip - that's where
        # the trail starts.
        candidates = {
            "top": (bx1 + w / 2, by1),
            "bottom": (bx1 + w / 2, by2),
            "left": (bx1, by1 + h / 2),
            "right": (bx2, by1 + h / 2),
        }
        start_side, (sx, sy) = min(
            candidates.items(),
            key=lambda kv: (kv[1][0] - tip_x) ** 2 + (kv[1][1] - tip_y) ** 2,
        )

        r0 = trail_r_start if trail_r_start > 0 else max(2.0, min(w, h) * 0.08)
        r1 = trail_r_end if trail_r_end > 0 else max(1.0, r0 * 0.35)

        # March from (sx, sy) toward (tip_x, tip_y). The first bubble's centre
        # sits a small step outside the body so it doesn't overlap the cloud.
        # The last bubble's centre sits just shy of the tip so the tip stays
        # visible as a "pointing" terminus.
        dx, dy = tip_x - sx, tip_y - sy
        length = math.hypot(dx, dy)
        ux, uy = (dx / length, dy / length) if length > 0 else (0.0, 0.0)

        anchors["trail-start-side"] = Point(sx, sy)

        for i in range(trail_bubbles):
            # Position parameter t in (0, 1): 0 = at body edge, 1 = at tip.
            if trail_bubbles == 1:
                t = 0.5
            else:
                t = (i + 1) / (trail_bubbles + 1)
            cx_i = sx + ux * length * t
            cy_i = sy + uy * length * t
            r_i = r0 + (r1 - r0) * (i / max(1, trail_bubbles - 1))
            # Ellipse slightly squashed vertically for a more "puffy" feel.
            rx_i = r_i
            ry_i = r_i * 0.85
            if mode == "filled":
                trail_svgs.append(
                    f'<ellipse cx="{cx_i:.2f}" cy="{cy_i:.2f}" rx="{rx_i:.2f}" ry="{ry_i:.2f}" '
                    f'fill="{{accent}}" fill-opacity="0.08" stroke="{{accent}}" stroke-width="1"/>'
                )
            else:
                trail_svgs.append(
                    f'<ellipse cx="{cx_i:.2f}" cy="{cy_i:.2f}" rx="{rx_i:.2f}" ry="{ry_i:.2f}" '
                    f'fill="none" stroke="{{accent}}" stroke-width="1"/>'
                )
            anchors[f"trail-{i + 1}"] = Point(cx_i, cy_i)

    # Wrap body + trail in one <g>.
    parts = [body.svg, *trail_svgs]
    id_attr = f' id="{element_id}"' if element_id else ""
    svg = f"<g{id_attr}>\n  " + "\n  ".join(parts) + "\n</g>"

    kind = "thought-cloud"
    if trail_svgs:
        kind += f"+trail-{len(trail_svgs)}"

    return PrimitiveResult(kind, anchors, svg, body.path_d), warnings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


# Caveman-style one-liners per primitive (drop articles + copulas; keep
# technical accuracy). Used by --caveman in the catalogue. Edit alongside
# `_PRIMITIVE_GROUPS` whenever a new primitive lands.
_CAVEMAN_HELP: dict[str, str] = {
    "rect": "box. round corners maybe",
    "square": "box. equal sides",
    "circle": "round. 8 anchor points",
    "ellipse": "egg. two radii",
    "diamond": "tilted box",
    "hexagon": "6-side. flat or pointy top",
    "star": "spike thing. N points",
    "arc": "pie slice",
    "cube": "3D box. iso view",
    "cuboid": "3D box. w/h/d each different",
    "cylinder": "tube. ellipse top + bottom",
    "sphere": "ball. shaded",
    "plane": "tilted flat thing",
    "pyramid": "3D triangle peak",
    "gear": "tooth wheel",
    "cloud": "lumpy puff",
    "document": "paper. corner fold",
    "speech": "say-bubble + spike at tip. one path",
    "thought": "think-cloud + small-bubble trail to thinker",
    "spline": "smooth curve thru points",
    "axis": "x y z lines + ticks",
}

# Verbose one-liners shown when --caveman is NOT set. Mirror the help= strings
# on the subparsers so this list is the single source of truth for the catalogue.
_FULL_HELP: dict[str, str] = {
    "rect": "Rectangle (optional rounded corners, accent bar)",
    "square": "Square (equal sides)",
    "circle": "Circle with cardinal + diagonal anchors",
    "ellipse": "Ellipse with two radii",
    "diamond": "Diamond / rhombus",
    "hexagon": "Regular hexagon (flat or pointy top)",
    "star": "Regular star polygon (N points)",
    "arc": "Circular arc sector (pie slice)",
    "cube": "Isometric cube (filled or wireframe)",
    "cuboid": "Isometric cuboid (independent w/h/d)",
    "cylinder": "Cylinder with elliptical faces (filled or wireframe)",
    "sphere": "Sphere with shading (filled or wireframe)",
    "plane": "Isometric plane (tilted flat surface)",
    "pyramid": "Isometric 3D pyramid (filled or wireframe)",
    "gear": "Toothed gear wheel (filled or outline)",
    "cloud": "Lobed cloud shape (filled or outline)",
    "document": "Document shape with folded top-right corner",
    "speech": "Speech bubble (rect / soft-rect / ellipse) optionally merged with a callout spike at --tip-x, --tip-y",
    "thought": "Thought bubble (lobed cloud) optionally followed by a trail of small ellipses pointing at --tip-x, --tip-y",
    "spline": "Smooth PCHIP spline through control points",
    "axis": "Coordinate axes (x / y / xy / xyz) with ticks",
}

# Catalogue groups for the --list / bare-args display.
_PRIMITIVE_GROUPS: list[tuple[str, list[str]]] = [
    ("2D shapes", ["rect", "square", "circle", "ellipse", "diamond", "hexagon", "star", "arc"]),
    ("3D / isometric", ["cube", "cuboid", "cylinder", "sphere", "plane", "pyramid"]),
    ("Decorative", ["gear", "cloud", "document"]),
    ("Speech / thought bubbles", ["speech", "thought"]),
    ("Curves & layout", ["spline", "axis"]),
]


def _print_primitives_catalogue(caveman: bool = False) -> None:
    """Print every primitive grouped by family, one line each.

    `caveman=False` uses the long help string; `caveman=True` uses the terse
    `_CAVEMAN_HELP` variant. Both follow the same grouping.
    """
    desc_map = _CAVEMAN_HELP if caveman else _FULL_HELP
    header = "svg-infographics primitives - shape generators" + (" (caveman)" if caveman else "")
    print(header)
    print()
    for group, names in _PRIMITIVE_GROUPS:
        print(f"  {group}")
        for name in names:
            print(f"    {name:<12} {desc_map[name]}")
        print()
    print("Run 'svg-infographics primitives <name> --help' for the full flags of one primitive.")
    if not caveman:
        print("Run 'svg-infographics primitives --caveman' for ultra-terse one-liners.")


def _print_result(result: PrimitiveResult):
    """Print primitive result with anchors and SVG."""
    print(f"Primitive: {result.kind}")
    print()
    print("Anchors:")
    for name, pt in result.anchors.items():
        print(f"  {name}: ({pt.x}, {pt.y})")
    print()
    print("SVG snippet:")
    for line in result.svg.split("\n"):
        print(f"  {line}")
    if result.path_d:
        print()
        print(f'Path data:\n  d="{result.path_d}"')


def main():
    # Catalogue mode: bare invocation OR explicit --list / --caveman without a
    # primitive name → print the grouped catalogue and exit cleanly. This is a
    # friendlier fallback than argparse's "primitive required" error and gives
    # users a way to discover what's available without `--help`.
    argv = sys.argv[1:]
    if argv in ([], ["--list"], ["list"]):
        _print_primitives_catalogue(caveman=False)
        return 0
    if argv in (["--caveman"], ["caveman"], ["--list", "--caveman"], ["--caveman", "--list"]):
        _print_primitives_catalogue(caveman=True)
        return 0

    parser = argparse.ArgumentParser(
        prog="svg-infographics primitives",
        description="Generate SVG primitive geometry with exact coordinates. "
        "Run with no args, '--list', or '--caveman' to see the catalogue of available primitives.",
    )
    sub = parser.add_subparsers(dest="primitive", required=True)

    # rect
    p = sub.add_parser("rect", help="Rectangle (optional rounded corners, accent bar)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--radius", type=float, default=0, help="Corner radius (default: 0)")
    p.add_argument("--accent", action="store_true", help="Add accent bar")

    # square
    p = sub.add_parser("square", help="Square (equal sides)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--size", type=float, required=True)
    p.add_argument("--radius", type=float, default=0)

    # circle
    p = sub.add_parser("circle", help="Circle with cardinal + diagonal anchors")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--r", type=float, required=True)

    # ellipse
    p = sub.add_parser("ellipse", help="Ellipse")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--rx", type=float, required=True)
    p.add_argument("--ry", type=float, required=True)

    # cube
    p = sub.add_parser("cube", help="Isometric cube (fill or wireframe)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--depth", type=float, default=0, help="Depth (default: width*0.4)")
    p.add_argument("--mode", choices=["fill", "wire"], default="fill")

    # cylinder
    p = sub.add_parser("cylinder", help="Cylinder with elliptical faces (fill or wireframe)")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True, help="Center of top ellipse")
    p.add_argument("--rx", type=float, required=True)
    p.add_argument("--ry", type=float, required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--mode", choices=["fill", "wire"], default="fill")

    # diamond
    p = sub.add_parser("diamond", help="Diamond / rhombus")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--height", type=float, required=True)

    # hexagon
    p = sub.add_parser("hexagon", help="Regular hexagon")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--r", type=float, required=True, help="Circumradius")
    p.add_argument("--pointy-top", action="store_true", help="Pointy-top orientation")

    # star
    p = sub.add_parser("star", help="Regular star polygon")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--r", type=float, required=True, help="Outer radius")
    p.add_argument("--inner-r", type=float, default=0, help="Inner radius (default: r*0.4)")
    p.add_argument("--points", type=int, default=5, help="Number of points (default: 5)")

    # arc
    p = sub.add_parser("arc", help="Circular arc sector (pie slice)")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--r", type=float, required=True)
    p.add_argument("--start", type=float, required=True, help="Start angle (degrees, 0=right)")
    p.add_argument("--end", type=float, required=True, help="End angle (degrees)")

    # sphere
    p = sub.add_parser("sphere", help="Sphere with shading (fill or wireframe)")
    p.add_argument("--cx", type=float, required=True)
    p.add_argument("--cy", type=float, required=True)
    p.add_argument("--r", type=float, required=True)
    p.add_argument("--mode", choices=["fill", "wire"], default="fill")

    # cuboid
    p = sub.add_parser("cuboid", help="Isometric cuboid (independent w/h/d)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--depth", type=float, required=True)
    p.add_argument("--mode", choices=["fill", "wire"], default="fill")

    # plane
    p = sub.add_parser("plane", help="Isometric plane (tilted surface)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--width", type=float, required=True)
    p.add_argument("--depth", type=float, required=True)
    p.add_argument("--tilt", type=float, default=30, help="Projection angle (default: 30)")

    # gear
    p = sub.add_parser("gear", help="Toothed gear wheel (filled or outline)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--outer-r", type=float, required=True, help="Outer (tip) radius")
    p.add_argument(
        "--inner-r", type=float, default=0, help="Inner (root) radius (default: outer_r*0.7)"
    )
    p.add_argument("--teeth", type=int, default=12, help="Number of teeth (default: 12)")
    p.add_argument("--mode", choices=["filled", "outline"], default="filled")

    # pyramid
    p = sub.add_parser("pyramid", help="Isometric 3D pyramid (filled or wireframe)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--base-w", type=float, required=True, help="Base width")
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--mode", choices=["filled", "wire"], default="filled")

    # cloud
    p = sub.add_parser("cloud", help="Cloud shape with lobe bumps (filled or outline)")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--w", type=float, required=True)
    p.add_argument("--h", type=float, required=True)
    p.add_argument("--lobes", type=int, default=5, help="Number of top bumps (default: 5)")
    p.add_argument("--mode", choices=["filled", "outline"], default="filled")

    # document
    p = sub.add_parser("document", help="Document shape with folded top-right corner")
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--w", type=float, required=True)
    p.add_argument("--h", type=float, required=True)
    p.add_argument("--fold", type=float, default=0, help="Fold size (default: min(w,h)*0.2)")
    p.add_argument("--mode", choices=["filled", "outline"], default="filled")

    # speech (bubble + optional callout spike)
    p = sub.add_parser(
        "speech",
        help="Speech bubble: rect / soft-rect / ellipse body, optionally merged with a callout spike at --tip-x, --tip-y. Omit tip for a bare body (quote box).",
    )
    p.add_argument("--x", type=float, required=True, help="Body top-left x")
    p.add_argument("--y", type=float, required=True, help="Body top-left y")
    p.add_argument("--w", type=float, required=True, help="Body width")
    p.add_argument("--h", type=float, required=True, help="Body height")
    p.add_argument(
        "--tip-x",
        type=float,
        default=None,
        help="Spike apex x. Omit (along with --tip-y) for a bubble without a callout.",
    )
    p.add_argument(
        "--tip-y",
        type=float,
        default=None,
        help="Spike apex y. Omit (along with --tip-x) for a bubble without a callout.",
    )
    p.add_argument(
        "--shape",
        choices=["rect", "soft-rect", "ellipse"],
        default="soft-rect",
        help="Body shape (default: soft-rect)",
    )
    p.add_argument(
        "--corner-radius",
        type=float,
        default=12.0,
        help="Uniform corner radius for soft-rect (default 12). Overridden by --rx/--ry when set.",
    )
    p.add_argument(
        "--rx",
        type=float,
        default=None,
        help="Soft-rect horizontal corner radius (elliptical corners). Pair with --ry.",
    )
    p.add_argument(
        "--ry",
        type=float,
        default=None,
        help="Soft-rect vertical corner radius (elliptical corners). Pair with --rx.",
    )
    p.add_argument(
        "--spike-base-width",
        type=float,
        default=20.0,
        help="Spike base width along the bubble edge in px (default 20)",
    )
    p.add_argument(
        "--spike-anchor",
        choices=["auto", "top", "bottom", "left", "right"],
        default="auto",
        help="rect / soft-rect: pick the edge the spike attaches to (default auto, the edge nearest the tip). Ellipse always uses the centre->tip ray; explicit values are warned and overridden.",
    )
    p.add_argument(
        "--text-padding",
        type=float,
        default=10.0,
        help="Uniform inset for the text-area anchor inside the bubble (default 10)",
    )
    p.add_argument(
        "--text-padding-x",
        type=float,
        default=None,
        help="Per-axis horizontal text-area inset (overrides --text-padding on x)",
    )
    p.add_argument(
        "--text-padding-y",
        type=float,
        default=None,
        help="Per-axis vertical text-area inset (overrides --text-padding on y)",
    )
    p.add_argument(
        "--id",
        dest="element_id",
        type=str,
        default=None,
        help='Set id="<NAME>" on the emitted <path> so --replace-id in boolean can target it later',
    )
    p.add_argument("--mode", choices=["filled", "outline"], default="filled")

    # thought (lobed cloud + optional trail of decreasing bubbles)
    p = sub.add_parser(
        "thought",
        help="Thought bubble: lobed cloud body, optionally followed by a trail of small ellipses pointing at --tip-x, --tip-y. Omit tip for a bare cloud.",
    )
    p.add_argument("--x", type=float, required=True, help="Body top-left x")
    p.add_argument("--y", type=float, required=True, help="Body top-left y")
    p.add_argument("--w", type=float, required=True, help="Body width")
    p.add_argument("--h", type=float, required=True, help="Body height")
    p.add_argument(
        "--tip-x",
        type=float,
        default=None,
        help="Trail terminus x. Omit (along with --tip-y) for a cloud without a trail.",
    )
    p.add_argument(
        "--tip-y",
        type=float,
        default=None,
        help="Trail terminus y. Omit (along with --tip-x) for a cloud without a trail.",
    )
    p.add_argument("--lobes", type=int, default=5, help="Number of cloud lobes (default 5)")
    p.add_argument(
        "--trail-bubbles",
        type=int,
        default=3,
        help="Trail bubbles between body and tip (default 3; 0 = no trail). Requires tip.",
    )
    p.add_argument(
        "--trail-r-start",
        type=float,
        default=0.0,
        help="First (largest) trail-bubble radius; default min(w,h)*0.08",
    )
    p.add_argument(
        "--trail-r-end",
        type=float,
        default=0.0,
        help="Last (smallest) trail-bubble radius; default trail-r-start * 0.35",
    )
    p.add_argument(
        "--text-padding", type=float, default=12.0, help="Uniform text-area inset (default 12)"
    )
    p.add_argument(
        "--text-padding-x",
        type=float,
        default=None,
        help="Per-axis horizontal text-area inset (overrides --text-padding on x)",
    )
    p.add_argument(
        "--text-padding-y",
        type=float,
        default=None,
        help="Per-axis vertical text-area inset (overrides --text-padding on y)",
    )
    p.add_argument(
        "--id",
        dest="element_id",
        type=str,
        default=None,
        help='Set id="<NAME>" on the outer <g>',
    )
    p.add_argument("--mode", choices=["filled", "outline"], default="filled")

    # spline
    p = sub.add_parser("spline", help="Smooth PCHIP spline through control points")
    p.add_argument(
        "--points", required=True, help="Control points: 'x1,y1 x2,y2 ...' (x strictly increasing)"
    )
    p.add_argument("--samples", type=int, default=50, help="Interpolation points (default: 50)")
    p.add_argument("--closed", action="store_true", help="Close path with Z")

    # axis
    p = sub.add_parser("axis", help="Coordinate axes (x, y, xy, xyz)")
    p.add_argument("--origin", required=True, help="Origin point: 'x,y'")
    p.add_argument("--length", type=float, required=True, help="Axis length in pixels")
    p.add_argument(
        "--axes",
        default="xy",
        choices=["x", "y", "xy", "xyz"],
        help="Which axes to draw (default: xy)",
    )
    p.add_argument("--ticks", type=int, default=0, help="Number of ticks per axis")
    p.add_argument("--tick-spacing", type=float, default=0, help="Pixels between ticks")
    p.add_argument("--no-labels", action="store_true", help="Omit axis labels")

    args = parser.parse_args()

    if args.primitive == "rect":
        result = gen_rect(
            args.x,
            args.y,
            args.width,
            args.height,
            r=args.radius,
            accent="accent" if args.accent else "",
        )
    elif args.primitive == "square":
        result = gen_square(args.x, args.y, args.size, r=args.radius)
    elif args.primitive == "circle":
        result = gen_circle(args.cx, args.cy, args.r)
    elif args.primitive == "ellipse":
        result = gen_ellipse(args.cx, args.cy, args.rx, args.ry)
    elif args.primitive == "diamond":
        result = gen_diamond(args.cx, args.cy, args.width, args.height)
    elif args.primitive == "hexagon":
        result = gen_hexagon(args.cx, args.cy, args.r, flat_top=not args.pointy_top)
    elif args.primitive == "star":
        result = gen_star(args.cx, args.cy, args.r, inner_r=args.inner_r, points=args.points)
    elif args.primitive == "arc":
        result = gen_arc(args.cx, args.cy, args.r, args.start, args.end)
    elif args.primitive == "cube":
        result = gen_cube(
            args.x, args.y, args.width, args.height, depth=args.depth, mode=args.mode
        )
    elif args.primitive == "cylinder":
        result = gen_cylinder(args.cx, args.cy, args.rx, args.ry, args.height, mode=args.mode)
    elif args.primitive == "sphere":
        result = gen_sphere(args.cx, args.cy, args.r, mode=args.mode)
    elif args.primitive == "cuboid":
        result = gen_cuboid(args.x, args.y, args.width, args.height, args.depth, mode=args.mode)
    elif args.primitive == "plane":
        result = gen_plane(args.x, args.y, args.width, args.depth, tilt=args.tilt)
    elif args.primitive == "gear":
        result = gen_gear(
            args.x, args.y, args.outer_r, inner_r=args.inner_r, teeth=args.teeth, mode=args.mode
        )
    elif args.primitive == "pyramid":
        result = gen_pyramid(args.x, args.y, args.base_w, args.height, mode=args.mode)
    elif args.primitive == "cloud":
        result = gen_cloud(args.x, args.y, args.w, args.h, lobes=args.lobes, mode=args.mode)
    elif args.primitive == "document":
        result = gen_document(args.x, args.y, args.w, args.h, fold=args.fold, mode=args.mode)
    elif args.primitive == "speech":
        result, warnings = gen_speech_bubble(
            args.x,
            args.y,
            args.w,
            args.h,
            tip_x=args.tip_x,
            tip_y=args.tip_y,
            shape=args.shape,
            corner_radius=args.corner_radius,
            rx=args.rx,
            ry=args.ry,
            spike_base_width=args.spike_base_width,
            spike_anchor=args.spike_anchor,
            text_padding=args.text_padding,
            text_padding_x=args.text_padding_x,
            text_padding_y=args.text_padding_y,
            element_id=args.element_id,
            mode=args.mode,
        )
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)
    elif args.primitive == "thought":
        result, warnings = gen_thought_bubble(
            args.x,
            args.y,
            args.w,
            args.h,
            tip_x=args.tip_x,
            tip_y=args.tip_y,
            lobes=args.lobes,
            trail_bubbles=args.trail_bubbles,
            trail_r_start=args.trail_r_start,
            trail_r_end=args.trail_r_end,
            text_padding_x=args.text_padding_x,
            text_padding_y=args.text_padding_y,
            element_id=args.element_id,
            text_padding=args.text_padding,
            mode=args.mode,
        )
        for w in warnings:
            print(f"WARNING: {w}", file=sys.stderr)
    elif args.primitive == "spline":
        coords = re.findall(r"[-+]?\d*\.?\d+", args.points)
        if len(coords) < 4 or len(coords) % 2 != 0:
            print("Error: need at least 2 points as 'x1,y1 x2,y2 ...'", file=sys.stderr)
            sys.exit(1)
        pts = [(float(coords[i]), float(coords[i + 1])) for i in range(0, len(coords), 2)]
        result = gen_spline(pts, num_samples=args.samples, closed=args.closed)
    elif args.primitive == "axis":
        ox, oy = [float(v) for v in args.origin.split(",")]
        result = gen_axis(
            ox,
            oy,
            args.length,
            axes=args.axes,
            tick_spacing=args.tick_spacing,
            tick_count=args.ticks,
            labels=not args.no_labels,
        )

    _print_result(result)


if __name__ == "__main__":
    main()
