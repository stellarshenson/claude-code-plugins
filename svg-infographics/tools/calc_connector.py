#!/usr/bin/env python3
"""
SVG connector calculator for the svg-infographics skill.

Computes angle, stem length, translate/rotate transform, and arrowhead coordinates
for a connector between two points, with optional margin (padding) at source and tip.

Usage:
    python calc_connector.py --from 520,55 --to 590,135
    python calc_connector.py --from 520,55 --to 590,135 --margin 6 --head-size 10,5
    python calc_connector.py --from 140,150 --to 220,55 --margin 4 --head-size 8,4

Arguments:
    --from X,Y        Source point (edge of source element)
    --to X,Y          Target point (edge of target element)
    --margin N        Padding in px to pull back from both source and target edges (default: 0)
    --head-size L,H   Arrowhead length and half-height (default: 10,5)

Output:
    All values needed to write the SVG connector:
    - angle (degrees)
    - stem start/end in local (pre-rotation) coordinates
    - translate and rotate values for the <g> transform
    - polygon points for the arrowhead
    - actual world coordinates of stem start, stem end, and tip after rotation
    - ready-to-paste SVG snippet

The connector is designed FLAT (horizontal, left-to-right) and then translated+rotated
into position. This means the stem is always a horizontal <line> and the arrowhead is
always a right-pointing <polygon> - the transform does all the angular work.

Pill cutout mode:
    --cutout X,Y,W,H   If a pill label sits on the connector, provide its rect.
                        The script splits the connector into two segments with a gap
                        around the pill (adds --margin padding around the pill rect).
"""

import argparse
import math
import sys


def calc_connector(src_x, src_y, tgt_x, tgt_y, margin=0, head_len=10, head_half_h=5):
    dx = tgt_x - src_x
    dy = tgt_y - src_y
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    full_length = math.sqrt(dx ** 2 + dy ** 2)

    # Effective length after pulling back margins from both ends
    effective_length = full_length - 2 * margin

    if effective_length <= head_len + 2:
        print(f"WARNING: effective length {effective_length:.1f}px too short for arrowhead", file=sys.stderr)

    # In local (flat) coordinates:
    # - tip is at origin (0, 0) after translate
    # - stem runs from (-effective_length, 0) to (-head_len, 0)
    # - arrowhead polygon at (0,0 -head_len,-head_half_h -head_len,head_half_h)
    stem_start_local = -effective_length
    stem_end_local = -head_len

    # The <g> transform translates to the tip position (target minus margin along the line)
    tip_x = tgt_x - margin * math.cos(angle_rad)
    tip_y = tgt_y - margin * math.sin(angle_rad)

    # World coordinates of stem start (for verification)
    stem_start_world_x = tip_x + stem_start_local * math.cos(angle_rad)
    stem_start_world_y = tip_y + stem_start_local * math.sin(angle_rad)

    # World coordinates of stem end (where arrowhead back sits)
    stem_end_world_x = tip_x + stem_end_local * math.cos(angle_rad)
    stem_end_world_y = tip_y + stem_end_local * math.sin(angle_rad)

    return {
        "angle_deg": angle_deg,
        "full_length": full_length,
        "effective_length": effective_length,
        "tip_x": tip_x,
        "tip_y": tip_y,
        "stem_start_local": stem_start_local,
        "stem_end_local": stem_end_local,
        "head_len": head_len,
        "head_half_h": head_half_h,
        "stem_start_world": (stem_start_world_x, stem_start_world_y),
        "stem_end_world": (stem_end_world_x, stem_end_world_y),
    }


def calc_cutout(src_x, src_y, tgt_x, tgt_y, pill_x, pill_y, pill_w, pill_h,
                margin=0, padding=3, head_len=10, head_half_h=5):
    """Split a connector into two segments with a gap around a pill rect."""
    dx = tgt_x - src_x
    dy = tgt_y - src_y
    angle_rad = math.atan2(dy, dx)
    length = math.sqrt(dx ** 2 + dy ** 2)

    # Pill rect with padding
    px1, py1 = pill_x - padding, pill_y - padding
    px2, py2 = pill_x + pill_w + padding, pill_y + pill_h + padding

    # Find where the line enters and exits the padded pill rect
    # Parameterize line as P = src + t * (tgt - src), t in [0, 1]
    # Check intersection with all 4 edges
    intersections = []
    for edge_val, is_x in [(px1, True), (px2, True), (py1, False), (py2, False)]:
        if is_x:
            if dx == 0:
                continue
            t = (edge_val - src_x) / dx
        else:
            if dy == 0:
                continue
            t = (edge_val - src_y) / dy

        if 0 < t < 1:
            ix = src_x + t * dx
            iy = src_y + t * dy
            if px1 - 1 <= ix <= px2 + 1 and py1 - 1 <= iy <= py2 + 1:
                intersections.append((t, ix, iy))

    if len(intersections) < 2:
        return None  # Line doesn't cross pill

    intersections.sort(key=lambda x: x[0])
    t_enter, enter_x, enter_y = intersections[0]
    t_exit, exit_x, exit_y = intersections[-1]

    # Segment 1: source -> pill entry
    seg1 = calc_connector(src_x, src_y, enter_x, enter_y, margin=margin,
                          head_len=0, head_half_h=0)  # No arrowhead on seg1

    # Segment 2: pill exit -> target (with arrowhead)
    seg2 = calc_connector(exit_x, exit_y, tgt_x, tgt_y, margin=margin,
                          head_len=head_len, head_half_h=head_half_h)

    return {
        "segment1": seg1,
        "segment1_from": (src_x, src_y),
        "segment1_to": (enter_x, enter_y),
        "segment2": seg2,
        "segment2_from": (exit_x, exit_y),
        "segment2_to": (tgt_x, tgt_y),
    }


