"""SVG connector quality checker for infographic layout verification.

Checks: zero-length segments, edge-snap, L-routing, label clearance.
Usage: python check_connectors.py --svg path/to/file.svg
"""

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

NS = {"svg": "http://www.w3.org/2000/svg"}


@dataclass
class BBox:
    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


@dataclass
class CardRect:
    elem_id: str
    label: str
    bbox: BBox


@dataclass
class Connector:
    elem_id: str
    tag: str
    points: list[tuple[float, float]]


@dataclass
class Arrowhead:
    """A `<polygon>` element that looks like a triangular arrowhead.

    Triangles with a "tip" vertex (the furthest from the polygon centroid)
    are the canonical arrow shape. ``tip`` is the vertex pointing toward
    the arrow's logical destination; ``length`` is the distance from the
    tip back to the midpoint of the opposite edge (the arrow's head span).
    """

    elem_id: str
    points: list[tuple[float, float]]
    tip: tuple[float, float]
    length: float


@dataclass
class TextLabel:
    content: str
    cx: float
    cy: float
    bbox: BBox


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _safe_float(val: str | None, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _parse_points(points_str: str) -> list[tuple[float, float]]:
    nums = [float(n) for n in re.findall(r"[-+]?\d*\.?\d+", points_str)]
    return [(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]


def _is_card_element(el) -> bool:
    css_class = (el.get("class") or "").lower()
    if "card" in css_class or "box" in css_class:
        return True
    return _safe_float(el.get("width")) > 50 and _safe_float(el.get("height")) > 50


def _point_to_seg_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Distance from point to line segment."""
    dx, dy = x2 - x1, y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq < 1e-9:
        return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    return ((px - x1 - t * dx) ** 2 + (py - y1 - t * dy) ** 2) ** 0.5


def _point_inside_bbox(px: float, py: float, bb: BBox, margin: float) -> float:
    """How far inside bbox the point is. Returns -1 if outside."""
    dx_l, dx_r = px - bb.x, bb.x2 - px
    dy_t, dy_b = py - bb.y, bb.y2 - py
    if dx_l < -margin or dx_r < -margin or dy_t < -margin or dy_b < -margin:
        return -1
    return min(dx_l, dx_r, dy_t, dy_b)


def _rect_label(el) -> str:
    elem_id = el.get("id", "")
    if elem_id:
        return elem_id
    css_class = el.get("class", "")
    if css_class:
        return css_class
    return (
        f"rect {_safe_float(el.get('width')):.0f}x"
        f"{_safe_float(el.get('height')):.0f} "
        f"@({_safe_float(el.get('x')):.0f},{_safe_float(el.get('y')):.0f})"
    )


def _min_bbox_to_seg_dist(bb: BBox, x1: float, y1: float, x2: float, y2: float) -> float:
    """Min distance from bbox edge sample points to a line segment."""
    pts = [
        (bb.x, bb.y),
        (bb.x2, bb.y),
        (bb.x, bb.y2),
        (bb.x2, bb.y2),
        (bb.cx, bb.y),
        (bb.cx, bb.y2),
        (bb.x, bb.cy),
        (bb.x2, bb.cy),
    ]
    return min(_point_to_seg_dist(px, py, x1, y1, x2, y2) for px, py in pts)


_PATH_CMD_RE = re.compile(r"([MmLlHhVvZz])\s*([-\d.,\s]*)")


def _parse_path_d(d: str) -> list[tuple[float, float]]:
    """Flatten an SVG `d` attribute to a polyline.

    Supports M / L / H / V (absolute + relative) and Z closepath.
    Curves / arcs (C / S / Q / T / A) are approximated by their
    endpoint - good enough for stem-length measurement of typical
    connector paths which are polyline-shaped anyway.
    """
    pts: list[tuple[float, float]] = []
    cx, cy = 0.0, 0.0
    start_cx, start_cy = 0.0, 0.0
    nums_re = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
    tokens = list(_PATH_CMD_RE.finditer(d))
    for m in tokens:
        cmd = m.group(1)
        args = [float(n) for n in nums_re.findall(m.group(2))]
        if cmd in ("M", "m"):
            # Move-to then implicit LineTo for subsequent pairs
            first = True
            for i in range(0, len(args) - 1, 2):
                x, y = args[i], args[i + 1]
                if cmd == "m" and pts:
                    x += cx
                    y += cy
                cx, cy = x, y
                if first:
                    start_cx, start_cy = cx, cy
                pts.append((cx, cy))
                first = False
                # After first pair, absolute M becomes implicit L
                cmd = "L" if cmd == "M" else "l"
        elif cmd in ("L", "l"):
            for i in range(0, len(args) - 1, 2):
                x, y = args[i], args[i + 1]
                if cmd == "l":
                    x += cx
                    y += cy
                cx, cy = x, y
                pts.append((cx, cy))
        elif cmd in ("H", "h"):
            for x in args:
                if cmd == "h":
                    x += cx
                cx = x
                pts.append((cx, cy))
        elif cmd in ("V", "v"):
            for y in args:
                if cmd == "v":
                    y += cy
                cy = y
                pts.append((cx, cy))
        elif cmd in ("Z", "z"):
            cx, cy = start_cx, start_cy
            pts.append((cx, cy))
        # Other commands (C/S/Q/T/A) - consume their args and move cursor
        # to the last pair (approximate the curve as its endpoint).
        elif cmd in ("C", "c", "S", "s", "Q", "q", "T", "t"):
            # Pairs per command: C=3, S=2, Q=2, T=1
            pair_count = {"C": 3, "c": 3, "S": 2, "s": 2, "Q": 2, "q": 2, "T": 1, "t": 1}[cmd]
            step = pair_count * 2
            for i in range(0, len(args) - step + 1, step):
                x, y = args[i + step - 2], args[i + step - 1]
                if cmd.islower():
                    x += cx
                    y += cy
                cx, cy = x, y
                pts.append((cx, cy))
        elif cmd in ("A", "a"):
            # Arc: 7 args per segment; endpoint is args[5], args[6]
            for i in range(0, len(args) - 6, 7):
                x, y = args[i + 5], args[i + 6]
                if cmd == "a":
                    x += cx
                    y += cy
                cx, cy = x, y
                pts.append((cx, cy))
    return pts


def _polyline_length(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        dx = points[i + 1][0] - points[i][0]
        dy = points[i + 1][1] - points[i][1]
        total += (dx * dx + dy * dy) ** 0.5
    return total


def _arrowhead_from_polygon(el) -> Arrowhead | None:
    """Detect a triangular arrowhead and compute its tip + length.

    Rules:
    - 3 vertices (common arrowhead shape)
    - the "tip" is the vertex furthest from the centroid of the other two
    - length = distance from tip to midpoint of the opposite edge
    """
    pts = _parse_points(el.get("points", ""))
    if len(pts) != 3:
        return None
    a, b, c = pts
    # Compute the distance from each vertex to the midpoint of the opposite edge.
    # The tip has the max distance.
    candidates = []
    for i, v in enumerate([a, b, c]):
        others = [pts[j] for j in range(3) if j != i]
        mx = (others[0][0] + others[1][0]) / 2.0
        my = (others[0][1] + others[1][1]) / 2.0
        dist = ((v[0] - mx) ** 2 + (v[1] - my) ** 2) ** 0.5
        candidates.append((dist, v))
    length, tip = max(candidates, key=lambda c: c[0])
    return Arrowhead(elem_id=el.get("id", ""), points=pts, tip=tip, length=length)


def parse_svg(
    filepath: str,
) -> tuple[list[CardRect], list[Connector], list[TextLabel], list[Arrowhead]]:
    """Parse SVG and extract cards, connectors, text labels, arrowheads."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    cards: list[CardRect] = []
    connectors: list[Connector] = []
    labels: list[TextLabel] = []
    arrowheads: list[Arrowhead] = []
    for el in root.iter():
        tag = _strip_ns(el.tag)
        if tag == "rect" and _is_card_element(el):
            x, y = _safe_float(el.get("x")), _safe_float(el.get("y"))
            w, h = _safe_float(el.get("width")), _safe_float(el.get("height"))
            if w > 0 and h > 0:
                cards.append(CardRect(el.get("id", ""), _rect_label(el), BBox(x, y, w, h)))
        elif tag == "line":
            connectors.append(
                Connector(
                    el.get("id", ""),
                    "line",
                    [
                        (_safe_float(el.get("x1")), _safe_float(el.get("y1"))),
                        (_safe_float(el.get("x2")), _safe_float(el.get("y2"))),
                    ],
                )
            )
        elif tag == "polyline":
            pts = _parse_points(el.get("points", ""))
            if len(pts) >= 2:
                connectors.append(Connector(el.get("id", ""), "polyline", pts))
        elif tag == "path":
            d = el.get("d") or ""
            pts = _parse_path_d(d)
            if len(pts) >= 2:
                connectors.append(Connector(el.get("id", ""), "path", pts))
        elif tag == "polygon":
            arr = _arrowhead_from_polygon(el)
            if arr is not None:
                arrowheads.append(arr)
        elif tag == "text":
            content = el.text or ""
            for child in el:
                if _strip_ns(child.tag) == "tspan":
                    content += child.text or ""
            content = content.strip()
            if not content:
                continue
            x, y = _safe_float(el.get("x")), _safe_float(el.get("y"))
            fs = _safe_float(el.get("font-size"), 10.0)
            anchor = el.get("text-anchor", "start")
            est_w = len(content) * fs * 0.6
            y_top = y - fs * 0.85
            x_left = x
            if anchor == "middle":
                x_left = x - est_w / 2
            elif anchor == "end":
                x_left = x - est_w
            labels.append(
                TextLabel(
                    content, x_left + est_w / 2, y_top + fs / 2, BBox(x_left, y_top, est_w, fs)
                )
            )
    return cards, connectors, labels, arrowheads


def check_zero_length(connectors: list[Connector], tol: float = 0.5) -> list[str]:
    """Check 1: flag lines with zero length or polylines with duplicate points."""
    issues = []
    for c in connectors:
        cid = c.elem_id or "(no id)"
        if c.tag == "line" and len(c.points) == 2:
            (x1, y1), (x2, y2) = c.points
            if abs(x2 - x1) <= tol and abs(y2 - y1) <= tol:
                issues.append(
                    f"[zero-length] Line id={cid} at ({x1:.0f},{y1:.0f}) has zero length"
                )
        if c.tag == "polyline":
            for i in range(len(c.points) - 1):
                ax, ay = c.points[i]
                bx, by = c.points[i + 1]
                if abs(bx - ax) <= tol and abs(by - ay) <= tol:
                    issues.append(
                        f"[zero-length] Polyline id={cid} has duplicate point at ({ax:.0f},{ay:.0f})"
                    )
    return issues


def check_edge_snap(
    connectors: list[Connector], cards: list[CardRect], snap_tol: float = 3.0
) -> list[str]:
    """Check 2: flag connectors whose endpoints are too far inside a card."""
    issues = []
    for c in connectors:
        cid = c.elem_id or "(no id)"
        for label, (px, py) in [("start", c.points[0]), ("end", c.points[-1])]:
            for card in cards:
                dist = _point_inside_bbox(px, py, card.bbox, snap_tol)
                if dist > snap_tol:
                    issues.append(
                        f"[edge-snap] Connector id={cid} {label} at ({px:.0f},{py:.0f}) "
                        f'is {dist:.0f}px inside card "{card.label}"'
                    )
    return issues


def check_l_routing(connectors: list[Connector], tol: float = 2.0) -> list[str]:
    """Check 3: flag diagonal segments in polyline connectors."""
    issues = []
    for c in connectors:
        if c.tag != "polyline":
            continue
        cid = c.elem_id or "(no id)"
        for i in range(len(c.points) - 1):
            ax, ay = c.points[i]
            bx, by = c.points[i + 1]
            if abs(bx - ax) > tol and abs(by - ay) > tol:
                issues.append(
                    f"[l-routing] Polyline id={cid} has diagonal segment "
                    f"from ({ax:.0f},{ay:.0f}) to ({bx:.0f},{by:.0f})"
                )
    return issues


# Stubby-arrow rule: head must be AT MOST 40% of total connector length.
# Hardcoded because it's a visual-quality constant, not a tunable.
_MAX_HEAD_FRACTION = 0.40


def check_stem_head_ratio(
    connectors: list[Connector],
    arrowheads: list[Arrowhead],
    *,
    pairing_tol: float = 4.0,
) -> list[str]:
    """Check: warn when arrowhead length dominates total connector length.

    Rule: head length MUST be <= 40% of total (stem + head) length.
    Equivalently the stem is >= 60%. Stubby arrows (head dominates)
    read as misclicked shapes rather than directional connectors.

    Pairing: each arrowhead is associated with the connector whose
    endpoint (start or end) is within ``pairing_tol`` pixels of the
    arrowhead tip. Unpaired arrowheads and connectors without an
    arrowhead are skipped - the stem-to-head ratio only applies
    where an arrow is actually drawn.
    """
    issues: list[str] = []
    if not arrowheads:
        return issues
    for head in arrowheads:
        best_stem_len = None
        best_cid = None
        for c in connectors:
            if len(c.points) < 2:
                continue
            start_d = (
                (c.points[0][0] - head.tip[0]) ** 2 + (c.points[0][1] - head.tip[1]) ** 2
            ) ** 0.5
            end_d = (
                (c.points[-1][0] - head.tip[0]) ** 2 + (c.points[-1][1] - head.tip[1]) ** 2
            ) ** 0.5
            min_d = min(start_d, end_d)
            if min_d > pairing_tol:
                continue
            stem_len = _polyline_length(c.points)
            if best_stem_len is None or stem_len > best_stem_len:
                best_stem_len = stem_len
                best_cid = c.elem_id or "(no id)"
        if best_stem_len is None:
            # Unpaired arrowhead - a common pattern where the head sits
            # beyond the stroke's trimmed endpoint. Estimate stem length
            # by measuring the closest approach of any connector polyline
            # to the tip on its tail side. Too noisy to flag; skip.
            continue
        total = best_stem_len + head.length
        if total <= 0:
            continue
        head_fraction = head.length / total
        if head_fraction > _MAX_HEAD_FRACTION:
            issues.append(
                f"[stem-head-ratio] Arrow id={head.elem_id or '(no id)'} paired with "
                f"connector id={best_cid}: head={head.length:.1f}px is "
                f"{head_fraction * 100:.0f}% of total {total:.1f}px "
                f"(must be <= {_MAX_HEAD_FRACTION * 100:.0f}%). "
                f"Stem is stubby - extend the connector or shrink the head."
            )
    return issues


def check_label_clearance(
    connectors: list[Connector],
    labels: list[TextLabel],
    proximity: float = 20.0,
    min_clearance: float = 8.0,
) -> list[str]:
    """Check 4: flag text labels too close to connector paths."""
    issues = []
    for lbl in labels:
        flagged = False
        for c in connectors:
            if flagged:
                break
            for i in range(len(c.points) - 1):
                x1, y1 = c.points[i]
                x2, y2 = c.points[i + 1]
                if _point_to_seg_dist(lbl.cx, lbl.cy, x1, y1, x2, y2) > proximity:
                    continue
                edge_dist = _min_bbox_to_seg_dist(lbl.bbox, x1, y1, x2, y2)
                if edge_dist < min_clearance:
                    issues.append(
                        f'[clearance] Label "{lbl.content[:30]}" is only '
                        f"{edge_dist:.0f}px from connector path"
                    )
                    flagged = True
                    break
    return issues


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SVG connector quality checker")
    parser.add_argument("--svg", required=True, help="SVG file to check")
    args = parser.parse_args()

    print(f"Connector check: {args.svg}")
    print("=" * 72)
    cards, connectors, labels, arrowheads = parse_svg(args.svg)
    print(
        f"Found {len(connectors)} connectors, {len(cards)} cards, "
        f"{len(labels)} labels, {len(arrowheads)} arrowheads"
    )

    all_issues: list[str] = []
    all_issues.extend(check_zero_length(connectors))
    all_issues.extend(check_edge_snap(connectors, cards))
    all_issues.extend(check_l_routing(connectors))
    all_issues.extend(check_label_clearance(connectors, labels))
    all_issues.extend(check_stem_head_ratio(connectors, arrowheads))

    if all_issues:
        print()
        for issue in all_issues:
            print(issue)
        print(f"\nSUMMARY: {len(all_issues)} connector violations found")
    else:
        print("\nSUMMARY: no connector violations found")


if __name__ == "__main__":
    main()
