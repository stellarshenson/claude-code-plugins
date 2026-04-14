"""SVG alignment, grid snapping, and topology checker.

Parses SVG elements, extracts coordinates, and checks alignment consistency:
- Vertical rhythm: text lines within groups use consistent y-increments
- Horizontal alignment: equivalent elements share x values
- Grid snapping: coordinates align to a configurable grid step
- Symmetry: mirrored panels have matching internal offsets
- Named groups: discovers <g id="..."> groups and computes bounding boxes
- Relationship matrix: spatial relationships between named groups
- Topology verification: compares actual layout against declared LAYOUT TOPOLOGY

Usage:
    python check_alignment.py --svg path/to/file.svg
    python check_alignment.py --svg file.svg --grid 5
    python check_alignment.py --svg file.svg --grid 10 --tolerance 1
"""

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"


@dataclass
class PositionedElement:
    tag: str
    x: float
    y: float
    width: float = 0
    height: float = 0
    font_size: float = 0
    text: str = ""
    css_class: str = ""
    idx: int = 0
    text_anchor: str = "start"


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

    def __repr__(self) -> str:
        return f"BBox({self.x:.0f},{self.y:.0f} {self.w:.0f}x{self.h:.0f})"


def parse_svg_elements(filepath: str) -> list[PositionedElement]:
    """Parse SVG and extract all positioned elements."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    elements: list[PositionedElement] = []
    idx = 0

    # Walk the full element tree (not just direct children) to find
    # elements inside nested <g> groups.
    for child in root.iter():
        tag = child.tag.replace(f"{{{NS}}}", "")

        if tag == "text":
            elements.append(
                PositionedElement(
                    tag="text",
                    x=float(child.get("x", "0")),
                    y=float(child.get("y", "0")),
                    font_size=float(child.get("font-size", "10")),
                    text=(child.text or "".join(t.text or "" for t in child) or "")[:50],
                    css_class=child.get("class", ""),
                    idx=idx,
                    text_anchor=child.get("text-anchor", "start"),
                )
            )

        elif tag == "rect":
            w = float(child.get("width", "0"))
            h = float(child.get("height", "0"))
            if w < 2 or h < 2:
                idx += 1
                continue
            elements.append(
                PositionedElement(
                    tag="rect",
                    x=float(child.get("x", "0")),
                    y=float(child.get("y", "0")),
                    width=w,
                    height=h,
                    idx=idx,
                )
            )

        elif tag == "line":
            elements.append(
                PositionedElement(
                    tag="line",
                    x=float(child.get("x1", "0")),
                    y=float(child.get("y1", "0")),
                    width=float(child.get("x2", "0")),  # store x2 as width
                    height=float(child.get("y2", "0")),  # store y2 as height
                    idx=idx,
                )
            )

        idx += 1

    return elements


def check_grid_snapping(
    elements: list[PositionedElement], grid: int, tolerance: int = 0
) -> list[str]:
    """Check if element coordinates snap to grid multiples."""
    issues = []
    for el in elements:
        x_rem = el.x % grid
        y_rem = el.y % grid

        x_off = min(x_rem, grid - x_rem) if x_rem else 0
        y_off = min(y_rem, grid - y_rem) if y_rem else 0

        off_grid = []
        if x_off > tolerance:
            off_grid.append(f"x={el.x} (off by {x_off}px)")
        if y_off > tolerance:
            off_grid.append(f"y={el.y} (off by {y_off}px)")

        if off_grid:
            label = f'"{el.text}"' if el.text else f"{el.tag} {el.width:.0f}x{el.height:.0f}"
            issues.append(
                f"  [{el.idx:3d}] {el.tag:5s} {label} - not on {grid}px grid: {', '.join(off_grid)}"
            )

    return issues


def check_text_vertical_rhythm(elements: list[PositionedElement]) -> list[str]:
    """Check that text elements have consistent vertical spacing."""
    texts = [e for e in elements if e.tag == "text"]
    if len(texts) < 3:
        return []

    issues = []
    # Group texts by x coordinate (same column)
    x_groups: dict[float, list[PositionedElement]] = {}
    for t in texts:
        # Round x to nearest 5px to group aligned texts
        key = round(t.x / 5) * 5
        x_groups.setdefault(key, []).append(t)

    for x_key, group in sorted(x_groups.items()):
        if len(group) < 3:
            continue
        group.sort(key=lambda t: t.y)
        deltas = [group[i + 1].y - group[i].y for i in range(len(group) - 1)]
        unique_deltas = set(round(d, 1) for d in deltas if d > 0)

        if len(unique_deltas) > 2:
            delta_str = ", ".join(f"{d:.0f}" for d in deltas if d > 0)
            issues.append(
                f"  x~{x_key:.0f}: {len(group)} texts with irregular y-spacing: [{delta_str}]px"
            )

    return issues


def check_x_alignment(elements: list[PositionedElement]) -> list[str]:
    """Find text elements with similar but not identical x values."""
    texts = [e for e in elements if e.tag == "text" and e.text_anchor == "start"]
    if len(texts) < 2:
        return []

    issues = []
    x_values = sorted(set(t.x for t in texts))

    for i in range(len(x_values) - 1):
        diff = x_values[i + 1] - x_values[i]
        if 0 < diff <= 4:
            texts_a = [t for t in texts if t.x == x_values[i]]
            texts_b = [t for t in texts if t.x == x_values[i + 1]]
            issues.append(
                f"  Near-miss x alignment: x={x_values[i]} ({len(texts_a)} texts) "
                f"vs x={x_values[i + 1]} ({len(texts_b)} texts) - {diff:.1f}px apart"
            )

    return issues


def check_rect_alignment(elements: list[PositionedElement]) -> list[str]:
    """Check that rects at similar y positions share coordinates."""
    rects = [e for e in elements if e.tag == "rect"]
    if len(rects) < 2:
        return []

    issues = []
    # Group rects by y
    y_groups: dict[float, list[PositionedElement]] = {}
    for r in rects:
        key = round(r.y / 5) * 5
        y_groups.setdefault(key, []).append(r)

    for y_key, group in sorted(y_groups.items()):
        if len(group) < 2:
            continue
        heights = set(r.height for r in group)
        if len(heights) > 1:
            h_str = ", ".join(f"{h:.0f}" for h in sorted(heights))
            issues.append(
                f"  y~{y_key:.0f}: {len(group)} rects with mismatched heights: [{h_str}]px"
            )

    return issues


def check_legend_consistency(elements: list[PositionedElement]) -> list[str]:
    """Check legend chip + text pairs for consistent spacing."""
    rects = [e for e in elements if e.tag == "rect"]
    texts = [e for e in elements if e.tag == "text"]

    # Find small rects (legend chips) - width 5-30, height 5-30
    chips = [r for r in rects if 5 <= r.width <= 30 and 5 <= r.height <= 30]
    if len(chips) < 2:
        return []

    issues = []
    # Check chips have consistent size
    sizes = set((r.width, r.height) for r in chips)
    if len(sizes) > 1:
        size_str = ", ".join(f"{w:.0f}x{h:.0f}" for w, h in sorted(sizes))
        issues.append(f"  Legend chips have inconsistent sizes: {size_str}")

    # Check spacing between chip rows
    chip_ys = sorted(set(r.y for r in chips))
    if len(chip_ys) >= 2:
        deltas = [chip_ys[i + 1] - chip_ys[i] for i in range(len(chip_ys) - 1)]
        unique = set(round(d, 1) for d in deltas)
        if len(unique) > 1:
            delta_str = ", ".join(f"{d:.0f}" for d in deltas)
            issues.append(f"  Legend row spacing inconsistent: [{delta_str}]px")

    # Check chip-to-text gap
    gaps = []
    for chip in chips:
        # Find text element just to the right and at similar y
        for t in texts:
            if (
                abs(t.y - (chip.y + chip.height)) < chip.height
                and t.x > chip.x
                and t.x < chip.x + chip.width + 40
            ):
                gaps.append(t.x - (chip.x + chip.width))
                break
    if len(gaps) >= 2:
        unique_gaps = set(round(g, 1) for g in gaps)
        if len(unique_gaps) > 1:
            gap_str = ", ".join(f"{g:.0f}" for g in gaps)
            issues.append(f"  Legend chip-to-text gaps inconsistent: [{gap_str}]px")

    return issues


# ============================================================
# Named Group Parsing and Topology Verification
# ============================================================


def _element_bbox(el: ET.Element, ns: str) -> BBox | None:
    """Compute bounding box for a single SVG element."""
    tag = el.tag.replace(f"{{{ns}}}", "")

    if tag == "rect":
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
        w = float(el.get("width", "0"))
        h = float(el.get("height", "0"))
        if w > 0 and h > 0:
            return BBox(x, y, w, h)

    elif tag == "text":
        x = float(el.get("x", "0"))
        y = float(el.get("y", "0"))
        fs = float(el.get("font-size", "10"))
        txt = el.text or "".join(t.text or "" for t in el) or ""
        is_bold = "bold" in (el.get("font-weight", "") or "")
        char_w = fs * (0.57 if is_bold else 0.53)
        text_w = len(txt) * char_w
        anchor = el.get("text-anchor", "start")
        if anchor == "middle":
            x -= text_w / 2
        elif anchor == "end":
            x -= text_w
        ascent = fs * 0.78
        return BBox(x, y - ascent, text_w, fs)

    elif tag == "line":
        x1 = float(el.get("x1", "0"))
        y1 = float(el.get("y1", "0"))
        x2 = float(el.get("x2", "0"))
        y2 = float(el.get("y2", "0"))
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        return BBox(min_x, min_y, max(max_x - min_x, 1), max(max_y - min_y, 1))

    elif tag == "circle":
        cx = float(el.get("cx", "0"))
        cy = float(el.get("cy", "0"))
        r = float(el.get("r", "0"))
        return BBox(cx - r, cy - r, 2 * r, 2 * r)

    elif tag == "path":
        d = el.get("d", "")
        return _path_bbox(d)

    elif tag == "polygon":
        points_str = el.get("points", "")
        coords = re.findall(r"[-+]?\d*\.?\d+", points_str)
        if len(coords) >= 4:
            xs = [float(coords[i]) for i in range(0, len(coords), 2)]
            ys = [float(coords[i]) for i in range(1, len(coords), 2)]
            return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    return None


def _path_bbox(d: str) -> BBox | None:
    """Compute bounding box from SVG path data string."""
    tokens = re.findall(r"[MmLlHhVvCcSsQqTtAaZz]|[-+]?\d*\.?\d+", d)
    if len(tokens) < 3:
        return None

    xs, ys = [], []
    cx, cy = 0.0, 0.0
    cmd = "M"
    i = 0

    while i < len(tokens):
        t = tokens[i]
        if t.isalpha() or t in ("Z", "z"):
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                continue
            continue

        val = float(t)

        if cmd == "M":
            cx, cy = val, float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
            cmd = "L"
        elif cmd == "m":
            cx += val
            cy += float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
            cmd = "l"
        elif cmd == "L":
            cx, cy = val, float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
        elif cmd == "l":
            cx += val
            cy += float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
        elif cmd == "H":
            cx = val
            xs.append(cx)
            ys.append(cy)
            i += 1
        elif cmd == "h":
            cx += val
            xs.append(cx)
            ys.append(cy)
            i += 1
        elif cmd == "V":
            cy = val
            xs.append(cx)
            ys.append(cy)
            i += 1
        elif cmd == "v":
            cy += val
            xs.append(cx)
            ys.append(cy)
            i += 1
        elif cmd == "C":
            for j in range(0, 6, 2):
                xs.append(float(tokens[i + j]))
                ys.append(float(tokens[i + j + 1]))
            cx, cy = float(tokens[i + 4]), float(tokens[i + 5])
            i += 6
        elif cmd == "c":
            for j in range(0, 6, 2):
                xs.append(cx + float(tokens[i + j]))
                ys.append(cy + float(tokens[i + j + 1]))
            cx += float(tokens[i + 4])
            cy += float(tokens[i + 5])
            i += 6
        elif cmd == "S":
            for j in range(0, 4, 2):
                xs.append(float(tokens[i + j]))
                ys.append(float(tokens[i + j + 1]))
            cx, cy = float(tokens[i + 2]), float(tokens[i + 3])
            i += 4
        elif cmd == "s":
            for j in range(0, 4, 2):
                xs.append(cx + float(tokens[i + j]))
                ys.append(cy + float(tokens[i + j + 1]))
            cx += float(tokens[i + 2])
            cy += float(tokens[i + 3])
            i += 4
        elif cmd == "Q":
            for j in range(0, 4, 2):
                xs.append(float(tokens[i + j]))
                ys.append(float(tokens[i + j + 1]))
            cx, cy = float(tokens[i + 2]), float(tokens[i + 3])
            i += 4
        elif cmd == "q":
            for j in range(0, 4, 2):
                xs.append(cx + float(tokens[i + j]))
                ys.append(cy + float(tokens[i + j + 1]))
            cx += float(tokens[i + 2])
            cy += float(tokens[i + 3])
            i += 4
        elif cmd == "T":
            cx, cy = val, float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
        elif cmd == "t":
            cx += val
            cy += float(tokens[i + 1])
            xs.append(cx)
            ys.append(cy)
            i += 2
        elif cmd in ("A", "a"):
            # Arc: rx ry rotation large-arc sweep x y
            if i + 6 < len(tokens):
                if cmd == "A":
                    cx, cy = float(tokens[i + 5]), float(tokens[i + 6])
                else:
                    cx += float(tokens[i + 5])
                    cy += float(tokens[i + 6])
                xs.append(cx)
                ys.append(cy)
            i += 7
        else:
            i += 1

    if not xs or not ys:
        return None
    return BBox(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _merge_bboxes(boxes: list[BBox]) -> BBox:
    """Merge multiple bounding boxes into one enclosing box."""
    x1 = min(b.x for b in boxes)
    y1 = min(b.y for b in boxes)
    x2 = max(b.x2 for b in boxes)
    y2 = max(b.y2 for b in boxes)
    return BBox(x1, y1, x2 - x1, y2 - y1)


def _collect_child_bboxes(group: ET.Element, ns: str) -> list[BBox]:
    """Recursively collect bounding boxes from all children of a group."""
    boxes = []

    for child in group:
        tag = child.tag.replace(f"{{{ns}}}", "")

        if tag == "g":
            # Nested group - handle transform if present
            transform = child.get("transform", "")
            tx, ty = 0.0, 0.0
            scale = 1.0
            m = re.search(r"translate\(\s*([-\d.]+)[,\s]+([-\d.]+)\s*\)", transform)
            if m:
                tx, ty = float(m.group(1)), float(m.group(2))
            m = re.search(r"scale\(\s*([-\d.]+)", transform)
            if m:
                scale = float(m.group(1))
            child_boxes = _collect_child_bboxes(child, ns)
            for cb in child_boxes:
                boxes.append(
                    BBox(tx + cb.x * scale, ty + cb.y * scale, cb.w * scale, cb.h * scale)
                )
        elif tag == "defs":
            continue  # Skip defs (gradients, etc.)
        else:
            bb = _element_bbox(child, ns)
            if bb:
                boxes.append(bb)

    return boxes


def parse_named_groups(filepath: str) -> dict[str, BBox]:
    """Parse SVG and find all <g id="..."> groups, computing bounding boxes."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    groups: dict[str, BBox] = {}

    for child in root:
        tag = child.tag.replace(f"{{{NS}}}", "")
        if tag != "g":
            continue
        gid = child.get("id", "")
        if not gid or gid == "guide-grid":
            continue

        boxes = _collect_child_bboxes(child, NS)
        if boxes:
            groups[gid] = _merge_bboxes(boxes)

    return groups


