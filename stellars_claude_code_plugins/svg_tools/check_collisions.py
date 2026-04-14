"""Collision detection CLI for SVG connectors.

Wraps `detect_collisions` from calc_connector. Accepts a list of connectors
as Python literals in one of three forms:

1. List of sample lists:
     --connectors "[[(0,0),(100,100)], [(0,100),(100,0)]]"

2. List of (label, sample_list) tuples:
     --connectors "[('a',[(0,0),(100,100)]), ('b',[(0,100),(100,0)])]"

3. List of SVG path d strings (limited - only M/L commands supported for the
   parser, suitable for trimmed_path_d from calc_connector results):
     --connectors-d '["M0,0 L100,100", "M0,100 L100,0"]'

Outputs a JSON report of collision dicts to stdout. Each collision is:

    {"a": label_a, "b": label_b, "type": "crossing|near-miss|touching",
     "points": [[x,y],...], "min_distance": float}
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys


def _parse_path_d(path_d: str) -> list[tuple[float, float]]:
    """Parse an SVG path d containing only M / L commands into (x, y) tuples.

    Handles trimmed paths from calc_connector: one M + zero or more L commands.
    Raises on anything more complex (C, Q, arcs) - use direct samples for those.
    """
    tokens = re.findall(r"[MLml]|-?\d+(?:\.\d+)?", path_d)
    out: list[tuple[float, float]] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("M", "m", "L", "l"):
            # Two numeric tokens follow
            if i + 2 >= len(tokens):
                raise ValueError(f"truncated path at token {i}: {path_d!r}")
            x = float(tokens[i + 1])
            y = float(tokens[i + 2])
            out.append((x, y))
            i += 3
        else:
            raise ValueError(f"unexpected token {tok!r} in path d (only M/L supported)")
    return out


def _load_connectors(args) -> tuple[list[list[tuple]], list[str]]:
    """Normalise CLI inputs into (list_of_sample_lists, list_of_labels)."""
    if args.connectors_d is not None:
        path_list = ast.literal_eval(args.connectors_d)
        samples_list = [_parse_path_d(d) for d in path_list]
        labels = [f"c{i}" for i in range(len(samples_list))]
        return samples_list, labels
    if args.connectors is not None:
        parsed = ast.literal_eval(args.connectors)
        samples_list: list[list[tuple]] = []
        labels: list[str] = []
        for idx, item in enumerate(parsed):
            if (
                isinstance(item, tuple)
                and len(item) == 2
                and isinstance(item[0], str)
                and isinstance(item[1], list)
            ):
                labels.append(item[0])
                samples_list.append(item[1])
            elif isinstance(item, list):
                labels.append(f"c{idx}")
                samples_list.append(item)
            else:
                raise ValueError(f"item {idx} is not a sample list or (label, samples) tuple")
        return samples_list, labels
    raise ValueError("either --connectors or --connectors-d is required")


def main():
    parser = argparse.ArgumentParser(
        prog="svg-infographics collide",
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--connectors",
        default=None,
        help='Python-literal list of sample lists or (label, samples) tuples',
    )
    parser.add_argument(
        "--connectors-d",
        default=None,
        help='Python-literal list of SVG path d strings (M/L only)',
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.0,
        help="collision padding in pixels (default: 0 - strict crossing only)",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="write JSON report to file (default: stdout)",
    )
    args = parser.parse_args()

    # Late import: calc_connector is in the same package.
    from stellars_claude_code_plugins.svg_tools.calc_connector import detect_collisions

    samples_list, labels = _load_connectors(args)
    collisions = detect_collisions(samples_list, tolerance=args.tolerance, labels=labels)

    report = json.dumps(collisions, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(report + "\n")
        print(f"wrote {args.out} ({len(collisions)} collisions)", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
