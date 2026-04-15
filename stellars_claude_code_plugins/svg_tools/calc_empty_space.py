"""Identify empty regions on an SVG canvas.

Given an SVG file (path, stream, or XML string), the tool parses every
visible element via the ``svgelements`` library, builds an occupancy
bitmap at 1 px per canvas unit, applies an Euclidean-distance erosion
with the requested tolerance, labels connected components, and traces
their boundaries with a pure-numpy Moore walk.

The tool is universal: it works on any SVG file, whether produced by the
svg-infographics workflow or imported from another source. No shape list
is built by the caller - the SVG IS the source of truth.

Internally every SVG element is converted to one of three **surrogate**
primitives before rasterisation:

    * ``("rect", x, y, w, h)`` - filled rectangle
    * ``("polyline", stroke, [(x, y), ...])`` - stroked open path
    * ``("polygon", [(x, y), ...])`` - filled closed polygon

``svgelements`` resolves transforms, style cascades and stroke-widths for
us. Bezier / arc segments are adaptively sampled (``max(10, min(100,
round(arc_length_px)))`` samples per segment) and expressed as polylines.
Clip paths and masks are handled by rasterising clipped children into a
temporary mask and ANDing with the clip region before writing to the
main grid. ``<image>`` elements become opaque bboxes.
"""

from __future__ import annotations

import argparse
import fnmatch
import io
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
from scipy import ndimage as ndi

try:
    import svgelements as _se
except ImportError as _exc:  # pragma: no cover - dep is mandatory
    raise ImportError(
        "svgelements is required for find_empty_regions. Install via "
        "`pip install svgelements` or the project's pyproject extras."
    ) from _exc

try:
    from PIL import ImageFont as _ImageFont
except ImportError as _exc:  # pragma: no cover - dep is mandatory
    raise ImportError(
        "Pillow is required for find_empty_regions text metrics. Install "
        "via `pip install pillow` or the project's pyproject extras."
    ) from _exc


# Cache Pillow font instances per size - loading is cheap but not free
# and text elements in a typical SVG share the same handful of sizes.
_FONT_CACHE: dict[float, Any] = {}


def _text_width_px(text, font_size):
    """Measure the rendered width of ``text`` at ``font_size`` via Pillow.

    Uses ``PIL.ImageFont.load_default(size=font_size)`` which returns a
    scalable TrueType bundled with Pillow. The metrics are not an exact
    match for the font-family declared in the SVG (Segoe UI / Arial /
    Helvetica on production scenes) but all common sans-serif faces fall
    within ~10% of each other, so the result is a much better bound than
    a flat character-count heuristic (especially for large title-row
    sizes where the heuristic overshoots by 10-15%).
    """
    key = round(float(font_size), 2)
    font = _FONT_CACHE.get(key)
    if font is None:
        font = _ImageFont.load_default(size=key)
        _FONT_CACHE[key] = font
    return float(font.getlength(text))


# ---------------------------------------------------------------------------
# SVG source handling
# ---------------------------------------------------------------------------


def _parse_svg_source(source):
    """Coerce ``source`` into a parsed svgelements SVG document.

    Accepts:
      * ``pathlib.Path`` - file on disk
      * ``str`` - either an XML string (starts with ``<``) or a path
      * ``bytes`` - raw XML bytes
      * file-like object with a ``.read()`` method

    Returns a tuple ``(svg_doc, canvas_viewbox)`` where ``canvas_viewbox``
    is ``(x, y, w, h)`` derived from the SVG viewBox or falls back to
    ``(0, 0, width, height)`` from the root <svg> attributes.
    """
    if isinstance(source, Path):
        svg = _se.SVG.parse(str(source))
    elif isinstance(source, bytes):
        svg = _se.SVG.parse(io.BytesIO(source))
    elif isinstance(source, str):
        stripped = source.lstrip()
        if stripped.startswith("<"):
            svg = _se.SVG.parse(io.StringIO(source))
        else:
            svg = _se.SVG.parse(source)
    elif hasattr(source, "read"):
        svg = _se.SVG.parse(source)
    else:
        raise TypeError(
            f"unsupported SVG source type: {type(source).__name__}. "
            "Expected path, str, bytes, or file-like object."
        )

    vb = svg.viewbox
    if vb is not None:
        try:
            canvas = (float(vb.x), float(vb.y), float(vb.width), float(vb.height))
        except AttributeError:
            # Some svgelements versions expose viewbox as a string
            parts = str(vb).split()
            if len(parts) == 4:
                canvas = tuple(float(p) for p in parts)
            else:
                canvas = None
    else:
        canvas = None

    if canvas is None:
        w = float(svg.width) if svg.width else 1000.0
        h = float(svg.height) if svg.height else 1000.0
        canvas = (0.0, 0.0, w, h)

    return svg, canvas


