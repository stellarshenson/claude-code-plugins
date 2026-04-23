#!/usr/bin/env python3
"""Calibrate grounding configuration against the BENCHMARK.md composite score.

Runs a grid search over one or more tunable fields of :class:`GroundingConfig`
and reports the best-scoring combination against the five benchmark
components (liu_accuracy, agreement_gap_attainment, numeric_recall,
portability_pass, skill_rules_present).

A sweep spec is a YAML file mapping config field names to lists of candidate
values. Every combination of values is evaluated; the combination with the
lowest composite ``score`` wins.

Example sweep spec (``sweeps/agreement_sweep.yaml``)::

    agreement_threshold: [0.40, 0.45, 0.50, 0.55]
    classifier_mode: [absolute, adaptive_gap]
    entity_penalty_factor: [0.10, 0.15, 0.20]

This script:
    1. Reads the sweep spec.
    2. For each combination, writes a temporary ``.stellars-plugins/config.yaml``
       overlay.
    3. Runs all four ``scripts/bench_*.py`` probes to collect component values.
    4. Counts the three skill rules in ``validate-document/SKILL.md``.
    5. Computes the composite via ``scripts/validate.py --json``.
    6. Records ``{config_overlay, components, score}`` per run.

Output (JSON to stdout or to ``--output``):

    {
        "runs": [ ... sorted ascending by score ... ],
        "best": { overlay, components, score },
        "baseline_score": 69.3
    }

The original bundled config.yaml is NOT modified. Only the project-local
``.stellars-plugins/config.yaml`` overlay is touched; it is restored to its
pre-run contents (or deleted) when the run completes.

Usage:

    uv run python scripts/calibrate.py --sweep sweeps/my_sweep.yaml
    uv run python scripts/calibrate.py --sweep sweeps/my_sweep.yaml --output results.json
    uv run python scripts/calibrate.py --single  # just report the current score

Notes on cost:
    Each combination runs four bench scripts sequentially. The portability
    bench loads TWO embedding models, so it alone is 30-60 s per run. A
    sweep of 12 combinations takes ~10-15 minutes. Keep sweeps small.
"""

from __future__ import annotations

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OVERLAY_PATH = PROJECT_ROOT / ".stellars-plugins" / "config.yaml"
VALIDATE_PY = PROJECT_ROOT / "scripts" / "validate.py"
BENCH_DIR = PROJECT_ROOT / "scripts"
SKILL_MD = (
    PROJECT_ROOT / "document-processing" / "skills" / "validate-document" / "SKILL.md"
)


def _run_cmd(cmd: list[str]) -> str:
    """Run a shell command and return stripped stdout or raise."""
    result = subprocess.run(
        cmd, capture_output=True, text=True, cwd=str(PROJECT_ROOT), check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"stderr: {result.stderr.strip()[:300]}"
        )
    return result.stdout.strip()


def _bench_value(script_name: str) -> float:
    """Run a bench script and parse the last float on the last stdout line."""
    out = _run_cmd(["uv", "run", "python", str(BENCH_DIR / script_name)])
    # Bench scripts print progress to stderr; the number is on the last
    # stdout line. Some emit just the float, others the float after text.
    last = out.strip().splitlines()[-1].strip()
    try:
        return float(last)
    except ValueError:
        # Try extracting a trailing number from the last line
        tokens = last.split()
        for t in reversed(tokens):
            try:
                return float(t)
            except ValueError:
                continue
        raise RuntimeError(f"{script_name}: unable to parse a float from {out!r}")


def _skill_rules_count() -> float:
    """Return fraction of the three required skill rules present in SKILL.md."""
    if not SKILL_MD.is_file():
        return 0.0
    text = SKILL_MD.read_text(encoding="utf-8").lower()
    rules = (
        "agreement beats magnitude",
        "contradiction flag is the final word",
        "re-recommend semantic on struggle",
    )
    found = sum(1 for r in rules if r in text)
    return found / len(rules)


def _collect_components() -> dict[str, float]:
    """Run all probes and return the five benchmark components."""
    return {
        "liu_accuracy": _bench_value("bench_liu_accuracy.py"),
        "agreement_gap_attainment": _bench_value("bench_agreement_gap.py"),
        "numeric_recall": _bench_value("bench_numeric.py"),
        "portability_pass": _bench_value("bench_portability.py"),
        "skill_rules_present": _skill_rules_count(),
    }


def _compute_score(components: dict[str, float]) -> float:
    """Pipe component values through scripts/validate.py --json, return score."""
    args = ["uv", "run", "python", str(VALIDATE_PY), "--json"]
    for name, val in components.items():
        args.extend([f"--{name.replace('_', '-')}", f"{val}"])
    out = _run_cmd(args)
    data = json.loads(out)
    return float(data["score"])


def _write_overlay(overlay: dict[str, Any]) -> None:
    OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERLAY_PATH.write_text(yaml.safe_dump(overlay, sort_keys=True), encoding="utf-8")


def _restore_overlay(saved: str | None) -> None:
    if saved is None:
        if OVERLAY_PATH.is_file():
            OVERLAY_PATH.unlink()
    else:
        OVERLAY_PATH.write_text(saved, encoding="utf-8")


def _product_of(spec: dict[str, list[Any]]) -> list[dict[str, Any]]:
    keys = list(spec.keys())
    value_lists = [spec[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in product(*value_lists)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sweep",
        type=Path,
        help="YAML file mapping config field -> list of candidate values",
    )
    p.add_argument(
        "--single",
        action="store_true",
        help="Just report the score under the current config (no sweep)",
    )
    p.add_argument(
        "--output",
        type=Path,
        help="Write results JSON here (default: stdout)",
    )
    args = p.parse_args(argv)

    if args.single:
        components = _collect_components()
        score = _compute_score(components)
        result = {
            "mode": "single",
            "components": components,
            "score": score,
        }
        out = json.dumps(result, indent=2)
        if args.output:
            args.output.write_text(out, encoding="utf-8")
        else:
            print(out)
        return 0

    if not args.sweep:
        print(
            "ERROR: provide --sweep <path> or --single. See --help.", file=sys.stderr
        )
        return 1

    spec = yaml.safe_load(args.sweep.read_text(encoding="utf-8"))
    if not isinstance(spec, dict) or not spec:
        print("ERROR: sweep spec must be a non-empty YAML dict", file=sys.stderr)
        return 1

    combinations = _product_of(spec)
    print(
        f"calibrate: {len(combinations)} combinations over {list(spec.keys())}",
        file=sys.stderr,
    )

    saved_overlay = OVERLAY_PATH.read_text(encoding="utf-8") if OVERLAY_PATH.is_file() else None
    runs: list[dict[str, Any]] = []
    try:
        for idx, overlay in enumerate(combinations, 1):
            print(f"[{idx}/{len(combinations)}] {overlay}", file=sys.stderr)
            _write_overlay(overlay)
            components = _collect_components()
            score = _compute_score(components)
            runs.append({"overlay": overlay, "components": components, "score": score})
    finally:
        _restore_overlay(saved_overlay)

    runs.sort(key=lambda r: r["score"])
    result = {
        "sweep_spec": spec,
        "baseline_score": 69.3,
        "runs": runs,
        "best": runs[0] if runs else None,
    }
    out = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(out, encoding="utf-8")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
