"""Shared SVG path parsing, flattening, and emit helpers.

This module is the single source of truth for two operations the rest of
the toolkit needs:

1. Coercing arbitrary inputs (Path, str XML, bytes, file-like) into a parsed
   ``svgelements`` SVG document plus a viewBox tuple. ``calc_empty_space``,
   ``calc_connector``, and ``propose_callouts`` all need this.

2. Walking an svgelements ``Path`` (or a `<path d="...">` string) and
   flattening Bezier / Arc segments to polylines via adaptive sampling. The
   bitmap-based empty-space finder needs this; the boolean-ops calculator
   needs the same flattening to feed shapely.

On top of those two, the module exposes higher-level helpers used only by
``calc_boolean``: building a shapely Polygon / MultiPolygon from a path,
emitting a `d=` string from a shapely geometry, finding an element by id,
and rewriting a `d=` attribute in raw XML for the in-place ``--replace-id``
mode.

Curve flattening is polygon-only by design: shapely operates on
straight-segment polygons, so curves round-trip as polylines. Callers that
care about the lossy round-trip (boolean ops) surface a CURVE-FLATTENED
warning through the warning gate; callers that just need a rasterisation
(empty-space finder) ignore it.
"""

from __future__ import annotations

import io
import math
from pathlib import Path
import xml.etree.ElementTree as ET

try:
    import svgelements as _se
except ImportError as _exc:  # pragma: no cover - dep is mandatory
    raise ImportError(
        "svgelements is required for SVG path utilities. Install via "
        "`pip install svgelements` or the project's pyproject extras."
    ) from _exc


# ---------------------------------------------------------------------------
# SVG source handling
# ---------------------------------------------------------------------------


def parse_svg_source(source):
    """Coerce ``source`` into a parsed svgelements SVG document.

    Accepts:
      * ``pathlib.Path`` - file on disk
      * ``str`` - either an XML string (starts with ``<``) or a path
      * ``bytes`` - raw XML bytes
      * file-like object with a ``.read()`` method

    Returns ``(svg_doc, canvas_viewbox)`` where ``canvas_viewbox`` is
    ``(x, y, w, h)`` derived from the SVG viewBox or falls back to
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
# Path flattening
# ---------------------------------------------------------------------------


def _adaptive_sample_count(length_px):
    """Pick a per-segment sample count: ~1 sample per px, clamped [10, 100]."""
    if length_px is None or not math.isfinite(length_px) or length_px <= 0:
        return 10
    return max(10, min(100, int(round(length_px))))


def sample_path_to_polylines(path):
    """Convert an svgelements Path into a list of ``(points, closed)`` tuples.

    A path may contain multiple subpaths (separated by Move segments) and
    may alternate between open and closed via Close segments. Walks the
    segment list, collecting points for each subpath and sampling Bezier /
    Arc segments via ``.point(t)`` at adaptive sample counts.
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
        start_t = 1 if current else 0
        for i in range(start_t, n + 1):
            t = i / n
            p = seg.point(t)
            current.append((float(p.x), float(p.y)))

    if current:
        subpaths.append((current, closed))

    return subpaths


# ---------------------------------------------------------------------------
# Curve detection (for CURVE-FLATTENED warning)
# ---------------------------------------------------------------------------


def path_has_curves(path) -> bool:
    """True if any segment is a Bezier or Arc.

    Used by the boolean-ops gate to surface a CURVE-FLATTENED warning when
    the polyline round-trip is lossy.
    """
    for seg in path:
        name = type(seg).__name__
        if name in ("CubicBezier", "QuadraticBezier", "Arc"):
            return True
    return False


# ---------------------------------------------------------------------------
# Polygon construction + emit (boolean-ops support)
# ---------------------------------------------------------------------------