def _y_overlap(a: BBox, b: BBox) -> float:
    """Compute vertical overlap ratio (0..1) relative to smaller height."""
    overlap = min(a.y2, b.y2) - max(a.y, b.y)
    if overlap <= 0:
        return 0.0
    return overlap / min(a.h, b.h) if min(a.h, b.h) > 0 else 0.0


def _x_overlap(a: BBox, b: BBox) -> float:
    """Compute horizontal overlap ratio (0..1) relative to smaller width."""
    overlap = min(a.x2, b.x2) - max(a.x, b.x)
    if overlap <= 0:
        return 0.0
    return overlap / min(a.w, b.w) if min(a.w, b.w) > 0 else 0.0


def _contains(outer: BBox, inner: BBox, tolerance: float = 5) -> bool:
    """Check if inner is contained within outer (with tolerance)."""
    return (
        outer.x - tolerance <= inner.x
        and outer.y - tolerance <= inner.y
        and outer.x2 + tolerance >= inner.x2
        and outer.y2 + tolerance >= inner.y2
    )


@dataclass
class Relationship:
    spatial: str  # left-of, right-of, above, below, overlapping, contained-in, contains
    gap: float  # distance in px (negative means overlap)
    h_aligned: bool  # y-ranges overlap significantly
    v_aligned: bool  # x-ranges overlap significantly


