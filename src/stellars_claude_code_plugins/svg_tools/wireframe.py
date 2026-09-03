"""CLI that draws a real object as an SVG wireframe fragment.

Usage:
    svg-infographics wireframe --model anvil
    svg-infographics wireframe --model anvil --style hidden --w 400 --h 400
    svg-infographics wireframe --model ./car.obj --yaw 35 --pitch 20 --fov 25
    svg-infographics wireframe --model anvil --preview
    svg-infographics wireframe --model anvil --json

``--model`` takes a catalogue slug (see ``svg-infographics mesh search``), which
is downloaded once into the mesh cache, or a path to an OBJ file. The default
output is a ``<g class="wireframe">`` fragment the caller places with a
``transform``; colours come from the caller's CSS.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools.mesh_cache import MeshFetchError
from stellars_claude_code_plugins.svg_tools.mesh_catalog import resolve
from stellars_claude_code_plugins.svg_tools.obj_mesh import load_obj
from stellars_claude_code_plugins.svg_tools.wireframe_render import (
    DEFAULT_FIT,
    DEFAULT_FOV,
    DEFAULT_PITCH,
    DEFAULT_STROKE_WIDTH,
    DEFAULT_YAW,
    STYLES,
    WireframeResult,
    render_wireframe,
)

_PREVIEW_BACKGROUND = "#F3F4EC"
_PREVIEW_STROKE = "#1f2937"


def model_path(model: str) -> tuple[Path, str]:
    """Resolve ``--model`` to an OBJ file on disk.

    Args:
        model: Catalogue slug, or a path to an OBJ file.

    Returns:
        tuple[Path, str]: The OBJ path and the model name to label the drawing with.

    Raises:
        KeyError: The slug is not in the catalogue.
        MeshFetchError: The slug is known but could not be downloaded.
    """
    candidate = Path(model)
    if candidate.suffix.lower() == ".obj" or candidate.is_file():
        return candidate, candidate.stem
    return resolve(model), model


def _print_fragment(result: WireframeResult) -> None:
    """Print the placeable ``<g class="wireframe">`` group."""
    x, y, w, h = result.bbox
    print(
        f'<g class="wireframe" data-model="{result.model}" '
        f'data-bbox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}">'
    )
    for element in result.elements:
        print(f"  {element.svg}")
    print("</g>")


def _print_preview(result: WireframeResult, w: float, h: float) -> None:
    """Print a full SVG so the fragment can be rendered on its own."""
    print(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}">')
    print(f'  <rect width="{w}" height="{h}" fill="{_PREVIEW_BACKGROUND}"/>')
    print(f'  <g fill="{_PREVIEW_BACKGROUND}" stroke="{_PREVIEW_STROKE}" stroke-linejoin="round">')
    for element in result.elements:
        print(f"    {element.svg}")
    print("  </g>")
    print("</svg>")


def main() -> int:
    """Entry point for the ``wireframe`` subcommand of ``svg-infographics``."""
    parser = argparse.ArgumentParser(
        prog="svg-infographics wireframe",
        description="Draw a catalogue mesh or an OBJ file as SVG wireframe geometry.",
    )
    parser.add_argument("--model", required=True, help="Catalogue slug or path to an .obj file.")
    parser.add_argument(
        "--style", choices=STYLES, default="wire", help="wire or hidden (default: wire)"
    )
    parser.add_argument("--w", type=float, default=400, help="Canvas width (default: 400)")
    parser.add_argument("--h", type=float, default=400, help="Canvas height (default: 400)")
    parser.add_argument(
        "--yaw",
        type=float,
        default=DEFAULT_YAW,
        help=f"Degrees about the up axis (default: {DEFAULT_YAW})",
    )
    parser.add_argument(
        "--pitch",
        type=float,
        default=DEFAULT_PITCH,
        help=f"Degrees about the screen-horizontal axis (default: {DEFAULT_PITCH})",
    )
    parser.add_argument(
        "--roll", type=float, default=0.0, help="Degrees about the view axis (default: 0)"
    )
    parser.add_argument(
        "--fov",
        type=float,
        default=DEFAULT_FOV,
        help=f"Field of view in degrees, 0 for orthographic (default: {DEFAULT_FOV})",
    )
    parser.add_argument(
        "--fit",
        type=float,
        default=DEFAULT_FIT,
        help=f"Margin as a fraction of each canvas side (default: {DEFAULT_FIT})",
    )
    parser.add_argument(
        "--stroke-width",
        type=float,
        default=DEFAULT_STROKE_WIDTH,
        help=f"Stroke width on every element (default: {DEFAULT_STROKE_WIDTH})",
    )
    parser.add_argument("--preview", action="store_true", help="Wrap in a full SVG for preview")
    parser.add_argument("--json", action="store_true", help="Output drawing metadata as JSON")
    args = parser.parse_args()

    try:
        path, name = model_path(args.model)
        mesh = load_obj(path)
    except (KeyError, MeshFetchError, FileNotFoundError, ValueError) as exc:
        print(f"wireframe: {exc}", file=sys.stderr)
        if isinstance(exc, (KeyError, MeshFetchError)):
            print(
                f"Cache a catalogue mesh with: svg-infographics mesh fetch {args.model}",
                file=sys.stderr,
            )
        return 1

    result = render_wireframe(
        mesh,
        model=name,
        style=args.style,
        w=args.w,
        h=args.h,
        yaw=args.yaw,
        pitch=args.pitch,
        roll=args.roll,
        fov=args.fov,
        fit=args.fit,
        stroke_width=args.stroke_width,
    )

    if args.json:
        json.dump(
            {
                "model": result.model,
                "style": result.style,
                "bbox": [round(v, 2) for v in result.bbox],
                "edge_count": result.edge_count,
                "face_count": result.face_count,
            },
            sys.stdout,
            indent=2,
        )
        print()
        return 0

    if args.preview:
        _print_preview(result, args.w, args.h)
    else:
        _print_fragment(result)
    print(
        f"\n<!-- {result.model} {result.style}: {len(result.elements)} elements -->",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