# ---------------------------------------------------------------------------
# Surrogate primitives
# ---------------------------------------------------------------------------


# A surrogate is one of:
#   ("rect",     x, y, w, h)              - filled rect
#   ("polyline", stroke, [(x, y), ...])   - stroked open path
#   ("polygon",  [(x, y), ...])           - filled closed polygon


_CIRCLE_SIDES = 32


def _tx_point(transform, x, y):
    """Apply an svgelements Matrix to a single point and return (x', y').

    svgelements reifies transforms into coordinates for Rect / Circle /
    Ellipse / Line / Polyline / Polygon / Path when the transform is
    a pure translate+scale, but leaves ``element.transform`` non-identity
    for Text, Image, and any shape whose transform includes rotation or
    skew. Applying the per-element transform explicitly - even when it
    is identity - makes the converter work uniformly for every element
    kind, so the surrogate SVG always carries final world-space geometry.
    """
    if transform is None:
        return (float(x), float(y))
    a = transform.a
    b = transform.b
    c = transform.c
    d = transform.d
    e = transform.e
    f = transform.f
    return (a * x + c * y + e, b * x + d * y + f)


def _tx_is_axis_aligned(transform):
    """True when the transform has no rotation or skew (b == 0 and c == 0)
    and a / d are positive. Axis-aligned rects survive as rects; tilted
    or flipped rects must become 4-point polygons in the surrogate.
    """
    if transform is None:
        return True
    return (
        abs(transform.b) < 1e-9 and abs(transform.c) < 1e-9 and transform.a > 0 and transform.d > 0
    )


def _circle_to_polygon(cx, cy, rx, ry, sides=_CIRCLE_SIDES):
    """Approximate an ellipse as an N-sided polygon."""
    pts = []
    for i in range(sides):
        t = 2 * math.pi * i / sides
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return pts


def _adaptive_sample_count(length_px):
    """Pick a per-segment sample count: ~1 sample per px, clamped [10, 100]."""
    if length_px is None or not math.isfinite(length_px) or length_px <= 0:
        return 10
    return max(10, min(100, int(round(length_px))))


def _sample_path_to_segments(path):
    """Convert an svgelements Path into a list of (open_polyline, closed)
    tuples.

    A path may contain multiple subpaths (separated by Move segments) and
    may alternate between open and closed via Close segments. We walk the
    segment list, collecting points for each subpath and sampling Bezier /
    arc segments via ``.point(t)`` at adaptive sample counts.

    Returns a list of ``(points, closed)`` tuples where ``points`` is a
    list of ``(x, y)`` floats and ``closed`` is a bool.
    """
    subpaths = []
    current = []
    closed = False

    for seg in path:
        name = type(seg).__name__
        if name == "Move":
            if current:
                subpaths.append((current, closed))
            current = []
            if seg.end is not None:
                current.append((float(seg.end.x), float(seg.end.y)))
            closed = False
            continue

        if name == "Close":
            if current and seg.end is not None:
                # Ensure the subpath explicitly terminates at its start.
                start = (float(seg.end.x), float(seg.end.y))
                if not current or current[0] != start:
                    current.append(start)
            closed = True
            if current:
                subpaths.append((current, closed))
            current = []
            closed = False
            continue

        if name == "Line":
            if seg.end is not None:
                current.append((float(seg.end.x), float(seg.end.y)))
            continue

        # Curved segments: CubicBezier, QuadraticBezier, Arc
        try:
            length = float(seg.length(error=1e-3))
        except TypeError:
            length = float(seg.length())
        except Exception:
            length = None
        n = _adaptive_sample_count(length)
        # Include t=0 only if current is empty (otherwise last point is
        # already at t=0 of this segment).
        start_t = 1 if current else 0
        for i in range(start_t, n + 1):
            t = i / n
            p = seg.point(t)
            current.append((float(p.x), float(p.y)))

    if current:
        subpaths.append((current, closed))

    return subpaths


