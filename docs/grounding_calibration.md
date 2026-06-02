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
- **Full-pipeline simulation** (`notebooks/simulate_calibration.py`) - runs real e5 embeddings -> `ground_many` -> calibrate -> config transfer on authored en/nb/fr claims; the machinery runs end to end and config transfer is exact (10/10 identical verdicts), but the calibrated verdict does NOT beat the deterministic baseline on this data (en precision 0.67 / recall 1.0; nb and fr recall collapse to 0)

## Known limitation (proven by the simulation)

The simulation surfaced a premise failure, not a tuning gap.

- **Semantic similarity is a topic detector, not a truth detector** - for on-topic claims the e5 cosine of a fabrication is as high as a real match. Measured: false `"vineyard covers forty hectares"` scores 0.868 vs true `"rainfall averages 800 mm"` 0.827; nb fabrication `"stort bryggeri"` 0.799 vs nb true `"tre inngjerdede hager"` 0.790
- **Cross-lingual is the ceiling** - nb/fr claims have no lexical overlap, so semantic is the only available signal; since it does not separate true from false, real foreign-language matches cannot be confirmed without also confirming foreign-language fabrications -> recall collapses
- **`semantic_ratio` (match/self) systematically underrates cross-lingual** - same-language self-similarity is always higher than cross-language match similarity, so the ratio is < 1 by construction for cross-lingual hits
- **What actually separates grounding** is lexical specificity (bm25/exact of the claim's *specific* tokens) and the deterministic numeric/entity contradiction guard - not semantics

## Deterministic grounding fixes (the real lever)

The investigation found and fixed two real precision bugs in the deterministic engine - the path that actually works. Both validated against the full suite with no regression.

- **Contradiction completeness** - `extract_numbers` now recognises historical years (1500-2099, not just 19xx/20xx) and drops stopword context-words, so same-category years key consistently. Fixes the miss where `"built in 1650"` (source 1820) was CONFIRMED instead of CONTRADICTED. Regression: `TestYearContradiction`
- **IDF-weighted bm25 recall** - token recall is now IDF-weighted, so corpus-ubiquitous words no longer inflate recall and a claim whose *distinctive* tokens are absent does not confirm. Fixes the `"commercial brewery"` false positive (shares only `estate`/`runs`). Regression: `TestBm25IdfRecall`
- **End-to-end result** - `TestGroundingEndToEnd`: deterministic grounding on a realistic monolingual set (grounded / off-topic fabrication / numeric contradiction) reaches **precision 1.0, recall 1.0**
- **Remaining levers** - word-number contradictions (`forty` vs `twelve`) still a minor gap; cross-lingual on-topic is the embedding ceiling (needs an NLI/entailment model, not similarity)

## Conclusion

- The deterministic grounding engine is the **working default** and now passes end-to-end on realistic monolingual claims (precision/recall 1.0) after two real bug fixes; **598 tests green**, nothing shipped degraded
- The calibrated engine is **opt-in and not yet a proven improvement**; on adversarial on-topic data it does not beat the baseline
- Real-data validation against the DBA corpus is the remaining gate and has not been run; before further calibration investment, reconcile the cross-lingual semantic behaviour against that real data

## Files

- **`document_processing/calibration.py`** - the head, fit/predict, save/load, prior loader, evaluate
- **`document_processing/grounding.py`** - `extract_features`, calibrated branch in `ground()`/`ground_many`
- **`document_processing/cli.py`** - `calibrate` and `config` subcommands
- **`config_document_processing.yaml`** - `calibration` block (engine, threshold, prior)
- **`notebooks/calibration_demo.ipynb`** - executed walkthrough
- **`notebooks/simulate_calibration.py`** - full real-pipeline simulation / gate
- **`tests/test_calibration.py`, `tests/test_calibration_cli.py`, `tests/fixtures/calibration_multilingual.jsonl`** - the suite + fixture
