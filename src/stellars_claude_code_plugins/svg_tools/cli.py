"""Unified CLI for SVG infographic tools.

Usage:
    svg-infographics overlaps --svg file.svg [--inject-bounds] [--strip-bounds]
    svg-infographics contrast --svg file.svg [--level AA|AAA] [--show-all]
    svg-infographics alignment --svg file.svg [--grid 5] [--tolerance 0]
    svg-infographics connectors --svg file.svg
    svg-infographics css --svg file.svg [--strict]
    svg-infographics connector --from X,Y --to X,Y [--margin N] [--cutout X,Y,W,H]
    svg-infographics connector --mode l --from X,Y --to X,Y --first-axis h|v --arrow end
    svg-infographics connector --mode l-chamfer --from X,Y --to X,Y --chamfer 4
    svg-infographics connector --mode spline --waypoints "x1,y1 x2,y2 ..." --samples 200 --arrow both
    svg-infographics connector --mode manifold --starts "..." --ends "..." --merge-points "..." --fork-points "..." --shape l-chamfer
    svg-infographics primitives rect --x 20 --y 30 --width 200 --height 100
    svg-infographics primitives spline --points "80,200 150,80 300,120 450,60"
    svg-infographics primitives axis --origin 80,200 --length 400 --axes xyz --ticks 5
    svg-infographics text-to-path --text "Hello" --font path/to/Inter.ttf --size 24 --x 100 --y 200
"""

import sys

SUBCOMMANDS = {
    # ---- QUARTERMASTER / PRE-FLIGHT (declare intent, pull rules) ----
    "preflight": (
        "manifest",
        "PRE-FLIGHT: declare what you will build via flags; tool returns the matching rule bundle + warnings. Run FIRST, before authoring any <rect>.",
    ),
    "check": (
        "manifest",
        "CHECK: verify an SVG matches a flag-based declaration. Exits 1 on component-count drift or missing dark-mode.",
    ),
    "finalize": (
        "finalize",
        "FINALIZE: ship-ready gate. Runs XML + overlap + connector validators and returns exit 1 on any HARD finding. One answer: is this file shippable?",
    ),
    # ---- VALIDATORS (read an SVG, report problems) ----
    "overlaps": (
        "check_overlaps",
        "VALIDATE: text/shape overlaps, spacing rhythm, font sizes. Run on every finished SVG.",
    ),
    "contrast": (
        "check_contrast",
        "VALIDATE: WCAG 2.1 text contrast AND object-vs-background contrast in light + dark mode.",
    ),
    "alignment": (
        "check_alignment",
        "VALIDATE: grid snapping, vertical rhythm, topology. Catches eyeballed positions.",
    ),
    "connectors": (
        "check_connectors",
        "VALIDATE: connector quality (zero-length, edge-snap, L-routing chamfer, dangling ends).",
    ),
    "css": (
        "check_css",
        "VALIDATE: CSS compliance (inline fills that should be classes, missing dark-mode overrides).",
    ),
    "validate": (
        "check_svg_valid",
        "VALIDATE: XML well-formedness + SVG structural sanity. Catches '-- in comment' bugs, missing viewBox, empty <path d>. Run LAST on every finished SVG.",
    ),
    # ---- CALCULATORS (produce numbers + SVG snippets you paste in) ----
    "primitives": (
        "calc_primitives",
        "CALC primitive shapes with anchors: rect, circle, ellipse, hex, star, cube, cylinder, sphere, axis, spline.",
    ),
    "connector": (
        "calc_connector",
        "CALC connector geometry: straight, L, L-chamfer, PCHIP spline, or manifold (N starts + M ends with per-start merge points and per-end fork points). Returns trimmed path + arrowhead polygons + tangent angles.",
    ),
    "geom": (
        "calc_geometry",
        "CALC sketch constraints: attachment points, midpoint, tangent, intersection, offset, evenly-spaced, polar, bisector. The Fusion-360 toolkit.",
    ),
    "charts": (
        "charts",
        "CALC data charts as SVG via pygal: line, bar, hbar, area, radar, dot, histogram, pie. Themed (stellars-tech / kolomolo / meridian / neutral).",
    ),
    "empty-space": (
        "calc_empty_space",
        "CALC empty regions on an SVG canvas via svgelements + bitmap. GENERAL-PURPOSE placement tool: icons, text blocks, callouts, decorative elements, or any new content. Run before adding anything to verify it fits and to pick the target zone. Not a callout-only tool.",
    ),
    "callouts": (
        "propose_callouts",
        "CALC joint callout placement proposals. Given an SVG and a list of callout requests, returns one best layout plus top-N alternatives per callout with penalty breakdowns.",
    ),
    "place": (
        "place_icon",
        "PLACE: position an element (icon, text bbox, badge) inside a named container using the empty-space finder. Returns top-left (x, y) respecting margins. Use for every icon AND every text block instead of hand-positioning.",
    ),
    "collide": (
        "check_collisions",
        "VALIDATE: pairwise collision detection on a set of connectors (crossing, near-miss with tolerance, touching). Uses shapely LineString geometry.",
    ),
    # ---- ON-REQUEST ONLY (bundled, no optional extra needed) ----
    "text-to-path": (
        "text_to_path",
        "ON REQUEST: convert text + TTF/OTF font into SVG <path> outlines. Embeds text without font dependency.",
    ),
    # ---- DRAW.IO SHAPE LIBRARY ----
    "shapes": (
        "drawio_shapes",
        "SHAPES: index, search, catalogue, and render draw.io stencil libraries as SVG snippets.",
    ),
    # ---- BACKGROUND TEXTURE GENERATOR ----
    "background": (
        "gen_backgrounds",
        "BG: procedural background textures (circuit, neural, topo, grid, organic, celtic, scifi, constellation, flourish, geometric, crystalline).",
    ),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("svg-infographics - SVG infographic validation and geometry tools")
        print()
        print("Subcommands:")
        for name, (_, desc) in SUBCOMMANDS.items():
            print(f"  {name:<14} {desc}")
        print()
        print("Usage: svg-infographics <subcommand> [options]")
        print("       svg-infographics <subcommand> --help  for subcommand options")
        sys.exit(0)

    subcommand = sys.argv[1]

    if subcommand not in SUBCOMMANDS:
        print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
        print("Run 'svg-infographics --help' for available subcommands.", file=sys.stderr)
        sys.exit(1)

    module_name = SUBCOMMANDS[subcommand][0]
    # The manifest module hosts multiple sub-subcommands (preflight / check)
    # under one parser, so it needs the subcommand name preserved in argv.
    # Everything else is a single-subcommand module and gets the
    # subcommand folded into the prog name.
    if module_name == "manifest":
        sys.argv = [f"svg-infographics {subcommand}", subcommand] + sys.argv[2:]
    else:
        sys.argv = [f"svg-infographics {subcommand}"] + sys.argv[2:]

    module = __import__(
        f"stellars_claude_code_plugins.svg_tools.{module_name}",
        fromlist=["main"],
    )
    rc = module.main()
    # Propagate the subcommand's exit code. Modules that historically
    # never returned (e.g. raise SystemExit internally) yield None, which
    # we treat as success to preserve legacy behaviour.
    if isinstance(rc, int):
        sys.exit(rc)


if __name__ == "__main__":
    main()
