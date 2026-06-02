"""Full end-to-end calibration simulation through the REAL grounding pipeline.

Unlike the CI fixture test (which feeds feature vectors directly), this runs the
actual machinery: real e5 semantic embeddings -> ground_batch() -> feature
extraction -> Bayesian calibration -> config transfer -> ground() via config.

It authors a realistic multilingual (en / nb / fr) labelled set - the only thing
a real deployment swaps in is the domain corpus + gold labels. Run:

    uv run python notebooks/simulate_calibration.py

Exits 0 when the calibrated verdict meets the targets on the held-out split,
1 otherwise (so it can double as a gate). Prints a full report either way.
"""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import pandas as pd

from stellars_claude_code_plugins.config import load_document_processing_config
from stellars_claude_code_plugins.document_processing import calibration as C
from stellars_claude_code_plugins.document_processing.grounding import extract_features, ground_batch

# One shared source corpus (English). nb/fr claims are cross-lingual paraphrases
# of these facts - the real test of the portable semantic_ratio signal.
# Blank-line-separated paragraphs => a multi-passage corpus, so BM25 has a
# non-degenerate IDF (a single short passage makes bm25_recall collapse to 0).
SOURCES = [
    (
        "estate.txt",
        "The estate has three walled gardens and an orchard.\n\n"
        "Rainfall in the region averages 800 millimetres per year.\n\n"
        "The manor was built in 1820 and restored in 1998.\n\n"
        "The vineyard covers twelve hectares on the south slope.\n\n"
        "Beekeeping has continued on the grounds since 1905.\n\n"
        "The estate library holds four thousand bound volumes.\n\n"
        "A trout stream runs along the eastern boundary.\n\n"
        "The walled kitchen garden supplies the manor kitchen.",
    )
]

# (claim, gold_label, lang). label 1 = grounded, 0 = not (fabrication/contradiction).
CLAIMS: list[tuple[str, int, str]] = [
    # English - grounded
    ("the estate has three walled gardens", 1, "en"),
    ("there is an orchard on the estate", 1, "en"),
    ("rainfall averages about 800 mm per year", 1, "en"),
    ("the vineyard covers twelve hectares", 1, "en"),
    ("the manor was restored in 1998", 1, "en"),
    # English - fabrication
    ("the estate employs twenty full-time gardeners", 0, "en"),
    ("a helicopter pad sits behind the manor", 0, "en"),
    ("the estate keeps a herd of alpacas", 0, "en"),
    # English - contradiction
    ("the manor was built in 1750", 0, "en"),
    ("the vineyard covers forty hectares", 0, "en"),
    # Norwegian - grounded (cross-lingual)
    ("eiendommen har tre inngjerdede hager", 1, "nb"),
    ("nedboren er omtrent 800 millimeter per ar", 1, "nb"),
    ("vingarden dekker tolv hektar", 1, "nb"),
    # Norwegian - fabrication
    ("eiendommen har en privat flyplass", 0, "nb"),
    ("eiendommen driver et stort bryggeri", 0, "nb"),
    # French - grounded (cross-lingual)
    ("le domaine possede trois jardins clos", 1, "fr"),
    ("les precipitations sont d'environ 800 mm par an", 1, "fr"),
    ("le manoir a ete restaure en 1998", 1, "fr"),
    # French - fabrication
    ("le domaine eleve des chevaux de course", 0, "fr"),
    ("le domaine possede un heliport", 0, "fr"),
]


def build_evidence() -> pd.DataFrame:
    """Run the real grounding pipeline (semantic ON) and extract features."""
    from stellars_claude_code_plugins.document_processing.semantic import (
        SemanticGrounder,
        is_available,
    )

    if not is_available():
        raise SystemExit("semantic extras not importable - cannot run the real-model simulation")

    grounder = SemanticGrounder()  # default e5-small, cached after first use
    gcfg = load_document_processing_config()
    claims = [c for c, _, _ in CLAIMS]
    matches = ground_batch(claims, SOURCES, semantic_grounder=grounder, config=gcfg)

    rows = []
    for (claim, label, lang), m in zip(CLAIMS, matches):
        feat = extract_features(m, gcfg)
        feat["grounded"] = float(label)
        feat["lang"] = lang
        rows.append(feat)
    return pd.DataFrame(rows)


def main() -> int:
    print("=== building evidence through the real e5 + ground_batch pipeline ===")
    df = build_evidence()
    print(f"  {len(df)} claims grounded "
          f"(en={sum(df.lang == 'en')}, nb={sum(df.lang == 'nb')}, fr={sum(df.lang == 'fr')})")

    # Deterministic split: even rows train, odd rows test.
    train = df[df.index % 2 == 0].reset_index(drop=True)
    test = df[df.index % 2 == 1].reset_index(drop=True)

    prior = C.CalibratedVerdict.from_weights(
        {k: mu for k, (mu, _sd) in C.load_prior_spec().items()}, threshold=0.5
    )
    print("\n=== calibrating on the training split (bambi / PyMC) ===")
    cal = C.fit_calibrator(train, draws=1000, tune=1000, random_seed=0, include_anchor=False)

    prior_m = C.evaluate(prior, test)
    cal_m = C.evaluate(cal, test)

    def line(tag, m):
        print(f"  {tag:18s} precision={m['precision']:.3f} recall={m['recall']:.3f} "
              f"f1={m['f1']:.3f} acc={m['accuracy']:.3f} (n={m['n']})")

    print("\n=== held-out metrics ===")
    line("prior (untrained)", prior_m)
    line("calibrated", cal_m)
    print("  per-language (calibrated):")
    for lang, lm in cal_m.get("by_lang", {}).items():
        print(f"    {lang}: precision={lm['precision']:.3f} recall={lm['recall']:.3f} (n={lm['n']})")

    # Config-transfer leg: learned weights -> config -> verdict_from_weights.
    weights = {k: mu for k, (mu, _sd) in cal.posterior_summary().items()}
    v_cfg = C.CalibratedVerdict.from_weights(weights, threshold=0.5)
    same = sum(
        1
        for _, r in test.iterrows()
        if (v_cfg.predict_proba({k: r[k] for k in C.PREDICTORS})[0] >= 0.5)
        == (cal.predict_proba({k: r[k] for k in C.PREDICTORS})[0] >= 0.5)
    )
    print(f"\n=== config transfer: {same}/{len(test)} verdicts identical "
          "between fitted posterior and config point-weights ===")

    ok = cal_m["precision"] >= 0.90 and cal_m["recall"] >= 0.80 and cal_m["accuracy"] >= prior_m["accuracy"]
    print("\n=== GATE:", "PASS" if ok else "BELOW TARGET", "(precision>=0.90, recall>=0.80, >= prior) ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
