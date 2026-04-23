"""Render SVG to PNG via Playwright with proper dark/light mode support.

Playwright's page.emulate_media(color_scheme="dark") natively triggers
@media (prefers-color-scheme: dark) CSS media queries without modifying
the SVG. Combined with screenshot(omit_background=True) for transparent
PNG output.

Usage:
    render-png input.svg output.png --mode light --width 3000
    render-png input.svg output.png --mode dark --width 3000
    render-png input.svg output.png --mode dark --bg "#0a1a24" --width 3000
    render-png input.svg output.png --mode both --width 3000
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import tempfile

from playwright.sync_api import sync_playwright


def _parse_viewbox(svg_text: str) -> tuple[float, float] | None:
    m = re.search(r'viewBox="([^"]+)"', svg_text)
    if not m:
        return None
    parts = m.group(1).split()
    if len(parts) >= 4:
        return float(parts[2]), float(parts[3])
    return None


def render_svg_to_png(
    svg_path: str | Path,
    output_path: str | Path,
    mode: str = "light",
    width: int = 3000,
    bg: str | None = None,
) -> Path:
    """Render SVG to PNG using Playwright (Chromium).

    Uses page.emulate_media(color_scheme=mode) to natively trigger
    @media (prefers-color-scheme: dark/light) CSS media queries.
    No SVG modification needed.

    Args:
        svg_path: Path to the SVG file.
        output_path: Path for the output PNG.
        mode: 'light' or 'dark'.
        width: Output width in pixels.
        bg: Background colour (default: transparent).
    """
    svg_path = Path(svg_path).resolve()
    output_path = Path(output_path).resolve()

    svg_text = svg_path.read_text(encoding="utf-8")

    vb = _parse_viewbox(svg_text)
    if vb:
        vb_w, vb_h = vb
        scale = width / vb_w
        target_height = int(vb_h * scale)
    else:
        target_height = int(width * 0.6)

    bg_css = bg if bg else "transparent"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; }}
  html, body {{ background: {bg_css}; overflow: hidden; width: {width}px; height: {target_height}px; }}
  svg {{ width: {width}px; height: {target_height}px; display: block; }}
</style>
</head>
<body>
{svg_text}
</body>
</html>"""

    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", encoding="utf-8", delete=False
    ) as f:
        f.write(html)
        html_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                color_scheme=mode,
                viewport={"width": width, "height": target_height},
            )
            page = context.new_page()
            page.goto(f"file://{html_path}")

            omit_bg = bg is None
            page.screenshot(
                path=str(output_path),
                type="png",
                omit_background=omit_bg,
                clip={"x": 0, "y": 0, "width": width, "height": target_height},
            )
            browser.close()
    finally:
        Path(html_path).unlink(missing_ok=True)

    if not output_path.exists():
        raise RuntimeError(f"Playwright did not create {output_path}")

    size = output_path.stat().st_size
    print(
        f"Rendered {output_path.name} ({mode}, {width}x{target_height}, bg={bg_css}, {size:,} bytes)"
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(
        prog="render-png",
        description="Render SVG to PNG via Playwright with dark/light mode.",
    )
    parser.add_argument("svg", help="Input SVG file")
    parser.add_argument("output", help="Output PNG file")
    parser.add_argument(
        "--mode",
        choices=["light", "dark", "both"],
        default="light",
        help="Colour scheme (default: light)",
    )
    parser.add_argument("--width", type=int, default=3000, help="Output width px (default: 3000)")
    parser.add_argument(
        "--bg",
        default=None,
        help='Background colour (default: transparent). E.g. "#ffffff", "#0a1a24"',
    )
    args = parser.parse_args()

    if args.mode == "both":
        base = Path(args.output)
        stem = base.stem
        suffix = base.suffix or ".png"
        parent = base.parent
        render_svg_to_png(
            args.svg,
            parent / f"{stem}.light{suffix}",
            mode="light",
            width=args.width,
            bg=args.bg,
        )
        render_svg_to_png(
            args.svg,
            parent / f"{stem}.dark{suffix}",
            mode="dark",
            width=args.width,
            bg=args.bg,
        )
    else:
        render_svg_to_png(args.svg, args.output, mode=args.mode, width=args.width, bg=args.bg)


if __name__ == "__main__":
    main()
