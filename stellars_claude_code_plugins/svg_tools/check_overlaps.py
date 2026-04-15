"""SVG element overlap detector for infographic layout verification.

Parses all visual elements, computes approximate bounding boxes using
Segoe UI font metrics, and tests every element pair for overlap and
spacing violations. Generates diagnostic reports and optional bounding
box verification overlays.

Inner/outer bounding box model:
- Inner bbox: rendered extent including stroke width
- Outer bbox: inner bbox + per-element-type padding
- Overlap detection compares outer bboxes by default

Usage:
    python check_overlaps.py --svg path/to/file.svg
    python check_overlaps.py --svg file.svg --inject-bounds
    python check_overlaps.py --svg file.svg --strip-bounds
    python check_overlaps.py --svg file.svg --extra-padding 2
"""

from dataclasses import dataclass
from itertools import combinations
import math
import re
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Per-role padding table (outer bbox = inner bbox + padding on all sides)
# ---------------------------------------------------------------------------

ROLE_PADDING: dict[str, float] = {
    "icon": 6,
    "logo": 6,
    "text": 4,  # 4px from neighbouring elements; card-edge clearance checked separately
    "card": 10,
    "accent-bar": 0,  # structural, flush with card top
    "bg-fill": 0,
    "background": 0,
    "milestone": 6,
    "divider": 4,
    "track-line": 4,
    "arrow": 6,
    "path": 4,
    "circle": 4,
    "color-chip": 2,
    "rect": 4,
}


# ---------------------------------------------------------------------------
# Bounding box
# ---------------------------------------------------------------------------


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

    def padded(self, padding: float) -> "BBox":
        """Return a new BBox expanded by padding on all sides."""
        return BBox(self.x - padding, self.y - padding, self.w + 2 * padding, self.h + 2 * padding)

    def overlaps(self, other: "BBox") -> bool:
        if self.x >= other.x2 or other.x >= self.x2:
            return False
        if self.y >= other.y2 or other.y >= self.y2:
            return False
        return True

    def overlap_area(self, other: "BBox") -> float:
        ox = max(0, min(self.x2, other.x2) - max(self.x, other.x))
        oy = max(0, min(self.y2, other.y2) - max(self.y, other.y))
        return ox * oy

    def overlap_pct(self, other: "BBox") -> float:
        """Overlap area as % of the smaller element."""
        area = self.overlap_area(other)
        smaller = min(self.w * self.h, other.w * other.h)
        if smaller <= 0:
            return 0.0
        return 100.0 * area / smaller

    def contains(self, other: "BBox") -> bool:
        """True if self fully contains other."""
        return (
            self.x <= other.x and self.y <= other.y and self.x2 >= other.x2 and self.y2 >= other.y2
        )

    def gap_to(self, other: "BBox") -> tuple[float, str, float, str]:
        """Compute horizontal and vertical gaps to another bbox.

        Returns (h_gap, h_dir, v_gap, v_dir) where:
        - h_gap: horizontal distance (negative = overlap)
        - h_dir: 'left' or 'right' (direction of other relative to self)
        - v_gap: vertical distance (negative = overlap)
        - v_dir: 'above' or 'below' (direction of other relative to self)
        """
        # horizontal
        if other.x >= self.x2:
            h_gap = other.x - self.x2
            h_dir = "right"
        elif self.x >= other.x2:
            h_gap = self.x - other.x2
            h_dir = "left"
        else:
            h_gap = -(min(self.x2, other.x2) - max(self.x, other.x))
            h_dir = "h-overlap"

        # vertical
        if other.y >= self.y2:
            v_gap = other.y - self.y2
            v_dir = "below"
        elif self.y >= other.y2:
            v_gap = self.y - other.y2
            v_dir = "above"
        else:
            v_gap = -(min(self.y2, other.y2) - max(self.y, other.y))
            v_dir = "v-overlap"

        return h_gap, h_dir, v_gap, v_dir

    def __repr__(self) -> str:
        return f"BBox({self.x:.1f},{self.y:.1f} {self.w:.1f}x{self.h:.1f})"


# ---------------------------------------------------------------------------
# Element record
# ---------------------------------------------------------------------------


@dataclass
class Element:
    tag: str  # text, rect, path, circle, line, polygon, g-icon
    label: str  # human-readable description
    bbox: BBox  # inner bbox (rendered extent including stroke)
    section: str = ""  # which section it belongs to
    role: str = ""  # functional role (text, card, divider, track, etc.)
    parent_bg: str = ""  # background context (transparent, light, dark)

    @property
    def outer_bbox(self) -> BBox:
        """Outer bbox = inner bbox + role-specific padding."""
        pad = ROLE_PADDING.get(self.role, 4)
        return self.bbox.padded(pad)


# ---------------------------------------------------------------------------
# Segoe UI font metrics (approximate)
# ---------------------------------------------------------------------------


def text_bbox(
    x: float,
    y: float,
    font_size: float,
    text: str,
    font_weight: str = "normal",
    letter_spacing: float = 0,
    text_anchor: str = "start",
) -> BBox:
    """Compute approximate bounding box for SVG text element."""
    is_bold = font_weight in ("600", "700", "bold")
    char_w = font_size * (0.57 if is_bold else 0.53)

    # letter-spacing adds per-character gap (applied to all chars)
    if letter_spacing > 0:
        char_w += letter_spacing

    width = len(text) * char_w
    height = font_size
    ascent = font_size * 0.78

    bx = x
    if text_anchor == "middle":
        bx = x - width / 2
    elif text_anchor == "end":
        bx = x - width

    by = y - ascent
    return BBox(bx, by, width, height)


# ---------------------------------------------------------------------------
# Path bounding box (simple M/H/V/Q/Z parser)
# ---------------------------------------------------------------------------