def _element_to_surrogates(elem):
    """Convert one svgelements element into zero or more surrogate primitives.

    Called per element in the recursive walk. Returns a list of tuples in
    the surrogate format. Every element's coordinates pass through
    ``elem.transform`` so the surrogate SVG always carries FINAL
    world-space geometry - svgelements reifies transforms into some
    element types but not Text, Image, or any rotated shape, so applying
    the transform uniformly makes the converter work for every case.
    Unknown element kinds return an empty list (silently skipped).
    """
    T = type(elem).__name__

    if T in ("SVG", "Group", "Defs", "Use"):
        return []

    fill = getattr(elem, "fill", None)
    stroke = getattr(elem, "stroke", None)
    stroke_width = getattr(elem, "stroke_width", None)
    if stroke_width is None or stroke_width == 0:
        stroke_width = 1.0
    stroke_width = max(1.0, float(stroke_width))
    has_fill = fill is not None and getattr(fill, "value", True) is not None
    has_stroke = stroke is not None and getattr(stroke, "value", True) is not None

    transform = getattr(elem, "transform", None)

    def tx(x, y):
        return _tx_point(transform, x, y)

    out: list[tuple] = []

    if T == "Rect":
        x = float(elem.x)
        y = float(elem.y)
        w = float(elem.width)
        h = float(elem.height)
        corners = [
            tx(x, y),
            tx(x + w, y),
            tx(x + w, y + h),
            tx(x, y + h),
        ]
        if _tx_is_axis_aligned(transform):
            # Still an axis-aligned rect after transform (identity or pure
            # scale+translate). Emit as a fast-path rect primitive.
            x0, y0 = corners[0]
            x2, y2 = corners[2]
            rx = min(x0, x2)
            ry = min(y0, y2)
            rw = abs(x2 - x0)
            rh = abs(y2 - y0)
            if has_fill:
                out.append(("rect", rx, ry, rw, rh))
            if has_stroke:
                out.append(("polyline", stroke_width, corners + [corners[0]]))
        else:
            # Rotated / skewed rect - emit as a 4-corner polygon.
            if has_fill:
                out.append(("polygon", corners))
            if has_stroke:
                out.append(("polyline", stroke_width, corners + [corners[0]]))
        return out

    if T in ("Circle", "Ellipse"):
        cx = float(elem.cx)
        cy = float(elem.cy)
        rx = float(elem.rx)
        ry = float(getattr(elem, "ry", rx))
        # Approximate as a 32-sided polygon in LOCAL coords, then apply
        # the transform to every vertex so rotation/scale come out right.
        local = _circle_to_polygon(cx, cy, rx, ry)
        pts = [tx(px, py) for px, py in local]
        if has_fill:
            out.append(("polygon", pts))
        if has_stroke:
            out.append(("polyline", stroke_width, pts + [pts[0]]))
        return out

    if T in ("SimpleLine", "Line"):
        x1 = float(elem.x1)
        y1 = float(elem.y1)
        x2 = float(elem.x2)
        y2 = float(elem.y2)
        pts = [tx(x1, y1), tx(x2, y2)]
        out.append(("polyline", stroke_width, pts))
        return out

    if T == "Polyline":
        pts = [tx(float(p.x), float(p.y)) for p in elem.points]
        if has_fill:
            out.append(("polygon", pts))
        if has_stroke or not has_fill:
            out.append(("polyline", stroke_width, pts))
        return out

    if T == "Polygon":
        pts = [tx(float(p.x), float(p.y)) for p in elem.points]
        if has_fill:
            out.append(("polygon", pts))
        if has_stroke:
            out.append(("polyline", stroke_width, pts + [pts[0]]))
        return out

    if T == "Path":
        subpaths = _sample_path_to_segments(elem)
        for local_pts, closed in subpaths:
            if len(local_pts) < 2:
                continue
            pts = [tx(px, py) for px, py in local_pts]
            if closed and has_fill:
                out.append(("polygon", pts))
            if has_stroke or (not closed and not has_fill):
                out.append(("polyline", stroke_width, pts))
        return out

    if T == "Text":
        # <text> x, y is the glyph baseline (or middle/right depending on
        # text-anchor). Apply the element transform to the anchor point
        # first, THEN build the glyph-row bbox around it.
        try:
            x = float(elem.x)
            y = float(elem.y)
        except TypeError:
            return []
        wx, wy = tx(x, y)
        font_size = float(getattr(elem, "font_size", 12) or 12)
        text = getattr(elem, "text", "") or ""
        lines = [ln for ln in text.splitlines() if ln] or [""]
        glyph_width = max(_text_width_px(ln, font_size) for ln in lines)
        h = font_size * len(lines) + 2
        pad = 2.0
        w = glyph_width + 2 * pad

        anchor = getattr(elem, "anchor", None) or "start"
        if anchor == "middle":
            left = wx - glyph_width / 2 - pad
        elif anchor == "end":
            left = wx - glyph_width - pad
        else:
            left = wx - pad
        top = wy - font_size - pad
        out.append(("rect", left, top, w, h))
        return out

    if T == "Image":
        try:
            x = float(elem.x)
            y = float(elem.y)
            w = float(getattr(elem, "image_width", None) or getattr(elem, "width", 0) or 0)
            h = float(getattr(elem, "image_height", None) or getattr(elem, "height", 0) or 0)
        except (TypeError, ValueError):
            return []
        if w <= 0 or h <= 0:
            return []
        corners = [
            tx(x, y),
            tx(x + w, y),
            tx(x + w, y + h),
            tx(x, y + h),
        ]
        if _tx_is_axis_aligned(transform):
            x0, y0 = corners[0]
            x2, y2 = corners[2]
            out.append(("rect", min(x0, x2), min(y0, y2), abs(x2 - x0), abs(y2 - y0)))
        else:
            out.append(("polygon", corners))
        return out

    return []


