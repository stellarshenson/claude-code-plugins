# Grounding methods and calibration

Grounding scores a claim against sources through three layers - lexical, semantic retrieval, and NLI entailment - whose verdict is either the deterministic cascade (default) or a Bayesian calibrator that combines all layers. NLI entailment is the truth signal: lexical matching tests word presence and cosine similarity tests topic, but only entailment tests "does the evidence support the claim?".

## Grounding methods (layers)

- **Exact** - whitespace/case-tolerant regex; 1.0 on a verbatim hit
- **Fuzzy** - rapidfuzz partial-ratio in [0, 1]; near-verbatim paraphrase
- **BM25** - IDF-weighted token recall; distinctive claim tokens present in the winning passage (common words do not inflate it)
- **Semantic** - e5 embeddings (ONNX), passage retrieval + the portable `semantic_ratio` feature; optional, opt-in
- **NLI** - multilingual cross-encoder entailment (ONNX), the grounding primitive; optional, opt-in
- **Contradiction guard** - deterministic numeric/entity mismatch + NLI contradiction; always forces CONTRADICTED

## Verdict engines

Selected by config `calibration.engine`.

- **lexical** (default, back-compat) - cascade: contradicted > NLI verdict (if an NLI grounder ran) > exact > fuzzy > bm25 > semantic > none; `verdict_probability` stays -1.0
- **calibrated** - `P(grounded) = sigma(weights . features)`; CONFIRMED iff `P >= threshold`, labelled by the strongest firing layer
- **verification_needed** - flagged when `P` is within `verification_threshold_proximity` of the threshold (borderline)
- Both engines are byte-identical to the historical behaviour when no NLI grounder and no calibration weights are supplied

## NLI / entailment (the grounding primitive)

- **What** - a cross-encoder scores `(premise = evidence, hypothesis = claim)` -> {entailment, neutral, contradiction} = {grounded, unconfirmed, contradicted}
- **Model** - `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`, multilingual (MNLI + XNLI), run via ONNX Runtime, torch-free; ships `onnx/model.onnx`, cached on first use (~560 MB)
- **Cross-lingual** - entailment against an English source: NB 0.998, FR 0.998; the case lexical overlap and cosine similarity both cannot do
- **Module** - `document_processing/nli.py` (`NLIGrounder.scores` / `.verdict`); pass an `nli_grounder` to `ground()` / `ground_many`
- **Verdict role** - NLI argmax is a first-class signal: its contradiction folds into the guard, its entailment counts as signal so a cross-lingual hit with zero lexical overlap still confirms

## Calibrator

- **Library** - bambi / PyMC for fit + predict, arviz for the posterior; no hand-rolled Bayesian math
- **Features** - `exact, fuzzy, bm25_recall, semantic, voters, lexical_cosupport, entity_absent, nli_entail, nli_contra`; all on `GroundingMatch.verdict_features` for audit
- **Posterior** - Gaussian over coefficients; prediction is the posterior-predictive mean, spread is the uncertainty; constant-in-training predictors drop cleanly
- **Incremental** - a new fit seeds priors from the previous posterior (posterior-as-prior), so feedback accumulates
- **Prior in config, not code** - `calibration.prior` in `config_document_processing.yaml`, per-coefficient `Normal(mu, sigma)`; loud error if no config carries it
- **Runtime** - grounding loads the saved weights and scores via a one-draw posterior; PyMC is imported only when the calibrated engine is active

## CLI

- **Calibrate** - `document-processing calibrate --action update --evidence evidence.json --profile .stellars-plugins/calibrator.json --semantic on`; each record is grounded -> features -> Bayesian fit -> saved profile
- **Evidence** - JSON list of `{claim, sources:[paths] (or source_text), label:0|1, lang?, weight?}`
- **Incremental** - `--from <profile>` seeds from a previous posterior
- **Transfer to config** - `config set-calibrator --profile ...` writes the learned weights into the `calibration` block (`engine: calibrated`); grounding then uses them with no fitting
- **Public-data validation** - `make grounding-validate [N= ENGINE=lexical|nli]` (cache only: `make grounding-dataset`)

## Metrics

Synthetic (CI suite, `make test`):

- Deterministic monolingual end-to-end (`TestGroundingEndToEnd`) - precision 1.0, recall 1.0
- Calibrated multilingual fixture, held-out - precision >= 0.90, recall >= 0.80, beats the prior

Public real data - VitaminC dev, balanced (`make grounding-validate`):

| engine | CONFIRMED precision | recall | contradiction recall | cross-lingual |
|--------|--------------------|--------|---------------------|---------------|
| lexical | 0.33 | ~0.12 | ~0.05 | no |
| NLI (integrated) | 0.57 | 0.56 | **0.81** | yes (entailment 0.998) |

- 604 tests green, ruff clean

## Design rationale

- **Lexical alone over-confirms or under-confirms** - it tests token presence, not truth; on-topic fabrications share tokens, real paraphrases/inferences do not
- **Cosine similarity is a topic detector, not a truth detector** - measured: false "vineyard covers forty hectares" 0.868 > true "rainfall averages 800 mm" 0.827; `semantic_ratio` (match/self) further underrates cross-lingual (self-similarity always exceeds cross-language similarity)
- **Entailment is the right primitive** - NLI directly answers support/refute/neutral, in any language; it lifts VitaminC contradiction recall from ~0.05 to 0.81 and unlocks cross-lingual
- **Residual** - NLI conflates an unsupported addition with contradiction (NEI <-> contradiction); the calibrator is positioned to temper this once trained on labelled data. VitaminC 3-way accuracy beyond ~0.5 needs a fine-tuned model, not more wiring

## Files

- **`document_processing/nli.py`** - multilingual cross-encoder NLI grounder (ONNX, torch-free)
- **`document_processing/calibration.py`** - the Bayesian head: fit/predict, save/load, prior loader, evaluate
- **`document_processing/grounding.py`** - layers, `extract_features` (incl. NLI), verdict engines, `nli_grounder`/`calibrated_verdict` in `ground()`/`ground_many`
- **`document_processing/cli.py`** - `calibrate` and `config` subcommands
- **`config_document_processing.yaml`** - `calibration` block (engine, threshold, prior incl. NLI features)
- **`scripts/validate_public_grounding.py`** - VitaminC validation harness (`make grounding-validate`)
- **`scripts/simulate_calibration.py`** - full real-pipeline simulation
- **`notebooks/calibration_demo.ipynb`** - executed calibrator walkthrough
- **`tests/test_calibration.py`, `tests/test_calibration_cli.py`, `tests/test_document_processing.py` (TestNLIGrounding), `tests/fixtures/calibration_multilingual.jsonl`** - suite + fixture
