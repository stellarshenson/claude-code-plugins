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


def _right_skewed(rng, loc, scale, skew=1.5):
    """Sample from a right-skewed distribution (power transform).

    Most values cluster near loc (thin traces), fewer reach loc + scale (thick).
    skew=1 is uniform, skew=2 gives strong right skew.
    Returns value >= loc * 0.3.
    """
    # Power distribution: u^(1/skew) where u ~ Uniform(0,1)
    # skew > 1 pushes mass toward 0 (thin), long tail toward 1 (thick)
    u = rng.random() ** skew
    return max(loc * 0.3, loc * (0.3 + 1.7 * u) + rng.gauss(0, scale * 0.2))


# ---------------------------------------------------------------------------
# Space colonization engine (Runions et al. 2007) - shared by circuit & neural
# ---------------------------------------------------------------------------


def _idw_density(x, y, w, h, grad_pts):
    """Inverse distance weighted density at (x,y). grad_pts: [(fx,fy,weight),...]"""
    if not grad_pts:
        return 1.0
    total_w, total = 0.0, 0.0
    for fx, fy, wt in grad_pts:
        px, py = fx * w, fy * h
        d2 = (px - x) ** 2 + (py - y) ** 2
        iw = 1.0 / max(1.0, d2)
        total_w += iw
        total += iw * wt
    return total / max(1e-6, total_w)


def _snap_direction_45(dx, dy):
    """Snap (dx,dy) unit vector to nearest 45-degree angle (0, 45, 90, ...)."""
    mag = math.hypot(dx, dy)
    if mag < 1e-6:
        return 1.0, 0.0
    angle = math.atan2(dy, dx)
    snap = round(angle / (math.pi / 4)) * (math.pi / 4)
    return math.cos(snap), math.sin(snap)


