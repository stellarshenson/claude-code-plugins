#!/usr/bin/env python3
"""3-fold cross-validation calibration for the grounding pipeline.

Three labelled corpora: Liu 2023, Ye 2024, Han 2024. Each has 14 claims
(12 real paraphrases + 2 fabrications). Claim fixtures and source texts
live under ``/tmp/grounding-demo/`` (Liu) and ``/tmp/holdout/`` (Ye, Han).

For each of 3 leave-one-out folds:
    1. Calibrate on 2 corpora: grid-search ``CONFIG_SPACE`` picking the
       combination that maximises mean cal_score across the calibration set.
    2. Evaluate the winning config on the held-out third corpus.
    3. Record winner + held-out scores.

Output: ``calibration_cv.json`` with per-fold details + aggregate stats.

The calibration scoring rule is intentionally NOT the BENCHMARK.md composite
(which was tuned to Liu). Here we use a CV-native mix:

    cal_score = mean_accuracy + 0.25 * mean_portability_bin + 0.25 * mean_gap_attainment

Accuracy dominates. Portability and gap are guardrails.
"""

from __future__ import annotations

import contextlib
from dataclasses import replace
from itertools import product
import io
import json
from pathlib import Path
import statistics
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from stellars_claude_code_plugins.config import load_document_processing_config as load_config  # noqa: E402
from stellars_claude_code_plugins.document_processing.grounding import ground_many  # noqa: E402
from stellars_claude_code_plugins.document_processing.semantic import SemanticGrounder  # noqa: E402

# --------------------------------------------------------------------------
# Corpus definitions
# --------------------------------------------------------------------------

CORPORA = {
    "liu": {
        "claims": Path("/tmp/grounding-demo/liu_claims.json"),
        "source": Path("/tmp/grounding-demo/liu2023.txt"),
        "expected": {
            "l01": "CONFIRMED",
            "l02": "CONFIRMED",
            "l03": "CONFIRMED",
            "l04": "CONFIRMED",
            "l05": "CONFIRMED",
            "l06": "CONFIRMED",
            "l07": "CONFIRMED",
            "l08": "CONFIRMED",
            "l09": "CONFIRMED",
            "l10": "CONFIRMED",
            "l11": "CONFIRMED",
            "l12": "CONFIRMED",
            "l13": "REJECTED",
            "l14": "REJECTED",
        },
        "real_ids": tuple(f"l{i:02d}" for i in range(1, 13)),
        "fake_ids": ("l13", "l14"),
    },
    "ye": {
        "claims": Path("/tmp/holdout/ye_claims.json"),
        "source": Path("/tmp/holdout/ye2024.txt"),
        "expected": {f"y{i:02d}": "CONFIRMED" for i in range(1, 13)}
        | {"y13": "REJECTED", "y14": "REJECTED"},
        "real_ids": tuple(f"y{i:02d}" for i in range(1, 13)),
        "fake_ids": ("y13", "y14"),
    },
    "han": {
        "claims": Path("/tmp/holdout/han_claims.json"),
        "source": Path("/tmp/holdout/han2024.txt"),
        "expected": {f"h{i:02d}": "CONFIRMED" for i in range(1, 13)}
        | {"h13": "REJECTED", "h14": "REJECTED"},
        "real_ids": tuple(f"h{i:02d}" for i in range(1, 13)),
        "fake_ids": ("h13", "h14"),
    },
}

CONFIRMED_TYPES = {"exact", "fuzzy", "bm25", "semantic"}

MODELS = (
    "intfloat/multilingual-e5-small",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)

# --------------------------------------------------------------------------
# Sweep space
# --------------------------------------------------------------------------

CONFIG_SPACE = {
    "classifier_mode": ["absolute", "adaptive_gap"],
    "agreement_threshold": [0.40, 0.45, 0.50],
    "entity_penalty_factor": [0.10, 0.15, 0.20],
}

FOLDS = [
    {"name": "A", "calibrate": ["liu", "ye"], "test": "han"},
    {"name": "B", "calibrate": ["liu", "han"], "test": "ye"},
    {"name": "C", "calibrate": ["ye", "han"], "test": "liu"},
]

# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def evaluate_corpus(
    corpus_name: str,
    config_overrides: dict,
    grounders: dict,
) -> dict:
    """Run ground_many on a corpus with two models and return metrics.

    Returns ``{accuracy, portability, gap_attainment, per_model}``.
    """
    meta = CORPORA[corpus_name]
    claims_raw = json.loads(meta["claims"].read_text(encoding="utf-8"))
    claims = [c["claim"] for c in claims_raw]
    ids = [c["id"] for c in claims_raw]
    text = meta["source"].read_text(encoding="utf-8", errors="replace")
    source_pair = (str(meta["source"]), text)

    base_cfg = load_config()
    cfg = replace(base_cfg, **config_overrides)

    per_model = {}
    match_types_by_model = {}
    accs = []
    gaps = []

    for model_name in MODELS:
        grounder = grounders[(corpus_name, model_name)]
        with contextlib.redirect_stderr(io.StringIO()):
            matches = ground_many(
                claims,
                [source_pair],
                semantic_grounder=grounder,
                semantic_threshold_percentile=0.02,
                config=cfg,
            )
        # Accuracy: correct CONFIRMED/REJECTED per expectation
        correct = 0
        real_agr = []
        fake_agr = []
        type_map = {}
        for cid, m in zip(ids, matches):
            type_map[cid] = m.match_type
            outcome = "CONFIRMED" if m.match_type in CONFIRMED_TYPES else "REJECTED"
            if outcome == meta["expected"][cid]:
                correct += 1
            if cid in meta["real_ids"]:
                real_agr.append(m.agreement_score)
            elif cid in meta["fake_ids"]:
                fake_agr.append(m.agreement_score)
        acc = correct / len(ids)
        gap_raw = min(real_agr) - max(fake_agr) if real_agr and fake_agr else 0.0
        gap_att = max(0.0, min(1.0, gap_raw / 0.10))
        per_model[model_name] = {"accuracy": acc, "gap_attainment": gap_att, "gap_raw": gap_raw}
        match_types_by_model[model_name] = type_map
        accs.append(acc)
        gaps.append(gap_att)

    # Portability: do both models produce same match_type for every claim?
    type_a = match_types_by_model[MODELS[0]]
    type_b = match_types_by_model[MODELS[1]]
    portability = 1 if all(type_a[cid] == type_b[cid] for cid in ids) else 0

    return {
        "accuracy": statistics.fmean(accs),
        "portability": portability,
        "gap_attainment": statistics.fmean(gaps),
        "per_model": per_model,
    }


def cal_score(metrics: dict) -> float:
    """CV-native calibration score. Higher is better."""
    return metrics["accuracy"] + 0.25 * metrics["portability"] + 0.25 * metrics["gap_attainment"]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


