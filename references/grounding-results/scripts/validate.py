#!/usr/bin/env python3
"""Benchmark score validator for grounding-improvements program.

Takes the five component values (each in ``[0, 1]``) and computes the
composite score per ``BENCHMARK.md``:

    quality = 0.30 * liu_accuracy
            + 0.25 * agreement_gap_attainment
            + 0.25 * numeric_recall
            + 0.10 * portability_pass
            + 0.10 * skill_rules_present

    score   = round(100 * (1 - quality), 1)

Direction: MINIMIZE. Target: 0.

Usage:

    # Positional or flag-based inputs
    python scripts/validate.py \\
        --liu-accuracy 0.857 \\
        --agreement-gap-attainment 0.20 \\
        --numeric-recall 0.0 \\
        --portability-pass 0 \\
        --skill-rules-present 0

    # Or from the baseline-seed shorthand
    python scripts/validate.py --baseline

    # Machine-readable output
    python scripts/validate.py --liu-accuracy 1.0 ... --json
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import sys

WEIGHTS: dict[str, float] = {
    "liu_accuracy": 0.30,
    "agreement_gap_attainment": 0.25,
    "numeric_recall": 0.25,
    "portability_pass": 0.10,
    "skill_rules_present": 0.10,
}

BASELINE: dict[str, float] = {
    "liu_accuracy": 0.857,
    "agreement_gap_attainment": 0.200,
    "numeric_recall": 0.000,
    "portability_pass": 0.0,
    "skill_rules_present": 0.0,
}

TARGET: dict[str, float] = {
    "liu_accuracy": 1.000,
    "agreement_gap_attainment": 1.000,
    "numeric_recall": 0.800,
    "portability_pass": 1.0,
    "skill_rules_present": 1.0,
}


@dataclass
class Components:
    liu_accuracy: float
    agreement_gap_attainment: float
    numeric_recall: float
    portability_pass: float
    skill_rules_present: float

    def validate_ranges(self) -> list[str]:
        errs: list[str] = []
        for name, val in self.as_dict().items():
            if not 0.0 <= val <= 1.0:
                errs.append(f"{name}={val} not in [0, 1]")
        return errs

    def as_dict(self) -> dict[str, float]:
        return {
            "liu_accuracy": self.liu_accuracy,
            "agreement_gap_attainment": self.agreement_gap_attainment,
            "numeric_recall": self.numeric_recall,
            "portability_pass": self.portability_pass,
            "skill_rules_present": self.skill_rules_present,
        }


def compute(c: Components) -> dict:
    """Compute quality + score + per-component breakdown."""
    vals = c.as_dict()
    contribs = {k: WEIGHTS[k] * vals[k] for k in WEIGHTS}
    quality = sum(contribs.values())
    score = round(100.0 * (1.0 - quality), 1)

    max_contrib = {k: WEIGHTS[k] for k in WEIGHTS}  # if value == 1.0
    residuals = {k: round(max_contrib[k] - contribs[k], 4) for k in WEIGHTS}

    return {
        "components": vals,
        "weights": WEIGHTS,
        "contributions": {k: round(v, 4) for k, v in contribs.items()},
        "residuals": residuals,
        "quality": round(quality, 4),
        "score": score,
    }


def render_text(result: dict) -> str:
    lines = [
        "=" * 60,
        "Grounding benchmark score",
        "=" * 60,
        "",
        f"{'Component':<30} {'Value':>7} {'Weight':>7} {'Contrib':>9} {'Resid':>7}",
        "-" * 60,
    ]
    for k in WEIGHTS:
        lines.append(
            f"{k:<30} "
            f"{result['components'][k]:>7.3f} "
            f"{result['weights'][k]:>7.2f} "
            f"{result['contributions'][k]:>9.4f} "
            f"{result['residuals'][k]:>7.4f}"
        )
    lines.extend(
        [
            "-" * 60,
            f"{'TOTAL':<30} {' ':>7} {'1.00':>7} "
            f"{result['quality']:>9.4f} {round(1.0 - result['quality'], 4):>7}",
            "",
            f"quality = {result['quality']}",
            f"score   = {result['score']}  (MINIMIZE toward 0)",
            "",
        ]
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="validate",
        description=(
            "Compute the grounding-improvements benchmark score from its five "
            "component values (each in [0, 1]). See BENCHMARK.md."
        ),
    )
    for name in WEIGHTS:
        flag = "--" + name.replace("_", "-")
        p.add_argument(flag, type=float, help=f"{name} in [0, 1]")
    p.add_argument(
        "--baseline",
        action="store_true",
        help="Use the baseline values from BENCHMARK.md (v1.3.26 state)",
    )
    p.add_argument(
        "--target",
        action="store_true",
        help="Use the target values from BENCHMARK.md",
    )
    p.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of formatted text",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.baseline and args.target:
        print("ERROR: --baseline and --target are mutually exclusive", file=sys.stderr)
        return 1
    if args.baseline:
        src = BASELINE
    elif args.target:
        src = TARGET
    else:
        src = {
            k: getattr(args, k.replace("-", "_"), None) for k in WEIGHTS
        }

    missing = [k for k, v in src.items() if v is None]
    if missing:
        print(
            "ERROR: missing value(s): " + ", ".join(missing) + "\n"
            "Pass each via --<name> or use --baseline / --target.",
            file=sys.stderr,
        )
        return 1

    c = Components(**{k: float(src[k]) for k in WEIGHTS})
    range_errs = c.validate_ranges()
    if range_errs:
        for e in range_errs:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1

    result = compute(c)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(render_text(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