def polygons_from_path(path, *, tolerance: float | None = None):
    """Build a shapely Polygon / MultiPolygon from an svgelements Path.

    Multiple closed subpaths become separate components (MultiPolygon). If a
    component contains another wholly inside it, the inner one is treated as
    a hole on the outer (matches SVG nonzero / even-odd interpretation for
    well-behaved infographic input).

    Open subpaths (no Close segment) are implicit-closed by repeating the
    first point. Self-intersections are repaired with ``.buffer(0)`` per the
    shapely docs.

    Returns a shapely Polygon or MultiPolygon. Raises ValueError on inputs
    that have fewer than 3 distinct points across all subpaths.

    ``tolerance``: if given, applies ``.simplify(tolerance,
    preserve_topology=True)`` before returning to drop near-collinear
    polyline noise from heavy curve flattening.
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    subpaths = sample_path_to_polylines(path)
    if not subpaths:
        raise ValueError("path has no subpaths")

    # Drop subpaths that collapse to fewer than 3 distinct points.
    rings = []
    for points, _closed in subpaths:
        deduped = _dedupe_consecutive(points)
        if len(deduped) < 3:
            continue
        # Implicit-close: Polygon constructor handles open rings, but be
        # explicit to match shapely's expectations.
        if deduped[0] != deduped[-1]:
            deduped.append(deduped[0])
        rings.append(deduped)

    if not rings:
        raise ValueError("path has no closable subpath with >= 3 points")

    # Build a polygon per ring, then unary_union to merge / detect holes.
    raw_polys = []
    for ring in rings:
        try:
            poly = Polygon(ring)
        except Exception:
            continue
        if poly.is_empty:
            continue
        # Repair self-intersections.
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        raw_polys.append(poly)

    if not raw_polys:
        raise ValueError("path produced no valid polygon (all subpaths empty)")

    # Detect inner-rings-as-holes: a polygon fully contained by another with
    # opposite orientation becomes a hole on the outer one. unary_union on
    # rings does NOT do this for us (it treats them all as filled), so we
    # have to handle it explicitly.
    geom = _resolve_holes(raw_polys)

    if not geom.is_valid:
        geom = geom.buffer(0)

    if tolerance is not None and tolerance > 0:
        geom = geom.simplify(tolerance, preserve_topology=True)

    # Normalise to MultiPolygon so callers do not need to special-case.
    if geom.geom_type == "Polygon":
        return geom
    if geom.geom_type == "MultiPolygon":
        if len(list(geom.geoms)) == 1:
            return list(geom.geoms)[0]
        return geom
    # GeometryCollection or other: union to coerce.
    coerced = unary_union(geom)
    return coerced


def _dedupe_consecutive(points):
    """Drop consecutive duplicate points (within 1e-9)."""
    if not points:
        return []
    out = [points[0]]
    for p in points[1:]:
        if abs(p[0] - out[-1][0]) > 1e-9 or abs(p[1] - out[-1][1]) > 1e-9:
            out.append(p)
    return out


def _resolve_holes(polys):
    """Take a list of polygon rings, return Polygon/MultiPolygon with holes.

    A polygon fully contained in another becomes a hole on the outer one.
    Multiple disjoint outers become a MultiPolygon. Outer + outer that
    overlap fall back to ``unary_union`` (no hole, just merged shape).
    """
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union

    if len(polys) == 1:
        return polys[0]

    # Build a containment graph: outer -> [inner, inner, ...].
    n = len(polys)
    is_inside = [False] * n
    holes_of = {i: [] for i in range(n)}

    for i in range(n):
        for j in range(n):
            if i == j or is_inside[i]:
                continue
            try:
                if polys[j].covers(polys[i]):
                    # j contains i. Mark i as inside, attribute it to j.
                    holes_of[j].append(polys[i])
                    is_inside[i] = True
                    break
            except Exception:
                continue

    outer_idxs = [i for i in range(n) if not is_inside[i]]
    out_polys = []
    for i in outer_idxs:
        outer = polys[i]
        holes = holes_of[i]
        if holes:
            try:
                hole_rings = [list(h.exterior.coords) for h in holes]
                shell = list(outer.exterior.coords)
                merged = Polygon(shell, hole_rings)
                if not merged.is_valid:
                    merged = merged.buffer(0)
                out_polys.append(merged)
            except Exception:
                out_polys.append(outer)
        else:
            out_polys.append(outer)

    if len(out_polys) == 1:
        return out_polys[0]
    # If outers overlap, unary_union them to merge.
    try:
        candidate = MultiPolygon(out_polys)
        if candidate.is_valid:
            return candidate
    except Exception:
        pass
    return unary_union(out_polys)


def path_d_from_geom(geom) -> str:
    """Emit an SVG ``d=`` string from a shapely Polygon / MultiPolygon.

    Multi-island MultiPolygon emits multiple ``M ... Z`` subpaths in one
    string. Each polygon's holes follow the shell as additional ``M ... Z``
    subpaths with reverse winding (svgelements / browsers honour the
    nonzero or even-odd fill-rule per inner-ring direction).

    Returns ``""`` for empty geometry.
    """
    if geom is None or geom.is_empty:
        return ""

    parts = []
    geoms = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for poly in geoms:
        if poly.is_empty:
            continue
        parts.append(_ring_to_d(list(poly.exterior.coords), reverse=False))
        for interior in poly.interiors:
            parts.append(_ring_to_d(list(interior.coords), reverse=True))
    return " ".join(p for p in parts if p)


def _ring_to_d(coords, *, reverse: bool) -> str:
    """Format a single closed ring as ``M x y L x y L x y Z``."""
    if not coords:
        return ""
    if reverse:
        coords = list(reversed(coords))
    out = [f"M {coords[0][0]:.3f} {coords[0][1]:.3f}"]
    for x, y in coords[1:-1]:
        out.append(f"L {x:.3f} {y:.3f}")
    # Drop the closing duplicate; emit explicit Z.
    out.append("Z")
    return " ".join(out)


# ---------------------------------------------------------------------------
# Element lookup + in-place rewrite
# ---------------------------------------------------------------------------


def find_element_by_id(svg_doc, element_id: str):
    """Walk an svgelements SVG tree and return the first element with the
    given ``id`` attribute, or ``None`` if not found.
    """
    for elem in svg_doc.elements():
        eid = getattr(elem, "id", None)
        if eid == element_id:
            return elem
        # Some svgelements element kinds expose id via .values dict.
        values = getattr(elem, "values", None)
        if isinstance(values, dict) and values.get("id") == element_id:
            return elem
    return None


_SVG_NS = "http://www.w3.org/2000/svg"


def replace_path_d_in_xml(xml_text: str, element_id: str, new_d: str) -> str:
    """Rewrite the ``d=`` attribute on the element with ``id=element_id``.

    Operates on raw XML text (not svgelements) so all sibling attributes
    and namespace declarations survive the round-trip. Returns the new XML
    text. Raises ``ValueError`` if no element with that id exists.
    """
    # Register the SVG namespace so ET serialises without ns0: prefixes.
    ET.register_namespace("", _SVG_NS)

    root = ET.fromstring(xml_text)
    target = None
    for elem in root.iter():
        if elem.attrib.get("id") == element_id:
            target = elem
            break
    if target is None:
        raise ValueError(f"no element with id={element_id!r} found in SVG")
    target.set("d", new_d)
    return ET.tostring(root, encoding="unicode")


def get_element_class(elem) -> str | None:
    """Read the CSS class attribute off an svgelements element, or None."""
    values = getattr(elem, "values", None)
    if isinstance(values, dict):
        cls = values.get("class")
        if cls:
            return cls
    return None
