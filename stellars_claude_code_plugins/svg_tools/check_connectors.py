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


def parse_svg(filepath: str) -> tuple[list[CardRect], list[Connector], list[TextLabel]]:
    """Parse SVG and extract cards, connectors, and text labels."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    cards: list[CardRect] = []
    connectors: list[Connector] = []
    labels: list[TextLabel] = []
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
    return cards, connectors, labels


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
    cards, connectors, labels = parse_svg(args.svg)
    print(f"Found {len(connectors)} connectors, {len(cards)} cards, {len(labels)} labels")

    all_issues: list[str] = []
    all_issues.extend(check_zero_length(connectors))
    all_issues.extend(check_edge_snap(connectors, cards))
    all_issues.extend(check_l_routing(connectors))
    all_issues.extend(check_label_clearance(connectors, labels))

    if all_issues:
        print()
        for issue in all_issues:
            print(issue)
        print(f"\nSUMMARY: {len(all_issues)} connector violations found")
    else:
        print("\nSUMMARY: no connector violations found")


if __name__ == "__main__":
    main()