def _space_colonize(
    w,
    h,
    rng,
    seeds,
    attractors,
    reach,
    step,
    branch_prob,
    merge_radius=0,
    snap_grid=0,
    use_occupancy=False,
    quantize_45=False,
    max_iterations=40,
    density_fn=None,
):
    """Space colonization tree growth toward attractor goals.

    Args:
        seeds: [(x,y,dx,dy)] - starting points with initial directions
        attractors: [(x,y)] - goal points traces grow toward (consumed on arrival)
        reach: max distance a tip senses attractors
        step: growth distance per iteration (should be large for long traces)
        branch_prob: fork probability per step
        merge_radius: distance to merge into existing chain (0=disabled)
        snap_grid: >0 snaps positions to grid (circuit-style)
        use_occupancy: True enables collision avoidance (circuit)
        quantize_45: True snaps growth direction to nearest 45° (PCB-like)
        density_fn: (x,y) -> 0-1, boosts branching in dense areas,
                    terminates in sparse areas

    Returns: (nodes, edges) where
        nodes: [[x, y, kind, depth], ...]  kind in {root, junction, terminal}
        edges: [(src_idx, dst_idx, depth), ...]  parent-child tree
    """
    nodes = []
    edges = []
    attractor_live = list(attractors)

    def _sn(v):
        return round(v / snap_grid) * snap_grid if snap_grid > 0 else v

    occ = set() if use_occupancy else None
    occ_grid = max(snap_grid, 4) if use_occupancy else 6

    def _mark_occ(x1, y1, x2, y2):
        if occ is None:
            return
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(dist / occ_grid) + 1)
        for i in range(steps + 1):
            t = i / steps
            gx = int(round((x1 + t * (x2 - x1)) / occ_grid))
            gy = int(round((y1 + t * (y2 - y1)) / occ_grid))
            occ.add((gx, gy))

    def _is_clear(x1, y1, x2, y2):
        """Check path is clear. Skip first cell (we grow FROM it - already marked)."""
        if occ is None:
            return True
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(dist / occ_grid) + 1)
        for i in range(1, steps + 1):
            t = i / steps
            gx = int(round((x1 + t * (x2 - x1)) / occ_grid))
            gy = int(round((y1 + t * (y2 - y1)) / occ_grid))
            if (gx, gy) in occ:
                return False
        return True

    margin = step * 0.3
    _att_grid = max(reach * 0.5, 20)
    _att_map = {}

    def _index_attractors():
        _att_map.clear()
        for ai, (ax, ay) in enumerate(attractor_live):
            gx, gy = int(ax / _att_grid), int(ay / _att_grid)
            _att_map.setdefault((gx, gy), set()).add(ai)

    def _find_nearby(tx, ty):
        gx, gy = int(tx / _att_grid), int(ty / _att_grid)
        rc = int(reach / _att_grid) + 1
        result = []
        for ddx in range(-rc, rc + 1):
            for ddy in range(-rc, rc + 1):
                for ai in _att_map.get((gx + ddx, gy + ddy), ()):
                    ax, ay = attractor_live[ai]
                    d = math.hypot(ax - tx, ay - ty)
                    if d < reach:
                        result.append((ai, ax, ay, d))
        return result

    _index_attractors()

    frontier = []
    for sx, sy, dx, dy in seeds:
        idx = len(nodes)
        nodes.append([_sn(sx), _sn(sy), "root", 0])
        # (tip_idx, pref_dx, pref_dy, seed_dx, seed_dy)
        frontier.append((idx, dx, dy, dx, dy))

    # Spatial index of placed nodes for merge detection
    _node_grid = max(step * 0.75, 6)
    _node_map = {}

    def _add_node_index(idx):
        nx_, ny_ = nodes[idx][0], nodes[idx][1]
        gx, gy = int(nx_ / _node_grid), int(ny_ / _node_grid)
        _node_map.setdefault((gx, gy), []).append(idx)

    def _find_merge_target(nx_, ny_, exclude_idx, radius):
        gx, gy = int(nx_ / _node_grid), int(ny_ / _node_grid)
        rc = int(radius / _node_grid) + 1
        best = None
        best_d = radius
        for ddx in range(-rc, rc + 1):
            for ddy in range(-rc, rc + 1):
                for ni in _node_map.get((gx + ddx, gy + ddy), ()):
                    if ni == exclude_idx:
                        continue
                    # Don't merge into root seeds (would short-circuit bus groups)
                    if nodes[ni][2] == "root":
                        continue
                    dx_ = nodes[ni][0] - nx_
                    dy_ = nodes[ni][1] - ny_
                    dd = math.hypot(dx_, dy_)
                    if dd < best_d:
                        best_d = dd
                        best = ni
        return best

    # Index initial seed nodes
    for idx, *_ in frontier:
        _add_node_index(idx)

    for _it in range(max_iterations):
        if not frontier or not attractor_live:
            break
        new_frontier = []
        for tip_idx, pref_dx, pref_dy, seed_dx, seed_dy in frontier:
            tx, ty = nodes[tip_idx][0], nodes[tip_idx][1]
            tip_depth = nodes[tip_idx][3]
            local_d = density_fn(tx, ty) if density_fn else 1.0

            nearby = _find_nearby(tx, ty)
            if not nearby:
                nodes[tip_idx][2] = "terminal"
                continue

            # Density-driven termination (past depth 2): softer contrast
            # At d=0.15 -> 51% terminate, at d=1.0 -> 0%
            if tip_depth > 2 and rng.random() > local_d * 0.75 + 0.25:
                nodes[tip_idx][2] = "terminal"
                continue

            # No hooks: forward filter allows up to ~120° cone from seed
            # and ~150° cone from pref. Rejects U-turns (> 135° from seed).
            forward = []
            for ai, ax, ay, d in nearby:
                # Normalized forward-dot (cosine of angle)
                inv_d = 1.0 / max(1.0, d)
                fdot_seed = ((ax - tx) * seed_dx + (ay - ty) * seed_dy) * inv_d
                fdot_pref = ((ax - tx) * pref_dx + (ay - ty) * pref_dy) * inv_d
                # cos(120°) = -0.5, cos(150°) = -0.87
                if fdot_seed > -0.5 and fdot_pref > -0.87:
                    forward.append((ai, ax, ay, d))
            if forward:
                nearby = forward
            else:
                nodes[tip_idx][2] = "terminal"
                continue

            # Compute raw attractor direction
            avg_dx, avg_dy = 0.0, 0.0
            for _, ax, ay, d in nearby:
                wa = 1.0 / max(1.0, d)
                avg_dx += (ax - tx) * wa
                avg_dy += (ay - ty) * wa
            mag = math.hypot(avg_dx, avg_dy)
            if mag < 0.001:
                att_dx, att_dy = pref_dx, pref_dy
            else:
                att_dx, att_dy = avg_dx / mag, avg_dy / mag

            if quantize_45:
                # PCB: discrete choice among 8 cardinal/diagonal directions.
                # No blending - pick ONE direction with persistence bias so traces
                # form long straight runs then turn only when needed.
                inv_s2 = 1.0 / math.sqrt(2)
                candidates = [
                    (1, 0),
                    (inv_s2, inv_s2),
                    (0, 1),
                    (-inv_s2, inv_s2),
                    (-1, 0),
                    (-inv_s2, -inv_s2),
                    (0, -1),
                    (inv_s2, -inv_s2),
                ]
                best = None
                best_score = -1e9
                for cdx, cdy in candidates:
                    # Persistence (strong): keep previous direction
                    persist = cdx * pref_dx + cdy * pref_dy
                    # Attractor alignment
                    attract = cdx * att_dx + cdy * att_dy
                    # Seed alignment (mild anchor)
                    seed_align = cdx * seed_dx + cdy * seed_dy
                    score = 0.65 * persist + 0.25 * attract + 0.1 * seed_align
                    if score > best_score:
                        best_score = score
                        best = (cdx, cdy)
                avg_dx, avg_dy = best
            else:
                # Neural: progressive fan-out based on depth.
                # Near seed (depth 0-3): bundled, strong seed bias.
                # Middle (depth 4-8): transition.
                # Far (depth 9+): lateral spread dominates.
                depth_factor = min(1.0, tip_depth / 10.0)
                w_seed = 0.7 * (1 - depth_factor) + 0.05 * depth_factor
                w_pref = 0.2 * (1 - depth_factor) + 0.25 * depth_factor
                w_att = 0.1 * (1 - depth_factor) + 0.5 * depth_factor
                avg_dx = w_seed * seed_dx + w_pref * pref_dx + w_att * att_dx
                avg_dy = w_seed * seed_dy + w_pref * pref_dy + w_att * att_dy
                # Add lateral push past depth 4: perpendicular to seed direction
                if depth_factor > 0.3:
                    perp_dx, perp_dy = -seed_dy, seed_dx
                    # Deterministic lateral side per tip lineage (hash of tip_idx)
                    lateral_sign = 1 if (tip_idx * 2654435761) & 0x40000000 else -1
                    lateral = (depth_factor - 0.3) * 0.35
                    avg_dx += lateral_sign * perp_dx * lateral
                    avg_dy += lateral_sign * perp_dy * lateral
                mag = math.hypot(avg_dx, avg_dy)
                if mag > 1e-6:
                    avg_dx, avg_dy = avg_dx / mag, avg_dy / mag

            nx = _sn(tx + avg_dx * step)
            ny = _sn(ty + avg_dy * step)
            nx = max(margin, min(w - margin, nx))
            ny = max(margin, min(h - margin, ny))

            # Check if new position should MERGE into an existing node
            merge_to = None
            if merge_radius > 0:
                merge_to = _find_merge_target(nx, ny, tip_idx, merge_radius)
            if merge_to is not None:
                # Create merge edge to existing node; this tip stops growing
                edges.append((tip_idx, merge_to, tip_depth + 1))
                nodes[tip_idx][2] = "junction"
                continue

            if not _is_clear(tx, ty, nx, ny):
                nodes[tip_idx][2] = "terminal"
                continue

            new_depth = tip_depth + 1
            new_idx = len(nodes)
            nodes.append([nx, ny, "junction", new_depth])
            edges.append((tip_idx, new_idx, new_depth))
            _mark_occ(tx, ty, nx, ny)
            _add_node_index(new_idx)

            consumed = set()
            for ai, _ax, _ay, d in nearby:
                if d < step * 1.5:
                    consumed.add(ai)
            if consumed:
                attractor_live = [a for i, a in enumerate(attractor_live) if i not in consumed]
                _index_attractors()

            new_frontier.append((new_idx, avg_dx, avg_dy, seed_dx, seed_dy))

            # Density-boosted branching
            bp = branch_prob * (0.2 + local_d * 0.8)
            if rng.random() < bp:
                if quantize_45:
                    # PCB: T-junction = strictly perpendicular (90° turn left or right)
                    side = rng.choice([-1, 1])
                    bdx, bdy = -avg_dy * side, avg_dx * side
                    bdx, bdy = _snap_direction_45(bdx, bdy)
                else:
                    # Neural: lateral branch (70-110° from current) biased away from seed
                    turn_mag = rng.uniform(math.pi * 0.4, math.pi * 0.6)
                    side = rng.choice([-1, 1])
                    c, s = math.cos(turn_mag * side), math.sin(turn_mag * side)
                    bdx = avg_dx * c - avg_dy * s
                    bdy = avg_dx * s + avg_dy * c
                # Branch gets its OWN seed direction so it spreads outward
                new_frontier.append((new_idx, bdx, bdy, bdx, bdy))

        if len(new_frontier) > 120:
            rng.shuffle(new_frontier)
            for tip_idx, _, _, _, _ in new_frontier[120:]:
                nodes[tip_idx][2] = "terminal"
            new_frontier = new_frontier[:120]
        frontier = new_frontier

    for tip_idx, _, _, _, _ in frontier:
        if nodes[tip_idx][2] == "junction":
            nodes[tip_idx][2] = "terminal"

    return nodes, edges


def _chain_tree(nodes, edges):
    """Walk tree from roots/junctions to terminals, collecting continuous chains.

    Returns list of (node_indices, max_depth). Branch points break chains so
    each chain is a single continuous polyline.
    """
    adj = {}
    for src, dst, _dep in edges:
        adj.setdefault(src, []).append(dst)
        adj.setdefault(dst, []).append(src)

    degree = {i: len(adj.get(i, [])) for i in range(len(nodes))}
    # Chain endpoints: degree != 2 (roots, branches, terminals)
    endpoints = [i for i in range(len(nodes)) if degree.get(i, 0) != 2]

    visited_edges = set()
    chains = []

    def _edge_key(a, b):
        return (min(a, b), max(a, b))

    # Walk chains from each endpoint
    for start in endpoints:
        for nxt in adj.get(start, []):
            ek = _edge_key(start, nxt)
            if ek in visited_edges:
                continue
            chain = [start]
            cur, prev = nxt, start
            visited_edges.add(ek)
            chain.append(cur)
            # Continue until we hit another endpoint
            while degree.get(cur, 0) == 2:
                neighbors = adj[cur]
                nn = neighbors[0] if neighbors[0] != prev else neighbors[1]
                ek2 = _edge_key(cur, nn)
                if ek2 in visited_edges:
                    break
                visited_edges.add(ek2)
                prev, cur = cur, nn
                chain.append(cur)
            if len(chain) >= 2:
                max_d = max(nodes[i][3] for i in chain)
                chains.append((chain, max_d))
    return chains


