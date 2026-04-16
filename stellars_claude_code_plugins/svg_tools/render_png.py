"""Render SVG to PNG via headless Chrome with proper dark/light mode support.

Unlike cairosvg, Chrome evaluates @media (prefers-color-scheme: dark) CSS
so dark-mode PNGs show the REAL dark-mode colours, not light-mode colours
on a dark background.

Usage:
    render-png input.svg output.png --mode light --width 3000
    render-png input.svg output.png --mode dark --width 3000
    render-png input.svg output.png --mode both --width 3000  # generates output.light.png + output.dark.png
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def _find_chrome() -> str:
    """Find Chrome/Chromium binary."""
    for name in [
        "google-chrome",
        "google-chrome-stable",
        "chromium",
        "chromium-browser",
    ]:
        try:
            result = subprocess.run(["which", name], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return result.stdout.strip()
        except FileNotFoundError:
            continue
    raise FileNotFoundError("Chrome/Chromium not found. Install google-chrome or chromium.")


def _parse_viewbox(svg_text: str) -> tuple[float, float] | None:
    """Extract viewBox width and height from SVG text."""
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
    chrome_path: str | None = None,
) -> Path:
    """Render SVG to PNG using headless Chrome.

    Args:
        svg_path: Path to the SVG file.
        output_path: Path for the output PNG.
        mode: 'light' or 'dark'. Controls prefers-color-scheme.
        width: Output width in pixels.
        chrome_path: Optional path to Chrome binary.

    Returns:
        Path to the rendered PNG.
    """
    svg_path = Path(svg_path).resolve()
    output_path = Path(output_path).resolve()
    chrome = chrome_path or _find_chrome()

    svg_text = svg_path.read_text(encoding="utf-8")
    vb = _parse_viewbox(svg_text)
    if vb:
        vb_w, vb_h = vb
        scale = width / vb_w
        height = int(vb_h * scale)
    else:
        height = int(width * 0.6)

    bg_color = "#0a1a24" if mode == "dark" else "#ffffff"
    color_scheme = "dark" if mode == "dark" else "light"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {{ color-scheme: {color_scheme}; }}
  html, body {{ margin: 0; padding: 0; background: {bg_color}; overflow: hidden; }}
  body {{ width: {width}px; height: {height}px; }}
  svg {{ width: {width}px; height: {height}px; display: block; }}
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
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--hide-scrollbars",
            f"--screenshot={output_path}",
            f"--window-size={width},{height}",
        ]
        if mode == "dark":
            cmd.append("--force-dark-mode")
        cmd.append(f"file://{html_path}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        if result.returncode != 0:
            print(f"Chrome stderr: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"Chrome exited with code {result.returncode}")
    finally:
        os.unlink(html_path)

    if not output_path.exists():
        raise RuntimeError(f"Chrome did not create {output_path}")

    size = output_path.stat().st_size
    print(f"Rendered {output_path.name} ({mode}, {width}x{height}, {size:,} bytes)")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        prog="render-png",
        description="Render SVG to PNG via headless Chrome with dark/light mode support.",
    )
    parser.add_argument("svg", help="Input SVG file")
    parser.add_argument("output", help="Output PNG file")
    parser.add_argument(
        "--mode",
        choices=["light", "dark", "both"],
        default="light",
        help="Colour scheme: light, dark, or both (default: light)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=3000,
        help="Output width in pixels (default: 3000)",
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
        )
        render_svg_to_png(
            args.svg,
            parent / f"{stem}.dark{suffix}",
            mode="dark",
            width=args.width,
        )
    else:
        render_svg_to_png(args.svg, args.output, mode=args.mode, width=args.width)


if __name__ == "__main__":
    main()
