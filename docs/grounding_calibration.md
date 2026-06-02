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
- **Comparative-quantifier fix** - the numeric contradiction guard now ignores comparative/approximate values (`more than`, `less than`, `over`, `~`, `<`, `>`); without it, comparative/threshold claims flooded false contradictions on real data (see below)

## Public-data validation (VitaminC, reproducible)

The real-data gate is run on a public, reproducible corpus - **VitaminC** (FEVER-derived: `claim` + inline `evidence` + label SUPPORTS/REFUTES/NotEnoughInfo), fetched via `huggingface_hub` (a core dep), no `datasets` library. Reproduce with `make grounding-validate` (`N=` overrides the slice size; `make grounding-dataset` just caches it). Harness: `notebooks/validate_public_grounding.py`. Label map: SUPPORTS→grounded, REFUTES→contradicted, NotEnoughInfo→unconfirmed.

Honest result on 600 balanced dev claims (deterministic engine):

- **Comparative fix is a real win** - NEI correctly left unconfirmed rose 0.28 → 0.845; the false-contradiction flood (139/200 NEI wrongly contradicted) is gone
- **But CONFIRMED recall is low (~0.12) and contradiction recall ~0.03** - VitaminC is an **NLI / entailment** task; our tool is a **lexical document-grounder**. SUPPORTS claims need inference (not lexical token presence); REFUTES are mostly comparative/semantic refutations our exact-numeric guard cannot reason about
- **The fix is entailment, not more lexical tuning** - the lexical engine is a *document grounder* ("are the claim's terms/values present?"), but real grounding is *fact verification* ("does the evidence support the claim?"). That needs an NLI model - added below

## NLI / entailment layer (the real grounding primitive)

Grounding is fundamentally **entailment** - which neither lexical overlap nor cosine similarity captures. A cross-encoder NLI model scores `(premise = evidence, hypothesis = claim)` into {entailment, neutral, contradiction} = {grounded, unconfirmed, contradicted}.

- **Model** - `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, **multilingual** (MNLI + XNLI), run via ONNX Runtime (a core dep), torch-free; ships `onnx/model.onnx`, cached on first use (~560 MB). Module: `document_processing/nli.py`
- **Wired into the calibrator** - `ground()` / `ground_many` accept an `nli_grounder`; the entailment and contradiction probabilities enter the Bayesian calibrator as the `nli_entail` / `nli_contra` features (config prior gives them strong +/- weights). The calibrator combines NLI with the lexical and semantic signals
- **Solves cross-lingual** - measured entailment against an English source: NB 0.998, FR 0.998 - the ceiling that defeated cosine similarity
- **Real-data result** (`make grounding-validate ENGINE=nli`) - on VitaminC: CONFIRMED precision 0.57 / recall 0.56, **contradiction recall 0.79** (vs lexical 0.33 / ~0.05); catches word-number and semantic contradictions the lexical guard cannot
- **Residual** - NLI conflates "unsupported addition" with contradiction (NEI ↔ contradiction); that is exactly what the calibrator is positioned to temper

## Conclusion

- The deterministic lexical engine is the **fast default** (document grounding); two real bug fixes (contradiction completeness, IDF-weighted bm25) brought it to precision/recall 1.0 on a realistic monolingual set
- The **NLI / entailment layer is the real grounding primitive** - multilingual, torch-free, wired as calibrator features; on public real data (VitaminC) it lifts contradiction recall from ~0.05 to **0.79** and solves cross-lingual, which neither lexical nor cosine could
- The **calibrator** combines all signals (lexical + semantic + NLI); with NLI features present it has genuine signal to weight, unlike the semantic-only version
- **598 tests green**, nothing shipped degraded; real-data gate now run on a public corpus (`make grounding-validate`). Remaining: temper the NLI NEI↔contradiction confusion via calibration on labelled data

## Files

- **`document_processing/calibration.py`** - the head, fit/predict, save/load, prior loader, evaluate
- **`document_processing/nli.py`** - the multilingual cross-encoder NLI grounder (ONNX, torch-free)
- **`document_processing/grounding.py`** - `extract_features` (incl. `nli_entail`/`nli_contra`), calibrated branch + `nli_grounder` in `ground()`/`ground_many`
- **`document_processing/cli.py`** - `calibrate` and `config` subcommands
- **`config_document_processing.yaml`** - `calibration` block (engine, threshold, prior incl. NLI features)
- **`notebooks/validate_public_grounding.py`** - public-data (VitaminC) validation harness; `make grounding-validate [ENGINE=lexical|nli]`
- **`notebooks/calibration_demo.ipynb`** - executed walkthrough
- **`notebooks/simulate_calibration.py`** - full real-pipeline simulation / gate
- **`tests/test_calibration.py`, `tests/test_calibration_cli.py`, `tests/fixtures/calibration_multilingual.jsonl`** - the suite + fixture
