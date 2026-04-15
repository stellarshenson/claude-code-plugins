"""Callout placement proposal tool.

Greedy placer with random-ordering restarts. Given an SVG and a list of
callout requests, returns a globally-consistent joint placement: each
callout's text bbox fully inside a free region, each leader clean of
hard-shape crossings, no pairwise conflicts between placed callouts.

Approach:
  1. Parse the SVG via svgelements and reuse ``find_empty_regions`` to
     obtain the free-region polygons (``callout-*`` groups already
     excluded by that tool's default). Runs once per distinct standoff
     value when the callout list mixes leader and leaderless entries.
  2. Rasterise every visible surrogate (rect / polygon / stroked line)
     into a single boolean obstacle bitmap via the existing
     ``_rasterise_surrogates`` helper. Leader cleanness checks walk
     this bitmap pixel-by-pixel along the candidate line, which is
     100x faster than shapely pairwise intersection scans.
  3. For each callout, enumerate candidate positions on a coarse grid
     inside every free region. A position is a TEXT BBOX CENTRE.
     Filter candidates whose bbox is not fully inside the free-region
     bitmap OR (for leader callouts) whose leader crosses an obstacle
     pixel after the initial grace zone near the target.
  4. Score each surviving candidate with a weighted sum: leader length
     deviation from a sweet-spot, text-to-target distance beyond a
     generous cap, preferred-side miss, and leader-near-axial penalty
     (diagonal leaders read better than near-horizontal or near-vertical
     ones in dense scenes).
  5. Sort callouts by ascending feasibility (tightest shortlists go
     first) and greedily place each by picking the best-scoring
     candidate that does not pairwise-conflict with already-placed
     callouts. Pairwise conflicts are hard: text bbox overlap, leader
     crosses placed text bbox, leader crosses placed leader.
  6. Repeat with ``restart_orderings`` random shufflings via a seeded
     RNG; keep the ordering that produced the lowest total penalty and
     zero hard failures.

The API mirrors ``find_empty_regions`` in input handling: ``svg`` can be
a path, string, bytes, or file-like. Callouts are passed as a list of
``CalloutRequest`` dataclasses or as the JSON equivalent via the CLI.

Soft pairwise penalties (near-miss proximity) are intentionally not
modelled. If greedy fails to produce good layouts in practice the API
stays stable while we graduate the solver to simulated annealing.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import fnmatch
import json
import math
import random
import sys
import time
from typing import Any

import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString
from shapely.geometry import box as sbox

from .calc_empty_space import (
    _element_to_surrogates,
    _parse_svg_source,
    _text_width_px,
    find_empty_regions,
)
from .calc_geometry import rect_ray_exit

try:
    import svgelements as _se
except ImportError as _exc:  # pragma: no cover - dep is mandatory
    raise ImportError(
        "svgelements is required for propose_callouts. Reinstall stellars-claude-code-plugins."
    ) from _exc


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CalloutRequest:
    """One callout to place.

    ``id`` must start with ``callout-`` so existing tooling (the
    `empty-space` exclude_ids default and `overlaps` cross-collision
    audit) finds it consistently.

    ``target`` is either a point ``(x, y)`` or a rect bbox
    ``(x, y, w, h)``. When a bbox is given the centre is used as the
    leader origin and the bbox is recorded as the "target shape" so
    leaders are allowed to start inside it without being flagged as
    crossing an obstacle.

    ``text`` is a single string; ``\\n`` breaks lines and ``\\t`` expands
    to 4 spaces. Use this instead of a list of strings.

    ``font_size`` defaults to 8.5 matching the existing
    ``.callout-text`` convention.

    ``standoff`` is the gap (in px) between the leader end and the text
    bounding box edge, enforced via the leader anchor computation.

    ``leader`` (default True) controls whether a leader line is drawn.
    Set to ``False`` for a leaderless label - a text block placed as
    close as possible to the target without a connecting line. Used
    for waypoint labels, chart legends, and any callout where the
    visual proximity to the target is sufficient without a drawn
    connection. Leaderless callouts use the global
    ``leaderless_standoff`` (default 5 px) as their text-to-obstacle
    breath, much tighter than the leader standoff (20 px) because the
    text itself is the pointer and must sit close to the target. The
    scoring function pulls the text bbox CENTRE toward the target
    point (sweet spot 0), so horizontally-symmetric labels settle
    centred on their target instead of drifting to one side.

    ``preferred_side`` is an optional hint: ``"above"``, ``"below"``,
    ``"left"``, ``"right"``. Violations are a soft penalty, not a hard
    filter.
    """

    id: str
    target: Any  # (x, y) or (x, y, w, h)
    text: str
    font_size: float = 8.5
    standoff: float = 8.0
    leader: bool = True
    preferred_side: str | None = None

    def lines(self) -> list[str]:
        """Split ``text`` on newlines; expand tabs to 4 spaces per line."""
        return [ln.expandtabs(4) for ln in self.text.split("\n")]

    def target_point(self) -> tuple[float, float]:
        """Return the leader origin as a point."""
        if len(self.target) == 2:
            return (float(self.target[0]), float(self.target[1]))
        if len(self.target) == 4:
            x, y, w, h = self.target
            return (float(x) + float(w) / 2, float(y) + float(h) / 2)
        raise ValueError(f"target must be (x, y) or (x, y, w, h); got {self.target!r}")

    def target_bbox(self) -> tuple[float, float, float, float] | None:
        """Return the target's bbox if the target is a rect, else None."""
        if len(self.target) == 4:
            return tuple(float(v) for v in self.target)  # type: ignore[return-value]
        return None