def _product_of(spec: dict) -> list[dict]:
    keys = list(spec.keys())
    value_lists = [spec[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in product(*value_lists)]


def _build_grounders() -> dict:
    """Load one SemanticGrounder per (corpus, model) pair and index its source."""
    grounders: dict = {}
    for corpus_name, meta in CORPORA.items():
        text = meta["source"].read_text(encoding="utf-8", errors="replace")
        pair = (str(meta["source"]), text)
        for model_name in MODELS:
            print(f"loading {corpus_name} × {model_name.split('/')[-1]}", file=sys.stderr)
            g = SemanticGrounder(
                model_name=model_name,
                device="cpu",
                cache_dir=".stellars-plugins/cache",
            )
            with contextlib.redirect_stderr(io.StringIO()):
                g.index_sources([(0, str(meta["source"]), text)])
            grounders[(corpus_name, model_name)] = g
    return grounders


def main() -> int:
    t_start = time.time()
    combos = _product_of(CONFIG_SPACE)
    print(
        f"calibrate_cv: {len(combos)} combos × {len(FOLDS)} folds = "
        f"{len(combos) * len(FOLDS)} runs",
        file=sys.stderr,
    )

    # Pre-load all grounders once (each combo re-runs ground_many but the
    # semantic index is reused via the shared grounder instance).
    grounders = _build_grounders()

    # Evaluate every (config, corpus) pair once, cache the result so folds
    # just compose cached metrics.
    cache: dict[tuple[str, str], dict] = {}
    for c_idx, overrides in enumerate(combos, 1):
        ovr_key = json.dumps(overrides, sort_keys=True)
        for corpus_name in CORPORA:
            key = (ovr_key, corpus_name)
            if key in cache:
                continue
            m = evaluate_corpus(corpus_name, overrides, grounders)
            cache[key] = m
        print(
            f"  [{c_idx}/{len(combos)}] evaluated combo {overrides} "
            f"(elapsed {time.time() - t_start:.0f}s)",
            file=sys.stderr,
        )

    # Compose folds from the cache.
    fold_results = []
    for fold in FOLDS:
        ranked: list[tuple[float, dict, dict]] = []
        for overrides in combos:
            ovr_key = json.dumps(overrides, sort_keys=True)
            cal_metrics = [cache[(ovr_key, c)] for c in fold["calibrate"]]
            cal_mean = {
                "accuracy": statistics.fmean(m["accuracy"] for m in cal_metrics),
                "portability": statistics.fmean(m["portability"] for m in cal_metrics),
                "gap_attainment": statistics.fmean(m["gap_attainment"] for m in cal_metrics),
            }
            score = cal_score(cal_mean)
            ranked.append((score, overrides, cal_mean))
        ranked.sort(key=lambda t: t[0], reverse=True)
        best_score, best_cfg, best_cal = ranked[0]
        test_metrics = cache[(json.dumps(best_cfg, sort_keys=True), fold["test"])]
        fold_results.append(
            {
                "fold": fold["name"],
                "calibrate": fold["calibrate"],
                "test": fold["test"],
                "best_config": best_cfg,
                "cal_score": round(best_score, 4),
                "cal_metrics": {k: round(v, 4) for k, v in best_cal.items()},
                "test_accuracy": round(test_metrics["accuracy"], 4),
                "test_portability": test_metrics["portability"],
                "test_gap_attainment": round(test_metrics["gap_attainment"], 4),
                "overfit_gap": round(best_cal["accuracy"] - test_metrics["accuracy"], 4),
                "runners_up": [{"config": r[1], "cal_score": round(r[0], 4)} for r in ranked[1:4]],
            }
        )

    # Also evaluate the CURRENT default config on all 3 corpora.
    default_cfg = {
        "classifier_mode": load_config().classifier_mode,
        "agreement_threshold": load_config().agreement_threshold,
        "entity_penalty_factor": load_config().entity_penalty_factor,
    }
    default_key = json.dumps(default_cfg, sort_keys=True)
    # default may not be in cache if it's outside the sweep (it should be
    # though, since defaults align with sweep values 0.45/0.15/adaptive_gap)
    if default_key not in {json.dumps(c, sort_keys=True) for c in combos}:
        for corpus_name in CORPORA:
            cache[(default_key, corpus_name)] = evaluate_corpus(
                corpus_name, default_cfg, grounders
            )
    default_per_corpus = {
        c: {
            "accuracy": round(cache[(default_key, c)]["accuracy"], 4),
            "portability": cache[(default_key, c)]["portability"],
            "gap_attainment": round(cache[(default_key, c)]["gap_attainment"], 4),
        }
        for c in CORPORA
    }

    # Aggregate
    test_accs = [f["test_accuracy"] for f in fold_results]
    winners = [json.dumps(f["best_config"], sort_keys=True) for f in fold_results]
    all_same = len(set(winners)) == 1

    aggregate = {
        "mean_test_accuracy": round(statistics.fmean(test_accs), 4),
        "std_test_accuracy": round(statistics.pstdev(test_accs) if len(test_accs) > 1 else 0.0, 4),
        "mean_overfit_gap": round(statistics.fmean(f["overfit_gap"] for f in fold_results), 4),
        "all_folds_same_winner": all_same,
        "winning_config_if_same": fold_results[0]["best_config"] if all_same else None,
        "current_default_config": default_cfg,
        "current_default_per_corpus": default_per_corpus,
    }

    result = {
        "sweep": CONFIG_SPACE,
        "folds": fold_results,
        "aggregate": aggregate,
        "runtime_seconds": round(time.time() - t_start, 1),
    }
    output_path = PROJECT_ROOT / "calibration_cv.json"
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"wrote {output_path}", file=sys.stderr)
    print(json.dumps(aggregate, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
