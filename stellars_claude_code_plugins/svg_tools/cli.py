"""Unified CLI for SVG infographic validation tools.

Usage:
    svg-infographics overlaps --svg file.svg [--inject-bounds] [--strip-bounds]
    svg-infographics contrast --svg file.svg [--level AA|AAA] [--show-all]
    svg-infographics alignment --svg file.svg [--grid 5] [--tolerance 0]
    svg-infographics connectors --svg file.svg
    svg-infographics connector --from X,Y --to X,Y [--margin N] [--cutout X,Y,W,H]
"""

import sys

SUBCOMMANDS = {
    "overlaps": ("check_overlaps", "Check element overlaps, spacing, typography"),
    "contrast": ("check_contrast", "WCAG 2.1 contrast validation (light + dark mode)"),
    "alignment": ("check_alignment", "Grid snapping, vertical rhythm, topology"),
    "connectors": ("check_connectors", "Connector quality (zero-length, edge-snap, L-routing)"),
    "connector": ("calc_connector", "Calculate connector geometry between two points"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("svg-infographics - SVG infographic validation tools")
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
