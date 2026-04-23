"""Convert text + font into SVG `<path>` outlines.

On-request tool: use this when the user explicitly wants text rendered as
glyph outlines instead of `<text>` elements. Typical reasons:

- Embed a custom font without depending on the renderer having it installed
- Print or hand off SVGs that must look identical everywhere
- Headlines / labels that need a deterministic bounding box (e.g. for
  fit-to-width scaling without the ugliness of `textLength`)

Tradeoffs the caller should accept:
- The output is no longer editable as text (search/replace, screen readers, etc.)
- File size grows ~5-20x compared to a `<text>` element
- A `.ttf` or `.otf` font file path is required (no system font resolution)

Uses the `fonttools` package (bundled with the core install).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys

try:
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    _FONTTOOLS_AVAILABLE = True
    _FONTTOOLS_ERROR: str | None = None
except ImportError as exc:
    _FONTTOOLS_AVAILABLE = False
    _FONTTOOLS_ERROR = str(exc)


VALID_ANCHORS = ("start", "middle", "end")


@dataclass
class TextPathResult:
    """Outcome of a text-to-path conversion."""

    svg: str
    advance: float
    scale: float
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float

    def to_dict(self) -> dict:
        return asdict(self)


def _require_fonttools() -> None:
    if not _FONTTOOLS_AVAILABLE:
        raise ImportError(
            "fonttools is required for text_to_path. It is a core dependency "
            "of stellars-claude-code-plugins - your install may be corrupted.\n"
            f"Original error: {_FONTTOOLS_ERROR}"
        )


def text_to_path(
    text: str,
    font_path: str | Path,
    size: float = 24.0,
    x: float = 0.0,
    y: float = 0.0,
    anchor: str = "start",
    fill: str | None = None,
    css_class: str | None = None,
    fit_width: float | None = None,
) -> TextPathResult:
    """Convert `text` rendered in `font_path` at `size` into an SVG `<path>`.

    Coordinates match SVG `<text>` semantics: `(x, y)` is the **baseline**
    origin. `anchor` mirrors `text-anchor` (start | middle | end).

    If `fit_width` is given and the natural advance exceeds it, the path is
    uniformly scaled down to fit (NO glyph stretching - aspect preserved).

    `fill` and `css_class` are mutually optional; pass neither if you want the
    path to inherit fill from a parent `<g>` or stylesheet.
    """
    _require_fonttools()

    if anchor not in VALID_ANCHORS:
        raise ValueError(f"anchor must be one of {VALID_ANCHORS}, got {anchor!r}")
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")
    if fit_width is not None and fit_width <= 0:
        raise ValueError(f"fit_width must be positive when provided, got {fit_width}")

    font = TTFont(str(font_path))
    upem = font["head"].unitsPerEm
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    notdef = ".notdef" if ".notdef" in glyph_set else next(iter(glyph_set))

    pen = SVGPathPen(glyph_set)
    cursor_units = 0.0
    for ch in text:
        gname = cmap.get(ord(ch), notdef)
        glyph = glyph_set[gname]
        # Translate this glyph by the running cursor before drawing into the
        # shared SVGPathPen. fontTools affine = (xx, xy, yx, yy, dx, dy).
        tpen = TransformPen(pen, (1, 0, 0, 1, cursor_units, 0))
        glyph.draw(tpen)
        cursor_units += glyph.width

    natural_advance_units = cursor_units
    base_scale = size / upem

    if fit_width is not None and natural_advance_units * base_scale > fit_width:
        scale = fit_width / natural_advance_units
    else:
        scale = base_scale

    final_advance = natural_advance_units * scale

    if anchor == "middle":
        anchor_offset = -final_advance / 2
    elif anchor == "end":
        anchor_offset = -final_advance
    else:
        anchor_offset = 0.0

    origin_x = x + anchor_offset

    # Y-flip: font coords are Y-up, SVG is Y-down.
    transform = f"translate({_fmt(origin_x)},{_fmt(y)}) scale({_fmt(scale)},{_fmt(-scale)})"

    attrs = [f'd="{pen.getCommands()}"', f'transform="{transform}"']
    if fill is not None:
        attrs.append(f'fill="{fill}"')
    if css_class is not None:
        attrs.append(f'class="{css_class}"')
    svg = "<path " + " ".join(attrs) + "/>"

    hhea = font["hhea"]
    ascent_user = hhea.ascent * scale
    descent_user = hhea.descent * scale  # negative number

    return TextPathResult(
        svg=svg,
        advance=final_advance,
        scale=scale,
        bbox_x=origin_x,
        bbox_y=y - ascent_user,
        bbox_width=final_advance,
        bbox_height=ascent_user - descent_user,
    )


def _fmt(value: float) -> str:
    """Format a float compactly: drop trailing zeros, no scientific notation."""
    formatted = f"{value:.4f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="svg-infographics text-to-path",
        description="Render text as SVG path outlines using a TTF/OTF font.",
    )
    parser.add_argument("--text", required=True, help="String to render")
    parser.add_argument("--font", required=True, help="Path to .ttf or .otf font file")
    parser.add_argument("--size", type=float, default=24.0, help="Font size in user units")
    parser.add_argument("--x", type=float, default=0.0, help="Baseline x (SVG text semantics)")
    parser.add_argument("--y", type=float, default=0.0, help="Baseline y (SVG text semantics)")
    parser.add_argument(
        "--anchor",
        choices=VALID_ANCHORS,
        default="start",
        help="Text anchor (mirrors text-anchor attribute)",
    )
    parser.add_argument("--fill", default=None, help='Fill colour (e.g. "#222")')
    parser.add_argument("--class", dest="css_class", default=None, help="CSS class name")
    parser.add_argument(
        "--fit-width",
        type=float,
        default=None,
        help="Max width in user units; scales path down uniformly if exceeded",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable result (svg + bbox) instead of just the snippet",
    )

    args = parser.parse_args()

    if not _FONTTOOLS_AVAILABLE:
        print(
            "ERROR: fonttools not installed. It is a core dependency of "
            "stellars-claude-code-plugins - reinstall the package.",
            file=sys.stderr,
        )
        sys.exit(2)

    font_path = Path(args.font)
    if not font_path.exists():
        print(f"ERROR: font file not found: {font_path}", file=sys.stderr)
        sys.exit(2)

    result = text_to_path(
        text=args.text,
        font_path=font_path,
        size=args.size,
        x=args.x,
        y=args.y,
        anchor=args.anchor,
        fill=args.fill,
        css_class=args.css_class,
        fit_width=args.fit_width,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.svg)
        print(
            f"<!-- bbox: x={_fmt(result.bbox_x)} y={_fmt(result.bbox_y)} "
            f"w={_fmt(result.bbox_width)} h={_fmt(result.bbox_height)} "
            f"scale={_fmt(result.scale)} -->",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
