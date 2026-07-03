"""Space map: one-glance per-layer + global occupancy scan of an SVG.

The cheap "where is everything" tool: ONE SVG parse, one obstacle bucket
per canonical layer, one coarse ASCII grid where each cell shows the
TOPMOST occupying layer (callouts > content > connectors > nodes >
background). The agent reads the map instead of running several
empty-space calls and reconstructing the scene mentally.

Legend: ``b``=background ``n``=nodes ``c``=connectors ``t``=content(text)
``o``=callouts ``?``=unlayered ``.``=free.

Usage:
    svg-infographics map --svg file.svg [--cell 30] [--json]
"""

import argparse
import json as _json
import sys

# Render order bottom-up; occupancy display picks the TOPMOST.
_LAYER_LETTERS = {
    "background": "b",
    "nodes": "n",
    "connectors": "c",
    "content": "t",
    "callouts": "o",
    None: "?",
}
_TOP_FIRST = ("callouts", "content", "connectors", "nodes", "background", None)

# A cell counts as occupied when at least this fraction of its pixels is.
_CELL_OCCUPANCY_THRESHOLD = 0.05
_MAX_GRID_COLS = 48


def _largest_rect(free):
    """Largest all-True axis-aligned rectangle in a boolean grid.

    Classic largest-rectangle-in-histogram sweep, O(rows*cols). Returns
    ``(row, col, height, width)`` in cell units, or None when no free
    cell exists.
    """
    rows, cols = free.shape
    heights = [0] * cols
    best = None  # (area, r, c, h, w)
    for r in range(rows):
        for c in range(cols):
            heights[c] = heights[c] + 1 if free[r, c] else 0
        stack: list[int] = []
        c = 0
        while c <= cols:
            cur = heights[c] if c < cols else 0
            if not stack or cur >= heights[stack[-1]]:
                stack.append(c)
                c += 1
                continue
            top = stack.pop()
            width = c - stack[-1] - 1 if stack else c
            area = heights[top] * width
            if area and (best is None or area > best[0]):
                left = stack[-1] + 1 if stack else 0
                best = (area, r - heights[top] + 1, left, heights[top], width)
        # keep sweeping next row
    if best is None:
        return None
    _, r, c, h, w = best
    return (r, c, h, w)