# ---------------------------------------------------------------------------
# Circuit: bus-group traces with configurable bend angle, T-junction branching.
# Reference: circuit.jpg - parallel bus runs from edges, 45-deg diagonal bends
# creating staircase patterns, filled-circle pads at endpoints and junctions,
# ZERO trace crossings, thin uniform strokes, directional flow.
# ---------------------------------------------------------------------------


def _gen_circuit(
    w,
    h,
    density,
    direction,
    rng,
    bend_angle=45,
    origin_directions=None,
    stroke_width=2.5,
    stroke_std=0.4,
    pad_radius=4.5,
    pad_std=1.0,
    branch_prob=None,
    merge_prob=0.15,
    density_points=None,
    density_gradient=None,
    subdivision_rounds=2,
):
    """PCB-style traces via grid-annealing with density gradients.

    Generation uses a multi-round grid subdivision:
    - Round 0: 3x3 coarse grid, bus groups placed proportional to local density
    - Rounds 1-N: under-target cells subdivide 2x2, extend/add traces
    - Final: full-span traces and merge pass

    Args:
        bend_angle: Bend angle in degrees (default 45).
        origin_directions: List of angles for trace origins.
            0=top, 90=right, 180=bottom, 270=left. Default: [0, 180].
        stroke_width: Mean trace stroke width (default 2.5).
        stroke_std: Std deviation for stroke width variation (default 0.4).
        pad_radius: Mean pad outer radius (default 4.5).
        pad_std: Std deviation for pad radius variation (default 1.0).
        branch_prob: Probability of branch stubs (default: from density preset).
        merge_prob: Probability of merging into nearby trace (default 0.15).
        density_points: List of (x_frac, y_frac, weight) for spatial density
            control. Fractions 0-1, weight 0-1. IDW interpolation between points.
        density_gradient: Shorthand preset: "left-to-right", "right-to-left",
            "top-down", "bottom-up", "center-out", "edges-in".
        subdivision_rounds: Number of subdivision rounds 0-3 (default 2).
    """
    d = _DENSITY[density]
    factor = d["factor"]
    branch_p = branch_prob if branch_prob is not None else d["branch_p"]

    # --- Space colonization with 45° quantization (PCB-like) ---
    grad_pts = density_points
    if grad_pts is None and density_gradient:
        _presets = {
            "left-to-right": [(0, 0.5, 0.15), (1, 0.5, 1.0)],
            "right-to-left": [(0, 0.5, 1.0), (1, 0.5, 0.15)],
            "top-down": [(0.5, 0, 1.0), (0.5, 1, 0.15)],
            "bottom-up": [(0.5, 0, 0.15), (0.5, 1, 1.0)],
            "center-out": [(0.5, 0.5, 1.0), (0, 0, 0.1), (1, 0, 0.1), (0, 1, 0.1), (1, 1, 0.1)],
            "edges-in": [(0.5, 0.5, 0.1), (0, 0, 1.0), (1, 0, 1.0), (0, 1, 1.0), (1, 1, 1.0)],
        }
        grad_pts = _presets.get(density_gradient)

    def density_fn(x, y):
        return _idw_density(x, y, w, h, grad_pts)

    grid = 4
    # Origin directions -> seed directions
    _angle_map = {"down": [0], "up": [180], "right": [270], "left": [90], "radial": [0, 180]}
    origin_angles = (
        _angle_map.get(direction, [0, 180]) if origin_directions is None else origin_directions
    )
    _cardinal = {0: (0, 1), 90: (-1, 0), 180: (0, -1), 270: (1, 0)}

    # Seeds: bus groups along canvas edges with wider spacing
    bus_gap = grid * 6  # 24px spacing between parallel buses (was 12)
    n_bus_groups = max(3, int(6 * factor))
    seeds = []
    for _ in range(n_bus_groups):
        angle = origin_angles[rng.randint(0, len(origin_angles) - 1)] % 360
        snapped = round(angle / 90) * 90 % 360
        pdx, pdy = _cardinal.get(snapped, (0, 1))
        n_parallel = rng.randint(2, max(3, int(3 * min(factor, 2.0))))
        if snapped in (0, 180):
            base = rng.uniform(w * 0.05, w * 0.75)
            y_edge = 0 if snapped == 0 else h
            for ti in range(n_parallel):
                seeds.append((base + ti * bus_gap, y_edge, pdx, pdy))
        else:
            base = rng.uniform(h * 0.05, h * 0.75)
            x_edge = 0 if snapped == 270 else w
            for ti in range(n_parallel):
                seeds.append((x_edge, base + ti * bus_gap, pdx, pdy))

    # Attractor pads weighted by density gradient
    n_attractors = max(30, int(90 * factor))
    attractors = []
    for _ in range(n_attractors * 4):
        ax = rng.uniform(w * 0.05, w * 0.95)
        ay = rng.uniform(h * 0.05, h * 0.95)
        if rng.random() < density_fn(ax, ay):
            attractors.append((ax, ay))
        if len(attractors) >= n_attractors:
            break

    # Grow tree with 45° quantized extensions - more branching, tight merges
    step = min(w, h) * 0.12
    reach = max(w, h) * 0.5
    nodes, edges_t = _space_colonize(
        w,
        h,
        rng,
        seeds,
        attractors,
        reach=reach,
        step=step,
        branch_prob=branch_p * 1.3,
        merge_radius=step * 0.5,  # only VERY close merges (no bus-eating)
        snap_grid=grid,
        use_occupancy=True,
        quantize_45=True,
        max_iterations=35,
        density_fn=density_fn if grad_pts else None,
    )

    # Chain tree into continuous polylines
    chains = _chain_tree(nodes, edges_t)

    # Render as PCB traces: polylines + pads
    elements = []
    max_depth = max((n[3] for n in nodes), default=1) or 1

    # Chamfer 90-degree corners into 45-degree diagonal bends (PCB signature)
    def _chamfer_corners(pts, chamfer=6.0):
        """Replace sharp 90° corners with 45° diagonal chamfer.

        Detects direction change >= 80°. Backs off by `chamfer` on each side
        of the corner and connects with a diagonal segment.
        """
        if len(pts) < 3:
            return pts
        out = [pts[0]]
        for i in range(1, len(pts) - 1):
            px, py = pts[i - 1]
            cx, cy = pts[i]
            nx, ny = pts[i + 1]
            dx1, dy1 = cx - px, cy - py
            dx2, dy2 = nx - cx, ny - cy
            l1 = math.hypot(dx1, dy1)
            l2 = math.hypot(dx2, dy2)
            # Skip chamfer for short segments (prevents hook artifacts)
            if l1 < chamfer * 2.5 or l2 < chamfer * 2.5:
                out.append((cx, cy))
                continue
            # Angle between segments - check if it's a near-90° turn
            cross = dx1 * dy2 - dy1 * dx2
            dot = dx1 * dx2 + dy1 * dy2
            angle = abs(math.atan2(abs(cross), dot))
            # Insert chamfer only if turn is near-orthogonal (70°-110°)
            if math.pi * 0.4 < angle < math.pi * 0.6:
                ch = min(chamfer, l1 * 0.4, l2 * 0.4)
                # Back off from corner toward previous point
                ax = cx - dx1 / l1 * ch
                ay = cy - dy1 / l1 * ch
                # Forward off from corner toward next point
                bx = cx + dx2 / l2 * ch
                by = cy + dy2 / l2 * ch
                out.append((ax, ay))
                out.append((bx, by))
            else:
                out.append((cx, cy))
        out.append(pts[-1])
        return out

    for chain, _chain_max_depth in chains:
        pts = [(nodes[i][0], nodes[i][1]) for i in chain]
        if len(pts) < 2:
            continue
        # Apply 45° chamfer at orthogonal corners
        pts = _chamfer_corners(pts, chamfer=6.0)
        # Depth-based taper: root thick, terminals thin
        root_depth = nodes[chain[0]][3]
        thickness_factor = 1.0 - min(0.7, root_depth / max_depth * 0.65)
        sw = _right_skewed(rng, stroke_width * thickness_factor, stroke_std, skew=1.8)
        d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
        for px, py in pts[1:]:
            d_str += f" L{px:.1f},{py:.1f}"
        elements.append(
            BackgroundElement(
                kind="path",
                svg=f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                role="trace",
            )
        )

    # Ring pads at terminals and junctions (degree != 2)
    adj = {}
    for src, dst, _ in edges_t:
        adj.setdefault(src, []).append(dst)
        adj.setdefault(dst, []).append(src)
    edge_margin = min(w, h) * 0.04
    # Collect all trace segments for pad collision check
    all_segments = []
    for src, dst, _ in edges_t:
        all_segments.append((nodes[src][0], nodes[src][1], nodes[dst][0], nodes[dst][1], src, dst))

    def _pad_collides(cx, cy, pr, own_idx):
        """Check if pad at (cx,cy) with radius pr overlaps any trace segment
        that's NOT incident to own_idx."""
        for x1, y1, x2, y2, s, d in all_segments:
            if s == own_idx or d == own_idx:
                continue
            # Distance from (cx,cy) to segment (x1,y1)-(x2,y2)
            dx, dy = x2 - x1, y2 - y1
            seg_len2 = dx * dx + dy * dy
            if seg_len2 < 1:
                continue
            t = max(0.0, min(1.0, ((cx - x1) * dx + (cy - y1) * dy) / seg_len2))
            px = x1 + t * dx
            py = y1 + t * dy
            if math.hypot(cx - px, cy - py) < pr + 1.5:
                return True
        return False

    for i, n in enumerate(nodes):
        deg = len(adj.get(i, []))
        if deg == 0:
            continue
        # Skip pads at root seeds (canvas edge entry points)
        if n[2] == "root":
            continue
        # Skip pads near canvas border
        if (
            n[0] < edge_margin
            or n[0] > w - edge_margin
            or n[1] < edge_margin
            or n[1] > h - edge_margin
        ):
            continue
        # Only pads at terminals (deg=1) and junctions (deg>=3)
        if not (deg == 1 or deg >= 3):
            continue
        pr = _right_skewed(rng, pad_radius, pad_std, skew=1.4)
        # Skip if pad would cover another trace (short-circuit prevention)
        if _pad_collides(n[0], n[1], pr, i):
            continue
        elements.append(
            BackgroundElement(
                kind="circle",
                svg=f'<circle cx="{n[0]:.1f}" cy="{n[1]:.1f}" r="{pr:.1f}"/>',
                role="pad",
            )
        )
        elements.append(
            BackgroundElement(
                kind="circle",
                svg=f'<circle cx="{n[0]:.1f}" cy="{n[1]:.1f}" r="{pr * 0.4:.1f}" style="fill:#0a1a24"/>',
                role="pad-hole",
            )
        )

    return elements