def format_svg(c, stroke_color="#5456f3", stroke_width="1.2", opacity="0.4"):
    """Generate ready-to-paste SVG snippet."""
    tip_x = c["tip_x"]
    tip_y = c["tip_y"]
    angle = c["angle_deg"]
    s_start = c["stem_start_local"]
    s_end = c["stem_end_local"]
    hl = c["head_len"]
    hh = c["head_half_h"]

    lines = []
    lines.append(f'  <!-- Connector: angle={angle:.1f}deg len={c["effective_length"]:.0f}px -->')

    if hl > 0:
        lines.append(
            f'  <g transform="translate({tip_x:.1f}, {tip_y:.1f}) rotate({angle:.1f})">'
        )
        lines.append(
            f'    <line x1="{s_start:.0f}" y1="0" x2="{s_end:.0f}" y2="0"'
            f' stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )
        lines.append(
            f'    <polygon points="0,0 -{hl},{-hh} -{hl},{hh}"'
            f' fill="{stroke_color}" opacity="0.6"/>'
        )
        lines.append("  </g>")
    else:
        # Stem only (no arrowhead) - for cutout segment 1
        lines.append(
            f'  <line x1="{c["stem_start_world"][0]:.1f}" y1="{c["stem_start_world"][1]:.1f}"'
            f' x2="{tip_x:.1f}" y2="{tip_y:.1f}"'
            f' stroke="{stroke_color}" stroke-width="{stroke_width}" opacity="{opacity}"/>'
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SVG connector calculator")
    parser.add_argument("--from", dest="src", required=True, help="Source point X,Y")
    parser.add_argument("--to", dest="tgt", required=True, help="Target point X,Y")
    parser.add_argument("--margin", type=float, default=0, help="Edge margin in px (default: 0)")
    parser.add_argument("--head-size", default="10,5", help="Arrowhead length,half-height (default: 10,5)")
    parser.add_argument("--cutout", default=None, help="Pill rect X,Y,W,H for cutout gap")
    parser.add_argument("--color", default="#5456f3", help="Stroke colour (default: #5456f3)")
    parser.add_argument("--width", default="1.2", help="Stroke width (default: 1.2)")
    parser.add_argument("--opacity", default="0.4", help="Stroke opacity (default: 0.4)")
    args = parser.parse_args()

    src_x, src_y = map(float, args.src.split(","))
    tgt_x, tgt_y = map(float, args.tgt.split(","))
    head_len, head_half_h = map(float, args.head_size.split(","))

    if args.cutout:
        px, py, pw, ph = map(float, args.cutout.split(","))
        result = calc_cutout(src_x, src_y, tgt_x, tgt_y, px, py, pw, ph,
                             margin=args.margin, head_len=head_len, head_half_h=head_half_h)
        if result is None:
            print("Line does not cross pill rect - no cutout needed")
            c = calc_connector(src_x, src_y, tgt_x, tgt_y,
                               margin=args.margin, head_len=head_len, head_half_h=head_half_h)
            print_result(c, args)
        else:
            print("=== CUTOUT MODE: two segments ===\n")
            s1 = result["segment1"]
            s2 = result["segment2"]
            print(f"Segment 1: ({result['segment1_from'][0]:.1f},{result['segment1_from'][1]:.1f})"
                  f" -> ({result['segment1_to'][0]:.1f},{result['segment1_to'][1]:.1f})")
            print(f"Segment 2: ({result['segment2_from'][0]:.1f},{result['segment2_from'][1]:.1f})"
                  f" -> ({result['segment2_to'][0]:.1f},{result['segment2_to'][1]:.1f})")
            print(f"\n--- SVG Snippet ---\n")
            print(format_svg(s1, args.color, args.width, args.opacity))
            print(format_svg(s2, args.color, args.width, args.opacity))
    else:
        c = calc_connector(src_x, src_y, tgt_x, tgt_y,
                           margin=args.margin, head_len=head_len, head_half_h=head_half_h)
        print_result(c, args)


def print_result(c, args):
    print(f"=== CONNECTOR ===")
    print(f"Source:           ({c['stem_start_world'][0]:.1f}, {c['stem_start_world'][1]:.1f})")
    print(f"Target (tip):     ({c['tip_x']:.1f}, {c['tip_y']:.1f})")
    print(f"Angle:            {c['angle_deg']:.1f} degrees")
    print(f"Full length:      {c['full_length']:.1f}px")
    print(f"Effective length: {c['effective_length']:.1f}px")
    print(f"")
    print(f"=== TRANSFORM ===")
    print(f"translate({c['tip_x']:.1f}, {c['tip_y']:.1f}) rotate({c['angle_deg']:.1f})")
    print(f"")
    print(f"=== LOCAL COORDINATES (flat, pre-rotation) ===")
    print(f"Stem:     x1={c['stem_start_local']:.0f}  x2={c['stem_end_local']:.0f}  y=0")
    print(f"Head:     points=\"0,0 -{c['head_len']},{-c['head_half_h']:.0f} -{c['head_len']},{c['head_half_h']:.0f}\"")
    print(f"")
    print(f"=== WORLD COORDINATES (after rotation, for verification) ===")
    print(f"Stem start: ({c['stem_start_world'][0]:.1f}, {c['stem_start_world'][1]:.1f})")
    print(f"Stem end:   ({c['stem_end_world'][0]:.1f}, {c['stem_end_world'][1]:.1f})")
    print(f"Tip:        ({c['tip_x']:.1f}, {c['tip_y']:.1f})")
    print(f"")
    print(f"--- SVG Snippet ---\n")
    print(format_svg(c, args.color, args.width, args.opacity))


if __name__ == "__main__":
    main()
