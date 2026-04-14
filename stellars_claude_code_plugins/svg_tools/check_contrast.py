"""SVG contrast checker using WCAG 2.1 relative luminance.

Two checks run in light + dark mode:

1. **Text contrast** (WCAG SC 1.4.3): every <text> element vs its
   resolved background (containing rect/path/document bg).

2. **Object contrast** (WCAG SC 1.4.11 non-text): every filled shape
   (rect, path, circle, ellipse, polygon) vs the document background.
   A shape passes if its fill OR stroke reaches the 3:1 threshold,
   so cards with near-transparent fills but strong strokes still pass.

Text WCAG thresholds:
  - AA normal text (< 18px or < 14px bold): 4.5:1
  - AA large text  (>= 18px or >= 14px bold): 3.0:1
  - AAA normal text: 7.0:1
  - AAA large text:  4.5:1

Object WCAG threshold (non-text): 3:1 (max of fill or stroke contrast).

Usage:
    python check_contrast.py --svg path/to/file.svg
    python check_contrast.py --svg file.svg --level AAA
    python check_contrast.py --svg file.svg --dark-bg "#272b31"
    python check_contrast.py --svg file.svg --show-all
    python check_contrast.py --svg file.svg --skip-objects
    python check_contrast.py --svg file.svg --object-min-area 1200
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Colour utilities
# ---------------------------------------------------------------------------

def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert #RRGGBB or #RGB to (r, g, b) integers."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.1 relative luminance from sRGB values (0-255)."""
    def linearize(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(lum1: float, lum2: float) -> float:
    """WCAG contrast ratio from two relative luminance values."""
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    return (lighter + 0.05) / (darker + 0.05)


def is_large_text(font_size: float, font_weight: str) -> bool:
    """WCAG large text: >= 18px normal or >= 14px bold."""
    is_bold = font_weight in ("600", "700", "bold")
    return font_size >= 18 or (is_bold and font_size >= 14)


def blend_over(fg_hex: str, opacity: float, base_hex: str) -> str:
    """Alpha-composite fg colour at opacity over base colour."""
    r, g, b = hex_to_rgb(fg_hex)
    br, bg_, bb = hex_to_rgb(base_hex)
    out_r = round(r * opacity + br * (1 - opacity))
    out_g = round(g * opacity + bg_ * (1 - opacity))
    out_b = round(b * opacity + bb * (1 - opacity))
    return f"#{out_r:02x}{out_g:02x}{out_b:02x}"


# ---------------------------------------------------------------------------
# Named CSS colours (subset used in SVGs)
# ---------------------------------------------------------------------------

CSS_COLORS = {
    "white": "#ffffff", "black": "#000000", "red": "#ff0000",
    "green": "#008000", "blue": "#0000ff", "yellow": "#ffff00",
    "magenta": "#ff00ff", "cyan": "#00ffff", "orange": "#ffa500",
    "gray": "#808080", "grey": "#808080", "lime": "#00ff00",
    "none": None, "transparent": None,
}


def resolve_color(color_str: str) -> str | None:
    """Resolve a colour string to #RRGGBB or None."""
    if not color_str:
        return None
    color_str = color_str.strip().lower()
    if color_str in ("none", "transparent", ""):
        return None
    if color_str in CSS_COLORS:
        return CSS_COLORS[color_str]
    if color_str.startswith("#"):
        return color_str
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", color_str)
    if m:
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


# ---------------------------------------------------------------------------
# CSS class colour resolver
# ---------------------------------------------------------------------------

def parse_css_classes(style_text: str) -> dict[str, str]:
    """Extract .class { fill: #hex; } mappings from <style> block (light mode only)."""
    mappings = {}
    clean = _strip_media_blocks(style_text)
    for m in re.finditer(r"\.(\w[\w-]*)\s*\{\s*fill:\s*(#[0-9a-fA-F]{3,6})\s*;?\s*\}", clean):
        mappings[m.group(1)] = m.group(2)
    return mappings


def _strip_media_blocks(text: str) -> str:
    """Remove all @media { ... } blocks including nested braces."""
    result = []
    i = 0
    while i < len(text):
        at_pos = text.find("@media", i)
        if at_pos == -1:
            result.append(text[i:])
            break
        result.append(text[i:at_pos])
        brace_pos = text.find("{", at_pos)
        if brace_pos == -1:
            break
        depth = 1
        j = brace_pos + 1
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        i = j
    return "".join(result)


def parse_dark_classes(style_text: str) -> dict[str, str]:
    """Extract dark mode .class { fill: #hex; } mappings from @media block."""
    mappings = {}
    at_pos = style_text.find("@media")
    if at_pos == -1:
        return mappings
    brace_pos = style_text.find("{", at_pos)
    if brace_pos == -1:
        return mappings
    depth = 1
    j = brace_pos + 1
    while j < len(style_text) and depth > 0:
        if style_text[j] == "{":
            depth += 1
        elif style_text[j] == "}":
            depth -= 1
        j += 1
    block = style_text[brace_pos + 1:j - 1]
    for m in re.finditer(r"\.(\w[\w-]*)\s*\{\s*fill:\s*(#[0-9a-fA-F]{3,6})\s*;?\s*\}", block):
        mappings[m.group(1)] = m.group(2)
    return mappings


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TextElement:
    content: str
    fill: str
    font_size: float
    font_weight: str
    x: float
    y: float
    css_class: str
    text_anchor: str = "start"


@dataclass
class Background:
    label: str
    fill: str
    opacity: float
    x: float
    y: float
    w: float
    h: float


@dataclass
class ContrastResult:
    text: TextElement
    background: Background
    effective_bg: str  # resolved bg hex after blending
    ratio: float
    aa_pass: bool
    aaa_pass: bool
    large: bool
    mode: str


@dataclass
class Shape:
    """A filled shape (card, panel, icon) checked against the document bg."""
    tag: str                        # rect/path/circle/ellipse/polygon
    fill: str | None                # resolved hex or None
    fill_opacity: float
    fill_class: str
    stroke: str | None              # resolved hex or None
    stroke_opacity: float
    stroke_width: float
    stroke_class: str
    x: float
    y: float
    w: float
    h: float
    label: str


@dataclass
class ObjectContrastResult:
    shape: Shape
    fill_ratio: float | None        # None if shape has no visible fill
    stroke_ratio: float | None      # None if shape has no visible stroke
    effective_bg: str
    fill_used: str | None           # blended fill hex used for ratio
    stroke_used: str | None         # stroke hex used for ratio
    threshold: float                # 3.0 for non-text
    passed: bool                    # max(fill, stroke) >= threshold
    mode: str                       # "light" or "dark"


NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# SVG parser
# ---------------------------------------------------------------------------

def parse_svg_for_contrast(filepath: str) -> tuple[list[TextElement], list[Background], dict[str, str], dict[str, str]]:
    """Parse SVG and extract text elements and background regions."""
    tree = ET.parse(filepath)
    root = tree.getroot()

    texts: list[TextElement] = []
    backgrounds: list[Background] = []
    light_classes: dict[str, str] = {}
    dark_classes: dict[str, str] = {}

    for child in root:
        tag = child.tag.replace(f"{{{NS}}}", "")
        if tag == "style":
            style_text = child.text or ""
            light_classes = parse_css_classes(style_text)
            dark_classes = parse_dark_classes(style_text)

    # Walk the full element tree (not just direct children) to find
    # text, rect, and path elements inside nested <g> groups.
    for child in root.iter():
        tag = child.tag.replace(f"{{{NS}}}", "")

        if tag == "text":
            x = float(child.get("x", "0"))
            y = float(child.get("y", "0"))
            fs = float(child.get("font-size", "10"))
            fw = child.get("font-weight", "normal")
            content = child.text or ""
            fill_attr = child.get("fill", "")
            css_class = child.get("class", "")
            text_anchor = child.get("text-anchor", "start")

            fill_hex = resolve_color(fill_attr) if fill_attr else None
            if not fill_hex and css_class and css_class in light_classes:
                fill_hex = light_classes[css_class]
            if not fill_hex:
                fill_hex = "#000000"

            texts.append(TextElement(
                content=content, fill=fill_hex, font_size=fs,
                font_weight=fw, x=x, y=y, css_class=css_class,
                text_anchor=text_anchor
            ))

        elif tag == "rect":
            x = float(child.get("x", "0"))
            y = float(child.get("y", "0"))
            w = float(child.get("width", "0"))
            h = float(child.get("height", "0"))
            fill = child.get("fill", "")
            opacity_str = child.get("opacity", "1")
            fill_opacity_str = child.get("fill-opacity", "")

            fill_hex = resolve_color(fill)
            if not fill_hex:
                continue

            opacity = float(opacity_str) if opacity_str else 1.0
            if fill_opacity_str:
                opacity = float(fill_opacity_str)

            label = f"rect {w:.0f}x{h:.0f}"
            if w >= 780:
                label = f"bg-strip {fill}"

            backgrounds.append(Background(
                label=label, fill=fill_hex, opacity=opacity,
                x=x, y=y, w=w, h=h
            ))

        elif tag == "path":
            d = child.get("d", "")
            fill = child.get("fill", "")
            opacity_str = child.get("opacity", "1")
            fill_opacity_str = child.get("fill-opacity", "")

            fill_hex = resolve_color(fill)
            if not fill_hex or fill == "none":
                continue

            opacity = float(opacity_str) if opacity_str else 1.0
            if fill_opacity_str:
                opacity = float(fill_opacity_str)

            bbox = _parse_path_bbox(d)
            if bbox is not None:
                min_x, min_y, w, h = bbox
                backgrounds.append(Background(
                    label=f"path-fill {fill}",
                    fill=fill_hex, opacity=opacity,
                    x=min_x, y=min_y, w=w, h=h
                ))

    return texts, backgrounds, light_classes, dark_classes


def estimate_text_bbox(text: TextElement) -> tuple[float, float, float, float]:
    """Estimate text bounding box as (x_left, y_top, width, height).

    Uses approximate character width = font_size * 0.6 for normal weight,
    font_size * 0.65 for bold. Height = font_size.
    Adjusts x based on text-anchor (start/middle/end).
    """
    is_bold = text.font_weight in ("600", "700", "bold")
    char_w = text.font_size * (0.65 if is_bold else 0.6)
    est_width = len(text.content) * char_w
    y_top = text.y - text.font_size * 0.85  # baseline to top

    x_left = text.x
    if text.text_anchor == "middle":
        x_left = text.x - est_width / 2
    elif text.text_anchor == "end":
        x_left = text.x - est_width

    return x_left, y_top, est_width, text.font_size


def bbox_overlaps(ax: float, ay: float, aw: float, ah: float,
                  bx: float, by: float, bw: float, bh: float) -> bool:
    """Check if two axis-aligned bounding boxes overlap."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def find_background_for_text(text: TextElement, backgrounds: list[Background]) -> Background | None:
    """Find the most specific (smallest) background that overlaps the text.

    Uses bounding-box overlap rather than point containment so text
    partially overlapping a filled rect is still detected.
    """
    tx, ty, tw, th = estimate_text_bbox(text)
    candidates = []
    for bg in backgrounds:
        if bbox_overlaps(tx, ty, tw, th, bg.x, bg.y, bg.w, bg.h):
            candidates.append(bg)
    if not candidates:
        return None
    candidates.sort(key=lambda b: b.w * b.h)
    return candidates[0]


# ---------------------------------------------------------------------------
# Shape parser (for object contrast)
# ---------------------------------------------------------------------------

_PATH_CMD_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)")
_PATH_NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")

# Number of coords each path command consumes per repeat. For Bezier and arc
# commands we only sample the segment endpoint, not the control points - this
# gives a tight bbox for the visible shape on every example we ship.
_CMD_STRIDE = {
    "M": 2, "L": 2, "T": 2,
    "H": 1, "V": 1,
    "C": 6, "S": 4, "Q": 4,
    "A": 7,
}


def _parse_path_bbox(d: str) -> tuple[float, float, float, float] | None:
    """Compute axis-aligned bbox of an SVG path with command awareness.

    Walks the d attribute one command at a time, tracking the current point.
    Handles relative commands, H/V single-coordinate moves, and the multi-
    coordinate Bezier/arc forms by sampling segment endpoints. Loose for
    curves that bow outside their endpoints, but exact for the rect/rounded-
    rect paths used in our infographics.
    """
    if not d:
        return None

    cx = cy = 0.0
    start_x = start_y = 0.0
    xs: list[float] = []
    ys: list[float] = []

    for match in _PATH_CMD_RE.finditer(d):
        cmd = match.group(1)
        if cmd in ("Z", "z"):
            cx, cy = start_x, start_y
            xs.append(cx)
            ys.append(cy)
            continue

        nums = [float(v) for v in _PATH_NUM_RE.findall(match.group(2))]
        cmd_upper = cmd.upper()
        is_rel = cmd.islower()
        stride = _CMD_STRIDE.get(cmd_upper, 2)
        if not nums:
            continue

        i = 0
        first = True
        while i + stride <= len(nums):
            chunk = nums[i:i + stride]
            i += stride

            if cmd_upper == "M":
                nx, ny = chunk
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny
                if first:
                    start_x, start_y = cx, cy
                # Subsequent pairs after the first M are implicit L
                first = False
            elif cmd_upper in ("L", "T"):
                nx, ny = chunk
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny
            elif cmd_upper == "H":
                nx = chunk[0]
                if is_rel:
                    nx += cx
                cx = nx
            elif cmd_upper == "V":
                ny = chunk[0]
                if is_rel:
                    ny += cy
                cy = ny
            elif cmd_upper == "C":
                nx, ny = chunk[4], chunk[5]
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny
            elif cmd_upper == "S":
                nx, ny = chunk[2], chunk[3]
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny
            elif cmd_upper == "Q":
                nx, ny = chunk[2], chunk[3]
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny
            elif cmd_upper == "A":
                nx, ny = chunk[5], chunk[6]
                if is_rel:
                    nx += cx
                    ny += cy
                cx, cy = nx, ny

            xs.append(cx)
            ys.append(cy)

    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _parse_polygon_bbox(points: str) -> tuple[float, float, float, float] | None:
    """Compute bbox from a polygon points attribute."""
    nums = [float(v) for v in re.findall(r"[-+]?\d*\.?\d+", points)]
    if len(nums) < 4:
        return None
    xs = nums[0::2]
    ys = nums[1::2]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _get_canvas_size(root: ET.Element) -> tuple[float, float]:
    """Extract canvas (width, height) from viewBox or width/height attrs."""
    vb = root.get("viewBox")
    if vb:
        parts = re.split(r"[\s,]+", vb.strip())
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])
    w = root.get("width", "0").rstrip("px")
    h = root.get("height", "0").rstrip("px")
    try:
        return float(w), float(h)
    except ValueError:
        return 0.0, 0.0


def parse_svg_shapes(filepath: str) -> tuple[list[Shape], dict[str, str], dict[str, str], float, float]:
    """Parse SVG and extract filled shapes plus CSS class lookups.

    Returns (shapes, light_classes, dark_classes, canvas_w, canvas_h).
    """
    tree = ET.parse(filepath)
    root = tree.getroot()

    canvas_w, canvas_h = _get_canvas_size(root)

    light_classes: dict[str, str] = {}
    dark_classes: dict[str, str] = {}
    for child in root:
        tag = child.tag.replace(f"{{{NS}}}", "")
        if tag == "style":
            style_text = child.text or ""
            light_classes = parse_css_classes(style_text)
            dark_classes = parse_dark_classes(style_text)

    shapes: list[Shape] = []

    for child in root.iter():
        tag = child.tag.replace(f"{{{NS}}}", "")
        if tag not in ("rect", "path", "circle", "ellipse", "polygon"):
            continue

        # bbox extraction per tag
        bbox: tuple[float, float, float, float] | None = None
        if tag == "rect":
            bbox = (
                float(child.get("x", "0")),
                float(child.get("y", "0")),
                float(child.get("width", "0")),
                float(child.get("height", "0")),
            )
        elif tag == "path":
            bbox = _parse_path_bbox(child.get("d", ""))
        elif tag == "circle":
            cx = float(child.get("cx", "0"))
            cy = float(child.get("cy", "0"))
            r = float(child.get("r", "0"))
            bbox = (cx - r, cy - r, 2 * r, 2 * r)
        elif tag == "ellipse":
            cx = float(child.get("cx", "0"))
            cy = float(child.get("cy", "0"))
            rx = float(child.get("rx", "0"))
            ry = float(child.get("ry", "0"))
            bbox = (cx - rx, cy - ry, 2 * rx, 2 * ry)
        elif tag == "polygon":
            bbox = _parse_polygon_bbox(child.get("points", ""))

        if bbox is None or bbox[2] <= 0 or bbox[3] <= 0:
            continue
        x, y, w, h = bbox

        # fill resolution
        css_class = child.get("class", "")
        fill_attr = child.get("fill", "")
        fill_hex = resolve_color(fill_attr) if fill_attr else None
        fill_class_used = ""
        if not fill_hex and not fill_attr and css_class and css_class in light_classes:
            # only inherit class fill when no explicit fill attr present
            fill_hex = light_classes[css_class]
            fill_class_used = css_class

        opacity = float(child.get("opacity", "1") or 1.0)
        fill_op_str = child.get("fill-opacity", "")
        fill_opacity = float(fill_op_str) if fill_op_str else opacity

        # stroke resolution
        stroke_attr = child.get("stroke", "")
        stroke_hex = resolve_color(stroke_attr) if stroke_attr else None
        stroke_class_used = ""
        if not stroke_hex and not stroke_attr and css_class and css_class in light_classes:
            stroke_hex = None  # we don't assume class targets stroke
        stroke_op_str = child.get("stroke-opacity", "")
        stroke_opacity = float(stroke_op_str) if stroke_op_str else opacity
        stroke_width = float(child.get("stroke-width", "0") or 0)

        if not fill_hex and not stroke_hex:
            continue

        shapes.append(Shape(
            tag=tag,
            fill=fill_hex,
            fill_opacity=fill_opacity,
            fill_class=fill_class_used,
            stroke=stroke_hex,
            stroke_opacity=stroke_opacity,
            stroke_width=stroke_width,
            stroke_class=stroke_class_used,
            x=x, y=y, w=w, h=h,
            label=f"{tag} {w:.0f}x{h:.0f}",
        ))

    return _merge_paired_shapes(shapes), light_classes, dark_classes, canvas_w, canvas_h


def _merge_paired_shapes(shapes: list[Shape]) -> list[Shape]:
    """Merge sibling shapes sharing the same geometry into one logical shape.

    Infographics often use two elements for the same card:
      <path d="..." fill="#00a6ff" fill-opacity="0.04"/>
      <path d="..." fill="none" stroke="#00a6ff" stroke-width="1"/>
    The fill alone is near-invisible but the stroke makes the card visible.
    Treating them as one shape lets the stroke contrast count for the card.
    """
    by_geom: dict[tuple, list[int]] = {}
    for idx, s in enumerate(shapes):
        key = (s.tag, round(s.x, 1), round(s.y, 1), round(s.w, 1), round(s.h, 1))
        by_geom.setdefault(key, []).append(idx)

    merged: list[Shape] = []
    consumed: set[int] = set()
    for indices in by_geom.values():
        if len(indices) == 1:
            merged.append(shapes[indices[0]])
            consumed.add(indices[0])
            continue

        base = shapes[indices[0]]
        merged_shape = Shape(**base.__dict__)
        for j in indices[1:]:
            other = shapes[j]
            if (merged_shape.fill is None or merged_shape.fill_opacity == 0) and other.fill is not None:
                merged_shape.fill = other.fill
                merged_shape.fill_opacity = other.fill_opacity
                merged_shape.fill_class = other.fill_class
            if (merged_shape.stroke is None or merged_shape.stroke_width == 0) and other.stroke is not None:
                merged_shape.stroke = other.stroke
                merged_shape.stroke_opacity = other.stroke_opacity
                merged_shape.stroke_width = other.stroke_width
                merged_shape.stroke_class = other.stroke_class
        merged.append(merged_shape)
        consumed.update(indices)

    return merged


# ---------------------------------------------------------------------------
# Object contrast checking (WCAG SC 1.4.11 non-text)
# ---------------------------------------------------------------------------

OBJECT_THRESHOLD = 3.0


def _shape_is_doc_background(shape: Shape, canvas_w: float, canvas_h: float) -> bool:
    """A shape that fills >=80% of the canvas is treated as the doc bg."""
    if canvas_w <= 0 or canvas_h <= 0:
        return False
    canvas_area = canvas_w * canvas_h
    if canvas_area <= 0:
        return False
    return (shape.w * shape.h) / canvas_area >= 0.8


def _resolve_dark_color(hex_color: str | None, css_class: str,
                       dark_classes: dict[str, str]) -> str | None:
    """Return the dark-mode equivalent of a colour, or the original."""
    if css_class and css_class in dark_classes:
        return dark_classes[css_class]
    return hex_color


def _check_one_shape(shape: Shape, doc_bg: str, mode: str,
                     dark_classes: dict[str, str]) -> ObjectContrastResult:
    """Compute fill+stroke contrast for one shape vs the document bg."""
    if mode == "dark":
        fill_hex = _resolve_dark_color(shape.fill, shape.fill_class, dark_classes)
        stroke_hex = _resolve_dark_color(shape.stroke, shape.stroke_class, dark_classes)
    else:
        fill_hex = shape.fill
        stroke_hex = shape.stroke

    bg_lum = relative_luminance(*hex_to_rgb(doc_bg))

    fill_ratio: float | None = None
    fill_used: str | None = None
    if fill_hex and shape.fill_opacity > 0.0:
        if shape.fill_opacity < 1.0:
            blended = blend_over(fill_hex, shape.fill_opacity, doc_bg)
        else:
            blended = fill_hex
        fill_used = blended
        fill_ratio = contrast_ratio(
            relative_luminance(*hex_to_rgb(blended)), bg_lum
        )

    stroke_ratio: float | None = None
    stroke_used: str | None = None
    if stroke_hex and shape.stroke_width > 0 and shape.stroke_opacity > 0.0:
        if shape.stroke_opacity < 1.0:
            blended_stroke = blend_over(stroke_hex, shape.stroke_opacity, doc_bg)
        else:
            blended_stroke = stroke_hex
        stroke_used = blended_stroke
        stroke_ratio = contrast_ratio(
            relative_luminance(*hex_to_rgb(blended_stroke)), bg_lum
        )

    candidates = [r for r in (fill_ratio, stroke_ratio) if r is not None]
    best = max(candidates) if candidates else 0.0
    passed = best >= OBJECT_THRESHOLD

    return ObjectContrastResult(
        shape=shape,
        fill_ratio=fill_ratio,
        stroke_ratio=stroke_ratio,
        effective_bg=doc_bg,
        fill_used=fill_used,
        stroke_used=stroke_used,
        threshold=OBJECT_THRESHOLD,
        passed=passed,
        mode=mode,
    )


def check_object_contrasts(
    shapes: list[Shape],
    dark_classes: dict[str, str],
    canvas_w: float,
    canvas_h: float,
    dark_doc_bg: str = "#1e1e1e",
    light_doc_bg: str = "#ffffff",
    min_area: float = 800.0,
    min_dimension: float = 20.0,
) -> list[ObjectContrastResult]:
    """Check every meaningful shape against the document bg in both modes.

    Filters: skips shapes that are the document background (>=80% canvas),
    shapes smaller than min_area px², and shapes with min(w,h) < min_dimension
    (these are typically thin accent bars or decorative dividers).
    """
    results: list[ObjectContrastResult] = []
    for shape in shapes:
        if _shape_is_doc_background(shape, canvas_w, canvas_h):
            continue
        if shape.w * shape.h < min_area:
            continue
        if min(shape.w, shape.h) < min_dimension:
            continue
        results.append(_check_one_shape(shape, light_doc_bg, "light", dark_classes))
        results.append(_check_one_shape(shape, dark_doc_bg, "dark", dark_classes))
    return results


# ---------------------------------------------------------------------------
# Contrast checking
# ---------------------------------------------------------------------------

def resolve_effective_bg(bg: Background | None, doc_bg: str) -> str:
    """Resolve the effective background colour by blending with document bg."""
    if bg is None:
        return doc_bg
    if bg.opacity < 1.0:
        return blend_over(bg.fill, bg.opacity, doc_bg)
    return bg.fill


def build_class_lookup(light_classes: dict[str, str]) -> dict[str, list[str]]:
    """Build reverse lookup: normalised hex -> list of class names."""
    lookup: dict[str, list[str]] = {}
    for cls, hex_val in light_classes.items():
        key = hex_val.lower()
        lookup.setdefault(key, []).append(cls)
    return lookup


def check_all_contrasts(
    texts: list[TextElement],
    backgrounds: list[Background],
    light_classes: dict[str, str],
    dark_classes: dict[str, str],
    dark_doc_bg: str = "#1e1e1e",
) -> tuple[list[ContrastResult], list[str]]:
    """Check contrast for all text elements in both light and dark mode.

    Returns (results, hints) where hints are diagnostic messages about
    inline fills that match CSS class colours but don't use the class.
    """
    results = []
    hints: list[str] = []
    light_doc_bg = "#ffffff"
    fill_to_classes = build_class_lookup(light_classes)

    doc_bg_light = Background("document", light_doc_bg, 1.0, 0, 0, 9999, 9999)
    doc_bg_dark = Background("document", dark_doc_bg, 1.0, 0, 0, 9999, 9999)

    for text in texts:
        if not text.content.strip():
            continue

        large = is_large_text(text.font_size, text.font_weight)
        aa_threshold = 3.0 if large else 4.5
        aaa_threshold = 4.5 if large else 7.0

        bg = find_background_for_text(text, backgrounds)

        # --- Inline fill matches CSS class? ---
        if text.fill and not text.css_class:
            matching = fill_to_classes.get(text.fill.lower(), [])
            if matching:
                cls_name = matching[0]
                dark_alt = dark_classes.get(cls_name, "?")
                hints.append(
                    f"  \"{text.content[:40]}\" uses inline fill={text.fill} "
                    f"matching .{cls_name} - won't switch to {dark_alt} in dark mode"
                )

        # --- Light mode ---
        eff_bg = resolve_effective_bg(bg, light_doc_bg)
        text_lum = relative_luminance(*hex_to_rgb(text.fill))
        bg_lum = relative_luminance(*hex_to_rgb(eff_bg))
        ratio = contrast_ratio(text_lum, bg_lum)

        results.append(ContrastResult(
            text=text, background=bg or doc_bg_light,
            effective_bg=eff_bg, ratio=ratio,
            aa_pass=ratio >= aa_threshold,
            aaa_pass=ratio >= aaa_threshold,
            large=large, mode="light"
        ))

        # --- Dark mode ---
        # resolve text fill for dark mode
        dark_fill = None
        if text.css_class and text.css_class in dark_classes:
            dark_fill = dark_classes[text.css_class]
        elif text.fill and not text.css_class:
            # hardcoded fill stays the same in dark mode
            dark_fill = text.fill

        if dark_fill:
            dark_eff_bg = resolve_effective_bg(bg, dark_doc_bg)
            dark_text_lum = relative_luminance(*hex_to_rgb(dark_fill))
            dark_bg_lum = relative_luminance(*hex_to_rgb(dark_eff_bg))
            dark_ratio = contrast_ratio(dark_text_lum, dark_bg_lum)

            results.append(ContrastResult(
                text=TextElement(
                    content=text.content, fill=dark_fill,
                    font_size=text.font_size, font_weight=text.font_weight,
                    x=text.x, y=text.y, css_class=text.css_class
                ),
                background=bg or doc_bg_dark,
                effective_bg=dark_eff_bg, ratio=dark_ratio,
                aa_pass=dark_ratio >= aa_threshold,
                aaa_pass=dark_ratio >= aaa_threshold,
                large=large, mode="dark"
            ))

    return results, hints


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SVG contrast checker (WCAG 2.1)")
    parser.add_argument("--svg", required=True, help="SVG file to check")
    parser.add_argument("--level", choices=["AA", "AAA"], default="AA",
                        help="WCAG level for text checks (default: AA)")
    parser.add_argument("--dark-bg", default="#1e1e1e",
                        help="Document background colour for dark mode (default: #1e1e1e)")
    parser.add_argument("--show-all", action="store_true",
                        help="Show all elements including passing ones")
    parser.add_argument("--skip-objects", action="store_true",
                        help="Skip object (non-text) contrast checks")
    parser.add_argument("--object-min-area", type=float, default=800.0,
                        help="Minimum bbox area (px²) for object contrast checks (default: 800)")
    parser.add_argument("--object-min-dim", type=float, default=20.0,
                        help="Minimum bbox dimension (px) for object contrast checks (default: 20)")
    args = parser.parse_args()

    print(f"Contrast check: {args.svg}  (WCAG {args.level})")
    print(f"Document bg: light=#ffffff  dark={args.dark_bg}")
    print("=" * 72)

    texts, backgrounds, light_classes, dark_classes = parse_svg_for_contrast(args.svg)
    print(f"Found {len(texts)} text elements, {len(backgrounds)} background regions")

    if light_classes:
        print(f"\nCSS classes (light): {', '.join(f'.{k}={v}' for k, v in light_classes.items())}")
    if dark_classes:
        print(f"CSS classes (dark):  {', '.join(f'.{k}={v}' for k, v in dark_classes.items())}")

    results, hints = check_all_contrasts(texts, backgrounds, light_classes, dark_classes,
                                          dark_doc_bg=args.dark_bg)

    # Print inline-fill-matches-class hints
    if hints:
        print(f"\n{'=' * 72}")
        print("INLINE FILL MATCHES CSS CLASS (won't switch in dark mode)")
        print("-" * 72)
        for hint in hints:
            print(hint)

    light_results = [r for r in results if r.mode == "light"]
    dark_results = [r for r in results if r.mode == "dark"]

    check_aaa = args.level == "AAA"
    fails = 0
    warns = 0

    for mode_label, mode_results in [("LIGHT MODE", light_results), ("DARK MODE", dark_results)]:
        if not mode_results:
            continue

        print(f"\n{'=' * 72}")
        print(f"{mode_label}")
        print("-" * 72)

        for r in mode_results:
            passed = r.aaa_pass if check_aaa else r.aa_pass
            size_label = "large" if r.large else "normal"
            threshold = (4.5 if r.large else 7.0) if check_aaa else (3.0 if r.large else 4.5)

            if not passed:
                fails += 1
                marker = "FAIL"
            elif not r.aaa_pass and not check_aaa:
                warns += 1
                marker = "warn"
            else:
                marker = "pass"

            if not args.show_all and marker == "pass":
                continue

            content_preview = r.text.content[:40]
            bg_label = r.background.label
            if r.background.opacity < 1.0:
                bg_label += f" @{r.background.opacity:.0%}"

            class_note = f" .{r.text.css_class}" if r.text.css_class else ""

            print(f"  [{marker:4s}] {r.ratio:5.2f}:1 (need {threshold:.1f}:1) "
                  f"{size_label:6s} | \"{content_preview}\"")
            print(f"         text: {r.text.fill}{class_note}  "
                  f"({r.text.font_size:.0f}px/{r.text.font_weight})")
            print(f"         bg:   {r.effective_bg} <- {bg_label}")
            print()

    # ------------------------------------------------------------------
    # Object (non-text) contrast checks
    # ------------------------------------------------------------------
    object_fails = 0
    if not args.skip_objects:
        shapes, _, dark_classes_obj, canvas_w, canvas_h = parse_svg_shapes(args.svg)
        obj_results = check_object_contrasts(
            shapes,
            dark_classes_obj,
            canvas_w,
            canvas_h,
            dark_doc_bg=args.dark_bg,
            min_area=args.object_min_area,
            min_dimension=args.object_min_dim,
        )

        for mode_label, mode_name in [("LIGHT MODE", "light"), ("DARK MODE", "dark")]:
            mode_results = [r for r in obj_results if r.mode == mode_name]
            if not mode_results:
                continue

            print(f"\n{'=' * 72}")
            print(f"OBJECT CONTRAST - {mode_label} (WCAG SC 1.4.11, need >= 3.0:1)")
            print("-" * 72)

            for r in mode_results:
                marker = "pass" if r.passed else "FAIL"
                if not r.passed:
                    object_fails += 1
                if not args.show_all and r.passed:
                    continue

                fill_str = (
                    f"fill={r.fill_used} ratio={r.fill_ratio:.2f}:1"
                    if r.fill_ratio is not None else "fill=none"
                )
                stroke_str = (
                    f"stroke={r.stroke_used}@{r.shape.stroke_width:g}px ratio={r.stroke_ratio:.2f}:1"
                    if r.stroke_ratio is not None else "stroke=none"
                )

                print(f"  [{marker}] {r.shape.label} @ ({r.shape.x:.0f},{r.shape.y:.0f})")
                print(f"         {fill_str}")
                print(f"         {stroke_str}")
                print(f"         bg:   {r.effective_bg}")
                print()

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"{'=' * 72}")
    total = len(results)
    passed = total - fails - warns
    print(f"SUMMARY")
    print(f"  TEXT:    {total} checks, {passed} pass, {warns} AA-only, {fails} FAIL "
          f"(WCAG {args.level})")
    if not args.skip_objects:
        print(f"  OBJECTS: {object_fails} FAIL "
              "(WCAG SC 1.4.11, fill OR stroke must reach 3:1)")

    if hints:
        print(f"  {len(hints)} text element(s) use inline fills matching CSS classes "
              "(won't switch in dark mode).")
    if fails > 0:
        print(f"\n  {fails} text element(s) fail WCAG {args.level} minimum contrast.")
        print("  Fix: use a lighter/darker text colour, or change the background.")
    if object_fails > 0:
        print(f"\n  {object_fails} object(s) blend into the document background "
              "in light or dark mode.")
        print("  Fix: raise fill opacity, switch fill to a CSS class with dark-mode "
              "swap, or strengthen stroke.")


if __name__ == "__main__":
    main()
