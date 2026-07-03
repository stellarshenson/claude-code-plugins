"""Scaffold generator for standard SVG infographic formats.

Emits a ready-to-author SVG skeleton for a named format (document band,
16:9 / 4:3 slide, square) with everything the workflow's grid + scaffold
phases used to hand-type:

- file description comment (placeholders to fill in)
- ``=== GRID REFERENCE ===`` comment with COMPUTED, 5px-snapped column /
  row origins
- ``=== LAYOUT TOPOLOGY ===`` stub listing the placeholders
- ``<style>`` block with the neutral theme classes + dark-mode overrides
- transparent backplate + hidden ``guide-grid`` (layout lines) + hidden
  multi-granularity inspection grids ``grid-100`` / ``grid-20`` /
  ``grid-5`` (pattern fills; flip ``display`` to inspect)
- the five canonical layers (background / nodes / connectors / content /
  callouts) as empty named groups
- placeholders tagged ``data-placeholder="true"``: grid card groups
  (``--cards N``), or the doc-header slot anatomy (banner plate, title,
  subtitle, logo, decor) when scaffolding ``doc-header`` without cards

A fresh scaffold passes ``finalize`` with zero findings - good by design.

Usage:
    svg-infographics scaffold --format doc-grid --cards 4 --out file.svg
    svg-infographics scaffold --format slide-16x9 --cols 3 --rows 2 --out deck_01.svg
    svg-infographics scaffold --list
"""

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from stellars_claude_code_plugins.svg_tools._layers import CANONICAL_LAYERS, LAYER_ROLES


@dataclass(frozen=True)
class Format:
    name: str
    width: int
    height: int
    margin_x: int
    margin_y: int
    rhythm: int
    description: str


# Canonical formats. Document bands follow standards-core sizes
# (default width 1800); slides are 16:9 / 4:3 presentation canvases.
FORMATS: dict[str, Format] = {
    f.name: f
    for f in (
        Format("doc-stats", 1800, 200, 40, 20, 14, "stats banner strip"),
        Format("doc-timeline", 1800, 280, 40, 24, 14, "timeline band"),
        Format("doc-flow", 1800, 320, 40, 24, 14, "flow diagram band"),
        Format("doc-header", 1800, 400, 40, 24, 14, "header / cover banner"),
        Format("doc-grid", 1800, 700, 40, 60, 16, "card grid / full infographic"),
        Format("slide-16x9", 1280, 720, 60, 50, 16, "16:9 presentation slide"),
        # 1020x765 rather than 1024x768: same exact 4:3 ratio, but every
        # dimension divides by 5 so the whole grid lands on the layout grid.
        Format("slide-4x3", 1020, 765, 50, 45, 16, "4:3 presentation slide"),
        Format("square", 1080, 1080, 60, 60, 16, "square social / icon canvas"),
    )
}

CARD_GAP = 20
ROW_GAP = 20
# Vertical band reserved above the grid when a --title is requested, so
# the title text clears the first card row by design (the overlap
# checker pads text and cards; a title squeezed into the margin fails).
TITLE_BAND = 40

# Layer roles, bottom-up render order. Canon lives in _layers.py so
# scaffold, empty-space, auto-route and the manifest check agree.
LAYERS: tuple[tuple[str, str], ...] = tuple((name, LAYER_ROLES[name]) for name in CANONICAL_LAYERS)

# Neutral safe palette from standards-core.md. A scaffolded file is
# expected to be re-themed against the approved swatch; the classes and
# dark-mode structure are what matter.
_STYLE_BLOCK = """  <style>
    .fg-1 { fill: #1e3a5f; }
    .fg-2 { fill: #2d4a73; }
    .fg-3 { fill: #6b7280; }
    .fg-4 { fill: #8a94a3; }
    .accent-1 { fill: #0284c7; }
    .accent-2 { fill: #7c3aed; }
    .on-fill { fill: #eef6fb; }
    .card { fill: #0284c7; fill-opacity: 0.04; stroke: #0284c7; stroke-width: 1; }
    .slot { fill: #0284c7; fill-opacity: 0.03; stroke: #0284c7; stroke-width: 1; stroke-dasharray: 6 4; }
    .arrow-stroke { stroke: #0284c7; }
    .arrow-fill { fill: #0284c7; }
    @media (prefers-color-scheme: dark) {
      .fg-1 { fill: #cfe2f5; }
      .fg-2 { fill: #aac8e8; }
      .fg-3 { fill: #93a1b5; }
      .fg-4 { fill: #7d8aa0; }
      .accent-1 { fill: #4fb7ea; }
      .accent-2 { fill: #a78bfa; }
      .on-fill { fill: #eef6fb; }
      .card { stroke: #4fb7ea; }
      .slot { stroke: #4fb7ea; }
      .arrow-stroke { stroke: #4fb7ea; }
      .arrow-fill { fill: #4fb7ea; }
    }
  </style>"""