# ---------------------------------------------------------------------------
# Rasteriser for surrogate primitives
# ---------------------------------------------------------------------------


def _raster_rect(grid, origin, x, y, w, h):
    ox, oy = origin
    H, W = grid.shape
    x0 = max(0, int(round(x - ox)))
    y0 = max(0, int(round(y - oy)))
    x1 = min(W, int(round(x - ox + w)))
    y1 = min(H, int(round(y - oy + h)))
    if x0 < x1 and y0 < y1:
        grid[y0:y1, x0:x1] = True


def _raster_polyline(grid, origin, stroke, points):
    """Mark pixels within ``stroke/2`` of any segment of the polyline.

    Per-segment numpy mgrid over a local AABB, point-to-segment distance,
    threshold. ~1 ms per segment on typical infographic canvases.
    """
    if len(points) < 2:
        return
    ox, oy = origin
    H, W = grid.shape
    half = max(0.5, stroke / 2.0)
    pad = int(math.ceil(half)) + 1

    for i in range(len(points) - 1):
        x1 = points[i][0] - ox
        y1 = points[i][1] - oy
        x2 = points[i + 1][0] - ox
        y2 = points[i + 1][1] - oy
        xmin = max(0, int(math.floor(min(x1, x2))) - pad)
        xmax = min(W, int(math.ceil(max(x1, x2))) + pad + 1)
        ymin = max(0, int(math.floor(min(y1, y2))) - pad)
        ymax = min(H, int(math.ceil(max(y1, y2))) + pad + 1)
        if xmin >= xmax or ymin >= ymax:
            continue
        ys, xs = np.mgrid[ymin:ymax, xmin:xmax]
        dx = x2 - x1
        dy = y2 - y1
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq < 1e-9:
            dist_sq = (xs - x1) ** 2 + (ys - y1) ** 2
        else:
            t = ((xs - x1) * dx + (ys - y1) * dy) / seg_len_sq
            np.clip(t, 0, 1, out=t)
            px = x1 + t * dx
            py = y1 + t * dy
            dist_sq = (xs - px) ** 2 + (ys - py) ** 2
        mask = dist_sq <= half * half
        grid[ymin:ymax, xmin:xmax] |= mask


