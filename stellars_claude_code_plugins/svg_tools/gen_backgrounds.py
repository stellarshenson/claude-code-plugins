"""Procedural SVG background geometry generator.

Returns geometry primitives (paths, shapes, coordinates) that Claude
styles and places. Same contract philosophy as calc_primitives - the
tool computes geometry, the agent applies CSS classes and theme.

Each generator returns a ``BackgroundResult`` with unstyled SVG elements
tagged by role (trace, node, contour, knot, star, etc.) so Claude can
style each role independently.

Types:
    circuit      - PCB traces with 45-deg diagonals, pads, vias
    neural       - Dendritic branching via space colonization
    topo         - Contour lines from noise field
    grid         - Engineering grid with markers
    organic      - Flow-field streamlines from noise
    celtic       - Interlocking knot bands
    scifi        - HUD brackets, reticles, scan lines
    constellation - Star field with Delaunay connectivity
    flourish     - Bezier scrollwork with spiral caps
    geometric    - Hex/triangle/diamond tessellation
    crystalline  - Voronoi cell edges

Usage:
    svg-infographics background --type circuit --w 1000 --h 280 --density medium
    svg-infographics background --type topo --w 1000 --h 400 --density low --preview
    svg-infographics background --list
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import math
import random
import sys

import numpy as np

# Optional imports - degrade gracefully
try:
    import opensimplex as _simplex
except ImportError:
    _simplex = None

try:
    from scipy.ndimage import gaussian_filter as _gaussian_filter
    from scipy.spatial import Delaunay as _Delaunay
    from scipy.spatial import Voronoi as _Voronoi
except ImportError:
    _Voronoi = _Delaunay = _gaussian_filter = None


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class BackgroundElement:
    """Single geometry piece in a background pattern."""

    kind: str  # "path", "circle", "rect", "polygon", "line"
    svg: str  # unstyled SVG snippet (no class/fill/stroke attributes)
    role: str  # semantic role: "trace", "node", "pad", "contour", "knot", "star", etc.
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)  # x, y, w, h


@dataclass
class BackgroundResult:
    """Result of background generation - geometry for Claude to style."""

    bg_type: str
    elements: list[BackgroundElement] = field(default_factory=list)
    svg: str = ""  # all elements combined as unstyled SVG (convenience)
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)  # overall bounds

    def build_svg(self):
        """Combine all element SVGs into a single group."""
        parts = [e.svg for e in self.elements]
        self.svg = "\n".join(parts)
        return self.svg


# ---------------------------------------------------------------------------
# Density presets
# ---------------------------------------------------------------------------

_DENSITY = {
    "sparse": {"factor": 0.3, "branch_p": 0.12, "node_p": 0.25},
    "low": {"factor": 0.5, "branch_p": 0.18, "node_p": 0.35},
    "medium": {"factor": 1.0, "branch_p": 0.30, "node_p": 0.55},
    "high": {"factor": 1.8, "branch_p": 0.45, "node_p": 0.75},
    "dense": {"factor": 3.0, "branch_p": 0.60, "node_p": 0.90},
}

_DIRECTIONS = ("right", "down", "left", "up", "radial")

BG_TYPES = [
    "circuit",
    "neural",
    "topo",
    "grid",
    "organic",
    "celtic",
    "scifi",
    "constellation",
    "flourish",
    "geometric",
    "crystalline",
]


def _rng(seed=None):
    return random.Random(seed)


def _snap(v, grid):
    """Snap value to nearest grid point."""
    return round(v / grid) * grid


# ---------------------------------------------------------------------------
# Circuit: PCB traces with 45-degree diagonals, pads, vias
# ---------------------------------------------------------------------------


def _gen_circuit(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor, branch_p, node_p = d["factor"], d["branch_p"], d["node_p"]
    grid = max(6, int(15 / max(factor, 0.3)))
    elements = []

    n_roots = max(3, int(6 * factor))

    for _ in range(n_roots):
        # Root on an edge based on direction
        if direction in ("right", "radial"):
            sx = _snap(rng.uniform(0, w * 0.15), grid)
        elif direction == "left":
            sx = _snap(rng.uniform(w * 0.85, w), grid)
        else:
            sx = _snap(rng.uniform(w * 0.1, w * 0.9), grid)
        if direction == "down":
            sy = _snap(rng.uniform(0, h * 0.15), grid)
        elif direction == "up":
            sy = _snap(rng.uniform(h * 0.85, h), grid)
        else:
            sy = _snap(rng.uniform(h * 0.05, h * 0.95), grid)

        _circuit_tree(
            sx, sy, w, h, grid, direction, branch_p, node_p, elements, rng, depth=0, tw=1.4
        )

    return elements


def _circuit_tree(x, y, w, h, grid, direction, branch_p, node_p, elements, rng, depth, tw):
    """Grow a circuit trace tree: long segments with orthogonal + diagonal routing."""
    if depth > 4:
        return

    pts = [(x, y)]
    n_segments = rng.randint(3, 8 - depth)
    cur_tw = max(0.3, tw - depth * 0.2)

    # Primary angle based on direction
    if direction == "right":
        base_angle = 0
    elif direction == "left":
        base_angle = math.pi
    elif direction == "down":
        base_angle = math.pi / 2
    elif direction == "up":
        base_angle = -math.pi / 2
    else:
        base_angle = rng.uniform(0, 2 * math.pi)

    for seg in range(n_segments):
        # Long straight segment in primary direction with drift
        seg_len = _snap(rng.uniform(grid * 4, grid * 12), grid)

        # Occasionally diagonal (45-deg offset from base)
        if rng.random() < 0.35:
            angle = base_angle + rng.choice([-math.pi / 4, math.pi / 4])
        else:
            angle = base_angle + rng.gauss(0, 0.15)

        nx = _snap(x + seg_len * math.cos(angle), grid)
        ny = _snap(y + seg_len * math.sin(angle), grid)
        nx = max(0, min(w, nx))
        ny = max(0, min(h, ny))

        if nx == x and ny == y:
            continue

        pts.append((nx, ny))

        # Small junction node at branch points
        if rng.random() < node_p * 0.5:
            r = rng.uniform(1.2, 2.5)
            elements.append(
                BackgroundElement(
                    "circle",
                    f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="{r:.1f}"/>',
                    "via",
                    (nx - r, ny - r, r * 2, r * 2),
                )
            )

        # Branch off
        if rng.random() < branch_p:
            branch_angle = angle + rng.choice(
                [-math.pi / 2, math.pi / 2, -math.pi / 4, math.pi / 4]
            )
            _circuit_branch(
                nx,
                ny,
                w,
                h,
                grid,
                branch_angle,
                branch_p * 0.5,
                node_p,
                elements,
                rng,
                depth + 1,
                cur_tw,
            )

        x, y = nx, ny

    # Endpoint pad
    if rng.random() < node_p:
        ps = rng.uniform(3, 6)
        elements.append(
            BackgroundElement(
                "rect",
                f'<rect x="{x - ps / 2:.1f}" y="{y - ps / 2:.1f}" '
                f'width="{ps:.1f}" height="{ps:.1f}" rx="1"/>',
                "pad",
                (x - ps / 2, y - ps / 2, ps, ps),
            )
        )

    # Emit trace
    if len(pts) > 1:
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d}" stroke-width="{cur_tw:.1f}"/>',
                "trace",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )


def _circuit_branch(x, y, w, h, grid, angle, branch_p, node_p, elements, rng, depth, tw):
    """Short branch off a main circuit trace."""
    if depth > 5:
        return
    pts = [(x, y)]
    n_segs = rng.randint(1, 4)
    cur_tw = max(0.25, tw - depth * 0.15)

    for _ in range(n_segs):
        seg_len = _snap(rng.uniform(grid * 2, grid * 6), grid)
        # Slight wobble around branch angle
        a = angle + rng.gauss(0, 0.2)
        nx = _snap(x + seg_len * math.cos(a), grid)
        ny = _snap(y + seg_len * math.sin(a), grid)
        nx = max(0, min(w, nx))
        ny = max(0, min(h, ny))
        if nx == x and ny == y:
            break
        pts.append((nx, ny))

        if rng.random() < branch_p:
            sub_angle = a + rng.choice([-math.pi / 3, math.pi / 3])
            _circuit_branch(
                nx,
                ny,
                w,
                h,
                grid,
                sub_angle,
                branch_p * 0.4,
                node_p,
                elements,
                rng,
                depth + 1,
                cur_tw,
            )
        x, y = nx, ny

    # Small endpoint
    if rng.random() < node_p * 0.6:
        r = rng.uniform(0.8, 2)
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}"/>',
                "via",
                (x - r, y - r, r * 2, r * 2),
            )
        )

    if len(pts) > 1:
        d = "M" + " L".join(f"{px:.1f},{py:.1f}" for px, py in pts)
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d}" stroke-width="{cur_tw:.1f}"/>',
                "trace",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )


# ---------------------------------------------------------------------------
# Neural: space colonization dendritic branching
# ---------------------------------------------------------------------------


def _gen_neural(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    # Scatter attraction points
    n_attractors = max(20, int(60 * factor))
    attractors = [
        (rng.uniform(w * 0.05, w * 0.95), rng.uniform(h * 0.05, h * 0.95))
        for _ in range(n_attractors)
    ]

    # Seed roots based on direction
    n_seeds = max(2, int(4 * factor))
    seeds = []
    for _ in range(n_seeds):
        if direction == "down":
            seeds.append((rng.uniform(w * 0.1, w * 0.9), h * 0.02))
        elif direction == "up":
            seeds.append((rng.uniform(w * 0.1, w * 0.9), h * 0.98))
        elif direction == "right":
            seeds.append((w * 0.02, rng.uniform(h * 0.1, h * 0.9)))
        elif direction == "left":
            seeds.append((w * 0.98, rng.uniform(h * 0.1, h * 0.9)))
        else:
            seeds.append((w * 0.5 + rng.gauss(0, w * 0.1), h * 0.5 + rng.gauss(0, h * 0.1)))

    # Grow from seeds toward attractors
    reach = max(w, h) * 0.15
    step = max(w, h) * 0.03
    branches = []  # list of (points, width)

    for sx, sy in seeds:
        _neural_grow(sx, sy, attractors, w, h, reach, step, branches, rng, depth=0, tw=1.4)

    for pts, tw in branches:
        if len(pts) < 2:
            continue
        # Smooth quadratic bezier
        d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for i in range(1, len(pts)):
            px, py = pts[i]
            d += f" L{px:.1f},{py:.1f}"
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d}" stroke-width="{tw:.2f}"/>',
                "dendrite",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )

    return elements


def _neural_grow(x, y, attractors, w, h, reach, step, branches, rng, depth, tw):
    if depth > 6 or not attractors:
        return
    pts = [(x, y)]
    for _ in range(rng.randint(4, 10)):
        # Find nearest attractor within reach
        best_d = float("inf")
        best_a = None
        for ax, ay in attractors:
            d = math.hypot(ax - x, ay - y)
            if d < best_d:
                best_d = d
                best_a = (ax, ay)
        if best_a is None or best_d > reach * 3:
            break
        # Step toward it with some noise
        dx = best_a[0] - x
        dy = best_a[1] - y
        dist = math.hypot(dx, dy)
        if dist < 1:
            break
        nx = x + (dx / dist) * step + rng.gauss(0, step * 0.3)
        ny = y + (dy / dist) * step + rng.gauss(0, step * 0.3)
        nx = max(0, min(w, nx))
        ny = max(0, min(h, ny))
        pts.append((nx, ny))
        # Remove attractors that are reached
        attractors[:] = [
            (ax, ay) for ax, ay in attractors if math.hypot(ax - nx, ay - ny) > step * 0.5
        ]
        # Branch
        if rng.random() < 0.2 and depth < 4:
            _neural_grow(
                nx,
                ny,
                attractors,
                w,
                h,
                reach * 0.7,
                step * 0.8,
                branches,
                rng,
                depth + 1,
                tw * 0.65,
            )
        x, y = nx, ny

    if len(pts) > 1:
        branches.append((pts, max(0.3, tw - depth * 0.15)))


# ---------------------------------------------------------------------------
# Topo: contour lines from opensimplex noise
# ---------------------------------------------------------------------------


def _gen_topo(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    if _simplex is None or _gaussian_filter is None:
        return _gen_topo_fallback(w, h, density, direction, rng)

    # Generate noise field
    _simplex.seed(rng.randint(0, 99999))
    res = max(5, min(20, int(40 / factor)))
    nx, ny = max(3, int(w / res) + 1), max(3, int(h / res) + 1)
    freq = 0.008 * factor
    Z = np.array(
        [[_simplex.noise2(x * res * freq, y * res * freq) for x in range(nx)] for y in range(ny)]
    )
    Z = _gaussian_filter(Z, sigma=1.5)

    # Extract contours
    n_levels = max(3, int(6 * factor))
    levels = np.linspace(Z.min() + 0.1, Z.max() - 0.1, n_levels)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots()
    cs = ax.contour(Z, levels=levels)

    for li, level_segs in enumerate(cs.allsegs):
        for seg in level_segs:
            if len(seg) < 3:
                continue
            # Scale to canvas
            pts = [(float(p[0]) * res, float(p[1]) * res) for p in seg]
            d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
            for p in pts[1:]:
                d_str += f" L{p[0]:.1f},{p[1]:.1f}"
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            sw = 0.6 + (li / max(1, n_levels)) * 0.6
            elements.append(
                BackgroundElement(
                    "path",
                    f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                    "contour",
                    (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
                )
            )

    # Medium+: elevation numbers at contour midpoints
    if density in ("medium", "high", "dense"):
        for li, level_segs in enumerate(cs.allsegs):
            for seg in level_segs:
                if len(seg) < 10:
                    continue
                mid = len(seg) // 2
                mx, my = float(seg[mid][0]) * res, float(seg[mid][1]) * res
                elev = int(levels[li] * 1000)
                elements.append(
                    BackgroundElement(
                        "text",
                        f'<text x="{mx:.1f}" y="{my:.1f}" font-size="5">{elev}</text>',
                        "elevation",
                        (mx, my - 5, 18, 7),
                    )
                )

    # Medium+: grid overlay
    if density in ("medium", "high", "dense"):
        grid_sp = max(20, int(50 / factor))
        for gx in range(0, int(w) + 1, grid_sp):
            elements.append(
                BackgroundElement(
                    "line",
                    f'<line x1="{gx}" y1="0" x2="{gx}" y2="{h}" stroke-width="0.2" stroke-dasharray="2,4"/>',
                    "topo-grid",
                    (gx, 0, 0, h),
                )
            )
        for gy in range(0, int(h) + 1, grid_sp):
            elements.append(
                BackgroundElement(
                    "line",
                    f'<line x1="0" y1="{gy}" x2="{w}" y2="{gy}" stroke-width="0.2" stroke-dasharray="2,4"/>',
                    "topo-grid",
                    (0, gy, w, 0),
                )
            )

    # High+: coordinate labels, tick marks, area markers (military map style)
    if density in ("high", "dense"):
        label_sp = max(40, int(80 / factor))
        for gx in range(0, int(w) + 1, label_sp):
            elements.append(
                BackgroundElement(
                    "text",
                    f'<text x="{gx}" y="{h - 2}" font-size="4" font-family="monospace">{gx}</text>',
                    "coord-label",
                    (gx, h - 6, 15, 5),
                )
            )
        for gy in range(0, int(h) + 1, label_sp):
            elements.append(
                BackgroundElement(
                    "text",
                    f'<text x="2" y="{gy + 4}" font-size="4" font-family="monospace">{gy}</text>',
                    "coord-label",
                    (2, gy, 15, 5),
                )
            )
        # Hash marks on thicker contours
        for li, level_segs in enumerate(cs.allsegs):
            if li % 2 != 0:
                continue
            for seg in level_segs:
                if len(seg) < 15:
                    continue
                for k in range(0, len(seg), max(1, len(seg) // 5)):
                    px, py = float(seg[k][0]) * res, float(seg[k][1]) * res
                    elements.append(
                        BackgroundElement(
                            "line",
                            f'<line x1="{px - 2:.1f}" y1="{py - 2:.1f}" '
                            f'x2="{px + 2:.1f}" y2="{py + 2:.1f}" stroke-width="0.4"/>',
                            "hash-mark",
                            (px - 2, py - 2, 4, 4),
                        )
                    )

    plt.close(fig)
    return elements


def _gen_topo_fallback(w, h, density, direction, rng):
    """Sine-wave contours when opensimplex unavailable."""
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []
    n_contours = max(3, int(8 * factor))
    for i in range(n_contours):
        t = (i + 1) / (n_contours + 1)
        base_y = h * t
        pts = []
        steps = max(8, int(w / 25))
        for j in range(steps + 1):
            x = w * j / steps
            y = base_y + rng.gauss(0, h * 0.04) + math.sin(x / w * math.pi * 2) * h * 0.03
            pts.append((x, y))
        d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for k in range(1, len(pts)):
            d_str += f" L{pts[k][0]:.1f},{pts[k][1]:.1f}"
        sw = 0.6 + rng.random() * 0.4
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                "contour",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )
    return elements


# ---------------------------------------------------------------------------
# Grid: engineering grid with markers and ticks
# ---------------------------------------------------------------------------


def _gen_grid(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []
    spacing = max(15, int(50 / factor))

    # Grid lines
    for x in range(0, int(w) + 1, spacing):
        elements.append(
            BackgroundElement(
                "line",
                f'<line x1="{x}" y1="0" x2="{x}" y2="{h}" stroke-width="0.3"/>',
                "gridline",
                (x, 0, 0, h),
            )
        )
    for y in range(0, int(h) + 1, spacing):
        elements.append(
            BackgroundElement(
                "line",
                f'<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke-width="0.3"/>',
                "gridline",
                (0, y, w, 0),
            )
        )

    # Markers at intersections (every Nth)
    skip = max(1, int(3 / factor))
    ix = 0
    for x in range(0, int(w) + 1, spacing):
        iy = 0
        for y in range(0, int(h) + 1, spacing):
            if ix % skip == 0 and iy % skip == 0:
                elements.append(
                    BackgroundElement(
                        "circle",
                        f'<circle cx="{x}" cy="{y}" r="2"/>',
                        "marker",
                        (x - 2, y - 2, 4, 4),
                    )
                )
                # Tick marks
                elements.append(
                    BackgroundElement(
                        "line",
                        f'<line x1="{x - 3}" y1="{y}" x2="{x + 3}" y2="{y}" stroke-width="0.5"/>',
                        "tick",
                        (x - 3, y, 6, 0),
                    )
                )
                elements.append(
                    BackgroundElement(
                        "line",
                        f'<line x1="{x}" y1="{y - 3}" x2="{x}" y2="{y + 3}" stroke-width="0.5"/>',
                        "tick",
                        (x, y - 3, 0, 6),
                    )
                )
            iy += 1
        ix += 1

    return elements


# ---------------------------------------------------------------------------
# Organic: flow-field streamlines from opensimplex noise
# ---------------------------------------------------------------------------


def _gen_organic(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    if _simplex is None:
        # Fallback: simple S-curves
        return _gen_organic_fallback(w, h, density, direction, rng)

    _simplex.seed(rng.randint(0, 99999))
    freq = 0.005
    step_size = max(w, h) * 0.015
    n_lines = max(4, int(10 * factor))
    max_steps = max(20, int(50 * factor))

    for _ in range(n_lines):
        x = rng.uniform(0, w * 0.3)
        y = rng.uniform(h * 0.05, h * 0.95)
        pts = [(x, y)]

        for _ in range(max_steps):
            angle = _simplex.noise2(x * freq, y * freq) * math.pi * 2
            nx = x + math.cos(angle) * step_size
            ny = y + math.sin(angle) * step_size
            if not (0 < nx < w and 0 < ny < h):
                break
            pts.append((nx, ny))
            x, y = nx, ny

        if len(pts) > 3:
            d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
            for p in pts[1:]:
                d_str += f" L{p[0]:.1f},{p[1]:.1f}"
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            sw = 0.5 + rng.random() * 0.6
            elements.append(
                BackgroundElement(
                    "path",
                    f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                    "flow",
                    (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
                )
            )

    return elements


def _gen_organic_fallback(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []
    n_curves = max(3, int(7 * factor))
    for _ in range(n_curves):
        pts = []
        x = rng.uniform(0, w * 0.3)
        y = rng.uniform(h * 0.1, h * 0.9)
        pts.append((x, y))
        for _ in range(rng.randint(4, 8)):
            x += rng.uniform(w * 0.08, w * 0.2)
            y += rng.gauss(0, h * 0.08)
            y = max(0, min(h, y))
            pts.append((x, y))
        d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for i in range(1, len(pts)):
            px, py = pts[i]
            ppx, ppy = pts[i - 1]
            cx = ppx + (px - ppx) * 0.5
            d_str += f" S{cx:.1f},{py:.1f} {px:.1f},{py:.1f}"
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d_str}" stroke-width="0.6"/>',
                "flow",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )
    return elements


# ---------------------------------------------------------------------------
# Celtic: grid-based interlocking knot bands
# ---------------------------------------------------------------------------


def _gen_celtic(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    n_knots = max(2, int(5 * factor))
    for _ in range(n_knots):
        cx = rng.uniform(w * 0.1, w * 0.9)
        cy = rng.uniform(h * 0.15, h * 0.85)
        r = rng.uniform(12, 30)
        loops = rng.randint(2, 4)
        band_w = rng.uniform(2, 4)

        # Spiral band (two parallel spirals for over-under effect)
        for offset in [-band_w / 2, band_w / 2]:
            pts = []
            for t in range(0, 360 * loops, 6):
                angle = math.radians(t)
                sr = r * (1 + t / (360 * loops) * 0.8) + offset
                pts.append((cx + sr * math.cos(angle), cy + sr * math.sin(angle)))

            if len(pts) > 2:
                d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
                for p in pts[1:]:
                    d_str += f" L{p[0]:.1f},{p[1]:.1f}"
                elements.append(
                    BackgroundElement(
                        "path",
                        f'<path d="{d_str}" stroke-width="{band_w:.1f}"/>',
                        "knot-band",
                        (cx - r * 2, cy - r * 2, r * 4, r * 4),
                    )
                )

        # Connecting arcs between knots
        if rng.random() < 0.5:
            ax = cx + rng.uniform(-50, 50)
            ay = cy + rng.uniform(-25, 25)
            ex = cx + rng.uniform(-40, 40)
            ey = cy + rng.uniform(-40, 40)
            elements.append(
                BackgroundElement(
                    "path",
                    f'<path d="M{cx:.1f},{cy:.1f} Q{ax:.1f},{ay:.1f} {ex:.1f},{ey:.1f}" '
                    f'stroke-width="{band_w:.1f}"/>',
                    "knot-arc",
                    (
                        min(cx, ax, ex),
                        min(cy, ay, ey),
                        max(cx, ax, ex) - min(cx, ax, ex),
                        max(cy, ay, ey) - min(cy, ay, ey),
                    ),
                )
            )

    return elements


# ---------------------------------------------------------------------------
# Sci-fi: HUD brackets, reticles, scan lines, hex readouts
# ---------------------------------------------------------------------------


def _gen_scifi(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    # Corner brackets
    n_brackets = max(2, int(5 * factor))
    for _ in range(n_brackets):
        bx = rng.uniform(w * 0.05, w * 0.9)
        by = rng.uniform(h * 0.05, h * 0.9)
        bs = rng.uniform(10, 25)
        bw = rng.uniform(0.8, 1.5)
        # Four corners
        for dx, dy, sx, sy in [
            (0, 0, 1, 1),
            (bs * 2, 0, -1, 1),
            (0, bs, 1, -1),
            (bs * 2, bs, -1, -1),
        ]:
            px = bx + dx
            py = by + dy
            elements.append(
                BackgroundElement(
                    "path",
                    f'<path d="M{px:.1f},{py + bs * 0.4 * sy:.1f} L{px:.1f},{py:.1f} '
                    f'L{px + bs * 0.4 * sx:.1f},{py:.1f}" stroke-width="{bw:.1f}"/>',
                    "bracket",
                    (px - bs * 0.5, py - bs * 0.5, bs, bs),
                )
            )

    # Targeting reticles
    n_targets = max(1, int(3 * factor))
    for _ in range(n_targets):
        tx = rng.uniform(w * 0.15, w * 0.85)
        ty = rng.uniform(h * 0.15, h * 0.85)
        tr = rng.uniform(8, 18)
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="{tr:.1f}" stroke-width="0.8"/>',
                "reticle",
                (tx - tr, ty - tr, tr * 2, tr * 2),
            )
        )
        # Crosshairs
        gap = tr * 0.3
        for x1, y1, x2, y2 in [
            (tx - tr - 5, ty, tx - gap, ty),
            (tx + gap, ty, tx + tr + 5, ty),
            (tx, ty - tr - 5, tx, ty - gap),
            (tx, ty + gap, tx, ty + tr + 5),
        ]:
            elements.append(
                BackgroundElement(
                    "line",
                    f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke-width="0.6"/>',
                    "crosshair",
                    (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)),
                )
            )

    # Scan lines
    n_scans = max(1, int(4 * factor))
    for _ in range(n_scans):
        sy = rng.uniform(h * 0.1, h * 0.9)
        sx = rng.uniform(0, w * 0.3)
        sw = rng.uniform(w * 0.2, w * 0.5)
        elements.append(
            BackgroundElement(
                "line",
                f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{sx + sw:.1f}" y2="{sy:.1f}" '
                f'stroke-width="0.4" stroke-dasharray="3,5"/>',
                "scanline",
                (sx, sy, sw, 0),
            )
        )

    # Hex readout boxes
    n_hex = max(0, int(2 * factor))
    for _ in range(n_hex):
        hx = rng.uniform(w * 0.1, w * 0.9)
        hy = rng.uniform(h * 0.1, h * 0.9)
        hw, hh = rng.uniform(25, 45), rng.uniform(10, 18)
        elements.append(
            BackgroundElement(
                "rect",
                f'<rect x="{hx:.1f}" y="{hy:.1f}" width="{hw:.1f}" height="{hh:.1f}" rx="2" stroke-width="0.6"/>',
                "hex-box",
                (hx, hy, hw, hh),
            )
        )
        hex_str = f"{rng.randint(0, 0xFFFF):04X}"
        elements.append(
            BackgroundElement(
                "text",
                f'<text x="{hx + 3:.1f}" y="{hy + hh - 3:.1f}" font-size="7" font-family="monospace">{hex_str}</text>',
                "hex-text",
                (hx + 3, hy, hw - 6, hh),
            )
        )

    return elements


# ---------------------------------------------------------------------------
# Constellation: Delaunay-connected star field
# ---------------------------------------------------------------------------


def _gen_constellation(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    n_stars = max(10, int(25 * factor))
    stars = np.array(
        [
            (rng.uniform(w * 0.03, w * 0.97), rng.uniform(h * 0.03, h * 0.97))
            for _ in range(n_stars)
        ]
    )

    # Stars with varying brightness
    for sx, sy in stars:
        r = rng.uniform(1, 3.5)
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}"/>',
                "star",
                (sx - r, sy - r, r * 2, r * 2),
            )
        )

    # Delaunay connectivity
    if _Delaunay is not None and len(stars) >= 4:
        tri = _Delaunay(stars)
        max_dist = max(w, h) * 0.3
        seen = set()
        for simplex in tri.simplices:
            for i in range(3):
                a, b = simplex[i], simplex[(i + 1) % 3]
                edge = (min(a, b), max(a, b))
                if edge in seen:
                    continue
                seen.add(edge)
                ax, ay = stars[a]
                bx, by = stars[b]
                dist = math.hypot(bx - ax, by - ay)
                if dist < max_dist:
                    elements.append(
                        BackgroundElement(
                            "line",
                            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke-width="0.4"/>',
                            "connection",
                            (min(ax, bx), min(ay, by), abs(bx - ax), abs(by - ay)),
                        )
                    )
    else:
        # Fallback: connect nearest neighbours
        for i in range(len(stars)):
            for j in range(i + 1, len(stars)):
                dist = math.hypot(stars[j][0] - stars[i][0], stars[j][1] - stars[i][1])
                if dist < max(w, h) * 0.2 and rng.random() < 0.3:
                    elements.append(
                        BackgroundElement(
                            "line",
                            f'<line x1="{stars[i][0]:.1f}" y1="{stars[i][1]:.1f}" '
                            f'x2="{stars[j][0]:.1f}" y2="{stars[j][1]:.1f}" stroke-width="0.4"/>',
                            "connection",
                            (0, 0, w, h),
                        )
                    )

    return elements


# ---------------------------------------------------------------------------
# Flourish: bezier scrollwork with spiral end-caps
# ---------------------------------------------------------------------------


def _gen_flourish(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    n_swirls = max(2, int(6 * factor))
    for _ in range(n_swirls):
        cx = rng.uniform(w * 0.1, w * 0.9)
        cy = rng.uniform(h * 0.1, h * 0.9)
        span = rng.uniform(50, 120)
        lift = rng.uniform(20, 50)
        sw = rng.uniform(0.8, 1.8)

        # Main S-curve
        x0 = cx - span
        x3 = cx + span
        d_str = (
            f"M{x0:.1f},{cy:.1f} "
            f"C{cx - span * 0.4:.1f},{cy - lift:.1f} "
            f"{cx + span * 0.4:.1f},{cy + lift:.1f} "
            f"{x3:.1f},{cy:.1f}"
        )
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                "scroll",
                (x0, cy - lift, span * 2, lift * 2),
            )
        )

        # Spiral end-caps on both ends
        for end_x, chirality in [(x0, -1), (x3, 1)]:
            r = rng.uniform(4, 10)
            pts = []
            for t in range(0, 300, 10):
                angle = math.radians(t) * chirality
                sr = r * (1 - t / 360)
                if sr < 0.5:
                    break
                pts.append((end_x + sr * math.cos(angle), cy + sr * math.sin(angle)))
            if len(pts) > 2:
                d2 = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
                for p in pts[1:]:
                    d2 += f" L{p[0]:.1f},{p[1]:.1f}"
                elements.append(
                    BackgroundElement(
                        "path",
                        f'<path d="{d2}" stroke-width="{sw * 0.7:.1f}"/>',
                        "volute",
                        (end_x - r, cy - r, r * 2, r * 2),
                    )
                )

    return elements


# ---------------------------------------------------------------------------
# Geometric: hex/triangle/diamond tessellation
# ---------------------------------------------------------------------------


def _gen_geometric(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []
    cell = max(15, int(40 / factor))
    shape = rng.choice(["hex", "triangle", "diamond"])
    sw = max(0.5, 1.2 - factor * 0.2)

    if shape == "hex":
        # Proper hex grid
        r = cell * 0.45
        row_h = r * math.sqrt(3)
        row = 0
        y = 0.0
        while y < h + row_h:
            offset = r * 1.5 if row % 2 else 0
            x = offset
            while x < w + r * 2:
                pts = " ".join(
                    f"{x + r * math.cos(math.radians(a)):.1f},"
                    f"{y + r * math.sin(math.radians(a)):.1f}"
                    for a in range(0, 360, 60)
                )
                elements.append(
                    BackgroundElement(
                        "polygon",
                        f'<polygon points="{pts}" stroke-width="{sw:.1f}"/>',
                        "tile",
                        (x - r, y - r, r * 2, r * 2),
                    )
                )
                x += r * 3
            y += row_h
            row += 1

    elif shape == "triangle":
        s = cell * 0.8
        tri_h = s * math.sqrt(3) / 2
        row = 0
        y = 0.0
        while y < h + tri_h:
            x = 0.0
            col = 0
            while x < w + s:
                if (row + col) % 2 == 0:
                    pts = f"{x:.1f},{y + tri_h:.1f} {x + s / 2:.1f},{y:.1f} {x + s:.1f},{y + tri_h:.1f}"
                else:
                    pts = f"{x:.1f},{y:.1f} {x + s / 2:.1f},{y + tri_h:.1f} {x + s:.1f},{y:.1f}"
                elements.append(
                    BackgroundElement(
                        "polygon",
                        f'<polygon points="{pts}" stroke-width="{sw:.1f}"/>',
                        "tile",
                        (x, y, s, tri_h),
                    )
                )
                x += s / 2
                col += 1
            y += tri_h
            row += 1

    else:  # diamond
        s = cell * 0.5
        row = 0
        y = 0.0
        while y < h + s * 2:
            offset = s if row % 2 else 0
            x = offset
            while x < w + s * 2:
                pts = f"{x:.1f},{y - s:.1f} {x + s:.1f},{y:.1f} {x:.1f},{y + s:.1f} {x - s:.1f},{y:.1f}"
                elements.append(
                    BackgroundElement(
                        "polygon",
                        f'<polygon points="{pts}" stroke-width="{sw:.1f}"/>',
                        "tile",
                        (x - s, y - s, s * 2, s * 2),
                    )
                )
                x += s * 2
            y += s
            row += 1

    return elements


# ---------------------------------------------------------------------------
# Crystalline: Voronoi cell edges
# ---------------------------------------------------------------------------


def _gen_crystalline(w, h, density, direction, rng):
    d = _DENSITY[density]
    factor = d["factor"]
    elements = []

    n_seeds = max(8, int(20 * factor))
    seeds = np.array([(rng.uniform(0, w), rng.uniform(0, h)) for _ in range(n_seeds)])

    if _Voronoi is not None and len(seeds) >= 4:
        # Add mirror points for bounded Voronoi
        mirror = np.concatenate(
            [
                seeds,
                np.column_stack([seeds[:, 0], -seeds[:, 1]]),
                np.column_stack([seeds[:, 0], 2 * h - seeds[:, 1]]),
                np.column_stack([-seeds[:, 0], seeds[:, 1]]),
                np.column_stack([2 * w - seeds[:, 0], seeds[:, 1]]),
            ]
        )
        vor = _Voronoi(mirror)

        for ridge in vor.ridge_vertices:
            if -1 in ridge:
                continue
            v0 = vor.vertices[ridge[0]]
            v1 = vor.vertices[ridge[1]]
            if not (0 <= v0[0] <= w and 0 <= v0[1] <= h):
                continue
            if not (0 <= v1[0] <= w and 0 <= v1[1] <= h):
                continue
            elements.append(
                BackgroundElement(
                    "line",
                    f'<line x1="{v0[0]:.1f}" y1="{v0[1]:.1f}" '
                    f'x2="{v1[0]:.1f}" y2="{v1[1]:.1f}" stroke-width="0.6"/>',
                    "cell-edge",
                    (min(v0[0], v1[0]), min(v0[1], v1[1]), abs(v1[0] - v0[0]), abs(v1[1] - v0[1])),
                )
            )
    else:
        # Fallback: angular shards from seed points
        for sx, sy in seeds:
            n_shards = rng.randint(3, 6)
            for _ in range(n_shards):
                angle = rng.uniform(0, 2 * math.pi)
                length = rng.uniform(15, 50)
                ex = sx + length * math.cos(angle)
                ey = sy + length * math.sin(angle)
                elements.append(
                    BackgroundElement(
                        "line",
                        f'<line x1="{sx:.1f}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke-width="0.5"/>',
                        "shard",
                        (min(sx, ex), min(sy, ey), abs(ex - sx), abs(ey - sy)),
                    )
                )

    # Seed points
    for sx, sy in seeds[:n_seeds]:
        r = rng.uniform(1.5, 3)
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="{r:.1f}"/>',
                "seed",
                (sx - r, sy - r, r * 2, r * 2),
            )
        )

    return elements


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_GENERATORS = {
    "circuit": _gen_circuit,
    "neural": _gen_neural,
    "topo": _gen_topo,
    "grid": _gen_grid,
    "organic": _gen_organic,
    "celtic": _gen_celtic,
    "scifi": _gen_scifi,
    "constellation": _gen_constellation,
    "flourish": _gen_flourish,
    "geometric": _gen_geometric,
    "crystalline": _gen_crystalline,
}


def generate_background(
    bg_type: str,
    w: float = 1000,
    h: float = 280,
    density: str = "medium",
    direction: str = "right",
    seed: int | None = None,
) -> BackgroundResult:
    """Generate background geometry as primitives for Claude to style.

    Returns a BackgroundResult with unstyled SVG elements tagged by role.
    Claude wraps each element with CSS classes, opacity, and fade masks.

    Args:
        bg_type: One of BG_TYPES.
        w: Canvas width.
        h: Canvas height.
        density: sparse / low / medium / high / dense.
        direction: right / down / left / up / radial.
        seed: Random seed for reproducibility.
    """
    if bg_type not in _GENERATORS:
        raise ValueError(f"Unknown bg type {bg_type!r}. Choose from: {', '.join(BG_TYPES)}")
    if density not in _DENSITY:
        raise ValueError(f"Unknown density {density!r}. Choose from: {', '.join(_DENSITY)}")

    rng = _rng(seed)
    elements = _GENERATORS[bg_type](w, h, density, direction, rng)

    result = BackgroundResult(bg_type=bg_type, elements=elements, bbox=(0, 0, w, h))
    result.build_svg()
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics background",
        description="Generate procedural SVG background geometry for add-life.",
    )
    parser.add_argument(
        "--type",
        choices=BG_TYPES,
        default="circuit",
        help="Background type (default: circuit)",
    )
    parser.add_argument("--w", type=float, default=1000, help="Canvas width (default: 1000)")
    parser.add_argument("--h", type=float, default=280, help="Canvas height (default: 280)")
    parser.add_argument(
        "--density",
        choices=list(_DENSITY),
        default="medium",
        help="Pattern density (default: medium)",
    )
    parser.add_argument(
        "--direction",
        choices=_DIRECTIONS,
        default="right",
        help="Growth direction (default: right)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--list", action="store_true", help="List types and exit")
    parser.add_argument("--preview", action="store_true", help="Wrap in full SVG for preview")
    parser.add_argument("--json", action="store_true", help="Output element metadata as JSON")
    args = parser.parse_args()

    if args.list:
        print("Available background types:")
        for t in BG_TYPES:
            print(f"  {t}")
        return

    result = generate_background(
        bg_type=args.type,
        w=args.w,
        h=args.h,
        density=args.density,
        direction=args.direction,
        seed=args.seed,
    )

    if args.json:
        import json

        data = {
            "bg_type": result.bg_type,
            "bbox": result.bbox,
            "element_count": len(result.elements),
            "elements": [
                {"kind": e.kind, "role": e.role, "bbox": e.bbox} for e in result.elements
            ],
        }
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    if args.preview:
        print(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {args.w} {args.h}">')
        print(f'  <rect width="{args.w}" height="{args.h}" fill="#0a1a24"/>')
        print('  <g fill="none" stroke="#5cc8e0" opacity="0.5">')
        print('    <g class="bg-nodes" fill="#5cc8e0" stroke="none">')
        for e in result.elements:
            if e.kind in ("circle", "rect", "polygon") and e.role in (
                "pad",
                "via",
                "hole",
                "soma",
                "seed",
                "star",
                "marker",
            ):
                print(f"      {e.svg}")
        print("    </g>")
        print('    <g class="bg-traces">')
        for e in result.elements:
            if e.kind in ("path", "line"):
                print(f"      {e.svg}")
        print("    </g>")
        print("  </g>")
        print("</svg>")
    else:
        print(result.svg)

    print(f"\n<!-- {result.bg_type}: {len(result.elements)} elements -->", file=sys.stderr)


if __name__ == "__main__":
    main()
