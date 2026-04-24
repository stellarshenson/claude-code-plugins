"""Element placement inside a bounding box using the empty-space finder.

Generic positioner: given an SVG, a container element id, the width
and height of the element to place, and a preferred corner, the tool
finds the largest free region inside the container (via
:func:`calc_empty_space.find_empty_regions` in ``edges-only`` mode -
strokes and text count, filled card backgrounds do not), then anchors
the element at the requested corner of that region with a margin
from the container edge. Works for icons, text bboxes, inline
graphics, badges - anything with a width + height.

For text: compute the bbox first (rough: ``w ~= len(text) * font_size
* 0.6``; exact: pass through ``svg-infographics text-to-path`` and
measure the resulting path bbox) then feed the dimensions to this
tool.

Typical use::

    # Icon in the top-right of a card
    svg-infographics place \\
        --svg file.svg \\
        --container card-ai-lab \\
        --size 24,24 \\
        --corner top-right \\
        --margin 12

    # Title text at top-left of the same card (text_w from estimate or
    # text-to-path; text_h = font-size)
    svg-infographics place \\
        --svg file.svg \\
        --container card-ai-lab \\
        --size 96,13 \\
        --corner top-left \\
        --margin 16
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools.calc_empty_space import find_empty_regions

_CORNERS = {"top-left", "top-right", "bottom-left", "bottom-right", "center"}


def _polygon_bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    return x0, y0, x1 - x0, y1 - y0


def _position_at_corner(
    region_bbox: tuple[float, float, float, float],
    icon_w: float,
    icon_h: float,
    corner: str,
) -> tuple[float, float]:
    """Return the icon's top-left (x, y) anchored at ``corner`` of the region.

    Assumes the icon fits. Use ``_fits`` first to verify.
    """
    rx, ry, rw, rh = region_bbox
    if corner == "top-left":
        return rx, ry
    if corner == "top-right":
        return rx + rw - icon_w, ry
    if corner == "bottom-left":
        return rx, ry + rh - icon_h
    if corner == "bottom-right":
        return rx + rw - icon_w, ry + rh - icon_h
    if corner == "center":
        return rx + (rw - icon_w) / 2.0, ry + (rh - icon_h) / 2.0
    raise ValueError(f"unknown corner {corner!r}")


def _fits(region_bbox: tuple[float, float, float, float], icon_w: float, icon_h: float) -> bool:
    _, _, rw, rh = region_bbox
    return rw >= icon_w and rh >= icon_h


def place_element(
    svg_path: Path,
    *,
    container_id: str,
    width: float,
    height: float,
    corner: str = "top-left",
    margin: float = 8.0,
) -> dict:
    """Compute placement for an element of the given width x height.

    Returns a dict with keys ``x``, ``y`` (element top-left),
    ``region_bbox`` (the chosen free region's bbox), and ``fallback``
    (True if a non-preferred region was used because the preferred one
    did not fit). Raises ``ValueError`` when no region can accommodate
    the element.
    """
    if corner not in _CORNERS:
        raise ValueError(f"--corner must be one of {sorted(_CORNERS)}, got {corner!r}")

    regions = find_empty_regions(
        str(svg_path),
        tolerance=margin,
        min_area=max(50.0, width * height),
        container_id=container_id,
        edges_only=True,
    )
    if not regions:
        raise ValueError(
            f"no empty regions found inside container {container_id!r} "
            f"(margin={margin}). Relax margin or choose a different container."
        )

    # Regions are returned sorted by area descending. Walk them and pick
    # the first that fits.
    for idx, region in enumerate(regions):
        bbox = _polygon_bbox(region["boundary"])
        if _fits(bbox, width, height):
            x, y = _position_at_corner(bbox, width, height, corner)
            return {
                "x": x,
                "y": y,
                "region_bbox": bbox,
                "fallback": idx > 0,
                "container_id": container_id,
                "corner": corner,
                "size": [width, height],
            }

    raise ValueError(
        f"no empty region inside {container_id!r} is large enough to fit a "
        f"{width}x{height} element with margin={margin}. "
        f"Found {len(regions)} region(s), largest was "
        f"{_polygon_bbox(regions[0]['boundary'])[2:]}."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics place",
        description=(
            "Position an element (icon, text bbox, badge) inside a named "
            "container using the empty-space finder. Returns top-left "
            "(x, y) respecting margins."
        ),
    )
    parser.add_argument("--svg", required=True, help="Path to SVG")
    parser.add_argument(
        "--container",
        required=True,
        help="Container element id (must be a closed shape: rect, circle, "
        "polygon, etc.). The placed element lands inside it.",
    )
    parser.add_argument(
        "--size",
        required=True,
        help=(
            "Element WxH in pixels, comma-separated (e.g. '24,24' for an "
            "icon, '96,13' for a 13pt text of ~96px width)."
        ),
    )
    parser.add_argument(
        "--corner",
        default="top-left",
        choices=sorted(_CORNERS),
        help="Where in the chosen free region to anchor the element (default: top-left)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=8.0,
        help="Inward standoff from container edge AND gutter around obstacles (default: 8).",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of text")
    args = parser.parse_args(argv)

    try:
        w, h = (float(v) for v in args.size.split(","))
    except ValueError:
        parser.error(f"--size must be 'W,H', got {args.size!r}")

    svg_path = Path(args.svg)
    if not svg_path.is_file():
        print(f"ERROR: svg not found: {svg_path}", file=sys.stderr)
        return 2

    try:
        result = place_element(
            svg_path,
            container_id=args.container,
            width=w,
            height=h,
            corner=args.corner,
            margin=args.margin,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"Element {w:.0f}x{h:.0f} at corner={args.corner} inside "
            f"{args.container!r}: x={result['x']:.1f} y={result['y']:.1f}"
        )
        if result["fallback"]:
            print("(fallback: preferred region too small; used a larger alternative)")
    print(
        f"\nnext: anchor the element at (x={result['x']:.1f}, "
        f"y={result['y']:.1f}). For text, remember the y value is the "
        "TOP of the text bbox - SVG <text> uses baseline, so set "
        f"`y = {result['y']:.1f} + font-size`.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