def _raster_polygon(grid, origin, points):
    """Scanline fill of a closed polygon.

    For each row y, compute the x coordinates where the polygon edges
    cross y, sort them, and mark pixels between consecutive pairs as
    inside. Standard even-odd fill rule.
    """
    if len(points) < 3:
        return
    ox, oy = origin
    H, W = grid.shape

    # Translate to local coords once.
    local = [(p[0] - ox, p[1] - oy) for p in points]
    # Ensure closed.
    if local[0] != local[-1]:
        local.append(local[0])

    ys_poly = [p[1] for p in local]
    y_min = max(0, int(math.floor(min(ys_poly))))
    y_max = min(H - 1, int(math.ceil(max(ys_poly))))
    if y_min > y_max:
        return

    for y in range(y_min, y_max + 1):
        yc = y + 0.5  # sample at pixel centre
        crossings = []
        for i in range(len(local) - 1):
            x1, y1 = local[i]
            x2, y2 = local[i + 1]
            if (y1 <= yc < y2) or (y2 <= yc < y1):
                x_cross = x1 + (yc - y1) * (x2 - x1) / (y2 - y1)
                crossings.append(x_cross)
        crossings.sort()
        for k in range(0, len(crossings) - 1, 2):
            x0 = max(0, int(math.floor(crossings[k])))
            x1 = min(W, int(math.ceil(crossings[k + 1])))
            if x0 < x1:
                grid[y, x0:x1] = True


def _rasterise_surrogates(canvas, surrogates):
    """Build an occupancy grid from a list of surrogate primitives."""
    cx, cy, cw, ch = canvas
    W = int(round(cw))
    H = int(round(ch))
    grid = np.zeros((H, W), dtype=bool)
    origin = (cx, cy)
    for s in surrogates:
        kind = s[0]
        if kind == "rect":
            _raster_rect(grid, origin, s[1], s[2], s[3], s[4])
        elif kind == "polyline":
            _raster_polyline(grid, origin, s[1], s[2])
        elif kind == "polygon":
            _raster_polygon(grid, origin, s[1])
    return grid


_BACKGROUND_COVERAGE_THRESHOLD = 0.8


def _is_canvas_background(elem, canvas):
    """True when ``elem`` is a filled shape that covers >= 80% of the canvas.

    Used by every obstacle walk to automatically skip document background
    plates (full-canvas rects, oversized panels, etc.). Without this rule
    a single ``<rect class="bg-plate" width="W" height="H"/>`` would fill
    every pixel of the occupancy grid and leave zero free space for
    callouts or auto-route.

    Matches the threshold used by ``check_contrast._shape_is_doc_background``
    so empty-space and contrast agree on what counts as the doc background.
    """
    T = type(elem).__name__
    if T not in ("Rect", "Circle", "Ellipse", "Polygon", "Polyline", "Path"):
        return False
    fill = getattr(elem, "fill", None)
    if fill is None or getattr(fill, "value", True) is None:
        return False
    cx, cy, cw, ch = canvas
    canvas_area = cw * ch
    if canvas_area <= 0:
        return False

    surrogates = _element_to_surrogates(elem)
    if not surrogates:
        return False

    # Compute the filled bbox across all surrogates this element produced.
    xs: list[float] = []
    ys: list[float] = []
    for s in surrogates:
        kind = s[0]
        if kind == "rect":
            _, x, y, w, h = s
            xs.extend((x, x + w))
            ys.extend((y, y + h))
        elif kind == "polygon":
            for px, py in s[1]:
                xs.append(px)
                ys.append(py)
        else:
            # polylines alone (stroke-only) don't count as background
            continue
    if not xs:
        return False

    elem_area = (max(xs) - min(xs)) * (max(ys) - min(ys))
    return elem_area >= _BACKGROUND_COVERAGE_THRESHOLD * canvas_area