@dataclass
class CalloutProposal:
    """A single placement proposal for one callout.

    ``text_baseline`` is the ``(x, y)`` baseline of the first text line,
    with ``text_anchor="start"`` semantics (x is the left edge). Every
    subsequent line is offset by ``font_size + 2`` px vertically.

    ``text_bbox`` is ``(x, y, w, h)`` in world coordinates including a
    2px padding already baked in.

    ``leader_start`` and ``leader_anchor`` are ``None`` for leaderless
    callouts. For callouts with a leader, ``leader_start`` is the
    target point and ``leader_anchor`` is the point on the inflated
    text bbox where the leader terminates; the gap between
    ``leader_anchor`` and the raw text bbox edge is exactly
    ``standoff``.

    ``penalty`` is the total weighted score (lower is better). The
    ``breakdown`` dict contains one entry per penalty term so callers
    can see which terms dominate.
    """

    id: str
    text_baseline: tuple[float, float]
    text_anchor: str
    text_bbox: tuple[float, float, float, float]
    leader_start: tuple[float, float] | None
    leader_anchor: tuple[float, float] | None
    penalty: float
    breakdown: dict[str, float]

    def to_dict(self) -> dict:
        return asdict(self)


DEFAULT_WEIGHTS = {
    "leader_length": 0.02,  # quadratic around LEADER_SWEET_SPOT
    "target_distance": 0.05,  # quadratic beyond MAX_TARGET_DIST
    "preferred_side_miss": 10.0,
    "leader_angle": 0.5,  # penalise near-horizontal or near-vertical
}

LEADER_SWEET_SPOT = 55.0  # ideal leader length in px; quadratic penalty around this
MAX_TARGET_DIST = 120.0  # text-centre-to-target distance beyond this adds penalty

# Pad added around a measured text bbox before shapely containment checks
# and before the inflated-bbox leader anchor computation. Matches the
# existing find_empty_regions text rasterisation.
TEXT_PAD = 2.0


# ---------------------------------------------------------------------------
# Obstacle extraction
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Text metrics and bbox construction
# ---------------------------------------------------------------------------


def _text_metrics(request: CalloutRequest) -> tuple[float, float, int]:
    """Return (width, height, line_count) for a callout request in px.

    Uses Pillow's ``ImageFont.load_default(size=N).getlength(text)`` via
    the cached helper in ``calc_empty_space``. The width is the longest
    line's rendered width; the height is ``font_size * n_lines + 2``
    matching the existing text rasterisation convention.
    """
    lines = request.lines()
    if not lines:
        lines = [""]
    width = max(_text_width_px(ln, request.font_size) for ln in lines)
    height = request.font_size * len(lines) + 2
    return width, height, len(lines)


def _text_bbox_centred(cx: float, cy: float, text_w: float, text_h: float):
    """Return the text bbox as ``(x, y, w, h)`` centred on ``(cx, cy)``."""
    x = cx - text_w / 2 - TEXT_PAD
    y = cy - text_h / 2 - TEXT_PAD
    w = text_w + 2 * TEXT_PAD
    h = text_h + 2 * TEXT_PAD
    return (x, y, w, h)


def _text_baseline_from_bbox(
    bbox: tuple[float, float, float, float], font_size: float
) -> tuple[float, float]:
    """Return the baseline ``(x, y)`` of the FIRST text line for an SVG
    ``<text>`` element with ``text-anchor="start"``.

    The bbox top-left is the first line's ascender top; the baseline is
    ``TEXT_PAD + font_size`` down from that.
    """
    x, y, _, _ = bbox
    return (x + TEXT_PAD, y + TEXT_PAD + font_size)