# Hidden inspection grids, coarse to fine. Pattern fills keep the file
# tiny (one rect per grid) at any density; grid-5 matches the alignment
# checker's 5px snap unit. Flip display="none" off to inspect.
GRID_SCALES: tuple[tuple[int, float], ...] = ((100, 0.6), (20, 0.35), (5, 0.15))


def _snap_axis(total: float, margin: float, n: int, gap: float) -> tuple[float, float]:
    """Cell size + effective start margin for one axis, snapped to the
    5px layout grid.

    Cell sizes and origins land on multiples of 5 wherever the canvas
    allows (the alignment checker's grid), with the leftover centred
    symmetrically. Prefers the snap candidate whose centring margin is
    itself a multiple of 5.
    """
    usable = total - 2 * margin - (n - 1) * gap
    raw = usable / n
    candidates = [int(raw // 5) * 5, int(raw // 5) * 5 + 5]
    best = None
    for cell in candidates:
        if cell < 5:
            continue
        span = n * cell + (n - 1) * gap
        eff = (total - span) / 2
        if eff < 10:
            continue
        score = (eff % 5 != 0, abs(eff - margin))
        if best is None or score < best[0]:
            best = (score, cell, eff)
    if best is None:
        return round(raw, 1), margin
    _, cell, eff = best
    return float(cell), float(eff)


def compute_grid(fmt: Format, cols: int, rows: int, title_band: float = 0.0) -> dict:
    """Column / row origins and sizes for a cols x rows layout.

    Everything lands on the 5px layout grid by design (see ``_snap_axis``)
    so a fresh scaffold passes the alignment checker with zero findings.
    ``title_band`` reserves vertical space above the grid for a title.
    """
    col_w, mx = _snap_axis(fmt.width, fmt.margin_x, cols, CARD_GAP)
    row_h, my = _snap_axis(fmt.height - title_band, fmt.margin_y, rows, ROW_GAP)
    my += title_band
    columns = [round(mx + i * (col_w + CARD_GAP), 1) for i in range(cols)]
    row_ys = [round(my + j * (row_h + ROW_GAP), 1) for j in range(rows)]
    return {
        "columns": columns,
        "col_w": round(col_w, 1),
        "rows": row_ys,
        "row_h": round(row_h, 1),
        "margin_x": mx,
        "margin_y": my,
    }


def build_scaffold(
    fmt: Format,
    cols: int = 3,
    rows: int = 1,
    cards: int = 0,
    title: str = "",
) -> str:
    """Return the scaffold SVG text for ``fmt``."""
    grid = compute_grid(fmt, cols, rows, title_band=TITLE_BAND if title else 0.0)
    columns, col_w = grid["columns"], grid["col_w"]
    row_ys, row_h = grid["rows"], grid["row_h"]
    margin_x, margin_y = grid["margin_x"], grid["margin_y"]

    col_lines = "\n".join(
        f"    col-{i + 1}: x={x}..{round(x + col_w, 1)}  w={col_w}" for i, x in enumerate(columns)
    )
    row_lines = "\n".join(
        f"    row-{j + 1}: y={y}..{round(y + row_h, 1)}  h={row_h}" for j, y in enumerate(row_ys)
    )

    # Guide lines: real geometry so display="none" can be flipped while
    # authoring. Column boundaries + row boundaries + margin frame.
    guides = []
    for x in columns:
        guides.append(
            f'    <line x1="{x}" y1="0" x2="{x}" y2="{fmt.height}" '
            f'stroke="red" stroke-width="0.5"/>'
        )
        gx2 = round(x + col_w, 1)
        guides.append(
            f'    <line x1="{gx2}" y1="0" x2="{gx2}" y2="{fmt.height}" '
            f'stroke="red" stroke-width="0.5"/>'
        )
    for y in row_ys:
        guides.append(
            f'    <line x1="0" y1="{y}" x2="{fmt.width}" y2="{y}" '
            f'stroke="red" stroke-width="0.5"/>'
        )
        gy2 = round(y + row_h, 1)
        guides.append(
            f'    <line x1="0" y1="{gy2}" x2="{fmt.width}" y2="{gy2}" '
            f'stroke="red" stroke-width="0.5"/>'
        )
    guide_block = "\n".join(guides)

    # Per-layer placeholder inserts. Grid formats get row-major card
    # placeholders; doc-header (without --cards) gets its slot anatomy.
    layer_inserts: dict[str, str] = {name: "" for name, _ in LAYERS}
    topo_lines = "    (declare relationships here: h-stack / v-stack / contain / connect)"

    if fmt.name == "doc-header" and cards == 0:
        slots, topo_lines = _header_slots(fmt)
        for layer, markup in slots:
            layer_inserts[layer] += markup
    else:
        card_elems = []
        topology_cards = []
        for n in range(cards):
            col = n % cols
            row = n // cols
            if row >= rows:
                break
            x = columns[col]
            y = row_ys[row]
            card_elems.append(
                f'    <g id="card-{n + 1}" data-placeholder="true">\n'
                f'      <rect class="card" x="{x}" y="{y}" width="{col_w}" '
                f'height="{row_h}" rx="3"/>\n'
                f"    </g>"
            )
            topology_cards.append(f"card-{n + 1}")
        layer_inserts["nodes"] += ("\n" + "\n".join(card_elems)) if card_elems else ""

        if topology_cards:
            row_groups = [
                topology_cards[i : i + cols] for i in range(0, len(topology_cards), cols)
            ]
            topo_lines = "\n".join(
                f"    h-stack: {', '.join(group)} (gap={CARD_GAP})" for group in row_groups
            )
            topo_lines += f"\n    v-align: {', '.join(g[0] for g in row_groups)} share column x"

    if title:
        # Baseline 25px above the first row: clears the card outer bbox
        # (text pad 4 + card pad 6) by design and stays on the 5px grid.
        title_y = round(row_ys[0] - 25, 1)
        layer_inserts["content"] += (
            f'\n    <text class="fg-1" x="{margin_x}" y="{title_y}" '
            f'font-size="16" font-family="Segoe UI, Arial, sans-serif">{title}</text>'
        )

    layer_blocks = "\n".join(
        f'  <g id="{name}"><!-- {role} -->{layer_inserts[name]}\n  </g>' for name, role in LAYERS
    )

    # Multi-granularity inspection grids as pattern fills.
    pattern_defs = "\n".join(
        f'    <pattern id="grid-pat-{s}" width="{s}" height="{s}" '
        f'patternUnits="userSpaceOnUse">\n'
        f'      <path d="M {s} 0 L 0 0 0 {s}" fill="none" stroke="red" '
        f'stroke-width="{w}"/>\n'
        f"    </pattern>"
        for s, w in GRID_SCALES
    )
    grid_layers = "\n".join(
        f'  <g id="grid-{s}" display="none">'
        f'<rect x="0" y="0" width="{fmt.width}" height="{fmt.height}" '
        f'fill="url(#grid-pat-{s})"/></g>'
        for s, _ in GRID_SCALES
    )

    return f"""<!--
  SCAFFOLD ({fmt.name}) - fill in before delivery:
  filename.svg - <short role description>
  Shows: <visual elements in reading order>
  Intent: <purpose in document>
  Theme: neutral scaffold palette - re-theme against the approved swatch
-->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {fmt.width} {fmt.height}">
{_STYLE_BLOCK}

  <!-- === GRID REFERENCE ===
    viewBox: {fmt.width} x {fmt.height} ({fmt.name}: {fmt.description})
    Outer margins: {margin_x:g} left/right, {margin_y:g} top/bottom (5px-grid snapped)
    Vertical rhythm: {fmt.rhythm}px

    Columns (gap={CARD_GAP}):
{col_lines}

    Rows (gap={ROW_GAP}):
{row_lines}
  === -->

  <!-- === LAYOUT TOPOLOGY ===
{topo_lines}
  === -->

  <rect x="0" y="0" width="{fmt.width}" height="{fmt.height}" fill="transparent"/>

  <defs>
{pattern_defs}
  </defs>
{grid_layers}
  <g id="guide-grid" display="none">
{guide_block}
  </g>

{layer_blocks}
</svg>
"""


def _header_slots(fmt: Format) -> tuple[list[tuple[str, str]], str]:
    """Slot placeholders for the doc-header anatomy.

    Bounding boxes only (dashed ``.slot`` outlines, ``data-placeholder``)
    - the agent replaces each with real content: banner plate, title,
    subtitle, right-aligned logo, decorative zone. The user can always
    ask for a different composition; this is the starting concept.
    """
    W, H = fmt.width, fmt.height
    mx = fmt.margin_x

    def slot(sid, layer, x, y, w, h, note):
        return (
            layer,
            f'\n    <g id="{sid}" data-placeholder="true"><!-- {note} -->\n'
            f'      <rect class="slot" x="{x}" y="{y}" width="{w}" height="{h}"/>\n'
            f"    </g>",
        )

    logo_h = round(H * 0.4 / 5) * 5
    logo_x = W - mx - logo_h
    logo_y = round((H - logo_h) / 2 / 5) * 5
    slots = [
        slot(
            "slot-banner-plate",
            "background",
            0,
            0,
            W,
            H,
            "banner plate: full-bleed band or gradient - the one legitimate non-transparent bg",
        ),
        slot(
            "slot-decor",
            "background",
            round(W * 0.6 / 5) * 5,
            round(H * 0.15 / 5) * 5,
            round(W * 0.25 / 5) * 5,
            round(H * 0.7 / 5) * 5,
            "decorative imagery zone: fg-1/accent, opacity 0.30-0.35",
        ),
        slot(
            "slot-title",
            "content",
            mx + 20,
            round(H * 0.35 / 5) * 5,
            round(W * 0.45 / 5) * 5,
            60,
            "title block: 24-28px heading",
        ),
        slot(
            "slot-subtitle",
            "content",
            mx + 20,
            round(H * 0.35 / 5) * 5 + 80,
            round(W * 0.5 / 5) * 5,
            30,
            "subtitle / strapline: 12-14px",
        ),
        slot(
            "slot-logo",
            "content",
            logo_x,
            logo_y,
            logo_h,
            logo_h,
            "logo: right-aligned, aspect preserved, full opacity",
        ),
    ]
    topo = (
        "    contain: slot-banner-plate > slot-title, slot-subtitle, slot-decor, slot-logo\n"
        "    v-stack: slot-title, slot-subtitle (gap=20)\n"
        "    h-align: slot-title.left = slot-subtitle.left\n"
        "    mirror: slot-logo right margin = title left margin"
    )
    return slots, topo


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a ready-to-author SVG skeleton for a standard format: "
            "viewBox, grid comments, neutral theme CSS, guide grid, the five "
            "canonical layers, and optional placeholder cards."
        )
    )
    parser.add_argument(
        "--format",
        choices=sorted(FORMATS),
        help="Canvas format preset",
    )
    parser.add_argument("--list", action="store_true", help="List formats and exit")
    parser.add_argument("--cols", type=int, default=3, help="Grid columns (default 3)")
    parser.add_argument("--rows", type=int, default=1, help="Grid rows (default 1)")
    parser.add_argument(
        "--cards",
        type=int,
        default=0,
        help="Placeholder card rects to pre-place on the grid (row-major)",
    )
    parser.add_argument("--title", default="", help="Optional title text placeholder")
    parser.add_argument("--out", help="Output path; omit to print to stdout")
    parser.add_argument(
        "--force", action="store_true", help="Overwrite --out if it already exists"
    )
    args = parser.parse_args(argv)

    if args.list:
        print("Formats:")
        for f in FORMATS.values():
            print(f"  {f.name:<12} {f.width}x{f.height:<5} {f.description}")
        return 0

    if not args.format:
        parser.error("--format is required (or --list to see presets)")
    if args.cols < 1 or args.rows < 1:
        parser.error("--cols and --rows must be >= 1")
    if args.cards > args.cols * args.rows:
        parser.error(
            f"--cards {args.cards} does not fit a {args.cols}x{args.rows} grid; "
            "raise --rows / --cols"
        )

    fmt = FORMATS[args.format]
    svg = build_scaffold(fmt, cols=args.cols, rows=args.rows, cards=args.cards, title=args.title)

    if args.out:
        out = Path(args.out)
        if out.exists() and not args.force:
            print(f"ERROR: {out} exists - pass --force to overwrite", file=sys.stderr)
            return 1
        out.write_text(svg, encoding="utf-8")
        print(f"Scaffold written: {out} ({fmt.name}, {fmt.width}x{fmt.height})")
        print(
            "Next: fill the nodes layer (placeholder cards are tagged "
            'data-placeholder="true"), route arrows via `svg-infographics '
            "connector`, then `svg-infographics check` + `finalize`."
        )
    else:
        print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