def space_map(svg, cell=None):
    """Compute per-layer occupancy masks and the combined cell grid.

    Returns a dict: ``canvas``, ``cell``, ``grid`` (list of strings, one
    per cell row), ``layers`` (per-layer stats), ``free_regions`` (top-5
    global free bboxes ``(x, y, w, h, area)``).
    """
    import numpy as np
    import svgelements as _se

    from stellars_claude_code_plugins.svg_tools.calc_empty_space import (
        _element_to_surrogates,
        _is_canvas_background,
        _parse_svg_source,
        _rasterise_surrogates,
    )

    svg_doc, canvas = _parse_svg_source(svg)
    x0, y0, W, H = canvas

    buckets: dict = {}

    def walk(node, layer=None, depth=0):
        if not _is_canvas_background(node, canvas):
            raw = _element_to_surrogates(node)
            if raw:
                buckets.setdefault(layer, []).extend(raw)
        if isinstance(node, _se.Group):
            for child in node:
                child_layer = getattr(child, "id", None) if depth == 0 else layer
                if depth == 0 and child_layer not in _LAYER_LETTERS:
                    child_layer = None  # non-canonical top-level group
                walk(child, layer=child_layer, depth=depth + 1)

    walk(svg_doc)

    if cell is None:
        cell = max(10, int(round(W / _MAX_GRID_COLS / 10.0) * 10) or 10)
    cell = int(cell)
    g_cols = max(1, int(np.ceil(W / cell)))
    g_rows = max(1, int(np.ceil(H / cell)))

    def downsample(mask):
        pad_r = g_rows * cell - mask.shape[0]
        pad_c = g_cols * cell - mask.shape[1]
        padded = np.pad(mask, ((0, pad_r), (0, pad_c)))
        cells = padded.reshape(g_rows, cell, g_cols, cell).mean(axis=(1, 3))
        return cells >= _CELL_OCCUPANCY_THRESHOLD

    layer_stats = {}
    layer_cells = {}
    combined = np.zeros((int(H), int(W)), dtype=bool)
    for layer, surrogates in buckets.items():
        mask = _rasterise_surrogates(canvas, surrogates)
        combined |= mask
        layer_cells[layer] = downsample(mask)
        occupied = np.argwhere(mask)
        if occupied.size:
            rmin, cmin = occupied.min(axis=0)
            rmax, cmax = occupied.max(axis=0)
            extent = (
                float(x0 + cmin),
                float(y0 + rmin),
                float(x0 + cmax),
                float(y0 + rmax),
            )
        else:
            extent = None
        layer_stats[layer if layer is not None else "?"] = {
            "occupancy_pct": round(100.0 * mask.mean(), 1),
            "extent": extent,
        }

    # Combined ASCII grid: topmost layer letter per cell.
    grid_rows = []
    for r in range(g_rows):
        row_chars = []
        for c in range(g_cols):
            ch = "."
            for layer in _TOP_FIRST:
                cells = layer_cells.get(layer)
                if cells is not None and cells[r, c]:
                    ch = _LAYER_LETTERS[layer]
                    break
            row_chars.append(ch)
        grid_rows.append("".join(row_chars))

    # Global free PLACEMENT rectangles: greedy largest-empty-rectangle on
    # the combined cell grid (connected-component bboxes mislead - the
    # ring of free space around obstacles spans the whole canvas). Each
    # rect is directly usable as a "put it here" box.
    combined_cells = downsample(combined)
    free_cells = ~combined_cells
    free_regions = []
    for _ in range(5):
        rect = _largest_rect(free_cells)
        if rect is None:
            break
        r, c, h_cells, w_cells = rect
        if h_cells * w_cells < 4:  # ignore slivers below 2x2 cells
            break
        free_regions.append(
            {
                "x": float(x0 + c * cell),
                "y": float(y0 + r * cell),
                "w": float(w_cells * cell),
                "h": float(h_cells * cell),
                "area": int(w_cells * cell * h_cells * cell),
            }
        )
        free_cells[r : r + h_cells, c : c + w_cells] = False

    return {
        "canvas": [x0, y0, W, H],
        "cell": cell,
        "grid": grid_rows,
        "layers": layer_stats,
        "free_regions": free_regions,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="svg-infographics map",
        description=(
            "One-glance occupancy map: coarse ASCII grid of the canvas where "
            "each cell shows the topmost occupying layer (b/n/c/t/o, '.' = "
            "free), plus per-layer occupancy stats and the largest global "
            "free regions. Run before placing anything - it replaces several "
            "empty-space calls with one scan."
        ),
    )
    parser.add_argument("--svg", required=True, help="SVG file to map")
    parser.add_argument(
        "--cell",
        type=int,
        default=None,
        help="Cell size in px (default: canvas width / ~48 columns)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    args = parser.parse_args(argv)

    report = space_map(args.svg, cell=args.cell)

    if args.json:
        _json.dump(report, sys.stdout, indent=2)
        print()
        return 0

    x0, y0, W, H = report["canvas"]
    print(
        f"=== SPACE MAP {args.svg} ({W:g}x{H:g}, cell {report['cell']}px, "
        f"{len(report['grid'][0])}x{len(report['grid'])} cells) ==="
    )
    print("legend: b=background n=nodes c=connectors t=content o=callouts ?=unlayered .=free")
    print()
    for row in report["grid"]:
        print(f"  {row}")
    print()
    print("layer occupancy:")
    for layer in ("background", "nodes", "connectors", "content", "callouts", "?"):
        stats = report["layers"].get(layer)
        if stats is None:
            continue
        if stats["extent"]:
            ex = stats["extent"]
            extent = f"extent ({ex[0]:.0f},{ex[1]:.0f})-({ex[2]:.0f},{ex[3]:.0f})"
        else:
            extent = "empty"
        print(f"  {layer:<11} {stats['occupancy_pct']:>5.1f}%  {extent}")
    if report["free_regions"]:
        print("free regions (global, largest first):")
        for r in report["free_regions"]:
            print(f"  ({r['x']:.0f},{r['y']:.0f}) {r['w']:.0f}x{r['h']:.0f} area={r['area']}px^2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
