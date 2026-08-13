"""SVG contrast checker using WCAG 2.1 relative luminance.

Two checks run in light + dark mode:

1. **Text contrast** (WCAG SC 1.4.3): every <text> element vs its
   resolved background (containing rect/path/document bg).

2. **Object contrast** (WCAG SC 1.4.11 non-text): every filled shape
   (rect, path, circle, ellipse, polygon) vs the document background.
   A shape passes if its fill OR stroke reaches the 3:1 threshold,
   so cards with near-transparent fills but strong strokes still pass.

Text WCAG thresholds (large-scale is 18pt / 14pt bold = 24px / 18.66px):
  - AA normal text (< 24px or < 18.66px bold): 4.5:1
  - AA large text  (>= 24px or >= 18.66px bold): 3.0:1
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

from dataclasses import dataclass
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from stellars_claude_code_plugins.svg_tools.check_css import (
    _SPEC_ATTR,
    _in_template,
    _length,
    _resolved_opacity,
    _rgba,
    build_render_model,
    merged_rules,
    parse_style_block,
    theme_paint,
)
from stellars_claude_code_plugins.svg_tools.check_css import (
    strip_important as _strip_important,
)

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
    """WCAG large text: >= 18pt normal or >= 14pt bold - 24px / 18.66px in SVG
    user units (1pt = 96/72 px). The boundary sat at 18px/14px for years while
    `_font_size` resolved every CSS-declared size to 10px, so nothing live
    reached the band it mis-judged; a correct resolver made 18-23.99px text
    live, and the spec holds it to 4.5:1 where the px boundary gave it 3.0:1."""
    is_bold = font_weight in ("600", "700", "bold")
    return font_size >= 24 or (is_bold and font_size >= 18.66)


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
    "white": "#ffffff",
    "black": "#000000",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "magenta": "#ff00ff",
    "cyan": "#00ffff",
    "orange": "#ffa500",
    "gray": "#808080",
    "grey": "#808080",
    "lime": "#00ff00",
    "none": None,
    "transparent": None,
}


def resolve_color(color_str: str | None) -> str | None:
    """Resolve a colour string to `#rrggbb`, or None when it is not a colour.

    Delegates the parse to `check_css._rgba`, the module that already reads
    3/4/6/8-digit hex, `rgb()` and `rgba()`. Two readers of different capability
    behind ONE cascade is how a legal 4-digit `#3a4c` - unreachable before the
    cascade widened to `#id` and element rules - reached `hex_to_rgb` and killed
    the whole contrast layer with `invalid literal for int()`. The local
    12-name keyword table stays: `check_css` deliberately has no colour
    dictionary, and dropping the names here would silently unmeasure them.
    """
    if not color_str:
        return None
    raw = color_str.strip().lower()
    if raw in CSS_COLORS:
        return CSS_COLORS[raw]
    rgba = _rgba(raw)
    if rgba is None:
        return None
    r, g, b, a = rgba
    # Fully transparent paints nothing; it is not a colour to score against.
    if a == 0:
        return None
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


# ---------------------------------------------------------------------------
# CSS class colour resolver
# ---------------------------------------------------------------------------


def parse_stylesheet(svg_text: str):
    """`(light_rules, dark_rules, light_fills, dark_fills)` for one document.

    ONE cascade, shared with `check_css`. The local trio this replaced
    (`parse_css_classes` / `parse_dark_classes` / `_strip_media_blocks`) was a
    SECOND, weaker cascade - and it gated the HARD tier, so the strictest
    verdicts in the gate ran on the loosest model. It matched only a rule body
    holding exactly one `fill: #hex`, took the FIRST `@media` block whether or
    not it was a dark query, read one `<style>` element, and knew nothing of
    `!important`, comments, grouped selectors, `#id` or element rules -
    `charts.py` marks every colour it emits `!important`, so none of them were
    visible to it. The shared cascade reads those values now; what it still
    does not give most chart selectors is a cascade KEY - 30 of the 42
    `_dark_mode_override_style` selectors are bare-element or compound shapes
    the parser drops by design - so that gap narrowed rather than closed.

    `*_rules` are the full `{selector: {property: value}}` maps the cascade
    resolves against; `*_fills` are the flat `{class: hex}` maps the report
    helpers use to answer "which classes paint this colour".
    """
    light_cls, dark_cls, _colors, meta = parse_style_block(svg_text)
    return (
        meta["light_rules"],
        meta["dark_rules"],
        class_fills(light_cls),
        class_fills(dark_cls),
    )


# SVG/CSS initial `font-size` is `medium` = 16px, not the 10 this module used to
# assume from a missing attribute.
_INITIAL_FONT_SIZE = 16.0


def _font_size(node, rules, own_paint, parent_of) -> float:
    """Resolved font-size in user units, with `%` and `em` against the PARENT.

    `_length` resolves `em` against a fixed 16 and `%` against a span it is not
    given, so `1.2em` under `<g font-size="12">` read as 19.2 (large text, 3.0:1
    threshold) where it renders at 14.4 (normal, 4.5:1) - a false PASS in the
    un-ackable tier - and `250%` collapsed to the fallback, a false FAIL.
    """
    parent = parent_of.get(id(node))
    inherited = (
        _font_size(parent, rules, own_paint, parent_of)
        if parent is not None
        else _INITIAL_FONT_SIZE
    )
    # The node's OWN declaration. `winning_paint` walks ancestors for an
    # inherited property and hands back their SPECIFIED value, so reading it
    # here multiplied the same `1.2em` by the parent's already-computed size
    # once per generation - 24px rendered read as 34.56 two levels down, which
    # crossed the large-text boundary and flipped a real AA failure to PASS.
    raw = _strip_important(own_paint(node, "font-size", rules)[1])
    if not raw:
        return inherited
    if raw.endswith("%"):
        try:
            return float(raw[:-1]) / 100.0 * inherited
        except ValueError:
            return inherited
    if raw.endswith("em"):
        try:
            return float(raw[:-2]) * inherited
        except ValueError:
            return inherited
    v = _length(raw, 0.0)
    # `None` is unparseable; `0.0` is a real declaration and stays 0.
    return inherited if v is None else v


def class_fills(classes: dict[str, dict]) -> dict[str, str]:
    """`{class name: fill hex}`, for reporting only - resolution goes through
    the cascade, which a flat class map cannot express."""
    out: dict[str, str] = {}
    for cls, props in classes.items():
        hex_val = resolve_color(_strip_important(props.get("fill", "")))
        if hex_val:
            out[cls] = hex_val
    return out


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TextElement:
    content: str
    fill: str | None  # resolved light-mode hex, None when unreadable
    font_size: float
    font_weight: str
    x: float
    y: float
    css_class: str
    text_anchor: str = "start"
    # Resolved at parse time through the same cascade, so the scorer never has
    # to re-derive it from a class map that cannot see `#id` or element rules.
    dark_fill: str | None = None
    # The raw declaration when it is not a colour this checker can read
    # (`var(--fg)`, `currentColor`, an unknown keyword). UNMEASURABLE IS NOT
    # CLEAN: it is reported, never scored against an invented value.
    unresolved: str | None = None
    # Same for the DARK declaration. `none`/`transparent` means the text renders
    # NOTHING in dark mode - a failure, not an unmeasurable - and a `var()` is
    # unmeasurable. Both are reported; a silent absent dark row read as PASS.
    dark_unresolved: str | None = None
    # The presentation attribute is what actually paints it - no rule reaches
    # it, so no media query can repaint it in dark mode. That, not "has no
    # class", is what the inline-fill hint is about: once fill resolved through
    # the cascade, `text.fill` held a value for class- and element-painted text
    # too, and the hint fired on text that has no inline fill at all.
    attribute_painted: bool = False
    # Rotated or translated: the raw x/y box is not where it renders, so it can
    # elect neither its own plate NOR the document ground. Substituting the page
    # colour is a guess, and this module forbids guessing at an unreadable fill
    # one branch below - it manufactured 15 findings on one shipped file, at
    # 1.95:1 against #ffffff, for labels sitting on a #0a1a24 card at 9.1:1.
    # UNMEASURABLE is the honest answer, and it still reaches the gate as HARD.
    displaced: bool = False


@dataclass
class Background:
    label: str
    fill: str
    opacity: float
    x: float
    y: float
    w: float
    h: float
    # The ground under `prefers-color-scheme: dark`. Without it the dark row
    # scored dark-mode text against the LIGHT plate - dormant while backgrounds
    # were read from attributes only and so rarely found at all, and firing on
    # every file the moment they resolved through the cascade.
    dark_fill: str | None = None
    # Resolved against the MERGED sheet. A single opacity blended the dark
    # ground at the light alpha; 137 corpus plates declare a different one.
    dark_opacity: float | None = None
    # The dark block DECLARED a ground and this checker cannot read it
    # (`var()`, `url()`, an unknown keyword). Distinct from "declared nothing",
    # where the light value correctly carries over: scoring the dark row on the
    # light plate is judging against the wrong theme, which the module forbids
    # one branch away for an unreadable text fill.
    dark_unreadable: bool = False
    # The dark block paints this plate `none`/`transparent`: under the dark
    # query it is no ground at all, and text on it falls through to the
    # document ground. Distinct from `dark_unreadable` - a value nobody can
    # measure - and conflating them blocked a legible document with a HARD.
    dark_paints_nothing: bool = False


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

    tag: str  # rect/path/circle/ellipse/polygon
    fill: str | None  # resolved hex or None
    fill_opacity: float
    fill_class: str
    stroke: str | None  # resolved hex or None
    stroke_opacity: float
    stroke_width: float
    stroke_class: str
    x: float
    y: float
    w: float
    h: float
    label: str
    # Resolved at parse time through the cascade, like TextElement's. The class
    # lookup this replaces could not swap a stroke at all.
    dark_fill: str | None = None
    dark_stroke: str | None = None
    # The dark ALPHA travels with the dark colour - resolved against the merged
    # sheet, so it carries the light value unless the dark block declares its
    # own. Blending the dark fill at the LIGHT opacity scored a 4%-wash plate
    # as solid: 1.06 FAIL on a document that renders 5.35 PASS.
    dark_fill_opacity: float | None = None
    dark_stroke_opacity: float | None = None


@dataclass
class ObjectContrastResult:
    shape: Shape
    fill_ratio: float | None  # None if shape has no visible fill
    stroke_ratio: float | None  # None if shape has no visible stroke
    effective_bg: str
    fill_used: str | None  # blended fill hex used for ratio
    stroke_used: str | None  # stroke hex used for ratio
    threshold: float  # 3.0 for non-text
    passed: bool  # max(fill, stroke) >= threshold
    mode: str  # "light" or "dark"


NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# SVG parser
# ---------------------------------------------------------------------------


def _geo(raw: str | None, span: float) -> float | None:
    """One geometry value in user units; 0.0 when the attribute is absent.

    `x="20 32 44"` is a legal per-glyph list - the first number anchors the
    element, the rest position glyphs. A bare `float()` raised on that and on
    `width="100%"`, and the gate's own drill-in command died on the traceback.
    """
    parts = (raw or "").split()
    return _length(parts[0], span) if parts else 0.0


def parse_svg_for_contrast(
    filepath: str,
) -> tuple[list[TextElement], list[Background], dict[str, str], dict[str, str]]:
    """Parse SVG and extract text elements and background regions."""
    svg_text = Path(filepath).read_text(encoding="utf-8", errors="replace")
    root = ET.fromstring(svg_text)

    texts: list[TextElement] = []
    backgrounds: list[Background] = []
    # From the whole document, not the first direct-child <style>: a composed
    # deck carries one <style> per merged panel, and reading one of them scored
    # every other panel's text against colours the checker had not seen.
    lrules, drules, light_classes, dark_classes = parse_stylesheet(svg_text)
    _nr, is_displaced, resolve_paint, winning_paint, parent_of, own_paint = build_render_model(
        root
    )
    # One merge for the whole document - rebuilding it per element cost 0.61s
    # of a 0.80s parse on a 10k-element file.
    mrules = merged_rules(lrules, drules)
    # Percentages resolve against the viewport; a document without a readable
    # viewBox gives them no span, and the element is skipped, never crashed on.
    try:
        vb = [float(v) for v in re.split(r"[,\s]+", (root.get("viewBox") or "").strip()) if v]
        canvas_w, canvas_h = (vb[2], vb[3]) if len(vb) == 4 else (0.0, 0.0)
    except ValueError:
        canvas_w = canvas_h = 0.0

    # Walk the full element tree (not just direct children) to find
    # text, rect, and path elements inside nested <g> groups.
    for child in root.iter():
        tag = child.tag.replace(f"{{{NS}}}", "")

        if tag == "text":
            # The guard its three sibling branches already carry. Without it a
            # <symbol> label was scored at raw coordinates against a fabricated
            # ground, and `display:none` text produced a HARD finding whose
            # message blamed a transform the element does not have.
            if _nr(child) or _in_template(child, parent_of):
                continue
            x = _geo(child.get("x"), canvas_w)
            y = _geo(child.get("y"), canvas_h)
            if x is None or y is None:
                continue
            # Through the cascade like the fill. Read off the attribute, 101
            # corpus texts declared in CSS were all scored as 10px normal - so
            # a 34px heading was held to the 4.5:1 normal threshold instead of
            # AA-large's 3.0, and `estimate_text_bbox` sized its box from the
            # same wrong number, which is what elects its background.
            fs = _font_size(child, lrules, own_paint, parent_of)
            fw = _strip_important(winning_paint(child, "font-weight", lrules)[1]) or "normal"
            content = child.text or ""
            css_class = child.get("class", "")
            text_anchor = child.get("text-anchor", "start")

            # Through the cascade, in BOTH themes at once. The class map this
            # replaced was wrong three ways at the same time: it tested the
            # whole `class` attribute for membership, so `class="card body"`
            # never matched anything; it let the presentation attribute beat the
            # class rule, which is the inverse of CSS; and when nothing resolved
            # it invented `#000000`, turning an unreadable paint into the
            # highest-contrast colour there is - a false PASS on exactly the
            # elements nobody had measured.
            paint = theme_paint(child, "fill", lrules, drules, winning_paint, merged=mrules)
            fill_hex = resolve_color(_strip_important(paint.light))
            dark_hex = resolve_color(_strip_important(paint.dark))
            # The node's OWN declaration, not the winner's: `winning_paint` can
            # return an ANCESTOR's attribute, and the hint then told the
            # operator to strip an inline fill the text does not carry.
            own_spec, own_val, _own_sel = own_paint(child, "fill", lrules)

            texts.append(
                TextElement(
                    content=content,
                    fill=fill_hex,
                    dark_fill=dark_hex,
                    unresolved=None if fill_hex else (paint.light or ""),
                    dark_unresolved=None if dark_hex else (paint.dark or ""),
                    attribute_painted=own_val is not None and own_spec == _SPEC_ATTR,
                    displaced=is_displaced(child),
                    font_size=fs,
                    font_weight=fw,
                    x=x,
                    y=y,
                    css_class=css_class,
                    text_anchor=text_anchor,
                )
            )

        elif tag == "rect":
            x = _geo(child.get("x"), canvas_w)
            y = _geo(child.get("y"), canvas_h)
            w = _geo(child.get("width"), canvas_w)
            h = _geo(child.get("height"), canvas_h)
            if None in (x, y, w, h):
                continue
            # Through the cascade, like the text branch above. Reading the
            # attribute alone made every ground painted the way this project's
            # own CSS rule MANDATES invisible, and the text was then scored
            # against a fabricated white: a #24405f label on a .panel{#1e3a5f}
            # plate reported 10.64:1 PASS where the rendered ratio is 1.08:1.
            # A decoration under `<g transform="translate(166,92) scale(0.13)">`
            # renders 150 units from its raw x/y. Reading fill off the attribute
            # used to drop these (they resolved to None); resolving them through
            # the cascade admitted them AT RAW COORDINATES, and the ground
            # election then handed one to text nowhere near it - 17 false HARD
            # findings across 6 shipped files. `build_render_model` already
            # answers this; the answer was being discarded.
            if is_displaced(child) or _in_template(child, parent_of):
                continue
            bg_paint = theme_paint(child, "fill", lrules, drules, winning_paint, merged=mrules)
            fill = _strip_important(bg_paint.light)
            fill_hex = resolve_color(fill)
            if not fill_hex:
                continue
            dark_raw = _strip_important(bg_paint.dark)
            dark_bg_hex = resolve_color(dark_raw)
            # `fill:none` under the dark query is a DECISION - the plate renders
            # nothing, and text on it falls through to the document ground.
            # Only a genuinely unreadable value is `dark_unreadable`; conflating
            # the two blocked a legible document with a HARD.
            dark_paints_nothing = bg_paint.overridden and (dark_raw or "").lower() in (
                "none",
                "transparent",
            )
            dark_unreadable = (
                bg_paint.overridden and dark_bg_hex is None and not dark_paints_nothing
            )
            # The module's OWN opacity resolver, not a fourth weaker copy. It
            # takes the MIN across `fill-opacity`, `opacity`, the paint's own
            # alpha and every ancestor's opacity - not the spec's product, which
            # is a documented approximation (it under-reports a stacked wash) -
            # so `fill: rgba(30,58,95,0.05)` stops being scored as a solid plate.
            opacity = _resolved_opacity(child, "fill", lrules, resolve_paint, root, parent_of)
            dark_opacity = _resolved_opacity(child, "fill", mrules, resolve_paint, root, parent_of)

            label = f"rect {w:.0f}x{h:.0f}"
            if w >= 780:
                label = f"bg-strip {fill}"

            backgrounds.append(
                Background(
                    label=label,
                    fill=fill_hex,
                    opacity=opacity,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    dark_fill=dark_bg_hex,
                    dark_opacity=dark_opacity,
                    dark_unreadable=dark_unreadable,
                    dark_paints_nothing=dark_paints_nothing,
                )
            )

        elif tag == "path":
            if is_displaced(child) or _in_template(child, parent_of):
                continue
            d = child.get("d", "")
            bg_paint = theme_paint(child, "fill", lrules, drules, winning_paint, merged=mrules)
            fill = _strip_important(bg_paint.light)
            fill_hex = resolve_color(fill)
            if not fill_hex or fill == "none":
                continue
            dark_raw = _strip_important(bg_paint.dark)
            dark_bg_hex = resolve_color(dark_raw)
            dark_paints_nothing = bg_paint.overridden and (dark_raw or "").lower() in (
                "none",
                "transparent",
            )
            dark_unreadable = (
                bg_paint.overridden and dark_bg_hex is None and not dark_paints_nothing
            )
            opacity = _resolved_opacity(child, "fill", lrules, resolve_paint, root, parent_of)
            dark_opacity = _resolved_opacity(child, "fill", mrules, resolve_paint, root, parent_of)

            bbox = _parse_path_bbox(d)
            if bbox is not None:
                min_x, min_y, w, h = bbox
                backgrounds.append(
                    Background(
                        label=f"path-fill {fill}",
                        fill=fill_hex,
                        opacity=opacity,
                        x=min_x,
                        y=min_y,
                        w=w,
                        h=h,
                        dark_fill=dark_bg_hex,
                        dark_opacity=dark_opacity,
                        dark_unreadable=dark_unreadable,
                        dark_paints_nothing=dark_paints_nothing,
                    )
                )

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


def bbox_overlaps(
    ax: float, ay: float, aw: float, ah: float, bx: float, by: float, bw: float, bh: float
) -> bool:
    """Check if two axis-aligned bounding boxes overlap."""
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def find_background_for_text(
    text: TextElement, backgrounds: list[Background]
) -> Background | None:
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
    "M": 2,
    "L": 2,
    "T": 2,
    "H": 1,
    "V": 1,
    "C": 6,
    "S": 4,
    "Q": 4,
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
            chunk = nums[i : i + stride]
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


def parse_svg_shapes(
    filepath: str,
) -> tuple[list[Shape], dict[str, str], dict[str, str], float, float]:
    """Parse SVG and extract filled shapes plus CSS class lookups.

    Returns (shapes, light_classes, dark_classes, canvas_w, canvas_h).
    """
    svg_text = Path(filepath).read_text(encoding="utf-8", errors="replace")
    root = ET.fromstring(svg_text)

    canvas_w, canvas_h = _get_canvas_size(root)

    lrules, drules, light_classes, dark_classes = parse_stylesheet(svg_text)
    _nr, _dis, resolve_paint, winning_paint, parent_of, own_paint = build_render_model(root)
    # Hoisted like the sibling parser's: one merge for the whole document.
    mrules = merged_rules(lrules, drules)

    shapes: list[Shape] = []

    for child in root.iter():
        tag = child.tag.replace(f"{{{NS}}}", "")
        if tag not in ("rect", "path", "circle", "ellipse", "polygon"):
            continue
        # A displaced shape still has to reach 3:1 against the page - contrast
        # does not depend on position. Non-rendering and template contents are
        # dropped: they paint nothing here.
        if _nr(child) or _in_template(child, parent_of):
            continue

        # bbox extraction per tag
        bbox: tuple[float, float, float, float] | None = None
        if tag == "rect":
            vals = (
                _geo(child.get("x"), canvas_w),
                _geo(child.get("y"), canvas_h),
                _geo(child.get("width"), canvas_w),
                _geo(child.get("height"), canvas_h),
            )
            bbox = None if None in vals else vals
        elif tag == "path":
            bbox = _parse_path_bbox(child.get("d", ""))
        elif tag == "circle":
            cx = _geo(child.get("cx"), canvas_w)
            cy = _geo(child.get("cy"), canvas_h)
            r = _geo(child.get("r"), canvas_w)
            bbox = None if None in (cx, cy, r) else (cx - r, cy - r, 2 * r, 2 * r)
        elif tag == "ellipse":
            cx = _geo(child.get("cx"), canvas_w)
            cy = _geo(child.get("cy"), canvas_h)
            rx = _geo(child.get("rx"), canvas_w)
            ry = _geo(child.get("ry"), canvas_h)
            bbox = None if None in (cx, cy, rx, ry) else (cx - rx, cy - ry, 2 * rx, 2 * ry)
        elif tag == "polygon":
            bbox = _parse_polygon_bbox(child.get("points", ""))

        if bbox is None or bbox[2] <= 0 or bbox[3] <= 0:
            continue
        x, y, w, h = bbox

        # Through the SAME cascade as the text branch. The lookup this replaced
        # tested the whole `class` attribute for membership, so `class="card
        # body"` matched nothing; let the presentation attribute beat the class
        # rule; could not see `#id` or element rules at all; and never resolved
        # a stroke from a class, which left `Shape.stroke_class` permanently
        # empty and made object dark-mode stroke contrast fiction.
        css_class = child.get("class", "")
        fill_paint = theme_paint(child, "fill", lrules, drules, winning_paint, merged=mrules)
        stroke_paint = theme_paint(child, "stroke", lrules, drules, winning_paint, merged=mrules)
        fill_hex = resolve_color(_strip_important(fill_paint.light))
        stroke_hex = resolve_color(_strip_important(stroke_paint.light))
        dark_fill_hex = resolve_color(_strip_important(fill_paint.dark))
        dark_stroke_hex = resolve_color(_strip_important(stroke_paint.dark))

        fill_opacity = _resolved_opacity(child, "fill", lrules, resolve_paint, root, parent_of)
        # The dark alpha is resolved against the MERGED sheet - the light value
        # unless the dark block declares its own - so the dark row never blends
        # a dark colour at the light alpha.
        dark_fill_opacity = _resolved_opacity(
            child, "fill", mrules, resolve_paint, root, parent_of
        )
        # SVG's initial values, not borrowed ones. `stroke-opacity` defaulting to
        # the FILL's opacity faded a solid border to the 4% of the wash it sits
        # on - 417 of 795 object failures had a stroke that reaches 3:1 once its
        # real opacity is used - and `stroke-width` defaulting to 0 discarded the
        # stroke of 149 shapes outright, inverting this module's own promise that
        # "cards with near-transparent fills but strong strokes still pass".
        stroke_opacity = _resolved_opacity(child, "stroke", lrules, resolve_paint, root, parent_of)
        dark_stroke_opacity = _resolved_opacity(
            child, "stroke", mrules, resolve_paint, root, parent_of
        )
        stroke_width = _length(
            _strip_important(winning_paint(child, "stroke-width", lrules)[1]), 0.0
        )
        if stroke_width is None:
            stroke_width = 1.0

        if not fill_hex and not stroke_hex:
            continue

        shapes.append(
            Shape(
                tag=tag,
                fill=fill_hex,
                fill_opacity=fill_opacity,
                fill_class=css_class,
                dark_fill=dark_fill_hex,
                dark_fill_opacity=dark_fill_opacity,
                stroke=stroke_hex,
                stroke_opacity=stroke_opacity,
                stroke_width=stroke_width,
                stroke_class=css_class,
                dark_stroke=dark_stroke_hex,
                dark_stroke_opacity=dark_stroke_opacity,
                x=x,
                y=y,
                w=w,
                h=h,
                label=f"{tag} {w:.0f}x{h:.0f}",
            )
        )

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
    for indices in by_geom.values():
        if len(indices) == 1:
            merged.append(shapes[indices[0]])
            continue

        base = shapes[indices[0]]
        merged_shape = Shape(**base.__dict__)
        for j in indices[1:]:
            other = shapes[j]
            if (
                merged_shape.fill is None or merged_shape.fill_opacity == 0
            ) and other.fill is not None:
                merged_shape.fill = other.fill
                merged_shape.fill_opacity = other.fill_opacity
                merged_shape.fill_class = other.fill_class
                # Take the donor's DARK paint with its light one, or the merged
                # record holds sibling A's dark value beside sibling B's light
                # one - 223 dark object rows scored on the wrong colour.
                merged_shape.dark_fill = other.dark_fill
                merged_shape.dark_fill_opacity = other.dark_fill_opacity
            if (
                merged_shape.stroke is None or merged_shape.stroke_width == 0
            ) and other.stroke is not None:
                merged_shape.stroke = other.stroke
                merged_shape.stroke_opacity = other.stroke_opacity
                merged_shape.stroke_width = other.stroke_width
                merged_shape.stroke_class = other.stroke_class
                merged_shape.dark_stroke = other.dark_stroke
                merged_shape.dark_stroke_opacity = other.dark_stroke_opacity
        merged.append(merged_shape)

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


def _resolve_dark_color(
    hex_color: str | None, css_class: str, dark_classes: dict[str, str]
) -> str | None:
    """Return the dark-mode equivalent of a colour, or the original.

    Retained for callers holding a Shape built before the cascade repoint; the
    parser now resolves `Shape.dark_fill` / `dark_stroke` directly, so this is
    only the fallback when they are absent.
    """
    # A shape that declares no stroke has no dark stroke either. Returning the
    # class's dark FILL here gave strokeless cards a phantom border, which the
    # old `stroke_width = 0.0` default happened to discard - correcting that
    # default to the spec's 1.0 made it live.
    if hex_color is None:
        return None
    if css_class and css_class in dark_classes:
        return dark_classes[css_class]
    return hex_color


def _check_one_shape(
    shape: Shape, doc_bg: str, mode: str, dark_classes: dict[str, str]
) -> ObjectContrastResult:
    """Compute fill+stroke contrast for one shape vs the document bg."""
    if mode == "dark":
        fill_hex = shape.dark_fill or _resolve_dark_color(
            shape.fill, shape.fill_class, dark_classes
        )
        stroke_hex = shape.dark_stroke or _resolve_dark_color(
            shape.stroke, shape.stroke_class, dark_classes
        )
        # The dark colour blends at the DARK alpha. `Background` has carried
        # both since its dark fields were added; `Shape` got the colour without
        # the alpha, so a plate declared `fill-opacity:0.04` in light and `1`
        # in dark scored the light wash at the solid's ratio - 1.06 FAIL on a
        # document that renders 5.35 PASS.
        fill_opacity = (
            shape.dark_fill_opacity if shape.dark_fill_opacity is not None else shape.fill_opacity
        )
        stroke_opacity = (
            shape.dark_stroke_opacity
            if shape.dark_stroke_opacity is not None
            else shape.stroke_opacity
        )
    else:
        fill_hex = shape.fill
        stroke_hex = shape.stroke
        fill_opacity = shape.fill_opacity
        stroke_opacity = shape.stroke_opacity

    bg_lum = relative_luminance(*hex_to_rgb(doc_bg))

    fill_ratio: float | None = None
    fill_used: str | None = None
    if fill_hex and fill_opacity > 0.0:
        if fill_opacity < 1.0:
            blended = blend_over(fill_hex, fill_opacity, doc_bg)
        else:
            blended = fill_hex
        fill_used = blended
        fill_ratio = contrast_ratio(relative_luminance(*hex_to_rgb(blended)), bg_lum)

    stroke_ratio: float | None = None
    stroke_used: str | None = None
    if stroke_hex and shape.stroke_width > 0 and stroke_opacity > 0.0:
        if stroke_opacity < 1.0:
            blended_stroke = blend_over(stroke_hex, stroke_opacity, doc_bg)
        else:
            blended_stroke = stroke_hex
        stroke_used = blended_stroke
        stroke_ratio = contrast_ratio(relative_luminance(*hex_to_rgb(blended_stroke)), bg_lum)

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
        # These filters read SIZE, not position, and a translate - the common
        # case by far - leaves width and height exact. Exempting displaced
        # shapes admitted 829 decorative 2-6px circles as object failures on one
        # file: precisely the "thin accent bars or decorative dividers" the
        # filters exist to drop.
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


def resolve_effective_bg(bg: Background | None, doc_bg: str, dark: bool = False) -> str:
    """The ground this text actually sits on, blended over the document bg.

    ``dark`` selects the plate's dark-mode value. Scoring the dark row against
    the light plate is not a near-miss - a light-on-dark deck reads as every
    label failing, because the checker put the dark text back on the light
    ground.
    """
    if bg is None:
        return doc_bg
    # A plate the dark block paints `none` is no ground at all under the query -
    # the text on it falls through to the document ground.
    if dark and bg.dark_paints_nothing:
        return doc_bg
    # `is not None`, not `or`. A dark declaration that resolves to nothing
    # readable (`var()`, `url()`, `none`) is a DECISION, not an absence, and
    # falling back to the light plate scores the dark row against the wrong
    # theme - the line below already got this right.
    fill = (bg.dark_fill if bg.dark_fill is not None else bg.fill) if dark else bg.fill
    alpha = (
        (bg.dark_opacity if bg.dark_opacity is not None else bg.opacity) if dark else bg.opacity
    )
    if alpha < 1.0:
        return blend_over(fill, alpha, doc_bg)
    return fill


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

        # UNMEASURABLE IS NOT CLEAN. Scoring this against a fabricated black
        # printed 20.42:1 over text whose real ratio was 1.33:1 - a PASS in the
        # one tier that cannot be acked away.
        if text.displaced:
            hints.append(
                f'  UNMEASURABLE "{text.content[:40]}" - a transform moves it away from its '
                f"declared x/y, so the checker cannot tell which ground it sits on and its "
                f"contrast was NOT judged"
            )
            continue

        if text.fill is None:
            if text.unresolved:
                why = (
                    f'fill resolves to "{text.unresolved}", which this checker '
                    f"cannot read as a colour"
                )
            else:
                why = "nothing declares its fill (SVG initial: black)"
            hints.append(
                f'  UNMEASURABLE "{text.content[:40]}" - {why}, so its contrast was NOT judged'
            )
            continue

        large = is_large_text(text.font_size, text.font_weight)
        aa_threshold = 3.0 if large else 4.5
        aaa_threshold = 4.5 if large else 7.0

        bg = find_background_for_text(text, backgrounds)

        # --- Inline fill matches CSS class? ---
        if text.fill and text.attribute_painted:
            matching = fill_to_classes.get(text.fill.lower(), [])
            if matching:
                cls_name = matching[0]
                dark_alt = dark_classes.get(cls_name, "?")
                hints.append(
                    f'  "{text.content[:40]}" uses inline fill={text.fill} '
                    f"matching .{cls_name} - won't switch to {dark_alt} in dark mode"
                )

        # --- Light mode ---
        eff_bg = resolve_effective_bg(bg, light_doc_bg)
        text_lum = relative_luminance(*hex_to_rgb(text.fill))
        bg_lum = relative_luminance(*hex_to_rgb(eff_bg))
        ratio = contrast_ratio(text_lum, bg_lum)

        results.append(
            ContrastResult(
                text=text,
                background=bg or doc_bg_light,
                effective_bg=eff_bg,
                ratio=ratio,
                aa_pass=ratio >= aa_threshold,
                aaa_pass=ratio >= aaa_threshold,
                large=large,
                mode="light",
            )
        )

        # --- Dark mode ---
        # Resolved at parse time through the cascade. Re-deriving it here from
        # the class map missed every `#id` and element rule, and gave a
        # `class="a b"` element no dark value at all - so its dark row was
        # silently absent rather than failing.
        dark_fill = text.dark_fill
        if bg is not None and bg.dark_unreadable:
            hints.append(
                f'  UNMEASURABLE "{text.content[:40]}" - the dark block repaints its ground '
                f"with a value this checker cannot read, so its dark contrast was NOT judged"
            )
        elif dark_fill:
            dark_eff_bg = resolve_effective_bg(bg, dark_doc_bg, dark=True)
            dark_text_lum = relative_luminance(*hex_to_rgb(dark_fill))
            dark_bg_lum = relative_luminance(*hex_to_rgb(dark_eff_bg))
            dark_ratio = contrast_ratio(dark_text_lum, dark_bg_lum)

            results.append(
                ContrastResult(
                    text=TextElement(
                        content=text.content,
                        fill=dark_fill,
                        font_size=text.font_size,
                        font_weight=text.font_weight,
                        x=text.x,
                        y=text.y,
                        css_class=text.css_class,
                    ),
                    background=bg or doc_bg_dark,
                    effective_bg=dark_eff_bg,
                    ratio=dark_ratio,
                    aa_pass=dark_ratio >= aa_threshold,
                    aaa_pass=dark_ratio >= aaa_threshold,
                    large=large,
                    mode="dark",
                )
            )
        elif text.dark_unresolved is not None:
            if text.dark_unresolved.strip().lower() in ("none", "transparent"):
                # `fill:none` under the dark query renders NOTHING - invisible
                # text is a failure (1.00:1), not an unmeasurable.
                results.append(
                    ContrastResult(
                        text=TextElement(
                            content=text.content,
                            fill="none",
                            font_size=text.font_size,
                            font_weight=text.font_weight,
                            x=text.x,
                            y=text.y,
                            css_class=text.css_class,
                        ),
                        background=bg or doc_bg_dark,
                        effective_bg=resolve_effective_bg(bg, dark_doc_bg, dark=True),
                        ratio=1.0,
                        aa_pass=False,
                        aaa_pass=False,
                        large=large,
                        mode="dark",
                    )
                )
            else:
                # The sibling branch above answers this for the ground; a dark
                # TEXT paint nobody can read gets the same honesty - a silent
                # absent row read as PASS.
                hints.append(
                    f'  UNMEASURABLE "{text.content[:40]}" - its dark fill is '
                    f'"{text.dark_unresolved}", which this checker cannot read as a '
                    f"colour, so its dark contrast was NOT judged"
                )

    return results, hints


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SVG contrast checker (WCAG 2.1)")
    parser.add_argument("--svg", required=True, help="SVG file to check")
    parser.add_argument(
        "--level",
        choices=["AA", "AAA"],
        default="AA",
        help="WCAG level for text checks (default: AA)",
    )
    parser.add_argument(
        "--dark-bg",
        default="#1e1e1e",
        help="Document background colour for dark mode (default: #1e1e1e)",
    )
    parser.add_argument(
        "--show-all", action="store_true", help="Show all elements including passing ones"
    )
    parser.add_argument(
        "--skip-objects", action="store_true", help="Skip object (non-text) contrast checks"
    )
    parser.add_argument(
        "--object-min-area",
        type=float,
        default=800.0,
        help="Minimum bbox area (px²) for object contrast checks (default: 800)",
    )
    parser.add_argument(
        "--object-min-dim",
        type=float,
        default=20.0,
        help="Minimum bbox dimension (px) for object contrast checks (default: 20)",
    )
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

    results, hints = check_all_contrasts(
        texts, backgrounds, light_classes, dark_classes, dark_doc_bg=args.dark_bg
    )

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

            print(
                f"  [{marker:4s}] {r.ratio:5.2f}:1 (need {threshold:.1f}:1) "
                f'{size_label:6s} | "{content_preview}"'
            )
            print(
                f"         text: {r.text.fill}{class_note}  "
                f"({r.text.font_size:.0f}px/{r.text.font_weight})"
            )
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
                    if r.fill_ratio is not None
                    else "fill=none"
                )
                stroke_str = (
                    f"stroke={r.stroke_used}@{r.shape.stroke_width:g}px ratio={r.stroke_ratio:.2f}:1"
                    if r.stroke_ratio is not None
                    else "stroke=none"
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
    print("SUMMARY")
    print(
        f"  TEXT:    {total} checks, {passed} pass, {warns} AA-only, {fails} FAIL "
        f"(WCAG {args.level})"
    )
    if not args.skip_objects:
        print(f"  OBJECTS: {object_fails} FAIL (WCAG SC 1.4.11, fill OR stroke must reach 3:1)")

    if hints:
        print(
            f"  {len(hints)} text element(s) use inline fills matching CSS classes "
            "(won't switch in dark mode)."
        )
    if fails > 0:
        print(f"\n  {fails} text element(s) fail WCAG {args.level} minimum contrast.")
        print("  Fix: use a lighter/darker text colour, or change the background.")
    if object_fails > 0:
        print(
            f"\n  {object_fails} object(s) blend into the document background "
            "in light or dark mode."
        )
        print(
            "  Fix: raise fill opacity, switch fill to a CSS class with dark-mode "
            "swap, or strengthen stroke."
        )


if __name__ == "__main__":
    main()