def build_relationship_matrix(groups: dict[str, BBox]) -> dict[tuple[str, str], Relationship]:
    """For each pair of named groups, compute spatial relationship."""
    matrix: dict[tuple[str, str], Relationship] = {}
    names = sorted(groups.keys())

    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            a, b = groups[name_a], groups[name_b]

            h_aligned = _y_overlap(a, b) > 0.3
            v_aligned = _x_overlap(a, b) > 0.3

            # Determine spatial relationship
            if _contains(a, b):
                spatial = "contains"
                gap = 0.0
            elif _contains(b, a):
                spatial = "contained-in"
                gap = 0.0
            elif a.x2 <= b.x:
                spatial = "left-of"
                gap = b.x - a.x2
            elif b.x2 <= a.x:
                spatial = "right-of"
                gap = a.x - b.x2
            elif a.y2 <= b.y:
                spatial = "above"
                gap = b.y - a.y2
            elif b.y2 <= a.y:
                spatial = "below"
                gap = a.y - b.y2
            else:
                spatial = "overlapping"
                # Compute overlap area
                ox = min(a.x2, b.x2) - max(a.x, b.x)
                oy = min(a.y2, b.y2) - max(a.y, b.y)
                gap = -(ox * oy)  # negative = overlap area

            matrix[(name_a, name_b)] = Relationship(spatial, gap, h_aligned, v_aligned)

    return matrix