def _container_interior_surrogates(elem):
    """Surrogate primitives representing the FILLED interior of ``elem``.

    Used when the caller pins empty-space detection to a specific container
    shape via ``container_id``. The element's actual fill/stroke attributes
    are ignored - a stroked-only rect still counts as a closed region for
    masking purposes.

    Groups are rejected with ValueError: ``<g>`` is not closed geometry, it
    has no fill or boundary of its own. The caller must pass the ID of a
    visible shape (rect, circle, polygon, path) instead.
    """
    T = type(elem).__name__

    if T in ("SVG", "Group", "Defs", "Use"):
        raise ValueError(
            f"container_id must point to a closed shape, got <{T.lower()}>. "
            "Groups have no geometry - pass the ID of a rect, circle, "
            "ellipse, polygon, or path instead."
        )

    transform = getattr(elem, "transform", None)

    def tx(x, y):
        return _tx_point(transform, x, y)

    if T == "Rect":
        x = float(elem.x)
        y = float(elem.y)
        w = float(elem.width)
        h = float(elem.height)
        corners = [tx(x, y), tx(x + w, y), tx(x + w, y + h), tx(x, y + h)]
        if _tx_is_axis_aligned(transform):
            x0, y0 = corners[0]
            x2, y2 = corners[2]
            return [("rect", min(x0, x2), min(y0, y2), abs(x2 - x0), abs(y2 - y0))]
        return [("polygon", corners)]

    if T in ("Circle", "Ellipse"):
        cx = float(elem.cx)
        cy = float(elem.cy)
        rx = float(elem.rx)
        ry = float(getattr(elem, "ry", rx))
        local = _circle_to_polygon(cx, cy, rx, ry)
        return [("polygon", [tx(px, py) for px, py in local])]

    if T == "Polygon":
        pts = [tx(float(p.x), float(p.y)) for p in elem.points]
        return [("polygon", pts)]

    if T == "Polyline":
        pts = [tx(float(p.x), float(p.y)) for p in elem.points]
        if len(pts) >= 3:
            if pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            return [("polygon", pts)]
        return []

    if T == "Path":
        out = []
        subpaths = _sample_path_to_segments(elem)
        for local_pts, closed in subpaths:
            if len(local_pts) < 3:
                continue
            pts = [tx(px, py) for px, py in local_pts]
            # Force-close open subpaths - container is treated as closed
            # geometry regardless of source markup.
            if pts[0] != pts[-1]:
                pts = pts + [pts[0]]
            out.append(("polygon", pts))
        if not out:
            raise ValueError(
                "container_id resolved to a <path> with no closable subpath "
                "(need at least 3 points per subpath)."
            )
        return out

    raise ValueError(
        f"container_id points to <{T.lower()}> which is not a supported "
        "closed shape. Use rect, circle, ellipse, polygon, polyline, or path."
    )


# ---------------------------------------------------------------------------
# Moore-neighbourhood boundary tracer (unchanged from previous version)
# ---------------------------------------------------------------------------


_MOORE = [
    (0, 1),  # E
    (1, 1),  # SE
    (1, 0),  # S
    (1, -1),  # SW
    (0, -1),  # W
    (-1, -1),  # NW
    (-1, 0),  # N
    (-1, 1),  # NE
]


def _trace_boundary(mask):
    H, W = mask.shape
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return []
    i0 = int(np.argmin(ys * W + xs))
    start = (int(ys[i0]), int(xs[i0]))

    if len(ys) == 1:
        r, c = start
        return [(r, c), (r, c + 1), (r + 1, c + 1), (r + 1, c)]

    def in_bounds(r, c):
        return 0 <= r < H and 0 <= c < W and mask[r, c]

    contour = [start]
    prev_dir = 4
    current = start
    max_steps = 4 * (H + W) + 10 * len(ys)
    for _ in range(max_steps):
        found = False
        for k in range(8):
            idx = (prev_dir + 1 + k) % 8
            dr, dc = _MOORE[idx]
            nr, nc = current[0] + dr, current[1] + dc
            if in_bounds(nr, nc):
                if (nr, nc) == start and len(contour) > 1 and contour[1] == start:
                    return contour
                contour.append((nr, nc))
                prev_dir = (idx + 4) % 8
                current = (nr, nc)
                found = True
                break
        if not found:
            return contour
        if current == start and len(contour) > 2:
            return contour[:-1]
    return contour


