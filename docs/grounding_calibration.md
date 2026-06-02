# Grounding verdict calibration

The grounding verdict is a calibrated `P(grounded)` from a Bayesian logistic model over the per-layer grounding scores; it replaces the hand-tuned threshold cascade when learned weights are present, and falls back to the deterministic classifier otherwise. The meaning signal is the model- and language-portable `semantic_ratio`, so cross-lingual true matches confirm while topical fabrications do not.

## Why

- **A5 failure** - the old cascade let a semantic-only hit CONFIRM on bare cosine, so an on-topic fabrication (cosine 0.77) passed while real paraphrases were suppressed
- **Monolingual bias** - requiring lexical co-support would reject true cross-language matches (no word overlap); the fix is a learned boundary over a portable feature, not a hand threshold
- **Domain drift** - a confident match on contracts differs from farm telemetry or multilingual product docs; the boundary must be learned per corpus, not fixed

## Verdict engine

Two engines, selected by config `calibration.engine`.

- **lexical** (default, back-compat) - the deterministic cascade: exact > fuzzy > bm25 > semantic > agreement; `verdict_probability` stays -1.0
- **calibrated** - `P(grounded) = sigma(weights . features)`; CONFIRMED iff `P >= threshold`, labelled by the strongest firing layer for provenance
- **Contradiction guard** - a numeric/entity mismatch forces CONTRADICTED in both engines, always
- **verification_needed** - set when `P` sits within `verification_threshold_proximity` of the threshold (borderline)

## Features

Seven features per claim plus an intercept; all exposed on `GroundingMatch.verdict_features` for audit.

- **exact** - 1.0 on a verbatim hit, else 0
- **fuzzy** - Levenshtein partial-ratio in [0,1]
- **bm25_recall** - fraction of unique claim tokens in the winning passage
- **semantic** - ramped `semantic_ratio` (cosine-to-match / cosine-to-self); model/language-portable, ~1.0 for a real hit, lower for topical noise
- **voters** - count of layers above their vote threshold, normalised /4
- **lexical_cosupport** - 1.0 when a lexical layer co-fires with semantic
- **entity_absent** - fraction of claim proper-nouns absent from the source

## Model and library

- **Library** - bambi / PyMC for fitting and prediction; arviz for the posterior; no hand-rolled Bayesian math
- **Posterior** - Gaussian over the coefficients; prediction is the posterior-predictive mean, with the spread as predictive uncertainty
- **Incremental** - a new fit seeds its priors from the previous posterior (posterior-as-prior), so feedback accumulates
- **Runtime** - grounding loads the saved weights and predicts via a degenerate one-draw posterior through bambi; PyMC is only imported when the calibrated engine is active

## Prior - config, not code

- **Source of truth** - `calibration.prior` in `config_document_processing.yaml`, per-coefficient `Normal(mu, sigma)`; nothing hardcoded in Python
- **Intent** - word overlap OR a strong `semantic_ratio` confirms; weak topical signal and entity-absent fabrications do not
- **Resolution** - active override -> bundled fallback; loud error if no config carries it

## CLI workflow

- **Calibrate** - `document-processing calibrate --action update --evidence evidence.json --profile .stellars-plugins/calibrator.json --semantic on`; each record is grounded to extract features, then the posterior is fit and saved
- **Evidence** - JSON list of `{claim, sources:[paths] (or source_text), label:0|1, lang?, weight?}`
- **Inspect** - `calibrate --action show` prints coefficient mean +/- sd
- **Incremental** - `--from <profile>` seeds the fit from a previous posterior
- **Transfer** - `config set-calibrator --profile ...` writes the learned weights into the config `calibration` block (`engine: calibrated`); grounding then uses them with no fitting
- **Anchoring** - CLI fits append a small anchor set so a constant predictor on a tiny batch cannot break bambi, and untrained-region behaviour stays sane

## Validation status

- **Tests** - 16 calibration tests in the 592-test suite (head units, R3/R4 regression, ground() integration + back-compat, fixture calibrated-beats-prior, config-transfer round-trip, CI end-to-end)
- **R3 / R4** - on the untrained config prior, a fabrication (low ratio, no lexical) is denied and a cross-lingual true match (high ratio, no lexical) confirms
- **CI fixture** - a 36-row synthetic multilingual fixture; calibrated meets precision >= 0.90 / recall >= 0.80 and beats the prior on a held-out split
- **Full-pipeline simulation** (`notebooks/simulate_calibration.py`) - runs real e5 embeddings -> `ground_many` -> calibrate -> config transfer on 20 authored en/nb/fr claims; the machinery runs end to end and config transfer is exact (10/10 identical verdicts), but on a 10-claim held-out split the calibrated metrics sit at precision 0.50 / recall 0.60 - below target
- **Conclusion** - the system is built and tested; calibration quality requires real, sufficient labelled data. Toy-scale synthetic evidence does not produce good numbers. The real-data validation (the user's en/nb/fr corpus + LangWatch) is the remaining gate and has not been run

## Files

- **`document_processing/calibration.py`** - the head, fit/predict, save/load, prior loader, evaluate
- **`document_processing/grounding.py`** - `extract_features`, calibrated branch in `ground()`/`ground_many`
- **`document_processing/cli.py`** - `calibrate` and `config` subcommands
- **`config_document_processing.yaml`** - `calibration` block (engine, threshold, prior)
- **`notebooks/calibration_demo.ipynb`** - executed walkthrough
- **`notebooks/simulate_calibration.py`** - full real-pipeline simulation / gate
- **`tests/test_calibration.py`, `tests/test_calibration_cli.py`, `tests/fixtures/calibration_multilingual.jsonl`** - the suite + fixture