@dataclass
class DeclaredRelationship:
    kind: (
        str  # h-stack, v-stack, contain, mirror, h-align, v-align, right-of, left-of, above, below
    )
    groups: list[str]
    raw: str  # original text


def parse_topology_comment(filepath: str) -> list[DeclaredRelationship]:
    """Extract LAYOUT TOPOLOGY comment and parse declared relationships."""
    with open(filepath, "r") as f:
        content = f.read()

    # Find LAYOUT TOPOLOGY comment block
    m = re.search(r"<!--\s*===\s*LAYOUT TOPOLOGY\s*===\s*(.*?)\s*===\s*-->", content, re.DOTALL)
    if not m:
        return []

    topo_text = m.group(1)
    declared: list[DeclaredRelationship] = []

    for line in topo_text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("==="):
            continue

        # Skip section headings (ALL CAPS lines without colon operators)
        if re.match(r"^[A-Z /()]+$", line):
            continue

        # h-stack: A, B, C
        m = re.match(r"(h-stack|v-stack|h-align|v-align|h-spacing|v-spacing)\s*:\s*(.+)", line)
        if m:
            kind = m.group(1)
            # Extract group names - handle parenthetical notes
            rest = re.sub(r"\(.*?\)", "", m.group(2)).strip()
            groups = [g.strip() for g in rest.split(",") if g.strip()]
            declared.append(DeclaredRelationship(kind, groups, line))
            continue

        # contain: A > B, C, D
        m = re.match(r"contain\s*:\s*(\S+)\s*>\s*(.+)", line)
        if m:
            outer = m.group(1).strip()
            inners = [g.strip() for g in m.group(2).split(",") if g.strip()]
            for inner in inners:
                declared.append(DeclaredRelationship("contain", [outer, inner], line))
            continue

        # mirror: A, B
        m = re.match(r"mirror\s*:\s*(.+)", line)
        if m:
            rest = re.sub(r"\(.*?\)", "", m.group(1)).strip()
            groups = [g.strip() for g in rest.split(",") if g.strip()]
            if len(groups) >= 2:
                declared.append(DeclaredRelationship("mirror", groups[:2], line))
            continue

        # Free-text relationships like "waveform header right of waveform hexagons"
        m = re.match(r"(\S+)\s+(right of|left of|above|below)\s+(\S+)", line)
        if m:
            kind_map = {
                "right of": "right-of",
                "left of": "left-of",
                "above": "above",
                "below": "below",
            }
            declared.append(
                DeclaredRelationship(kind_map[m.group(2)], [m.group(1), m.group(3)], line)
            )

    return declared