def _boundary_to_world(contour, origin):
    ox, oy = origin
    if not contour:
        return []
    trimmed = [contour[0]]
    for i in range(1, len(contour) - 1):
        p = contour[i - 1]
        c = contour[i]
        n = contour[i + 1]
        dr1, dc1 = c[0] - p[0], c[1] - p[1]
        dr2, dc2 = n[0] - c[0], n[1] - c[1]
        if (dr1, dc1) != (dr2, dc2):
            trimmed.append(c)
    trimmed.append(contour[-1])
    if trimmed[0] != trimmed[-1]:
        trimmed.append(trimmed[0])
    return [(float(c + ox), float(r + oy)) for r, c in trimmed]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def find_empty_regions(
    svg,
    tolerance=20.0,
    min_area=500.0,
    canvas=None,
    exclude_ids=("callout-*",),
    container_id=None,
):
    """Find empty regions on an SVG canvas.

    Args:
        svg: SVG source - a ``pathlib.Path``, file path string, XML string,
            bytes, or file-like object. The SVG is parsed via svgelements,
            so every visible element (rects, circles, paths, text, images,
            groups with transforms, nested styles) is honoured - no manual
            shape list is built by the caller.
        tolerance: inward standoff in pixels. Each free region is shrunk
            by this amount using a Euclidean distance transform. Default
            20 px - the minimum recommended for callouts. Set 0 to
            disable inward erosion.
        min_area: drop regions whose area in px^2 is smaller than this
            after erosion. Default 500.
        canvas: optional ``(x, y, w, h)`` override for the scan canvas. If
            omitted the SVG viewBox is used.
        exclude_ids: iterable of glob patterns (``fnmatch`` syntax).
            Elements whose ``id`` attribute matches any pattern are NOT
            rasterised and therefore do not occupy space. Default is
            ``("callout-*",)`` so existing callouts are automatically
            excluded when re-running placement - rename your callout
            groups with the ``callout-`` prefix to benefit.
        container_id: when set, clip detection to the interior of the
            element with this ``id``. The element must be a closed shape
            (rect, circle, ellipse, polygon, polyline, or path) - groups
            are rejected. Its stroke/fill attributes are ignored; the
            geometry alone defines the clip region. Obstacles outside the
            container are irrelevant; obstacles inside still occupy.
            Returned regions are tagged with ``container_id``. Default
            ``None`` = no clipping (scan whole canvas).

    Returns:
        list of ``{"boundary": [(x, y), ...], "area": float, "container_id":
        str|None}`` dicts, one per connected free region, sorted by area
        descending. Boundary coordinates are integer pixel values exposed
        as floats.
    """
    svg_doc, viewbox_canvas = _parse_svg_source(svg)
    if canvas is None:
        canvas = viewbox_canvas

    container_elem = None
    if container_id is not None:
        container_elem = svg_doc.get_element_by_id(container_id)
        if container_elem is None:
            raise ValueError(f"container_id={container_id!r} not found in SVG")

    exclude_patterns = tuple(exclude_ids or ())

    def _id_excluded(elem):
        if not exclude_patterns:
            return False
        eid = getattr(elem, "id", None)
        if eid is None:
            return False
        return any(fnmatch.fnmatchcase(eid, pat) for pat in exclude_patterns)

    # Recursive walk with ancestor pruning: when a Group matches an
    # exclude pattern, its entire subtree is skipped. svg_doc itself is a
    # Group at the top. This is what lets `exclude_ids=["callout-*"]`
    # strip every <g id="callout-foo"> including its descendant children.
    #
    # The container element (if any) is skipped-self: we don't add its own
    # surrogates to the obstacle set (otherwise it would fill its own
    # interior), but children inside it remain obstacles.
    #
    # Full-canvas background plates (shapes filling >=80% of the canvas)
    # are always skipped - otherwise a single bg-plate would mark every
    # pixel as occupied and leave zero free space. Partial backgrounds
    # must be excluded via exclude_ids.
    surrogates = []

    def walk(node):
        if _id_excluded(node):
            return
        if node is not container_elem and not _is_canvas_background(node, canvas):
            surrogates.extend(_element_to_surrogates(node))
        # svgelements Group / SVG are iterable - recurse into children.
        if isinstance(node, _se.Group):
            for child in node:
                walk(child)

    walk(svg_doc)

    occ = _rasterise_surrogates(canvas, surrogates)
    free = ~occ
    if not free.any():
        return []

    # Container clip: AND with the interior mask so only pixels inside the
    # container count as free. Applied BEFORE erosion so the container
    # boundary becomes an implicit obstacle for the distance transform.
    if container_elem is not None:
        interior_surrogates = _container_interior_surrogates(container_elem)
        container_mask = _rasterise_surrogates(canvas, interior_surrogates)
        free = free & container_mask
        if not free.any():
            return []

    # Inward erosion via Euclidean distance transform. Pad with False on
    # all sides so the canvas edge counts as an implicit obstacle.
    if tolerance > 0:
        padded = np.zeros((free.shape[0] + 2, free.shape[1] + 2), dtype=bool)
        padded[1:-1, 1:-1] = free
        dist = ndi.distance_transform_edt(padded)
        free = dist[1:-1, 1:-1] > tolerance
        if not free.any():
            return []

    labels, n_components = ndi.label(free)
    if n_components == 0:
        return []

    slices = ndi.find_objects(labels)
    areas = np.bincount(labels.ravel())

    results = []
    cx, cy, _, _ = canvas
    for i, sl in enumerate(slices, start=1):
        if sl is None:
            continue
        area_px = int(areas[i])
        if area_px < min_area:
            continue
        sub = labels[sl] == i
        r0 = sl[0].start
        c0 = sl[1].start
        contour_local = _trace_boundary(sub)
        if not contour_local:
            continue
        contour_world = _boundary_to_world(contour_local, (cx + c0, cy + r0))
        if len(contour_world) < 3:
            continue
        results.append(
            {
                "boundary": contour_world,
                "area": float(area_px),
                "container_id": container_id,
            }
        )

    results.sort(key=lambda r: -r["area"])
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics empty-space",
        description="Identify empty regions on an SVG canvas via bitmap "
        "rasterisation and distance-transform erosion. Parses "
        "the SVG directly via svgelements - no manual shape list.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--svg",
        required=True,
        help="Path to the SVG file to scan",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=20.0,
        help="Inward standoff in px (default 20, callout minimum). 0 disables.",
    )
    parser.add_argument(
        "--min-area",
        type=float,
        default=500.0,
        help="Drop regions smaller than this in px^2 (default 500).",
    )
    parser.add_argument(
        "--exclude-id",
        action="append",
        default=None,
        help="Glob pattern for element ids to exclude. Repeatable. "
        "Defaults to 'callout-*' when omitted.",
    )
    parser.add_argument(
        "--container-id",
        default=None,
        help="Clip detection to the interior of the element with this id. "
        "Must point to a closed shape (rect/circle/ellipse/polygon/path); "
        "groups are rejected. Obstacles outside the container are ignored.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON output only",
    )
    args = parser.parse_args()

    if args.tolerance < 20.0:
        print(
            f"WARNING: --tolerance {args.tolerance} is below the 20px "
            "minimum recommended for callouts; leaders may clip adjacent "
            "shapes.",
            file=sys.stderr,
        )

    exclude_ids = args.exclude_id if args.exclude_id else ("callout-*",)

    regions = find_empty_regions(
        svg=args.svg,
        tolerance=args.tolerance,
        min_area=args.min_area,
        exclude_ids=exclude_ids,
        container_id=args.container_id,
    )

    if args.json:
        json.dump(regions, sys.stdout, indent=2)
        print()
        return

    print(f"=== EMPTY REGIONS ({len(regions)}) ===")
    for i, r in enumerate(regions):
        xs = [p[0] for p in r["boundary"]]
        ys = [p[1] for p in r["boundary"]]
        print(
            f"[{i}] area={r['area']:.0f}px^2  vertices={len(r['boundary'])}  "
            f"bbox=({min(xs):.0f},{min(ys):.0f})-({max(xs):.0f},{max(ys):.0f})"
        )
        points = " ".join(f"{x:.0f},{y:.0f}" for x, y in r["boundary"])
        print(f"    points: {points}")


if __name__ == "__main__":
    main()