# ---------------------------------------------------------------------------
# Leader anchor and scoring
# ---------------------------------------------------------------------------


def _leader_anchor(
    text_bbox: tuple[float, float, float, float],
    target: tuple[float, float],
    standoff: float,
) -> tuple[float, float]:
    """Compute the leader anchor by inflating the text bbox by ``standoff``
    and intersecting the ray from the inflated bbox centre toward the
    target with the inflated bbox perimeter.

    Guarantees the leader never enters the raw text bbox interior and
    never glues to its edge.
    """
    x, y, w, h = text_bbox
    inflated = (x - standoff, y - standoff, w + 2 * standoff, h + 2 * standoff)
    try:
        ax, ay = rect_ray_exit(inflated, target)
    except ValueError:
        # Target coincides with inflated centre - fall back to the bbox
        # midpoint closest to the caller's nominal direction.
        cx = x + w / 2
        cy = y + h / 2
        ax, ay = cx, cy - h / 2 - standoff
    return (ax, ay)


def _side_of_target(
    text_bbox: tuple[float, float, float, float],
    target: tuple[float, float],
) -> str:
    """Determine which side of the target the text sits: above/below/left/right.

    Uses the vector from target to text-bbox centre; picks the dominant
    axis.
    """
    x, y, w, h = text_bbox
    cx = x + w / 2
    cy = y + h / 2
    dx = cx - target[0]
    dy = cy - target[1]
    if abs(dx) > abs(dy):
        return "right" if dx > 0 else "left"
    return "below" if dy > 0 else "above"


def _score_candidate(
    text_bbox: tuple[float, float, float, float],
    target: tuple[float, float],
    leader_anchor: tuple[float, float] | None,
    request: CalloutRequest,
    weights: dict,
) -> tuple[float, dict[str, float]]:
    """Weighted sum score for a single candidate.

    Only position-dependent, single-callout terms are computed here.
    Pairwise terms are enforced hard during the greedy placement step.
    Leaderless callouts (``request.leader is False``) skip the
    leader-length and leader-angle terms and measure target distance
    from the text bbox EDGE instead of the centre, with a much tighter
    sweet spot so the text lands adjacent to the target.
    """
    breakdown: dict[str, float] = {}
    x, y, w, h = text_bbox
    cx = x + w / 2
    cy = y + h / 2

    if request.leader and leader_anchor is not None:
        leader_len = math.hypot(leader_anchor[0] - target[0], leader_anchor[1] - target[1])
        breakdown["leader_length"] = (
            weights["leader_length"] * (leader_len - LEADER_SWEET_SPOT) ** 2
        )
        target_dist = math.hypot(cx - target[0], cy - target[1])
        overshoot = max(0.0, target_dist - MAX_TARGET_DIST)
        breakdown["target_distance"] = weights["target_distance"] * overshoot**2
        if leader_len > 1.0:
            angle = math.atan2(
                abs(leader_anchor[1] - target[1]),
                abs(leader_anchor[0] - target[0]),
            )
            # 0 <= angle <= pi/2. sin(2*angle) peaks at pi/4, zeros at 0
            # and pi/2. We want HIGH diagonality, so penalty = 1 - it.
            diagonality = math.sin(2 * angle)
            breakdown["leader_angle"] = weights["leader_angle"] * (1 - diagonality)
        else:
            breakdown["leader_angle"] = 0.0
    else:
        # Leaderless: distance from target to text bbox CENTER,
        # pulled toward 0 so the label sits CENTRED on the target
        # point. Edge distance is direction-agnostic and causes
        # horizontally-symmetric labels to drift to one side; centre
        # distance has a single unique minimum at target == centre,
        # so the solver converges to a centred layout. Obstacle
        # standoff still prevents overlap with real shapes.
        target_dist = math.hypot(cx - target[0], cy - target[1])
        breakdown["leaderless_target_distance"] = weights["target_distance"] * target_dist**2 * 4.0

    if request.preferred_side is not None:
        actual = _side_of_target(text_bbox, target)
        breakdown["preferred_side_miss"] = (
            float(weights["preferred_side_miss"]) if actual != request.preferred_side else 0.0
        )

    total = sum(breakdown.values())
    return total, breakdown


# ---------------------------------------------------------------------------
# Free-region bitmap for fast bbox containment
# ---------------------------------------------------------------------------