def _gen_circuit_legacy(
    w,
    h,
    density,
    direction,
    rng,
    bend_angle=45,
    origin_directions=None,
    stroke_width=2.5,
    stroke_std=0.4,
    pad_radius=4.5,
    pad_std=1.0,
    branch_prob=None,
    merge_prob=0.15,
    density_points=None,
    density_gradient=None,
    subdivision_rounds=2,
):
    """Legacy v14 grid-annealing circuit. Kept for reference."""
    d = _DENSITY[density]
    factor = d["factor"]
    branch_p = branch_prob if branch_prob is not None else d["branch_p"]
    elements = []

    # Parse origin directions (angles -> edges with bend bias)
    if origin_directions is None:
        _angle_map = {"down": [0], "up": [180], "right": [270], "left": [90], "radial": [0, 180]}
        origin_angles = _angle_map.get(direction, [0, 180])
    else:
        origin_angles = origin_directions

    # Map angles to edge specs: (edge_name, pdx, pdy, is_vert, bend_bias)
    # bend_bias: -1 to 1, from the fractional offset of the angle
    _cardinal = {
        0: ("top", 0, 1, True),
        90: ("right", -1, 0, False),
        180: ("bottom", 0, -1, True),
        270: ("left", 1, 0, False),
    }
    edges = []
    for a in origin_angles:
        a = a % 360
        snapped = round(a / 90) * 90 % 360
        offset = (a - snapped) / 45.0  # -1 to +1 range
        ename, pdx, pdy, is_v = _cardinal.get(snapped, _cardinal[0])
        edges.append((ename, pdx, pdy, is_v, offset))

    if not edges:
        edges = [("top", 0, 1, True, 0.0)]

    # PCB parameters
    grid = 4
    bus_gap = grid * 2  # tight bus spacing

    # --- Occupancy grid (clearance scales with stroke width) ---
    # At grid=4px, clearance=2 means 8px exclusion zone per side of trace.
    # With sw=2.5, that gives ~5.5px visible gap - tight but no overlaps.
    clearance = max(2, int(math.ceil(stroke_width / grid)) + 1)
    occ = set()

    def _g(v):
        return int(round(v / grid))

    def _s(v):
        return round(v / grid) * grid

    def _mark(x1, y1, x2, y2):
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(dist / grid) + 1)
        for i in range(steps + 1):
            t = i / steps
            gx = _g(x1 + t * (x2 - x1))
            gy = _g(y1 + t * (y2 - y1))
            for ddx in range(-clearance, clearance + 1):
                for ddy in range(-clearance, clearance + 1):
                    occ.add((gx + ddx, gy + ddy))

    def _mark_pts(pts):
        for i in range(len(pts) - 1):
            _mark(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])

    def _clear(x1, y1, x2, y2):
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(dist / grid) + 1)
        for i in range(steps + 1):
            t = i / steps
            gx = _g(x1 + t * (x2 - x1))
            gy = _g(y1 + t * (y2 - y1))
            if (gx, gy) in occ:
                return False
        return True

    def _pts_ok(pts):
        for i in range(len(pts) - 1):
            if not _clear(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]):
                return False
        return True

    def _clear_branch(x1, y1, x2, y2):
        """Like _clear but skips first 30% of segment (allows start from occupied trace)."""
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(2, int(dist / grid) + 1)
        skip = max(1, int(steps * 0.3))
        for i in range(skip, steps + 1):
            t = i / steps
            gx = _g(x1 + t * (x2 - x1))
            gy = _g(y1 + t * (y2 - y1))
            if (gx, gy) in occ:
                return False
        return True

    def _clear_merge(x1, y1, x2, y2):
        """Like _clear but skips first and last 30% (connects two occupied traces)."""
        dist = math.hypot(x2 - x1, y2 - y1)
        steps = max(3, int(dist / grid) + 1)
        skip = max(1, int(steps * 0.3))
        for i in range(skip, steps - skip + 1):
            t = i / steps
            gx = _g(x1 + t * (x2 - x1))
            gy = _g(y1 + t * (y2 - y1))
            if (gx, gy) in occ:
                return False
        return True

    def _emit(pts, sw_override=None):
        if len(pts) < 2:
            return
        sw = sw_override or stroke_width
        d_str = "M" + " L".join(f"{p[0]:.0f},{p[1]:.0f}" for p in pts)
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                "path",
                f'<path d="{d_str}" stroke-width="{sw:.1f}"/>',
                "trace",
                (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )

    def _pad(cx, cy, r_override=None):
        """Ring annular pad."""
        r_out = r_override or pad_radius
        r_hole = r_out * 0.4
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r_out:.1f}"/>',
                "pad",
                (cx - r_out, cy - r_out, r_out * 2, r_out * 2),
            )
        )
        elements.append(
            BackgroundElement(
                "circle",
                f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r_hole:.1f}"/>',
                "pad-hole",
                (cx - r_hole, cy - r_hole, r_hole * 2, r_hole * 2),
            )
        )

    # Margin: pads and trace endpoints stay inside canvas by at least pad_radius
    _margin = _s(pad_radius + pad_std + 2)

    def _clamp(x, y):
        return max(_margin, min(w - _margin, _s(x))), max(_margin, min(h - _margin, _s(y)))

    # --- Density gradient ---
    _grad_pts = density_points
    if _grad_pts is None and density_gradient:
        _presets = {
            "left-to-right": [(0, 0.5, 0.15), (1, 0.5, 1.0)],
            "right-to-left": [(0, 0.5, 1.0), (1, 0.5, 0.15)],
            "top-down": [(0.5, 0, 1.0), (0.5, 1, 0.15)],
            "bottom-up": [(0.5, 0, 0.15), (0.5, 1, 1.0)],
            "center-out": [(0.5, 0.5, 1.0), (0, 0, 0.1), (1, 0, 0.1), (0, 1, 0.1), (1, 1, 0.1)],
            "edges-in": [(0.5, 0.5, 0.1), (0, 0, 1.0), (1, 0, 1.0), (0, 1, 1.0), (1, 1, 1.0)],
        }
        _grad_pts = _presets.get(density_gradient)

    def _density_at(x, y):
        """IDW interpolation of density at canvas point. Returns 0-1 weight."""
        if not _grad_pts:
            return 1.0
        xf, yf = x / max(1, w), y / max(1, h)
        total_w = 0.0
        total_v = 0.0
        for px, py, pw in _grad_pts:
            dist = max(0.01, math.hypot(xf - px, yf - py))
            inv_d = 1.0 / (dist * dist)
            total_w += inv_d
            total_v += inv_d * pw
        return min(1.0, max(0.0, total_v / total_w))

    # Track placed trace waypoints for merge detection
    _trace_pts = []

    def _density_change(x0, y0, x1, y1):
        """Compute density change along a trace: positive = density increasing."""
        if not _grad_pts:
            return 0.0
        return _density_at(x1, y1) - _density_at(x0, y0)

    # --- Inner function: lay one bus-group trace ---
    def _lay_trace(sx, sy, pdx, pdy, is_vert, bend_sign, base_run, bus_sw, bus_pad_r):
        """Place one trace from (sx,sy) in direction (pdx,pdy). Returns point list or None."""
        branch_sw = max(0.5, bus_sw * 0.6)
        branch_pad_r = max(2.0, bus_pad_r * 0.7)

        ex1 = sx + pdx * base_run
        ey1 = sy + pdy * base_run
        ex1, ey1 = _clamp(ex1, ey1)

        if abs(ex1 - sx) + abs(ey1 - sy) < min(w, h) * 0.08:
            return None
        if not _clear(sx, sy, ex1, ey1):
            return None

        pts = [(sx, sy), (ex1, ey1)]

        # Diagonal bend (forward-only)
        if rng.random() < 0.80:
            diag_len = _s(rng.uniform(min(w, h) * 0.05, min(w, h) * 0.15))
            post_len = _s(rng.uniform(min(w, h) * 0.08, min(w, h) * 0.30))

            if bend_angle >= 89:
                if is_vert:
                    bx, by = _s(ex1 + bend_sign * (diag_len + post_len)), ey1
                else:
                    bx, by = ex1, _s(ey1 + bend_sign * (diag_len + post_len))
                bx, by = _clamp(bx, by)
                new_pts = [(bx, by)]
            else:
                new_pts = []
                if is_vert:
                    dx = _s(ex1 + bend_sign * _s(diag_len))
                    dy = _s(ey1 + pdy * _s(diag_len))
                    dx, dy = _clamp(dx, dy)
                    new_pts.append((dx, dy))
                    if post_len > grid:
                        px, py = _clamp(dx + bend_sign * post_len, dy)
                        if abs(px - dx) >= grid:
                            new_pts.append((px, py))
                else:
                    dx = _s(ex1 + pdx * _s(diag_len))
                    dy = _s(ey1 + bend_sign * _s(diag_len))
                    dx, dy = _clamp(dx, dy)
                    new_pts.append((dx, dy))
                    if post_len > grid:
                        px, py = _clamp(dx, dy + bend_sign * post_len)
                        if abs(py - dy) >= grid:
                            new_pts.append((px, py))

            check = [pts[-1]] + new_pts
            if _pts_ok(check):
                pts.extend(new_pts)

        if len(pts) < 2:
            return None

        _mark_pts(pts)
        _emit(pts, bus_sw)
        _pad(pts[-1][0], pts[-1][1], bus_pad_r)
        for p in pts:
            _trace_pts.append(p)

        # Density-driven branch/merge modulation:
        #   density DECREASING along trace -> boost merge (traces converge)
        #   density INCREASING along trace -> boost branch (traces fork)
        d_change = _density_change(pts[0][0], pts[0][1], pts[-1][0], pts[-1][1])
        # d_change: positive = density increasing at endpoint, negative = decreasing
        local_merge_p = merge_prob * (1.0 + max(0, -d_change * 3))  # boost when decreasing
        local_branch_p = branch_p * (1.0 + max(0, d_change * 3))  # boost when increasing

        # Merge: connect endpoint to nearby existing trace
        # Short merge connections skip occupancy (intentional crossing)
        if local_merge_p > 0 and rng.random() < local_merge_p and len(_trace_pts) > 10:
            ex, ey = pts[-1]
            merge_r = min(w, h) * 0.12
            best_d, best_p = merge_r, None
            for tp in _trace_pts[: -len(pts)]:
                dd = math.hypot(tp[0] - ex, tp[1] - ey)
                if grid * 3 < dd < best_d:
                    best_d, best_p = dd, tp
            if best_p:
                # Short merges (< 40px): skip occupancy, just connect
                # Longer merges: check middle section only
                ok = best_d < 40 or _clear_merge(ex, ey, best_p[0], best_p[1])
                if ok:
                    _mark(ex, ey, best_p[0], best_p[1])
                    _emit([(ex, ey), best_p], branch_sw)

        # Branch stubs - density-modulated
        for si in range(len(pts) - 1):
            if rng.random() > local_branch_p * 0.8:
                continue
            t_frac = rng.uniform(0.25, 0.75)
            p0, p1 = pts[si], pts[si + 1]
            mx = _s(p0[0] + t_frac * (p1[0] - p0[0]))
            my = _s(p0[1] + t_frac * (p1[1] - p0[1]))
            sdx, sdy = p1[0] - p0[0], p1[1] - p0[1]
            br_len = _s(rng.uniform(min(w, h) * 0.03, min(w, h) * 0.10))
            if abs(sdy) > abs(sdx):
                bx, by = _s(mx + rng.choice([-1, 1]) * br_len), my
            else:
                bx, by = mx, _s(my + rng.choice([-1, 1]) * br_len)
            bx, by = _clamp(bx, by)
            if _clear_branch(mx, my, bx, by):
                _mark(mx, my, bx, by)
                _emit([(mx, my), (bx, by)], branch_sw)
                _pad(bx, by, branch_pad_r)

        return pts

    # --- Grid-annealing generation ---
    total_buses = max(12, int(25 * factor))
    rounds = max(0, min(3, subdivision_rounds))

    # Build initial 3x3 grid cells: (x0, y0, x1, y1, target_count, placed_count)
    nx0, ny0 = 3, 3
    cells = []
    for iy in range(ny0):
        for ix in range(nx0):
            x0 = ix * w / nx0
            y0 = iy * h / ny0
            x1 = (ix + 1) * w / nx0
            y1 = (iy + 1) * h / ny0
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            dw = _density_at(cx, cy)
            cell_frac = 1.0 / (nx0 * ny0)
            # Amplify gradient: dw^2 makes sparse areas much sparser
            target = max(0, round(total_buses * cell_frac * dw * dw))
            cells.append([x0, y0, x1, y1, target, 0])

    for rnd in range(rounds + 1):
        next_cells = []
        for cell in cells:
            x0, y0, x1, y1, target, placed = cell
            remaining = target - placed
            if remaining <= 0:
                continue

            cw, ch = x1 - x0, y1 - y0
            if cw < grid * 6 or ch < grid * 6:
                continue  # cell too small to subdivide further

            # Place bus groups in this cell
            n_to_place = remaining if rnd == rounds else max(1, remaining // 2)
            for _ in range(n_to_place):
                edge_name, pdx, pdy, is_vert, bend_bias = edges[rng.randint(0, len(edges) - 1)]
                bus_sw = _right_skewed(rng, stroke_width, stroke_std, skew=1.8)
                bus_pad_r = _right_skewed(rng, pad_radius, pad_std, skew=1.5)
                n_in_bus = rng.randint(2, max(3, int(4 * min(factor, 2.0))))

                if abs(bend_bias) > 0.3:
                    bend_sign = 1 if bend_bias > 0 else -1
                else:
                    bend_sign = rng.choice([-1, 1])

                # Starting position: along the cell edge nearest the canvas border
                if is_vert:
                    base = _s(rng.uniform(x0 + _margin, x1 - _margin - n_in_bus * bus_gap))
                    cross = 0 if edge_name == "top" else h
                else:
                    base = _s(rng.uniform(y0 + _margin, y1 - _margin - n_in_bus * bus_gap))
                    cross = 0 if edge_name == "left" else w

                base_run = rng.uniform(min(cw, ch) * 0.4, max(cw, ch) * 0.9)
                stair_step = rng.uniform(grid * 3, grid * 6)

                for ti in range(n_in_bus):
                    if is_vert:
                        sx = _s(base + ti * bus_gap)
                        sy = cross
                    else:
                        sx = cross
                        sy = _s(base + ti * bus_gap)

                    run1 = _s(base_run + ti * stair_step)
                    result = _lay_trace(
                        sx, sy, pdx, pdy, is_vert, bend_sign, run1, bus_sw, bus_pad_r
                    )
                    if result:
                        cell[5] += 1

            # Subdivide under-target cells for next round
            if rnd < rounds and cell[5] < target:
                mid_x, mid_y = (x0 + x1) / 2, (y0 + y1) / 2
                sub_target = max(1, (target - cell[5]) // 4)
                for sx0, sy0, sx1, sy1 in [
                    (x0, y0, mid_x, mid_y),
                    (mid_x, y0, x1, mid_y),
                    (x0, mid_y, mid_x, y1),
                    (mid_x, mid_y, x1, y1),
                ]:
                    sc = _density_at((sx0 + sx1) / 2, (sy0 + sy1) / 2)
                    next_cells.append([sx0, sy0, sx1, sy1, max(0, round(sub_target * sc * sc)), 0])

        if next_cells:
            cells = next_cells

    # --- Full-span traces ---
    span_sw = _right_skewed(rng, stroke_width, stroke_std, skew=1.8)
    n_span = max(2, int(4 * factor))
    for _ in range(n_span):
        edge_name, pdx, pdy, is_vert, _bias = edges[rng.randint(0, len(edges) - 1)]
        if is_vert:
            sx = _s(rng.uniform(w * 0.05, w * 0.95))
            sy = 0 if edge_name == "top" else h
            ex, ey = sx, (h if edge_name == "top" else 0)
        else:
            sy = _s(rng.uniform(h * 0.05, h * 0.95))
            sx = 0 if edge_name == "left" else w
            ex, ey = (w if edge_name == "left" else 0), sy
        if _clear(sx, sy, ex, ey):
            _mark(sx, sy, ex, ey)
            _emit([(sx, sy), (ex, ey)], span_sw)

    return elements


# ---------------------------------------------------------------------------
# Neural: space colonization dendritic branching
# ---------------------------------------------------------------------------


def _gen_neural(
    w, h, density, direction, rng, density_points=None, density_gradient=None, attract_repel=0.5
):
    """Dendritic branching via space colonization with density gradient.

    Args:
        attract_repel: Balance between attraction (toward attractors) and
            repulsion (away from existing branches). 0.0 = pure repulsion
            (max spread), 1.0 = pure attraction (convergent). Default 0.5.

    Thick root trunks taper to thin terminal branches. Density gradient
    controls where attractors cluster, so dense areas grow more branches.
    """
    d = _DENSITY[density]
    factor = d["factor"]
    branch_p = d["branch_p"]

    # Density gradient for attractor distribution
    grad_pts = density_points
    if grad_pts is None and density_gradient:
        _presets = {
            "left-to-right": [(0, 0.5, 0.15), (1, 0.5, 1.0)],
            "right-to-left": [(0, 0.5, 1.0), (1, 0.5, 0.15)],
            "top-down": [(0.5, 0, 1.0), (0.5, 1, 0.15)],
            "bottom-up": [(0.5, 0, 0.15), (0.5, 1, 1.0)],
            "center-out": [(0.5, 0.5, 1.0), (0, 0, 0.1), (1, 0, 0.1), (0, 1, 0.1), (1, 1, 0.1)],
            "edges-in": [(0.5, 0.5, 0.1), (0, 0, 1.0), (1, 0, 1.0), (0, 1, 1.0), (1, 1, 1.0)],
        }
        grad_pts = _presets.get(density_gradient)

    def density_fn(x, y):
        return _idw_density(x, y, w, h, grad_pts)

    # Many seeds along origin edge with inward-pointing directions
    n_seeds = max(6, int(12 * factor))
    seeds = []
    if direction in ("down", "up"):
        y_edge = 0 if direction == "down" else h
        pdy = 1 if direction == "down" else -1
        spacing = (w * 0.9) / max(1, n_seeds - 1)
        for si in range(n_seeds):
            sx = w * 0.05 + si * spacing + rng.gauss(0, spacing * 0.15)
            seeds.append((max(2, min(w - 2, sx)), y_edge, 0, pdy))
    elif direction in ("right", "left"):
        x_edge = 0 if direction == "right" else w
        pdx = 1 if direction == "right" else -1
        spacing = (h * 0.9) / max(1, n_seeds - 1)
        for si in range(n_seeds):
            sy = h * 0.05 + si * spacing + rng.gauss(0, spacing * 0.15)
            seeds.append((x_edge, max(2, min(h - 2, sy)), pdx, 0))
    else:
        # radial: seeds along ALL four edges, each pointing inward
        per_edge = max(3, n_seeds // 4)
        sp_w = w * 0.9 / per_edge
        sp_h = h * 0.9 / per_edge
        for i in range(per_edge):
            seeds.append((w * 0.05 + (i + 0.5) * sp_w, 0, 0, 1))  # top -> down
            seeds.append((w * 0.05 + (i + 0.5) * sp_w, h, 0, -1))  # bottom -> up
            seeds.append((0, h * 0.05 + (i + 0.5) * sp_h, 1, 0))  # left -> right
            seeds.append((w, h * 0.05 + (i + 0.5) * sp_h, -1, 0))  # right -> left

    # Attractors placed across canvas, weighted by density
    n_attractors = max(40, int(100 * factor))
    attractors = []
    for _ in range(n_attractors * 4):
        ax = rng.uniform(w * 0.03, w * 0.97)
        ay = rng.uniform(h * 0.03, h * 0.97)
        if rng.random() < density_fn(ax, ay):
            attractors.append((ax, ay))
        if len(attractors) >= n_attractors:
            break

    # Space colonization: small step -> hair-like curves through many points
    # merge_radius=0 so dendrites don't fuse. Long reach + iterations = long fan-out
    # strands reaching toward canvas sides.
    step = max(w, h) * 0.022
    reach = max(w, h) * 0.55
    nodes, edges_t = _space_colonize(
        w,
        h,
        rng,
        seeds,
        attractors,
        reach=reach,
        step=step,
        branch_prob=branch_p * 0.45,
        merge_radius=0,
        snap_grid=0,
        use_occupancy=False,
        quantize_45=False,
        max_iterations=80,
        density_fn=density_fn if grad_pts else None,
    )

    chains = _chain_tree(nodes, edges_t)

    # Render: smooth curves with aggressive depth-based taper
    # Thick parent trunks (4-6px) -> hair-like terminal dendrites (0.3-0.5px)
    elements = []
    max_depth = max((n[3] for n in nodes), default=1) or 1
    root_sw = 4.5 * min(2.0, factor + 0.5)

    # Adjacency for degree lookup
    adj = {}
    for src, dst, _ in edges_t:
        adj.setdefault(src, []).append(dst)
        adj.setdefault(dst, []).append(src)

    for chain, _chain_max_depth in chains:
        pts = [(nodes[i][0], nodes[i][1]) for i in chain]
        if len(pts) < 2:
            continue
        root_depth = nodes[chain[0]][3]
        # Depth-based taper (thinner deeper)
        taper = (1.0 - min(0.95, root_depth / max(1, max_depth) * 0.95)) ** 2.2
        # Gamma-like thickness: most chains thin, rare thick trunks
        # Gamma(shape=1.3, scale=0.35) -> mean ~0.45, long right tail
        gamma_mult = rng.gammavariate(1.3, 0.35)
        tw = max(0.2, root_sw * taper * gamma_mult)
        # Smooth quadratic bezier through chain points (organic curves)
        if len(pts) == 2:
            d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f} L{pts[1][0]:.1f},{pts[1][1]:.1f}"
        else:
            d_str = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
            for i in range(1, len(pts) - 1):
                # Midpoint between pts[i] and pts[i+1]
                mx = (pts[i][0] + pts[i + 1][0]) / 2
                my = (pts[i][1] + pts[i + 1][1]) / 2
                d_str += f" Q{pts[i][0]:.1f},{pts[i][1]:.1f} {mx:.1f},{my:.1f}"
            d_str += f" T{pts[-1][0]:.1f},{pts[-1][1]:.1f}"
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        elements.append(
            BackgroundElement(
                kind="path",
                svg=f'<path d="{d_str}" stroke-width="{tw:.2f}"/>',
                role="dendrite",
                bbox=(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)),
            )
        )

    # Synapse dots at terminal nodes (degree 1, not roots) - visible 2-3px
    for i, n in enumerate(nodes):
        deg = len(adj.get(i, []))
        if deg != 1 or n[2] == "root":
            continue
        r_dot = max(1.4, 2.4 - n[3] / max(1, max_depth) * 0.8)
        elements.append(
            BackgroundElement(
                kind="circle",
                svg=f'<circle cx="{n[0]:.1f}" cy="{n[1]:.1f}" r="{r_dot:.1f}"/>',
                role="synapse",
                bbox=(n[0] - r_dot, n[1] - r_dot, r_dot * 2, r_dot * 2),
            )
        )

    return elements


def _neural_grow(
    x,
    y,
    attractors,
    w,
    h,
    reach,
    step,
    branches,
    rng,
    depth,
    tw,
    parent_dx=0,
    parent_dy=1,
    all_pts=None,
    attract_repel=0.5,
    density_fn=None,
):
    """Space colonization with density-driven attraction/repulsion.

    In dense areas: attraction dominates -> branches converge and merge.
    In sparse areas: repulsion dominates -> branches spread out to fill space.
    """
    if depth > 5 or not attractors or (all_pts and len(all_pts) > 2000):
        return
    if all_pts is None:
        all_pts = []
    pts = [(x, y)]
    max_steps = rng.randint(8, 20)
    cur_dx, cur_dy = parent_dx, parent_dy
    repel_reach = step * 4  # how far repulsion acts

    for step_i in range(max_steps):
        # --- Attraction: toward nearest attractor ---
        best_d = float("inf")
        best_a = None
        for ax, ay in attractors:
            dd = math.hypot(ax - x, ay - y)
            if dd < best_d:
                best_d = dd
                best_a = (ax, ay)
        if best_a is None or best_d > reach * 3:
            break
        adx = best_a[0] - x
        ady = best_a[1] - y
        adist = math.hypot(adx, ady)
        if adist < 1:
            break
        attr_x, attr_y = adx / adist, ady / adist

        # --- Repulsion: away from nearby existing points ---
        # Use only the last ~50 points for O(1)-ish performance
        rep_x, rep_y = 0.0, 0.0
        n_rep = 0
        check_start = max(0, len(all_pts) - 60)
        for pi in range(check_start, len(all_pts)):
            px, py = all_pts[pi]
            rdx, rdy = x - px, y - py
            rdist = math.hypot(rdx, rdy)
            if 0.1 < rdist < repel_reach:
                force = 1.0 / (rdist * rdist)
                rep_x += (rdx / rdist) * force
                rep_y += (rdy / rdist) * force
                n_rep += 1
        if n_rep > 0:
            rmag = math.hypot(rep_x, rep_y)
            if rmag > 0.001:
                rep_x /= rmag
                rep_y /= rmag

        # --- Blend attraction + repulsion based on local density ---
        # High density -> more attraction (converge). Low density -> more repulsion (spread).
        local_ar = attract_repel
        if density_fn:
            local_ar = min(0.95, max(0.1, density_fn(x, y)))

        fx = local_ar * attr_x + (1 - local_ar) * rep_x
        fy = local_ar * attr_y + (1 - local_ar) * rep_y
        fmag = math.hypot(fx, fy)
        if fmag < 0.001:
            fx, fy = attr_x, attr_y
        else:
            fx, fy = fx / fmag, fy / fmag

        cur_dx, cur_dy = fx, fy
        nx = x + fx * step + rng.gauss(0, step * 0.15)
        ny = y + fy * step + rng.gauss(0, step * 0.15)
        nx = max(0, min(w, nx))
        ny = max(0, min(h, ny))
        pts.append((nx, ny))
        all_pts.append((nx, ny))

        # Remove reached attractors
        attractors[:] = [
            (ax, ay) for ax, ay in attractors if math.hypot(ax - nx, ay - ny) > step * 0.5
        ]

        # Branch: perpendicular spread, probability boosted in sparse areas
        branch_boost = 1.0 + (1.0 - local_ar) * 1.5
        if rng.random() < 0.20 * branch_boost and depth < 5 and step_i > 1:
            child_tw = tw * 0.6
            angle_off = rng.uniform(math.pi / 3, 2 * math.pi / 3) * rng.choice([-1, 1])
            cos_a, sin_a = math.cos(angle_off), math.sin(angle_off)
            br_dx = cur_dx * cos_a - cur_dy * sin_a
            br_dy = cur_dx * sin_a + cur_dy * cos_a
            branch_atts = [
                (ax, ay)
                for ax, ay in attractors
                if math.hypot(ax - nx, ay - ny) > 1
                and ((ax - nx) * br_dx + (ay - ny) * br_dy) > -0.2 * math.hypot(ax - nx, ay - ny)
            ] or list(attractors)
            _neural_grow(
                nx,
                ny,
                branch_atts,
                w,
                h,
                reach * 0.8,
                step * 0.85,
                branches,
                rng,
                depth + 1,
                child_tw,
                br_dx,
                br_dy,
                all_pts,
                attract_repel,
                density_fn,
            )
        x, y = nx, ny

    if len(pts) > 1:
        branch_tw = max(0.3, tw * (0.88**depth))
        branches.append((pts, branch_tw))


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
    **kwargs,
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
        **kwargs: Type-specific options (e.g. bend_angle=45 for circuit).
    """
    if bg_type not in _GENERATORS:
        raise ValueError(f"Unknown bg type {bg_type!r}. Choose from: {', '.join(BG_TYPES)}")
    if density not in _DENSITY:
        raise ValueError(f"Unknown density {density!r}. Choose from: {', '.join(_DENSITY)}")

    rng = _rng(seed)
    gen_fn = _GENERATORS[bg_type]

    # Pass type-specific kwargs if the generator accepts them
    import inspect

    sig = inspect.signature(gen_fn)
    extra = {k: v for k, v in kwargs.items() if k in sig.parameters}
    elements = gen_fn(w, h, density, direction, rng, **extra)

    result = BackgroundResult(bg_type=bg_type, elements=elements, bbox=(0, 0, w, h))
    result.build_svg()
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics background",
        description="Generate procedural SVG background geometry for beautify.",
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
    parser.add_argument(
        "--bend-angle",
        type=int,
        default=45,
        help="Bend angle in degrees for circuit traces (default: 45). Use 90 for right-angle only.",
    )
    parser.add_argument(
        "--origin-directions",
        type=str,
        default=None,
        help="Comma-separated origin angles: 0=top, 90=right, 180=bottom, 270=left (default: from --direction). Example: '0,180'",
    )
    parser.add_argument(
        "--stroke-width", type=float, default=2.5, help="Mean trace stroke width (default: 2.5)"
    )
    parser.add_argument(
        "--stroke-std", type=float, default=0.4, help="Stroke width std deviation (default: 0.4)"
    )
    parser.add_argument(
        "--pad-radius", type=float, default=4.5, help="Mean pad radius (default: 4.5)"
    )
    parser.add_argument(
        "--pad-std", type=float, default=1.0, help="Pad radius std deviation (default: 1.0)"
    )
    parser.add_argument(
        "--branch-prob",
        type=float,
        default=None,
        help="Branch probability (default: from density preset)",
    )
    parser.add_argument(
        "--merge-prob", type=float, default=0.15, help="Merge probability (default: 0.15)"
    )
    parser.add_argument(
        "--density-gradient",
        type=str,
        default=None,
        help="Density gradient preset: left-to-right, right-to-left, top-down, bottom-up, center-out, edges-in",
    )
    parser.add_argument(
        "--density-points",
        type=str,
        default=None,
        help="Custom density points as 'x1,y1,w1;x2,y2,w2;...' (fractions 0-1)",
    )
    parser.add_argument(
        "--subdivision-rounds",
        type=int,
        default=2,
        help="Grid subdivision rounds 0-3 (default: 2)",
    )
    parser.add_argument("--list", action="store_true", help="List types and exit")
    parser.add_argument("--preview", action="store_true", help="Wrap in full SVG for preview")
    parser.add_argument("--json", action="store_true", help="Output element metadata as JSON")
    args = parser.parse_args()

    if args.list:
        print("Available background types:")
        for t in BG_TYPES:
            print(f"  {t}")
        return

    # Parse origin_directions from comma-separated string
    origin_dirs = None
    if args.origin_directions:
        origin_dirs = [float(x.strip()) for x in args.origin_directions.split(",")]

    # Parse density_points from semicolon-separated string
    dp = None
    if args.density_points:
        dp = []
        for part in args.density_points.split(";"):
            vals = [float(v.strip()) for v in part.split(",")]
            if len(vals) == 3:
                dp.append(tuple(vals))

    result = generate_background(
        bg_type=args.type,
        w=args.w,
        h=args.h,
        density=args.density,
        direction=args.direction,
        seed=args.seed,
        bend_angle=args.bend_angle,
        origin_directions=origin_dirs,
        stroke_width=args.stroke_width,
        stroke_std=args.stroke_std,
        pad_radius=args.pad_radius,
        pad_std=args.pad_std,
        branch_prob=args.branch_prob,
        merge_prob=args.merge_prob,
        density_gradient=args.density_gradient,
        density_points=dp,
        subdivision_rounds=args.subdivision_rounds,
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