def path_bbox(d: str) -> BBox:
    """Extract bounding box from SVG path data string.

    Handles all standard SVG path commands: M/m, L/l, H/h, V/v,
    C/c, S/s, Q/q, T/t, A/a, Z/z. For bezier curves, control points
    are included in the bbox (slight overestimate but safe).
    """
    # tokenize: all single-letter commands + all numbers
    tokens = re.findall(r"[A-Za-z]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    if not tokens:
        return BBox(0, 0, 0, 0)

    xs, ys = [], []
    cx, cy = 0.0, 0.0  # current point
    sx, sy = 0.0, 0.0  # subpath start (for Z)
    cmd = "M"
    ti = 0

    # number of coordinate values consumed per command repeat
    PARAM_COUNT = {
        "M": 2,
        "m": 2,
        "L": 2,
        "l": 2,
        "T": 2,
        "t": 2,
        "H": 1,
        "h": 1,
        "V": 1,
        "v": 1,
        "C": 6,
        "c": 6,
        "S": 4,
        "s": 4,
        "Q": 4,
        "q": 4,
        "A": 7,
        "a": 7,
        "Z": 0,
        "z": 0,
    }

    def consume(n):
        """Read n float values from tokens starting at nonlocal ti."""
        nonlocal ti
        vals = []
        for _ in range(n):
            if ti < len(tokens):
                try:
                    vals.append(float(tokens[ti]))
                except ValueError:
                    break
                ti += 1
        return vals

    while ti < len(tokens):
        t = tokens[ti]
        if t in PARAM_COUNT:
            cmd = t
            ti += 1
            if cmd in ("Z", "z"):
                cx, cy = sx, sy
                continue
            continue

        # consume parameters based on current command
        nparams = PARAM_COUNT.get(cmd, 0)
        if nparams == 0:
            ti += 1
            continue

        vals = consume(nparams)
        if len(vals) < nparams:
            break

        if cmd == "M":
            cx, cy = vals[0], vals[1]
            sx, sy = cx, cy
            xs.append(cx)
            ys.append(cy)
            cmd = "L"  # subsequent coords are implicit lineto
        elif cmd == "m":
            cx += vals[0]
            cy += vals[1]
            sx, sy = cx, cy
            xs.append(cx)
            ys.append(cy)
            cmd = "l"
        elif cmd == "L":
            cx, cy = vals[0], vals[1]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "l":
            cx += vals[0]
            cy += vals[1]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "H":
            cx = vals[0]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "h":
            cx += vals[0]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "V":
            cy = vals[0]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "v":
            cy += vals[0]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "C":
            # cubic bezier: (cp1x,cp1y, cp2x,cp2y, x,y)
            xs.extend([vals[0], vals[2], vals[4]])
            ys.extend([vals[1], vals[3], vals[5]])
            cx, cy = vals[4], vals[5]
        elif cmd == "c":
            xs.extend([cx + vals[0], cx + vals[2], cx + vals[4]])
            ys.extend([cy + vals[1], cy + vals[3], cy + vals[5]])
            cx += vals[4]
            cy += vals[5]
        elif cmd == "S":
            xs.extend([vals[0], vals[2]])
            ys.extend([vals[1], vals[3]])
            cx, cy = vals[2], vals[3]
        elif cmd == "s":
            xs.extend([cx + vals[0], cx + vals[2]])
            ys.extend([cy + vals[1], cy + vals[3]])
            cx += vals[2]
            cy += vals[3]
        elif cmd == "Q":
            xs.extend([vals[0], vals[2]])
            ys.extend([vals[1], vals[3]])
            cx, cy = vals[2], vals[3]
        elif cmd == "q":
            xs.extend([cx + vals[0], cx + vals[2]])
            ys.extend([cy + vals[1], cy + vals[3]])
            cx += vals[2]
            cy += vals[3]
        elif cmd == "T":
            cx, cy = vals[0], vals[1]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "t":
            cx += vals[0]
            cy += vals[1]
            xs.append(cx)
            ys.append(cy)
        elif cmd == "A" or cmd == "a":
            # arc: (rx, ry, x-rot, large-arc, sweep, x, y)
            if cmd == "A":
                cx, cy = vals[5], vals[6]
            else:
                cx += vals[5]
                cy += vals[6]
            xs.append(cx)
            ys.append(cy)

    if not xs or not ys:
        return BBox(0, 0, 0, 0)

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return BBox(min_x, min_y, max_x - min_x, max_y - min_y)


# ---------------------------------------------------------------------------
# Parse transform for <g> elements
# ---------------------------------------------------------------------------


def parse_transform(transform: str) -> tuple[float, float, float, float]:
    """Parse translate, scale, and rotate from a transform attribute.

    Returns (tx, ty, scale, rotate_deg).
    """
    tx, ty = 0.0, 0.0
    scale = 1.0
    rotate = 0.0

    m = re.search(r"translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", transform)
    if m:
        tx, ty = float(m.group(1)), float(m.group(2))

    m = re.search(r"scale\(\s*([-\d.]+)\s*\)", transform)
    if m:
        scale = float(m.group(1))

    m = re.search(r"rotate\(\s*([-\d.]+)\s*\)", transform)
    if m:
        rotate = float(m.group(1))

    return tx, ty, scale, rotate


# ---------------------------------------------------------------------------
# Recursive group bounding box computation
# ---------------------------------------------------------------------------

NS = {"svg": "http://www.w3.org/2000/svg"}
SVG_NS = "http://www.w3.org/2000/svg"


def _strip_ns(tag: str) -> str:
    """Remove SVG namespace from tag."""
    return tag.replace(f"{{{SVG_NS}}}", "")


def _compute_local_bbox_recursive(el) -> BBox | None:
    """Recursively compute bounding box of an element in its local coordinate space.

    For <g> elements, recurses into children and applies child transforms.
    For primitives (path, rect, circle, line, polygon), computes directly.
    Returns None if no visual content found.
    """
    tag = _strip_ns(el.tag)

    if tag == "path":
        d = el.get("d", "")
        bb = path_bbox(d)
        if bb.w > 0 or bb.h > 0:
            return bb
        return None

    elif tag == "rect":
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
        w = float(el.get("width", "0"))
        h = float(el.get("height", "0"))
        if w > 0 or h > 0:
            return BBox(x, y, w, h)
        return None

    elif tag == "circle":
        cx = float(el.get("cx", "0"))
        cy = float(el.get("cy", "0"))
        r = float(el.get("r", "0"))
        sw = float(el.get("stroke-width", "0"))
        # include stroke in inner bbox
        return BBox(cx - r - sw / 2, cy - r - sw / 2, 2 * r + sw, 2 * r + sw)

    elif tag == "line":
        x1 = float(el.get("x1", "0"))
        y1 = float(el.get("y1", "0"))
        x2 = float(el.get("x2", "0"))
        y2 = float(el.get("y2", "0"))
        sw = float(el.get("stroke-width", "1"))
        min_x = min(x1, x2) - sw / 2
        min_y = min(y1, y2) - sw / 2
        w = abs(x2 - x1) + sw
        h = abs(y2 - y1) + sw
        return BBox(min_x, min_y, w, h)

    elif tag == "polygon":
        pts = el.get("points", "")
        coords = [float(v) for v in re.findall(r"[-\d.]+", pts)]
        if len(coords) < 4:
            return None
        xs = coords[0::2]
        ys = coords[1::2]
        return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    elif tag == "g":
        # recurse into children, applying this group's transform
        transform = el.get("transform", "")
        tx, ty, scale, rotate = parse_transform(transform)

        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")
        found = False

        for child in el:
            child_bb = _compute_local_bbox_recursive(child)
            if child_bb is None:
                continue
            found = True

            # apply this group's transform to child bbox corners
            corners = [
                (child_bb.x, child_bb.y),
                (child_bb.x2, child_bb.y),
                (child_bb.x, child_bb.y2),
                (child_bb.x2, child_bb.y2),
            ]

            if rotate != 0:
                rad = math.radians(rotate)
                cos_r, sin_r = math.cos(rad), math.sin(rad)
                transformed = []
                for cx, cy in corners:
                    rx = cx * cos_r - cy * sin_r
                    ry = cx * sin_r + cy * cos_r
                    transformed.append((tx + rx * scale, ty + ry * scale))
            else:
                transformed = [(tx + cx * scale, ty + cy * scale) for cx, cy in corners]

            for px, py in transformed:
                min_x = min(min_x, px)
                min_y = min(min_y, py)
                max_x = max(max_x, px)
                max_y = max(max_y, py)

        if not found:
            return None
        return BBox(min_x, min_y, max_x - min_x, max_y - min_y)

    return None


# ---------------------------------------------------------------------------
# SVG parser
# ---------------------------------------------------------------------------


def parse_svg(filepath: str) -> list[Element]:
    """Parse SVG and extract all visual elements with bounding boxes.

    Uses a two-pass approach:
    1. First pass identifies <g> groups and computes their bboxes recursively
       (applying transforms correctly). All descendants of processed groups
       are marked to avoid double-counting.
    2. Second pass processes standalone elements not inside any group.
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    elements: list[Element] = []
    current_section = "palette"
    current_bg = "transparent"

    # Track elements that are children of processed <g> groups
    # to avoid double-counting them as standalone elements
    processed_descendants: set[int] = set()

    def get_attr(el, name, default=""):
        return el.get(name, default)

    def _mark_descendants(el):
        """Mark all descendants of el as processed."""
        for desc in el.iter():
            if desc is not el:
                processed_descendants.add(id(desc))

    for child in root.iter():
        # skip already-processed descendants of groups
        if id(child) in processed_descendants:
            continue

        tag = _strip_ns(child.tag)

        # skip verification overlay group
        if tag == "g" and child.get("id") == "text-bounds":
            _mark_descendants(child)
            continue

        if tag == "text":
            x = float(get_attr(child, "x", "0"))
            y = float(get_attr(child, "y", "0"))
            fs = float(get_attr(child, "font-size", "10"))
            fw = get_attr(child, "font-weight", "normal")
            ls_str = get_attr(child, "letter-spacing", "0")
            ls = float(ls_str) if ls_str else 0
            anchor = get_attr(child, "text-anchor", "start")
            content = child.text or ""

            # detect section changes from section header text
            if "LIGHT BACKGROUND" in content.upper():
                current_section = "light-strip"
                current_bg = "light"
            elif "DARK BACKGROUND" in content.upper():
                current_section = "dark-strip"
                current_bg = "dark"
            elif "MID BACKGROUND" in content.upper():
                current_section = "mid-strip"
                current_bg = "mid"

            bbox = text_bbox(x, y, fs, content, fw, ls, anchor)
            elements.append(
                Element(
                    tag="text",
                    label=f'"{content}" ({fs}px/{fw})',
                    bbox=bbox,
                    section=current_section,
                    role="text",
                    parent_bg=current_bg,
                )
            )

        elif tag == "rect":
            x = float(get_attr(child, "x", "0"))
            y = float(get_attr(child, "y", "0"))
            w = float(get_attr(child, "width", "0"))
            h = float(get_attr(child, "height", "0"))

            fill = get_attr(child, "fill", "")
            opacity = get_attr(child, "opacity", "1")

            # detect background strip rects (full-width)
            if w >= 780:
                fill_lower = fill.lower()
                # light backgrounds
                if any(c in fill_lower for c in ("#f5f7fa", "#f8fafc", "#fafafa", "#f0f0f0")):
                    current_section = "light-strip"
                    current_bg = "light"
                # dark backgrounds
                elif any(c in fill_lower for c in ("#1a2332", "#0f172a", "#1e1e1e", "#111827")):
                    current_section = "dark-strip"
                    current_bg = "dark"
                elif "#8a9bb5" in fill_lower:
                    current_section = "mid-strip"
                    current_bg = "mid"
                elements.append(
                    Element(
                        tag="rect",
                        label=f"bg-strip {fill}",
                        bbox=BBox(x, y, w, h),
                        section=current_section,
                        role="background",
                        parent_bg=current_bg,
                    )
                )
                continue

            # classify rect role
            role = "rect"
            if w <= 14 and h <= 14:
                role = "color-chip"
            elif "fill-opacity" in child.attrib or (opacity and float(opacity) < 0.2):
                role = "bg-fill"
            elif h <= 6:
                role = "accent-bar"

            elements.append(
                Element(
                    tag="rect",
                    label=f"rect {w:.0f}x{h:.0f} @({x:.0f},{y:.0f})",
                    bbox=BBox(x, y, w, h),
                    section=current_section,
                    role=role,
                    parent_bg=current_bg,
                )
            )

        elif tag == "path":
            d = get_attr(child, "d", "")
            bbox = path_bbox(d)
            sw = float(get_attr(child, "stroke-width", "0"))
            # include stroke in inner bbox
            if sw > 0:
                bbox = BBox(bbox.x - sw / 2, bbox.y - sw / 2, bbox.w + sw, bbox.h + sw)
            role = "card" if bbox.w > 100 and bbox.h > 50 else "path"
            elements.append(
                Element(
                    tag="path",
                    label=f"path {bbox}",
                    bbox=bbox,
                    section=current_section,
                    role=role,
                    parent_bg=current_bg,
                )
            )

        elif tag == "circle":
            ccx = float(get_attr(child, "cx", "0"))
            ccy = float(get_attr(child, "cy", "0"))
            r = float(get_attr(child, "r", "0"))
            sw = float(get_attr(child, "stroke-width", "0"))
            # include stroke in inner bbox
            total_r = r + sw / 2
            elements.append(
                Element(
                    tag="circle",
                    label=f"circle r={r:.0f} @({ccx:.0f},{ccy:.0f})",
                    bbox=BBox(ccx - total_r, ccy - total_r, 2 * total_r, 2 * total_r),
                    section=current_section,
                    role="milestone",
                    parent_bg=current_bg,
                )
            )

        elif tag == "line":
            x1 = float(get_attr(child, "x1", "0"))
            y1 = float(get_attr(child, "y1", "0"))
            x2 = float(get_attr(child, "x2", "0"))
            y2 = float(get_attr(child, "y2", "0"))
            sw = float(get_attr(child, "stroke-width", "1"))
            min_x = min(x1, x2) - sw / 2
            min_y = min(y1, y2) - sw / 2
            w = abs(x2 - x1) + sw
            h = abs(y2 - y1) + sw
            if abs(x2 - x1) < 1:  # vertical divider
                role = "divider"
            else:
                role = "track-line"
            elements.append(
                Element(
                    tag="line",
                    label=f"line ({x1:.0f},{y1:.0f})->({x2:.0f},{y2:.0f})",
                    bbox=BBox(min_x, min_y, w, h),
                    section=current_section,
                    role=role,
                    parent_bg=current_bg,
                )
            )

        elif tag == "g":
            # Compute full recursive bbox with transform handling
            bbox = _compute_local_bbox_recursive(child)
            if bbox is None:
                continue

            # Mark all descendants so they are not double-counted
            _mark_descendants(child)

            transform = get_attr(child, "transform", "")
            tx, ty, scale, rotate = parse_transform(transform)

            # Count direct visual children for classification
            child_count = 0
            has_polygon = False
            has_line = False
            for c in child:
                ctag = _strip_ns(c.tag)
                if ctag in ("path", "rect", "circle", "line", "polygon", "g"):
                    child_count += 1
                if ctag == "polygon":
                    has_polygon = True
                if ctag == "line":
                    has_line = True

            # classify group
            if has_polygon and has_line and child_count <= 4:
                role_name = "arrow"
                tag_name = "g-arrow"
            elif bbox.w < 30 and bbox.h < 30:
                role_name = "icon"
                tag_name = "g-icon"
            elif bbox.w < 60 and bbox.h < 60:
                role_name = "icon"
                tag_name = "g-icon"
            else:
                role_name = "logo"
                tag_name = "g-logo"

            elements.append(
                Element(
                    tag=tag_name,
                    label=f"{role_name} @({tx:.0f},{ty:.0f}) s={scale:.2f} [{child_count} children] {bbox}",
                    bbox=bbox,
                    section=current_section,
                    role=role_name,
                    parent_bg=current_bg,
                )
            )

    return elements


# ---------------------------------------------------------------------------
# Overlap analysis
# ---------------------------------------------------------------------------


def classify_overlap(a: Element, b: Element) -> str:
    """Classify the relationship between two overlapping elements.

    Returns one of:
    - 'contained'     : one element fully inside the other (child in parent)
    - 'label-on-fill' : text element on a filled shape (intended label)
    - 'sibling'       : same-role elements touching (e.g. grid squares, bar segments)
    - 'violation'     : unexpected overlap that likely needs fixing
    """
    # contained: one inner bbox fully inside the other
    if a.bbox.contains(b.bbox) or b.bbox.contains(a.bbox):
        return "contained"

    # label-on-fill: text on a rect/path/circle (intentional label placement)
    fill_roles = ("rect", "color-chip", "bg-fill", "card", "accent-bar", "milestone", "background")
    if (a.tag == "text" and b.role in fill_roles) or (b.tag == "text" and a.role in fill_roles):
        return "label-on-fill"

    # sibling: same role and same section (grid squares, bar segments, etc.)
    if a.role == b.role and a.section == b.section:
        return "sibling"

    # everything else is a potential violation
    return "violation"


def analyze_overlaps(
    elements: list[Element],
    extra_padding: float = 0.0,
    use_outer: bool = True,
) -> list[tuple[int, int, Element, Element, float, str]]:
    """Report ALL overlapping element pairs with indices and classification.

    By default, compares outer bboxes (inner + per-role padding).
    When use_outer=False, compares raw inner bboxes (legacy mode).
    extra_padding adds uniform inflation on top of role-specific padding.

    Each result tuple includes a classification string from classify_overlap().
    """
    overlaps = []
    indexed = list(enumerate(elements))
    for (i, a), (j, b) in combinations(indexed, 2):
        if use_outer:
            ba = a.outer_bbox
            bb = b.outer_bbox
        else:
            ba = a.bbox
            bb = b.bbox

        if extra_padding:
            ba = ba.padded(extra_padding)
            bb = bb.padded(extra_padding)

        if not ba.overlaps(bb):
            continue
        pct = ba.overlap_pct(bb)
        if pct > 0:
            cls = classify_overlap(a, b)
            overlaps.append((i, j, a, b, pct, cls))
    overlaps.sort(key=lambda x: -x[4])
    return overlaps


# ---------------------------------------------------------------------------
# Proximity report
# ---------------------------------------------------------------------------


def proximity_report(
    elements: list[Element], threshold: float = 20.0
) -> list[tuple[Element, Element, float, str, float, str]]:
    """Find same-section element pairs within threshold px distance.

    Uses outer bboxes to measure spacing between elements.
    """
    results = []
    for a, b in combinations(elements, 2):
        if a.section != b.section:
            continue
        if a.role == "background" or b.role == "background":
            continue

        h_gap, h_dir, v_gap, v_dir = a.outer_bbox.gap_to(b.outer_bbox)

        # report the relevant gap (non-overlapping axis)
        if h_gap >= 0 and h_gap <= threshold:
            results.append((a, b, h_gap, h_dir, v_gap, v_dir))
        elif v_gap >= 0 and v_gap <= threshold:
            results.append((a, b, h_gap, h_dir, v_gap, v_dir))

    # sort by smallest positive gap
    def sort_key(item):
        _, _, h, _, v, _ = item
        gaps = [g for g in [h, v] if g >= 0]
        return min(gaps) if gaps else 999

    results.sort(key=sort_key)
    return results


# ---------------------------------------------------------------------------
# Spacing checks (from Theme Validation Checklist)
# ---------------------------------------------------------------------------


def check_spacing(elements: list[Element]) -> list[str]:
    issues = []

    strips = [e for e in elements if e.role == "background"]
    dividers = [e for e in elements if e.role == "divider"]
    cards = [e for e in elements if e.role == "card"]
    milestones = [e for e in elements if e.role == "milestone"]
    texts = [e for e in elements if e.tag == "text"]

    # card content min 10px padding
    for card in cards:
        for t in texts:
            if t.section != card.section:
                continue
            tb = t.bbox
            cb = card.bbox
            if tb.x >= cb.x and tb.x2 <= cb.x2 and tb.y >= cb.y and tb.y2 <= cb.y2:
                left_pad = tb.x - cb.x
                right_pad = cb.x2 - tb.x2
                top_pad = tb.y - cb.y
                bottom_pad = cb.y2 - tb.y2
                min_pad = min(left_pad, right_pad, top_pad, bottom_pad)
                if min_pad < 10:
                    issues.append(
                        f"CARD PADDING {min_pad:.0f}px < 10px: {t.label} "
                        f"in card @{card.bbox} "
                        f"(L={left_pad:.0f} R={right_pad:.0f} T={top_pad:.0f} B={bottom_pad:.0f})"
                    )

    # strip padding min 15px
    for strip in strips:
        for e in elements:
            if e.role == "background" or e.section != strip.section:
                continue
            eb = e.bbox
            sb = strip.bbox
            if eb.y >= sb.y and eb.y2 <= sb.y2:
                top_pad = eb.y - sb.y
                bottom_pad = sb.y2 - eb.y2
                if top_pad < 15 and top_pad > 0:
                    issues.append(
                        f"STRIP TOP PADDING {top_pad:.0f}px < 15px: {e.label} in {strip.label}"
                    )
                if bottom_pad < 15 and bottom_pad > 0:
                    issues.append(
                        f"STRIP BOTTOM PADDING {bottom_pad:.0f}px < 15px: {e.label} "
                        f"in {strip.label}"
                    )

    # timeline labels clear of circles min 6px
    for m in milestones:
        for t in texts:
            if t.section != m.section:
                continue
            tb = t.bbox
            mb = m.bbox
            if abs((tb.x + tb.w / 2) - (mb.x + mb.w / 2)) < 30:
                if tb.y2 < mb.y:
                    gap = mb.y - tb.y2
                    if gap < 6:
                        issues.append(
                            f"TIMELINE LABEL GAP {gap:.0f}px < 6px: {t.label} above {m.label}"
                        )

    # containment overflow: child elements that are mostly inside a
    # container (bg-fill, card) but extend past its boundary
    containers = [e for e in elements if e.role in ("bg-fill", "card")]
    for container in containers:
        cb = container.bbox
        for e in elements:
            if e is container or e.role == "background":
                continue
            eb = e.bbox
            # check if element centre is inside the container
            ecx = eb.x + eb.w / 2
            ecy = eb.y + eb.h / 2
            if not (cb.x <= ecx <= cb.x2 and cb.y <= ecy <= cb.y2):
                continue
            # element is inside - check for overflow on each edge
            overflows = []
            if eb.x < cb.x:
                overflows.append(f"left by {cb.x - eb.x:.0f}px")
            if eb.x2 > cb.x2:
                overflows.append(f"right by {eb.x2 - cb.x2:.0f}px")
            if eb.y < cb.y:
                overflows.append(f"top by {cb.y - eb.y:.0f}px")
            if eb.y2 > cb.y2:
                overflows.append(f"bottom by {eb.y2 - cb.y2:.0f}px")
            if overflows:
                issues.append(
                    f"CONTAINMENT OVERFLOW: {e.label} overflows "
                    f"container {container.label} ({', '.join(overflows)})"
                )

    # text crosses divider
    for d in dividers:
        for t in texts:
            if t.section != d.section:
                continue
            tb = t.bbox
            db = d.bbox
            if tb.x < db.x2 and tb.x2 > db.x and tb.y < db.y2 and tb.y2 > db.y:
                issues.append(
                    f"TEXT CROSSES DIVIDER: {t.label} "
                    f"(right={tb.x2:.0f}) crosses divider @x={db.x:.0f} "
                    f"(divider y={db.y:.0f}-{db.y2:.0f}, text y={tb.y:.0f}-{tb.y2:.0f})"
                )

    return issues


# ---------------------------------------------------------------------------
# Typography hierarchy check
# ---------------------------------------------------------------------------


def check_typography(elements: list[Element]) -> list[str]:
    issues = []
    texts = [e for e in elements if e.tag == "text"]

    sizes = set()
    for t in texts:
        m = re.search(r"\((\d+(?:\.\d+)?)px/", t.label)
        if m:
            sizes.add(float(m.group(1)))

    sorted_sizes = sorted(sizes, reverse=True)
    if sorted_sizes:
        if sorted_sizes[-1] < 7:
            issues.append(f"FONT TOO SMALL: {sorted_sizes[-1]}px (minimum 7px)")
        issues.append(f"Font size ladder: {' > '.join(str(s) for s in sorted_sizes)}")

    return issues


# ---------------------------------------------------------------------------
# Bounding box overlay generation
# ---------------------------------------------------------------------------


def generate_bounds_overlay(elements: list[Element], dividers: list[Element]) -> str:
    """Generate SVG group with inner and outer bounding box rectangles."""
    lines = []
    lines.append("  <!-- === VERIFICATION: bounding box overlay (auto-generated) === -->")
    lines.append('  <g id="text-bounds" opacity="0.6">')

    for e in elements:
        ib = e.bbox
        ob = e.outer_bbox

        if e.tag == "text":
            # inner bbox (magenta)
            lines.append(
                f'    <rect x="{ib.x:.1f}" y="{ib.y:.1f}" width="{ib.w:.1f}" '
                f'height="{ib.h:.1f}" fill="none" stroke="magenta" '
                f'stroke-width="0.5" stroke-dasharray="2,1"/>'
            )
            # outer bbox (magenta, wider dash)
            lines.append(
                f'    <rect x="{ob.x:.1f}" y="{ob.y:.1f}" width="{ob.w:.1f}" '
                f'height="{ob.h:.1f}" fill="none" stroke="magenta" '
                f'stroke-width="0.3" stroke-dasharray="4,2" opacity="0.4"/>'
            )

        elif e.role in ("icon", "logo", "arrow"):
            # inner bbox (orange)
            lines.append(
                f'    <rect x="{ib.x:.1f}" y="{ib.y:.1f}" width="{ib.w:.1f}" '
                f'height="{ib.h:.1f}" fill="none" stroke="orange" '
                f'stroke-width="0.5" stroke-dasharray="2,1"/>'
            )
            # outer bbox (orange, wider dash)
            lines.append(
                f'    <rect x="{ob.x:.1f}" y="{ob.y:.1f}" width="{ob.w:.1f}" '
                f'height="{ob.h:.1f}" fill="none" stroke="orange" '
                f'stroke-width="0.3" stroke-dasharray="4,2" opacity="0.4"/>'
            )

        elif e.role == "card":
            # inner bbox only (cyan)
            lines.append(
                f'    <rect x="{ib.x:.1f}" y="{ib.y:.1f}" width="{ib.w:.1f}" '
                f'height="{ib.h:.1f}" fill="none" stroke="cyan" '
                f'stroke-width="0.5" stroke-dasharray="4,2"/>'
            )

    # divider reference lines (green dashed, extended)
    for d in dividers:
        b = d.bbox
        lines.append(
            f'    <line x1="{b.x:.1f}" y1="{b.y - 10:.1f}" '
            f'x2="{b.x:.1f}" y2="{b.y2 + 10:.1f}" '
            f'stroke="lime" stroke-width="0.5" stroke-dasharray="3,2"/>'
        )

    # strip 15px padding inset margins (yellow dashed)
    for e in elements:
        if e.role == "background":
            b = e.bbox
            inset = 15
            lines.append(
                f'    <rect x="{b.x + inset:.1f}" y="{b.y + inset:.1f}" '
                f'width="{b.w - 2 * inset:.1f}" height="{b.h - 2 * inset:.1f}" '
                f'fill="none" stroke="yellow" stroke-width="0.5" stroke-dasharray="5,3"/>'
            )

    lines.append("  </g>")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Callout cross-collision check
# ---------------------------------------------------------------------------


def _parse_path_segments(d: str) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Extract straight-line segments from an SVG `d` attribute (M/L/H/V/Z only).

    Curves are approximated by their endpoints. Adequate for leader lines which
    are conventionally straight or L-shaped.
    """
    tokens = re.findall(r"[MLHVZmlhvz]|-?\d+\.?\d*(?:[eE][-+]?\d+)?", d or "")
    segs: list[tuple[tuple[float, float], tuple[float, float]]] = []
    x = y = 0.0
    start_x = start_y = 0.0
    i = 0
    cmd = None
    while i < len(tokens):
        tok = tokens[i]
        if tok.isalpha():
            cmd = tok
            i += 1
            continue
        if cmd in ("M", "m"):
            nx = float(tokens[i])
            ny = float(tokens[i + 1])
            if cmd == "m":
                nx += x
                ny += y
            x, y = nx, ny
            start_x, start_y = x, y
            i += 2
            cmd = "L" if cmd == "M" else "l"
        elif cmd in ("L", "l"):
            nx = float(tokens[i])
            ny = float(tokens[i + 1])
            if cmd == "l":
                nx += x
                ny += y
            segs.append(((x, y), (nx, ny)))
            x, y = nx, ny
            i += 2
        elif cmd in ("H", "h"):
            nx = float(tokens[i])
            if cmd == "h":
                nx += x
            segs.append(((x, y), (nx, y)))
            x = nx
            i += 1
        elif cmd in ("V", "v"):
            ny = float(tokens[i])
            if cmd == "v":
                ny += y
            segs.append(((x, y), (x, ny)))
            y = ny
            i += 1
        elif cmd in ("Z", "z"):
            segs.append(((x, y), (start_x, start_y)))
            x, y = start_x, start_y
            i += 1
        else:
            i += 1
    return segs


def _extract_font_size_from_style(svg_text: str, class_name: str) -> float:
    """Parse CSS `.class_name { font-size: Xpx }` from style block. Default 8.5."""
    m = re.search(
        rf"\.{re.escape(class_name)}\s*\{{[^}}]*font-size\s*:\s*(\d+(?:\.\d+)?)px",
        svg_text,
    )
    return float(m.group(1)) if m else 8.5


def parse_callouts(svg_path: str) -> list[dict]:
    """Extract callout groups from an SVG.

    Convention: `<g id="callout-*">` wrapping `<text class="callout-text">`
    entries and `<line class="callout-line">` / `<path class="callout-line">`
    leaders.

    Returns list of dicts: `{"id", "text_bbox": BBox|None, "leaders": [((x1,y1),(x2,y2)), ...]}`.
    """
    with open(svg_path, "r") as f:
        svg_text = f.read()

    font_size = _extract_font_size_from_style(svg_text, "callout-text")
    pad = 2.0

    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = "{http://www.w3.org/2000/svg}"

    callouts: list[dict] = []
    for g in root.iter(f"{ns}g"):
        gid = g.get("id", "")
        if not gid.startswith("callout"):
            continue

        text_bboxes: list[BBox] = []
        for t in g.iter(f"{ns}text"):
            cls = t.get("class", "")
            if "callout-text" not in cls:
                continue
            try:
                x = float(t.get("x", 0))
                y = float(t.get("y", 0))
            except ValueError:
                continue
            content = "".join(t.itertext() or "")
            width = max(1.0, len(content) * font_size * 0.55)
            text_bboxes.append(BBox(x - pad, y - font_size, width + 2 * pad, font_size + 2 * pad))

        text_bbox = None
        if text_bboxes:
            min_x = min(b.x for b in text_bboxes)
            min_y = min(b.y for b in text_bboxes)
            max_x = max(b.x2 for b in text_bboxes)
            max_y = max(b.y2 for b in text_bboxes)
            text_bbox = BBox(min_x, min_y, max_x - min_x, max_y - min_y)

        leaders: list[tuple[tuple[float, float], tuple[float, float]]] = []
        for line in g.iter(f"{ns}line"):
            cls = line.get("class", "")
            if "callout" not in cls:
                continue
            try:
                x1 = float(line.get("x1", 0))
                y1 = float(line.get("y1", 0))
                x2 = float(line.get("x2", 0))
                y2 = float(line.get("y2", 0))
            except ValueError:
                continue
            leaders.append(((x1, y1), (x2, y2)))
        for path in g.iter(f"{ns}path"):
            cls = path.get("class", "")
            if "callout" not in cls:
                continue
            leaders.extend(_parse_path_segments(path.get("d", "")))
        for pl in g.iter(f"{ns}polyline"):
            cls = pl.get("class", "")
            if "callout" not in cls:
                continue
            pts_raw = pl.get("points", "").replace(",", " ").split()
            try:
                coords = [
                    (float(pts_raw[k]), float(pts_raw[k + 1]))
                    for k in range(0, len(pts_raw) - 1, 2)
                ]
            except (ValueError, IndexError):
                continue
            for k in range(len(coords) - 1):
                leaders.append((coords[k], coords[k + 1]))

        callouts.append({"id": gid, "text_bbox": text_bbox, "leaders": leaders})
    return callouts


def check_callouts(svg_path: str) -> list[str]:
    """Pairwise cross-callout collision check.

    Reports when a callout's leader crosses another callout's text bbox or
    leader, and when callout text bboxes overlap each other. Uses shapely
    LineString / box intersection for the line-vs-line and line-vs-rect tests.
    """
    try:
        from shapely.geometry import LineString
        from shapely.geometry import box as sbox
    except ImportError:
        return ["shapely not installed - callout check skipped"]

    callouts = parse_callouts(svg_path)
    if not callouts:
        return []

    violations: list[str] = []
    n = len(callouts)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = callouts[i], callouts[j]

            # leader A vs text B
            if b["text_bbox"] is not None:
                bb = b["text_bbox"]
                b_box = sbox(bb.x, bb.y, bb.x2, bb.y2)
                for seg in a["leaders"]:
                    if seg[0] == seg[1]:
                        continue
                    line = LineString(seg)
                    if line.intersects(b_box) and not line.touches(b_box):
                        violations.append(f"leader of {a['id']} crosses text of {b['id']} at {bb}")
                        break

            # leader B vs text A
            if a["text_bbox"] is not None:
                ab = a["text_bbox"]
                a_box = sbox(ab.x, ab.y, ab.x2, ab.y2)
                for seg in b["leaders"]:
                    if seg[0] == seg[1]:
                        continue
                    line = LineString(seg)
                    if line.intersects(a_box) and not line.touches(a_box):
                        violations.append(f"leader of {b['id']} crosses text of {a['id']} at {ab}")
                        break

            # leader A vs leader B
            cross_found = False
            for sa in a["leaders"]:
                if sa[0] == sa[1] or cross_found:
                    continue
                la = LineString(sa)
                for sb in b["leaders"]:
                    if sb[0] == sb[1]:
                        continue
                    lb = LineString(sb)
                    if la.crosses(lb):
                        violations.append(f"leader of {a['id']} crosses leader of {b['id']}")
                        cross_found = True
                        break

            # text A vs text B (bbox overlap)
            if a["text_bbox"] is not None and b["text_bbox"] is not None:
                if a["text_bbox"].overlaps(b["text_bbox"]):
                    violations.append(f"text of {a['id']} overlaps text of {b['id']}")

    return violations


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SVG overlap detector with inner/outer bbox model"
    )
    parser.add_argument("--svg", default="theme_swatch.svg", help="SVG file to check")
    parser.add_argument(
        "--inject-bounds",
        action="store_true",
        help="Strip existing overlay then inject fresh bounding box overlay",
    )
    parser.add_argument(
        "--strip-bounds",
        action="store_true",
        help="Remove bounding box verification overlay from SVG",
    )
    parser.add_argument(
        "--ignore",
        type=str,
        default="",
        help="Comma-separated overlap IDs to skip (e.g. '21x23,24x25')",
    )
    parser.add_argument(
        "--extra-padding",
        type=float,
        default=0.0,
        help="Additional uniform inflation on top of per-role padding (catches near-misses)",
    )
    parser.add_argument(
        "--padding", type=float, default=0.0, help="(Legacy) Alias for --extra-padding"
    )
    parser.add_argument(
        "--raw", action="store_true", help="Compare raw inner bboxes only (skip per-role padding)"
    )
    args = parser.parse_args()

    # support legacy --padding flag
    extra_padding = args.extra_padding or args.padding

    # parse ignore set
    ignore_set = set()
    if args.ignore:
        for pair in args.ignore.split(","):
            pair = pair.strip()
            if "x" in pair:
                ignore_set.add(pair)

    print(f"Parsing: {args.svg}")
    mode = "raw inner" if args.raw else "outer (inner + per-role padding)"
    print(f"Bbox mode: {mode}")
    if extra_padding:
        print(f"Extra padding: {extra_padding:.0f}px")
    print("=" * 72)

    elements = parse_svg(args.svg)
    print(f"Found {len(elements)} elements\n")

    # role padding summary
    print("ROLE PADDING TABLE")
    print("-" * 72)
    roles_seen = sorted(set(e.role for e in elements))
    for role in roles_seen:
        pad = ROLE_PADDING.get(role, 4)
        print(f"  {role:12s}  {pad:2.0f}px")
    print()

    # list all elements with inner and outer bboxes
    print("ELEMENT INVENTORY")
    print("-" * 72)
    for i, e in enumerate(elements):
        ob = e.outer_bbox
        print(
            f"  [{i:2d}] {e.tag:8s} {e.role:12s} {e.section:12s} inner={e.bbox}  outer={ob}  {e.label}"
        )

    # overlap analysis
    print(f"\n{'=' * 72}")
    mode_note = " (raw inner)" if args.raw else " (outer bbox)"
    pad_note = f" +{extra_padding:.0f}px" if extra_padding else ""
    print(f"OVERLAPS{mode_note}{pad_note}")
    print("-" * 72)
    overlaps = analyze_overlaps(elements, extra_padding=extra_padding, use_outer=not args.raw)
    shown = 0
    ignored = 0

    # group overlaps by classification
    CLASS_ORDER = ["violation", "sibling", "label-on-fill", "contained"]
    CLASS_LABELS = {
        "violation": "VIOLATION (unexpected overlap - likely needs fixing)",
        "sibling": "SIBLING (same-role elements touching)",
        "label-on-fill": "LABEL-ON-FILL (text on filled shape)",
        "contained": "CONTAINED (child inside parent)",
    }

    if not overlaps:
        print("  None found!")
    else:
        # partition by class
        by_class: dict[str, list] = {c: [] for c in CLASS_ORDER}
        for entry in overlaps:
            i, j, a, b, pct, cls = entry
            oid = f"{i}x{j}"
            if oid in ignore_set:
                ignored += 1
                continue
            by_class.setdefault(cls, []).append(entry)

        for cls in CLASS_ORDER:
            entries = by_class.get(cls, [])
            if not entries:
                continue
            print(f"\n  --- {CLASS_LABELS.get(cls, cls)} ({len(entries)}) ---")
            for i, j, a, b, pct, _ in entries:
                oid = f"{i}x{j}"
                shown += 1
                severity = "!!!" if pct > 30 else "! " if pct > 10 else "  "
                h_gap, h_dir, v_gap, v_dir = a.outer_bbox.gap_to(b.outer_bbox)
                print(f"  {severity} [{oid}] {pct:5.1f}% overlap:")
                print(f"       A: [{a.role:12s}] [{i:2d}] {a.label}")
                print(f"          inner={a.bbox}  outer={a.outer_bbox}")
                print(f"       B: [{b.role:12s}] [{j:2d}] {b.label}")
                print(f"          inner={b.bbox}  outer={b.outer_bbox}")
                print(
                    f"       gaps (outer): h={h_gap:+.1f}px ({h_dir})  v={v_gap:+.1f}px ({v_dir})"
                )
                if cls == "violation" and h_gap < 0 and v_gap < 0:
                    fix_h = abs(h_gap) + 1
                    fix_v = abs(v_gap) + 1
                    print(
                        f"       FIX: shift B right by {fix_h:.0f}px OR down by {fix_v:.0f}px to clear"
                    )
                print()
        if ignored:
            print(f"  ({ignored} overlaps ignored via --ignore)")

    # proximity report
    print(f"{'=' * 72}")
    print("PROXIMITY REPORT (same-section pairs within 20px, outer bboxes)")
    print("-" * 72)
    prox = proximity_report(elements)
    if not prox:
        print("  No tight proximities found.")
    else:
        for a, b, h_gap, h_dir, v_gap, v_dir in prox:
            # report the meaningful gap
            if h_gap >= 0 and (v_gap < 0 or h_gap <= v_gap):
                print(f"  h_gap=+{h_gap:.1f}px ({h_dir})")
            else:
                print(f"  v_gap=+{v_gap:.1f}px ({v_dir})")
            print(f"    A: [{a.role:12s}] inner={a.bbox}  outer={a.outer_bbox}  {a.label}")
            print(f"    B: [{b.role:12s}] inner={b.bbox}  outer={b.outer_bbox}  {b.label}")
            print()

    # spacing checks
    print(f"{'=' * 72}")
    print("SPACING & CHECKLIST VIOLATIONS")
    print("-" * 72)
    spacing_issues = check_spacing(elements)
    if not spacing_issues:
        print("  All spacing checks pass!")
    else:
        for issue in spacing_issues:
            print(f"  - {issue}")

    # typography
    print(f"\n{'=' * 72}")
    print("TYPOGRAPHY")
    print("-" * 72)
    typo_issues = check_typography(elements)
    for issue in typo_issues:
        print(f"  - {issue}")

    # callout cross-collisions
    print(f"\n{'=' * 72}")
    print("CALLOUT CROSS-COLLISIONS (leader vs other callouts' text and leaders)")
    print("-" * 72)
    callout_issues = check_callouts(args.svg)
    if not callout_issues:
        print("  No callout cross-collisions found!")
    else:
        for issue in callout_issues:
            print(f"  - {issue}")

    # summary
    total_prox = len(prox)
    print(f"\n{'=' * 72}")
    ign_note = f" ({ignored} ignored)" if ignored else ""
    # classification breakdown
    if overlaps:
        cls_counts = {}
        for _, _, _, _, _, cls in overlaps:
            cls_counts[cls] = cls_counts.get(cls, 0) + 1
        cls_parts = [
            f"{cls_counts.get(c, 0)} {c}" for c in CLASS_ORDER if cls_counts.get(c, 0) > 0
        ]
        cls_summary = f" [{', '.join(cls_parts)}]"
    else:
        cls_summary = ""
    print(
        f"SUMMARY: {shown} overlaps{ign_note}{cls_summary}, {total_prox} tight proximities, "
        f"{len(spacing_issues)} spacing violations, {len(callout_issues)} callout cross-collisions, "
        f"{len(elements)} elements parsed"
    )

    # handle inject/strip bounds
    if args.strip_bounds or args.inject_bounds:
        with open(args.svg, "r") as f:
            svg_content = f.read()

        # always strip existing overlay first
        svg_content = re.sub(
            r"\s*<!-- === VERIFICATION:.*?</g>\s*", "\n", svg_content, flags=re.DOTALL
        )

        if args.inject_bounds:
            dividers = [e for e in elements if e.role == "divider"]
            overlay = generate_bounds_overlay(elements, dividers)
            svg_content = svg_content.replace("</svg>", f"\n{overlay}\n\n</svg>")
            print(f"\nInjected bounding box overlay into {args.svg}")
        else:
            print(f"\nStripped bounding box overlay from {args.svg}")

        with open(args.svg, "w") as f:
            f.write(svg_content)


if __name__ == "__main__":
    main()