def verify_topology(
    groups: dict[str, BBox],
    matrix: dict[tuple[str, str], Relationship],
    declared: list[DeclaredRelationship],
) -> list[str]:
    """Compare actual matrix against declared topology relationships."""
    results: list[str] = []

    def _get_rel(a: str, b: str) -> Relationship | None:
        """Look up relationship, handling either key order."""
        if (a, b) in matrix:
            return matrix[(a, b)]
        if (b, a) in matrix:
            rel = matrix[(b, a)]
            # Invert spatial direction
            inverse = {
                "left-of": "right-of",
                "right-of": "left-of",
                "above": "below",
                "below": "above",
                "contains": "contained-in",
                "contained-in": "contains",
                "overlapping": "overlapping",
            }
            return Relationship(
                inverse.get(rel.spatial, rel.spatial), rel.gap, rel.h_aligned, rel.v_aligned
            )
        return None

    # Track which groups are referenced in topology
    topo_groups: set[str] = set()

    for decl in declared:
        for g in decl.groups:
            topo_groups.add(g)

        # Check if all referenced groups exist
        missing = [g for g in decl.groups if g not in groups]
        if missing:
            results.append(f"  [WARN] {decl.raw}")
            for mg in missing:
                results.append(f'         group "{mg}" not found in SVG')
            continue

        if decl.kind == "h-stack":
            # Groups should be left-to-right with small gaps
            if len(decl.groups) < 2:
                continue
            all_ok = True
            for j in range(len(decl.groups) - 1):
                a, b = decl.groups[j], decl.groups[j + 1]
                rel = _get_rel(a, b)
                if rel and rel.spatial != "left-of":
                    results.append(
                        f"  [FAIL] h-stack: {a}, {b} - actual: {rel.spatial} (gap {rel.gap:.0f}px)"
                    )
                    all_ok = False
            if all_ok:
                results.append(f"  [PASS] h-stack: {', '.join(decl.groups)}")

        elif decl.kind == "v-stack":
            if len(decl.groups) < 2:
                continue
            all_ok = True
            for j in range(len(decl.groups) - 1):
                a, b = decl.groups[j], decl.groups[j + 1]
                rel = _get_rel(a, b)
                if rel and rel.spatial not in ("above", "overlapping"):
                    results.append(
                        f"  [FAIL] v-stack: {a}, {b} - actual: {rel.spatial} (gap {rel.gap:.0f}px)"
                    )
                    all_ok = False
            if all_ok:
                results.append(f"  [PASS] v-stack: {', '.join(decl.groups)}")

        elif decl.kind == "contain":
            outer, inner = decl.groups[0], decl.groups[1]
            rel = _get_rel(outer, inner)
            if rel:
                if rel.spatial == "contains":
                    results.append(f"  [PASS] contain: {outer} > {inner}")
                else:
                    results.append(f"  [FAIL] contain: {outer} > {inner} - actual: {rel.spatial}")

        elif decl.kind == "mirror":
            a_name, b_name = decl.groups[0], decl.groups[1]
            a, b = groups[a_name], groups[b_name]
            w_diff = abs(a.w - b.w)
            h_diff = abs(a.h - b.h)
            size_ok = w_diff <= 5 and h_diff <= 5
            if size_ok:
                results.append(
                    f"  [PASS] mirror: {a_name}, {b_name} (size match, offset {b.y - a.y:+.0f}px y)"
                )
            else:
                results.append(
                    f"  [FAIL] mirror: {a_name}, {b_name} - "
                    f"size mismatch: {a.w:.0f}x{a.h:.0f} vs {b.w:.0f}x{b.h:.0f}"
                )

        elif decl.kind in ("h-align", "v-align"):
            if len(decl.groups) < 2:
                continue
            if decl.kind == "h-align":
                # All groups should have similar x ranges
                x_starts = [groups[g].x for g in decl.groups]
                spread = max(x_starts) - min(x_starts)
                if spread <= 10:
                    results.append(
                        f"  [PASS] h-align: {', '.join(decl.groups)} (x spread {spread:.0f}px)"
                    )
                else:
                    results.append(
                        f"  [FAIL] h-align: {', '.join(decl.groups)} - x spread {spread:.0f}px"
                    )
            else:
                y_starts = [groups[g].y for g in decl.groups]
                spread = max(y_starts) - min(y_starts)
                if spread <= 10:
                    results.append(
                        f"  [PASS] v-align: {', '.join(decl.groups)} (y spread {spread:.0f}px)"
                    )
                else:
                    results.append(
                        f"  [FAIL] v-align: {', '.join(decl.groups)} - y spread {spread:.0f}px"
                    )

        elif decl.kind in ("right-of", "left-of", "above", "below"):
            if len(decl.groups) >= 2:
                a, b = decl.groups[0], decl.groups[1]
                rel = _get_rel(a, b)
                if rel and rel.spatial == decl.kind:
                    results.append(f"  [PASS] {a} {decl.kind} {b} (gap {rel.gap:.0f}px)")
                elif rel:
                    results.append(f"  [FAIL] {a} {decl.kind} {b} - actual: {rel.spatial}")

    # Check for groups in SVG not referenced in topology
    svg_only = set(groups.keys()) - topo_groups
    if svg_only:
        for g in sorted(svg_only):
            results.append(f'  [INFO] group "{g}" in SVG but not referenced in topology')

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="SVG alignment, grid snapping, and topology checker"
    )
    parser.add_argument("--svg", required=True, help="SVG file to check")
    parser.add_argument("--grid", type=int, default=5, help="Grid step in px (default: 5)")
    parser.add_argument(
        "--tolerance", type=int, default=0, help="Tolerance for grid snapping in px (default: 0)"
    )
    args = parser.parse_args()

    print(f"Alignment check: {args.svg}  (grid={args.grid}px, tolerance={args.tolerance}px)")
    print("=" * 72)

    elements = parse_svg_elements(args.svg)
    texts = [e for e in elements if e.tag == "text"]
    rects = [e for e in elements if e.tag == "rect"]
    print(f"Found {len(texts)} text elements, {len(rects)} rects, {len(elements)} total")
    print()

    total_issues = 0

    # Grid snapping
    snap_issues = check_grid_snapping(elements, args.grid, args.tolerance)
    if snap_issues:
        print(f"GRID SNAPPING ({args.grid}px)")
        print("-" * 72)
        for issue in snap_issues:
            print(issue)
        print()
        total_issues += len(snap_issues)
    else:
        print(f"GRID SNAPPING: all elements on {args.grid}px grid")
        print()

    # Vertical rhythm
    rhythm_issues = check_text_vertical_rhythm(elements)
    if rhythm_issues:
        print("VERTICAL RHYTHM")
        print("-" * 72)
        for issue in rhythm_issues:
            print(issue)
        print()
        total_issues += len(rhythm_issues)

    # X alignment
    x_issues = check_x_alignment(elements)
    if x_issues:
        print("X ALIGNMENT")
        print("-" * 72)
        for issue in x_issues:
            print(issue)
        print()
        total_issues += len(x_issues)

    # Rect alignment
    rect_issues = check_rect_alignment(elements)
    if rect_issues:
        print("RECT ALIGNMENT")
        print("-" * 72)
        for issue in rect_issues:
            print(issue)
        print()
        total_issues += len(rect_issues)

    # Legend consistency
    legend_issues = check_legend_consistency(elements)
    if legend_issues:
        print("LEGEND CONSISTENCY")
        print("-" * 72)
        for issue in legend_issues:
            print(issue)
        print()
        total_issues += len(legend_issues)

    # Named groups and topology
    groups = parse_named_groups(args.svg)
    if groups:
        print("COMPONENT GROUPS")
        print("-" * 72)
        for gid, bbox in sorted(groups.items()):
            print(f"  {gid:24s} {bbox}")
        print()

        matrix = build_relationship_matrix(groups)
        # Show key relationships (skip trivial distant pairs)
        interesting = [
            (k, v)
            for k, v in matrix.items()
            if v.spatial in ("left-of", "right-of", "contains", "contained-in", "overlapping")
            or (v.spatial in ("above", "below") and v.gap < 50)
        ]
        if interesting:
            print("RELATIONSHIP MATRIX")
            print("-" * 72)
            for (a, b), rel in sorted(interesting, key=lambda x: x[0]):
                align_info = ""
                if rel.h_aligned:
                    align_info = ", h-aligned"
                if rel.v_aligned:
                    align_info += ", v-aligned"
                print(f"  {a:24s} | {rel.spatial}: {b} (gap {rel.gap:.0f}px{align_info})")
            print()

        declared = parse_topology_comment(args.svg)
        if declared:
            topo_results = verify_topology(groups, matrix, declared)
            if topo_results:
                print("TOPOLOGY VERIFICATION")
                print("-" * 72)
                for r in topo_results:
                    print(r)
                print()
                fails = sum(1 for r in topo_results if "[FAIL]" in r)
                warns = sum(1 for r in topo_results if "[WARN]" in r)
                total_issues += fails
                if fails:
                    print(f"  Topology: {fails} failures, {warns} warnings")
                    print()
        elif groups:
            print("TOPOLOGY: no LAYOUT TOPOLOGY comment found")
            print()

    # Summary
    print("=" * 72)
    if total_issues == 0:
        print("SUMMARY: no alignment issues found")
    else:
        print(f"SUMMARY: {total_issues} alignment issues found")


if __name__ == "__main__":
    main()