def _free_mask_from_obstacles(obstacle_mask, standoff: float):
    """Compute the free mask (eroded by ``standoff``) directly from
    the obstacle bitmap via ``scipy.ndimage.distance_transform_edt``.

    Equivalent to the internal computation inside ``find_empty_regions``
    but preserves interior holes correctly. Using the polygon boundaries
    returned by ``find_empty_regions`` + PIL fill would lose holes
    (card interiors inside a huge concave free region end up flagged
    as "free" even though they are occluded).
    """
    free = ~obstacle_mask
    if standoff > 0:
        padded = np.zeros((free.shape[0] + 2, free.shape[1] + 2), dtype=bool)
        padded[1:-1, 1:-1] = free
        dist = ndi.distance_transform_edt(padded)
        free = dist[1:-1, 1:-1] > standoff
    return free


def _build_obstacle_mask(svg_doc, canvas, exclude_ids, container_elem=None):
    """Rasterise every visible surrogate into a raw obstacle bitmap.

    Distinct from the free_mask used by ``find_empty_regions`` because
    this one has NO distance-transform erosion - we want the exact
    pixels covered by obstacles so the leader walker can detect hits
    down to the pixel.

    When ``container_elem`` is set, the element's own surrogates are
    skipped (it is not an obstacle) but its descendants / siblings
    remain obstacles as usual. The caller is responsible for AND-ing
    the resulting mask's inverse with a container interior mask.
    """
    from .calc_empty_space import _rasterise_surrogates

    surrogates: list = []

    def walk(node):
        eid = getattr(node, "id", None)
        if eid is not None and any(fnmatch.fnmatchcase(eid, pat) for pat in exclude_ids):
            return
        if node is not container_elem:
            surrogates.extend(_element_to_surrogates(node))
        if isinstance(node, _se.Group):
            for child in node:
                walk(child)

    walk(svg_doc)
    cx, cy, _, _ = canvas
    return _rasterise_surrogates(canvas, surrogates), (cx, cy)


def _bbox_fits_mask(mask, origin, bbox: tuple[float, float, float, float]) -> bool:
    """True when every pixel under ``bbox`` is inside the free-region mask."""
    ox, oy = origin
    x, y, w, h = bbox
    H, W = mask.shape
    x0 = int(math.floor(x - ox))
    y0 = int(math.floor(y - oy))
    x1 = int(math.ceil(x - ox + w))
    y1 = int(math.ceil(y - oy + h))
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H or x0 >= x1 or y0 >= y1:
        return False
    return bool(mask[y0:y1, x0:x1].all())


# ---------------------------------------------------------------------------
# Candidate enumeration and hard filtering
# ---------------------------------------------------------------------------


