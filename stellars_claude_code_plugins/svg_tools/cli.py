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
    svg-infographics primitives rect --x 20 --y 30 --width 200 --height 100
    svg-infographics primitives spline --points "80,200 150,80 300,120 450,60"
    svg-infographics primitives axis --origin 80,200 --length 400 --axes xyz --ticks 5
"""

import sys

SUBCOMMANDS = {
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
    # ---- CALCULATORS (produce numbers + SVG snippets you paste in) ----
    "primitives": (
        "calc_primitives",
        "CALC primitive shapes with anchors: rect, circle, ellipse, hex, star, cube, cylinder, sphere, axis, spline.",
    ),
    "connector": (
        "calc_connector",
        "CALC connector geometry: straight, L, L-chamfer, or PCHIP spline. Returns trimmed path + arrowhead polygons + tangent angles.",
    ),
    "geom": (
        "calc_geometry",
        "CALC sketch constraints: attachment points, midpoint, tangent, intersection, offset, evenly-spaced, polar, bisector. The Fusion-360 toolkit.",
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
    sys.argv = [f"svg-infographics {subcommand}"] + sys.argv[2:]

    if subcommand not in SUBCOMMANDS:
        print(f"Unknown subcommand: {subcommand}", file=sys.stderr)
        print("Run 'svg-infographics --help' for available subcommands.", file=sys.stderr)
        sys.exit(1)

    module_name = SUBCOMMANDS[subcommand][0]
    module = __import__(
        f"stellars_claude_code_plugins.svg_tools.{module_name}",
        fromlist=["main"],
    )
    module.main()


if __name__ == "__main__":
    main()
