"""Render SVG to PNG via headless Chrome with proper dark/light mode support.

Chrome evaluates @media (prefers-color-scheme: dark) natively. For dark mode
uses --force-dark-mode to trigger the media query, with
--disable-features=WebContentsForceDark to prevent Chrome's auto-darkening
algorithm from inverting colours and corrupting sizing.

Usage:
    render-png input.svg output.png --mode light --width 3000
    render-png input.svg output.png --mode dark --width 3000
    render-png input.svg output.png --mode dark --bg "#0a1a24" --width 3000
    render-png input.svg output.png --mode both --width 3000
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
    raise FileNotFoundError("Chrome/Chromium not found.")


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
    chrome_path: str | None = None,
) -> Path:
    """Render SVG to PNG using headless Chrome.

    For dark mode: --force-dark-mode triggers prefers-color-scheme: dark,
    --disable-features=WebContentsForceDark prevents Chrome's auto-darkening
    from inverting/dimming colours. SVG stays untouched.

    Args:
        svg_path: Path to the SVG file.
        output_path: Path for the output PNG.
        mode: 'light' or 'dark'.
        width: Output width in pixels.
        bg: Background colour (default: transparent).
        chrome_path: Optional Chrome binary path.
    """
    svg_path = Path(svg_path).resolve()
    output_path = Path(output_path).resolve()
    chrome = chrome_path or _find_chrome()

    svg_text = svg_path.read_text(encoding="utf-8")
    vb = _parse_viewbox(svg_text)
    if vb:
        vb_w, vb_h = vb
        scale = width / vb_w
        target_height = int(vb_h * scale)
    else:
        target_height = int(width * 0.6)

    # Chrome viewport needs buffer to avoid crop; we'll trim after
    viewport_height = target_height + 100

    # Default bg: transparent for light, #0a1a24 for dark (bright dark-mode
    # colours on transparent bg look washed out in light-bg viewers)
    if bg:
        bg_css = bg
    elif mode == "dark":
        bg_css = "#0a1a24"
    else:
        bg_css = "transparent"

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ margin: 0; padding: 0; }}
  html, body {{ background: {bg_css}; overflow: hidden; width: {width}px; height: {viewport_height}px; }}
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
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-software-rasterizer",
            "--hide-scrollbars",
            f"--screenshot={output_path}",
            f"--window-size={width},{viewport_height}",
        ]
        if mode == "dark":
            cmd.extend(
                [
                    "--force-dark-mode",
                    "--disable-features=WebContentsForceDark",
                ]
            )
        cmd.append(f"file://{html_path}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
        if result.returncode != 0:
            print(f"Chrome stderr: {result.stderr}", file=sys.stderr)
            raise RuntimeError(f"Chrome exited with code {result.returncode}")
    finally:
        os.unlink(html_path)

    if not output_path.exists():
        raise RuntimeError(f"Chrome did not create {output_path}")

    # Crop to exact target dimensions (Chrome viewport may include buffer)
    from PIL import Image

    img = Image.open(output_path)
    if img.height > target_height or img.width > width:
        img = img.crop((0, 0, min(img.width, width), min(img.height, target_height)))
        img.save(output_path)

    size = output_path.stat().st_size
    print(
        f"Rendered {output_path.name} ({mode}, {width}x{target_height}, bg={bg_css}, {size:,} bytes)"
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(
        prog="render-png",
        description="Render SVG to PNG via headless Chrome with dark/light mode.",
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