def _enumerate_candidates(
    request: CalloutRequest,
    regions: list[dict],
    obstacle_mask,
    obstacle_origin: tuple[float, float],
    n_candidates: int,
    standoff: float,
    weights: dict,
    free_mask=None,
    mask_origin: tuple[float, float] | None = None,
) -> list[CalloutProposal]:
    """Enumerate, filter, and score candidate placements for ONE callout.

    Walks each free region polygon's bounding box on a coarse grid
    (spacing ``standoff // 4``, floor 4 px). For each grid point treats
    it as the text bbox CENTRE and keeps the candidate when:

      - every pixel under the text bbox is inside ``free_mask`` (fast
        numpy slice check, ~50 ns);
      - the leader from the target to the leader anchor does NOT cross
        any obstacle other than the target's containing shape (STRtree
        spatial index prunes the shapely intersect scan to nearby
        obstacles only).

    Surviving candidates are scored with ``_score_candidate`` and the
    top ``n_candidates`` by ascending penalty are returned. Passing
    ``free_mask`` and ``mask_origin`` is strongly recommended - without
    them the containment check falls back to a shapely polygon cover
    which is 100-1000x slower.
    """
    text_w, text_h, _ = _text_metrics(request)
    fit_w = text_w + 2 * TEXT_PAD
    fit_h = text_h + 2 * TEXT_PAD
    target = request.target_point()

    step = max(4, int(standoff // 4))
    survivors: list[CalloutProposal] = []
    seen: set[tuple[int, int]] = set()

    for reg in regions:
        xs_poly = [p[0] for p in reg["boundary"]]
        ys_poly = [p[1] for p in reg["boundary"]]
        if not xs_poly or not ys_poly:
            continue
        minx = min(xs_poly)
        miny = min(ys_poly)
        maxx = max(xs_poly)
        maxy = max(ys_poly)
        x0 = minx + fit_w / 2
        y0 = miny + fit_h / 2
        x1 = maxx - fit_w / 2
        y1 = maxy - fit_h / 2
        if x0 >= x1 or y0 >= y1:
            continue
        ys = _arange(y0, y1, step)
        xs = _arange(x0, x1, step)
        for cy in ys:
            for cx in xs:
                # De-duplicate candidates that fall inside multiple
                # region bboxes (large regions can overlap).
                key = (int(cx), int(cy))
                if key in seen:
                    continue
                seen.add(key)
                bbox = _text_bbox_centred(cx, cy, text_w, text_h)
                if not _bbox_fits_mask(free_mask, mask_origin, bbox):
                    continue
                if request.leader:
                    # Leader tip stops `request.standoff` px short of the
                    # text bbox edge (default 3 px, a visual gap). The
                    # outer `standoff` parameter is the empty-space
                    # breath used for the free-mask erosion - a different
                    # concept. Conflating the two leaves a visible 20 px
                    # gap between leader and text.
                    anchor = _leader_anchor(bbox, target, request.standoff)
                    if not _leader_is_clean(target, anchor, obstacle_mask, obstacle_origin):
                        continue
                    leader_start = target
                    leader_anchor = anchor
                else:
                    leader_start = None
                    leader_anchor = None
                score, breakdown = _score_candidate(bbox, target, leader_anchor, request, weights)
                proposal = CalloutProposal(
                    id=request.id,
                    text_baseline=_text_baseline_from_bbox(bbox, request.font_size),
                    text_anchor="start",
                    text_bbox=bbox,
                    leader_start=leader_start,
                    leader_anchor=leader_anchor,
                    penalty=score,
                    breakdown=breakdown,
                )
                survivors.append(proposal)

    survivors.sort(key=lambda p: p.penalty)
    return survivors[:n_candidates]


def _arange(start: float, stop: float, step: float) -> list[float]:
    """Tiny replacement for numpy.arange returning a Python float list.

    Keeps the module numpy-free on the hot path; numpy is still
    available via the rasteriser if we ever need it.
    """
    out: list[float] = []
    v = start
    while v < stop:
        out.append(v)
        v += step
    return out


def _leader_is_clean(
    target: tuple[float, float],
    anchor: tuple[float, float],
    obstacle_mask,
    mask_origin: tuple[float, float],
) -> bool:
    """True when the leader does not cross any obstacle pixel after
    initially walking out of the target's own containing shape.

    Walks the leader line one pixel per pixel of length via a
    vectorised ``np.linspace`` sampler. A "grace" phase lets the line
    start inside an obstacle (the target's container) and walk through
    obstacle pixels until it first reaches free space; from that point
    on, any further obstacle pixel is a real crossing and aborts with
    False. This handles both "target in free space" (grace ends at
    pixel 0) and "target inside a card" (grace ends when the line
    exits the card) without any special-case flags.
    """
    ox, oy = mask_origin
    H, W = obstacle_mask.shape
    dx = anchor[0] - target[0]
    dy = anchor[1] - target[1]
    leader_len = math.hypot(dx, dy)
    if leader_len <= 1.0:
        return True
    n = int(math.ceil(leader_len))
    if n < 2:
        return True
    t = np.linspace(0.0, 1.0, n + 1)
    xs = np.asarray(target[0] + t * dx - ox, dtype=np.int32)
    ys = np.asarray(target[1] + t * dy - oy, dtype=np.int32)
    valid = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
    if not valid.any():
        return True
    xs_v = xs[valid]
    ys_v = ys[valid]
    samples = obstacle_mask[ys_v, xs_v]
    # Find the first free sample; everything before is the grace zone
    # (walking out of the target's containing shape, if any).
    free_idx = np.where(~samples)[0]
    if len(free_idx) == 0:
        # Leader never reaches free space - this can only happen if
        # the anchor itself is inside an obstacle, which is already
        # ruled out by the caller's free_mask bbox check.
        return False
    first_free = int(free_idx[0])
    # After first_free any obstacle pixel is a real crossing.
    return not bool(samples[first_free:].any())


# ---------------------------------------------------------------------------
# Pairwise conflict checks for the greedy placement step
# ---------------------------------------------------------------------------


def _pairwise_conflict(candidate: CalloutProposal, placed: list[CalloutProposal]) -> bool:
    """True when ``candidate`` hard-conflicts with any already-placed
    callout: text bbox overlap, leader crosses placed text, or leader
    crosses placed leader. Leaderless callouts skip leader-related
    checks (only text-vs-text overlap matters for them).
    """
    cand_bbox = sbox(
        candidate.text_bbox[0],
        candidate.text_bbox[1],
        candidate.text_bbox[0] + candidate.text_bbox[2],
        candidate.text_bbox[1] + candidate.text_bbox[3],
    )
    cand_leader = None
    if candidate.leader_start is not None and candidate.leader_anchor is not None:
        cand_leader = LineString([candidate.leader_start, candidate.leader_anchor])

    for p in placed:
        p_bbox = sbox(
            p.text_bbox[0],
            p.text_bbox[1],
            p.text_bbox[0] + p.text_bbox[2],
            p.text_bbox[1] + p.text_bbox[3],
        )
        # Text-vs-text overlap: always a hard conflict.
        if cand_bbox.intersects(p_bbox) and not cand_bbox.touches(p_bbox):
            return True
        p_leader = None
        if p.leader_start is not None and p.leader_anchor is not None:
            p_leader = LineString([p.leader_start, p.leader_anchor])
        # Candidate leader vs placed text
        if cand_leader is not None:
            if cand_leader.intersects(p_bbox) and not cand_leader.touches(p_bbox):
                return True
        # Placed leader vs candidate text
        if p_leader is not None:
            if p_leader.intersects(cand_bbox) and not p_leader.touches(cand_bbox):
                return True
        # Leader vs leader (only meaningful when both exist)
        if cand_leader is not None and p_leader is not None:
            if cand_leader.crosses(p_leader):
                return True
    return False


# ---------------------------------------------------------------------------
# Greedy placement with random orderings
# ---------------------------------------------------------------------------


def _greedy_place(
    ordering: list[int],
    shortlists: list[list[CalloutProposal]],
) -> tuple[list[CalloutProposal | None], float]:
    """Run ONE greedy pass with a given ordering.

    Returns ``(layout, total_penalty)`` where ``layout[i]`` is the chosen
    proposal for callout ``i`` (or ``None`` if no feasible candidate).
    ``total_penalty`` is the sum of individual scores; unplaced callouts
    contribute ``float('inf')`` so an incomplete layout always ranks
    below any complete one.
    """
    n = len(shortlists)
    layout: list[CalloutProposal | None] = [None] * n
    placed: list[CalloutProposal] = []
    total = 0.0
    for i in ordering:
        picked: CalloutProposal | None = None
        for cand in shortlists[i]:
            if not _pairwise_conflict(cand, placed):
                picked = cand
                break
        layout[i] = picked
        if picked is None:
            total = float("inf")
        else:
            total += picked.penalty
            placed.append(picked)
    return layout, total


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def propose_callouts(
    svg,
    callouts: list[CalloutRequest],
    standoff: float = 20.0,
    leaderless_standoff: float = 5.0,
    n_candidates: int = 50,
    restart_orderings: int = 5,
    n_proposals: int = 5,
    seed: int = 42,
    weights: dict | None = None,
    exclude_ids=("callout-*",),
    container_id=None,
):
    """Propose joint placements for a list of callouts against an SVG.

    See the module docstring for the full algorithm. Returns a dict
    with ``best_layout`` (one proposal per input callout), ``proposals``
    (top-``n_proposals`` alternatives per callout, unfiltered by
    pairwise conflicts), ``empty_regions`` (the free-island polygons
    for debug rendering), and ``stats``.

    Leaderless callouts use ``leaderless_standoff`` (default 5 px,
    much tighter than the regular leader ``standoff`` of 20 px) so
    the text can sit close to its target. The scoring function then
    pulls the text bbox CENTRE toward the target point, penalised
    quadratically around 0 so horizontally-symmetric labels sit
    centred on their target instead of drifting to one side. Mixing
    leader and leaderless callouts triggers two empty-space passes
    so each callout is routed to its matching free regions.

    When ``container_id`` is set, placement is clipped to the interior
    of that element - both the free-mask used by the leader walker and
    the empty-region polygons consumed by the candidate enumerator.
    The element must be a closed shape (rect/circle/ellipse/polygon/
    polyline/path); groups are rejected. Useful for placing callouts
    inside a specific card without competing with whitespace outside.
    """
    if weights is None:
        weights = dict(DEFAULT_WEIGHTS)
    else:
        merged = dict(DEFAULT_WEIGHTS)
        merged.update(weights)
        weights = merged

    t_start = time.perf_counter()

    # Parse the SVG once, reuse for regions and obstacles.
    svg_doc, viewbox = _parse_svg_source(svg)

    # Optional container clip: resolved once, reused for both the raw
    # obstacle walk (skip-self) and the free-mask intersection.
    container_elem = None
    container_mask = None
    if container_id is not None:
        container_elem = svg_doc.get_element_by_id(container_id)
        if container_elem is None:
            raise ValueError(f"container_id={container_id!r} not found in SVG")
        from .calc_empty_space import (
            _container_interior_surrogates,
            _rasterise_surrogates,
        )

        interior_surrogates = _container_interior_surrogates(container_elem)
        container_mask = _rasterise_surrogates(viewbox, interior_surrogates)

    # Rasterise every visible obstacle to a raw pixel bitmap. The leader
    # walker samples this mask along each candidate line.
    obstacle_mask, obstacle_origin = _build_obstacle_mask(
        svg_doc, viewbox, exclude_ids, container_elem=container_elem
    )

    # Compute the free mask per distinct standoff directly from the
    # obstacle bitmap via distance_transform_edt. Preserves interior
    # holes correctly (boundary-polygon round-trip via PIL.polygon
    # would collapse holes inside a concave free region).
    standoffs_needed: set[float] = set()
    for req in callouts:
        standoffs_needed.add(leaderless_standoff if not req.leader else standoff)

    mask_by_so: dict[float, tuple] = {}
    regions_by_so: dict[float, list] = {}
    for s in standoffs_needed:
        free_mask = _free_mask_from_obstacles(obstacle_mask, s)
        if container_mask is not None:
            free_mask = free_mask & container_mask
        mask_by_so[s] = (free_mask, obstacle_origin)
        # Keep the polygon list for debug overlays and result output.
        regions_by_so[s] = find_empty_regions(
            svg, tolerance=s, exclude_ids=exclude_ids, container_id=container_id
        )

    # Per-callout candidate enumeration.
    shortlists: list[list[CalloutProposal]] = []
    proposals_top: list[list[CalloutProposal]] = []
    for req in callouts:
        eff_standoff = leaderless_standoff if not req.leader else standoff
        regions = regions_by_so[eff_standoff]
        free_mask, mask_origin = mask_by_so[eff_standoff]
        cands = _enumerate_candidates(
            req,
            regions,
            obstacle_mask,
            obstacle_origin,
            n_candidates=n_candidates,
            standoff=eff_standoff,
            weights=weights,
            free_mask=free_mask,
            mask_origin=mask_origin,
        )
        shortlists.append(cands)
        proposals_top.append(cands[:n_proposals])

    # Tightest-first default ordering; additional shuffled orderings
    # from a seeded RNG give the greedy pass a chance to escape locally
    # bad cascades.
    rng = random.Random(seed)
    n = len(callouts)
    base_ordering = sorted(range(n), key=lambda i: len(shortlists[i]))
    orderings = [base_ordering]
    for _ in range(max(0, restart_orderings - 1)):
        shuffled = list(range(n))
        rng.shuffle(shuffled)
        orderings.append(shuffled)

    best_layout: list[CalloutProposal | None] = [None] * n
    best_penalty = float("inf")
    for ordering in orderings:
        layout, total = _greedy_place(ordering, shortlists)
        if total < best_penalty:
            best_penalty = total
            best_layout = layout

    wall_ms = (time.perf_counter() - t_start) * 1000.0
    hard_failures = sum(1 for p in best_layout if p is None)

    # For debug overlays: return empty regions keyed by standoff so
    # callers can draw the right polygon set per callout standoff.
    return {
        "best_layout": best_layout,
        "best_penalty": best_penalty if best_penalty != float("inf") else None,
        "proposals": proposals_top,
        "empty_regions": regions_by_so.get(standoff, []),
        "empty_regions_by_standoff": {str(s): regions_by_so[s] for s in regions_by_so},
        "stats": {
            "orderings_tried": len(orderings),
            "wall_ms": wall_ms,
            "hard_failures": hard_failures,
            "candidates_per_callout": [len(s) for s in shortlists],
            "standoffs_used": sorted(standoffs_needed),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


_SCHEMA_EXAMPLE = """\
Schema for --plan JSON:

  [
    {
      "id": "callout-<name>",               # required, must start with "callout-"
      "target": [x, y],                     # required, point OR [x, y, w, h] bbox
      "text": "line 1\\nline 2",             # required, \\n breaks lines, \\t -> 4 spaces
      "font_size": 8.5,                     # optional, default 8.5
      "standoff": 8.0,                      # optional, leader-tip-to-text gap default 8.0
      "leader": true,                       # optional, default true; false = leaderless
      "preferred_side": null                # optional: "above" | "below" | "left" | "right"
    },
    ...
  ]

Example plan file (callouts.json):

  [
    {"id": "callout-merge",    "target": [410, 230], "text": "merge point\\n(single convergence)"},
    {"id": "callout-fork",     "target": [650, 230], "text": "fork point\\n(single divergence)"},
    {"id": "callout-standoff", "target": [808, 116], "text": "5px standoff\\n(arrow tip gap)"},
    {"id": "callout-waypoint", "target": [500, 400], "text": "Stage 3",            "leader": false}
  ]

Example invocation:

  svg-infographics callouts --svg diagram.svg --plan callouts.json --n-proposals 5
"""


def _load_plan(path: str) -> list[CalloutRequest]:
    with open(path, "r") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("plan JSON must be a list of callout objects")
    out = []
    for entry in raw:
        if "id" not in entry or "target" not in entry or "text" not in entry:
            raise ValueError(f"plan entry missing required field: {entry!r}")
        if not entry["id"].startswith("callout-"):
            raise ValueError(f"callout id must start with 'callout-': {entry['id']!r}")
        out.append(
            CalloutRequest(
                id=entry["id"],
                target=tuple(entry["target"]),
                text=entry["text"],
                font_size=float(entry.get("font_size", 8.5)),
                standoff=float(entry.get("standoff", 8.0)),
                leader=bool(entry.get("leader", True)),
                preferred_side=entry.get("preferred_side"),
            )
        )
    return out


def _proposal_to_dict(p: CalloutProposal | None) -> dict | None:
    if p is None:
        return None
    return p.to_dict()


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics callouts",
        description="Propose joint placements for a set of callouts against "
        "an SVG file. Greedy solver with random-ordering restarts; "
        "returns one best layout plus top-N alternatives per "
        "callout with penalty breakdowns.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_SCHEMA_EXAMPLE,
    )
    parser.add_argument("--svg", required=True, help="Path to the SVG file")
    parser.add_argument(
        "--plan",
        required=True,
        help="Path to a JSON file listing the callouts to place (see schema in --help epilog)",
    )
    parser.add_argument(
        "--standoff",
        type=float,
        default=20.0,
        help="Leader callout text-to-shape breath in px (default 20)",
    )
    parser.add_argument(
        "--leaderless-standoff",
        type=float,
        default=5.0,
        help="Leaderless callout text-to-shape breath in px (default 5)",
    )
    parser.add_argument(
        "--n-candidates",
        type=int,
        default=50,
        help="Max candidate positions per callout (default 50)",
    )
    parser.add_argument(
        "--restarts",
        type=int,
        default=5,
        help="Random-ordering restarts for the greedy solver (default 5)",
    )
    parser.add_argument(
        "--n-proposals",
        type=int,
        default=5,
        help="Top-K alternatives to return per callout (default 5)",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument(
        "--container-id",
        default=None,
        help="Clip placement to the interior of the element with this id. "
        "Must point to a closed shape (rect/circle/ellipse/polygon/path); "
        "groups are rejected. Callouts are routed only to empty regions "
        "inside the container.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the full result as JSON",
    )
    args = parser.parse_args()

    requests = _load_plan(args.plan)
    result = propose_callouts(
        svg=args.svg,
        callouts=requests,
        standoff=args.standoff,
        leaderless_standoff=args.leaderless_standoff,
        n_candidates=args.n_candidates,
        restart_orderings=args.restarts,
        n_proposals=args.n_proposals,
        seed=args.seed,
        container_id=args.container_id,
    )

    if args.json:
        serialisable = {
            "best_layout": [_proposal_to_dict(p) for p in result["best_layout"]],
            "best_penalty": result["best_penalty"],
            "proposals": [[_proposal_to_dict(p) for p in lst] for lst in result["proposals"]],
            "empty_regions": result["empty_regions"],
            "stats": result["stats"],
        }
        json.dump(serialisable, sys.stdout, indent=2)
        print()
        return

    # Human-readable text output
    stats = result["stats"]
    print(
        f"=== PROPOSAL ({len(requests)} callouts, "
        f"{stats['wall_ms']:.0f} ms, {stats['orderings_tried']} orderings) ==="
    )
    print(f"total penalty: {result['best_penalty']}")
    print(f"hard failures: {stats['hard_failures']}")
    print()
    print("Best layout:")
    for req, proposal in zip(requests, result["best_layout"]):
        if proposal is None:
            print(f"  [{req.id}] NO FIT")
            continue
        bx, by = proposal.text_baseline
        if proposal.leader_anchor is not None and proposal.leader_start is not None:
            ax, ay = proposal.leader_anchor
            tx, ty = proposal.leader_start
            llen = math.hypot(ax - tx, ay - ty)
            print(
                f"  [{req.id}] text=({bx:.0f},{by:.0f}) "
                f"anchor=({ax:.0f},{ay:.0f}) "
                f"leader_len={llen:.0f}px penalty={proposal.penalty:.2f}"
            )
        else:
            print(
                f"  [{req.id}] text=({bx:.0f},{by:.0f}) leaderless penalty={proposal.penalty:.2f}"
            )
    print()
    print(f"candidates per callout: {stats['candidates_per_callout']}")


if __name__ == "__main__":
    main()
