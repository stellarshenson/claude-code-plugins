# Deterministic cross-lingual grounding on the DeLaval gold

Experiment on the `experiment/grounding` branch: build a non-LLM grounder that classifies each claim as supported or hallucination on a real cross-lingual dataset, without training any model on the test fold. The current best is a **lexical-only, language-routed logistic** - no semantic model. Artefacts: `experiments/grounding/{harness.py, lab.py, HYPOTHESIS.md, RESEARCH.md, RESULTS.md, BENCHMARK.md}`; the labelled gold and transcripts stay in a git-ignored stash.

## Situational overview

The lexical grounder confirmed only ~12% of supported claims on the client gold; re-profiling overturned the team's "semantic is required" conclusion - and the final model needs no semantic layer at all.

- **Dataset (live)** - 1260 verified records `{claim, source_text, label, lang}`, **794 supported / 466 hallucination**, evidence always an English-dominant document dump (it carries a small non-English tail). The gold grew 375 → 856 → 1260 mid-experiment; several conclusions changed with it (the depth-2 GBT that won on 375 overfits on the larger sets)
- **Seven languages** - English dominant (~86%), then nb / fr / sv / it / es / pt
- **Few independent contexts** - only ~22 distinct `source_text` blobs (≈57 claims each); claims sharing a source are correlated, so the effective sample is far smaller than 1260
- **Two gaps** - English claims have their support present but the score is swamped by the mega-evidence; non-English recall collapses unless the claim is translated or a same-language chunk exists

## Executive summary

A purely lexical model with per-chunk language routing is the best, beating every model that used the NLI semantic layer.

- **Best model** - lexical-only, language-routed logistic: **macro-F1 0.837 (leave-one-source-out, the trustworthy split) / 0.779 (leave-one-language-out), hallucination-F1 0.80**, with no semantic model
- **Beats NLI** - the NLI-including model and the lexical `recall_split` rule both score below it; dropping NLI gained accuracy, simplicity, and speed
- **The lever is features, not model class** - a `same_lang` flag + dual recall (claim-as-is and translate-then-recall) + anchors; a plain logistic wins, gradient-boosted trees overfit the language-held-out folds
- **Replicated across data growth** - the leave-one-source-out number held at 0.829 → 0.837 as the gold grew 856 → 1260, the best validation that the result is real, not a snapshot artefact
- **Metric** - macro-F1 (imbalance-robust); the majority predictor reads ~0.64 accuracy but macro-F1 ~0.39 with hallucination-F1 0.000
- **Hallucination detection** - hal-F1 0.80 under the source-out split; the residual is data-bound (es/pt at n=5-6)

## Methodology

Per-claim, lexical signals computed two ways with language routing, then a learned verdict head; no semantic scorer.

- **Language detection** - per claim and per source chunk (lingua-py on short text; langdetect fallback); a `same_lang` flag marks whether the best chunk is in the claim's language
- **Dual lexical recall** - `r1_direct` (claim vs chunks as-is - the same-language path) and `r1_mt` (translate claim → English via argos, then recall - the cross-language path); the model learns which to trust per the language flag
- **Supporting lexical features** - char-ngram recall, rapidfuzz partial-ratio, anchor recall + anchor mismatch (numbers/IDs, language-invariant), oracle-chunk and top-k consensus recall
- **Verdict head** - a logistic over the lexical feature set; LightGBM was raced against it (with `class_weight='balanced'`) but lost under leave-one-language-out
- **Metric** - macro-F1 headline, hallucination-F1 watched separately
- **Anti-overfit, two cross-validation splits** - **LOLO** (leave-one-language-out): hold out a language, train on the other six, score the held-out one - tests generalisation to an unseen language. **LOSO** (leave-one-source-out): hold out all claims from one of the ~22 distinct source documents, train on the rest, score the held-out document - tests generalisation to unseen evidence and prevents a model from memorising the few correlated contexts. No learner ever touches the fold it scores. LOSO is the headline metric here because English is ~86% of the data, so the LOLO English-out fold trains on a tiny non-English slice and is artificially harsh

## Setup

- **Data** - live 1260-record gold, git-ignored stash; features cached (git-ignored)
- **Dependencies (experiment-only)** - `lingua-language-detector`, `argos-translate` (frozen MT bridge), `rapidfuzz`, `scikit-learn`, `lightgbm`
- **Operating point** - recursive chunking, 300-char chunks, 0.1 overlap (validated by a threshold-free AUC/Cohen's d separation sweep: whole-doc is the 0.50 floor, ~150-300 chars near-optimal)
- **Commands** - `python lab.py lexgbm` (the current model), `harness.py --tournament --mt` (the rule baseline), `lab.py final` (capacity ladder)

## How we got here

The result arrived in stages, several of which reversed earlier conclusions.

- **MT is the cross-lingual lever** - a frozen translator lifts every non-English language (per-language LOLO accuracy nb 0.40 → 0.93, fr 0.50 → 0.81, it 0.88 → 1.00); lexical-only without translation tops out ~0.67
- **Metric switch** - the 549/307 imbalance makes accuracy misleading; macro-F1 became primary (majority predictor: 0.641 accuracy but macro-F1 0.435 on the old snapshot, 0.391 on the live set, hallucination-F1 0.000)
- **Per-chunk language routing** - the source carries claim-language chunks for a real subpopulation (French claims match a French chunk 46% of the time, sv 50%); detecting chunk language lets those ground with no translation, which "always translate to English" missed
- **Lexical-only beats NLI** - giving the model `same_lang` + dual recall + anchors replaces what NLI was providing; the semantic layer became unnecessary

## Model class: lexical-LR vs GBT vs Bayesian calibration

The decisive factors are the features and the dataset size, not the fitting method.

- **Lexical-only logistic** (live 1260) - macro-F1 0.837 source-out / 0.779 language-out, the best; the language-routed lexical features carry the signal
- **Gradient-boosted trees** - on the old 375 snapshot (86 negatives) a depth-2 GBT won (0.775); on the live 856 (307 negatives) trees **overfit** the language-held-out folds and lose (LGBM 0.74 → 0.54 as depth rises), while the linear model wins - the conclusion flipped with more data
- **Bayesian calibration** (production `fit_calibrator`, bambi/PyMC logistic) - a Bayesian logistic is a hyperplane, so it lands at the linear level (0.733 on the 375 snapshot) and adds calibrated uncertainty, not capacity
- **Leave-one-source-out ≥ leave-one-language-out** (0.83 vs 0.81) - context leakage is not inflating results; the harder generalisation is to an unseen language

## What we tried

- **Kept** - per-chunk language routing, dual recall, anchors, char-ngram, fuzzy, the MT bridge (argos per-language), a logistic head
- **Dropped / refuted** - NLI entailment (superseded by lexical routing), claim decomposition (over-flags supported clauses), cross-corpus calibrator transfer (VitaminC mis-weights), oracle-chunk (retrieval is not the bottleneck), linear interaction terms and deep trees (overfit), OPUS-MT engine (worse and ~9x slower than argos)

## Lessons learned

- **Features beat model class** - the gain came from the language-routed dual-recall features, not from a nonlinear learner; a regularised logistic is the right head for ~19 contexts
- **Conclusions are dataset-size dependent** - doubling the data (375 → 856, 86 → 307 negatives) flipped "depth-2 GBT wins" into "linear wins, trees overfit"; never trust a single-snapshot conclusion on a small set
- **The right split matters** - leave-one-language-out and leave-one-source-out measure different generalisations; here unseen-language is the harder one, and the ~19-context worry was wrong-signed
- **Imbalance hides failure** - 0.64 accuracy looked fine while macro-F1 was 0.39 and hallucination-F1 0.00; pick the imbalance-robust metric first
- **A semantic model was not required** - good lexical features with language routing matched and beat NLI on this task
- **Anti-overfit is not no-modeling** - the rule bans fitting the test fold, not modeling; the win was a model fit honestly under LOLO/LOSO

## Conclusions

- **Ship a lexical-only, language-routed logistic** - per-chunk language detection + `same_lang` + `r1_direct`/`r1_mt` + anchors; macro-F1 0.837 (source-out), hal-F1 0.80, no semantic model, cheap and CPU-only
- **Translation is the only neural component** - a frozen argos bridge, used where a same-language chunk is absent; everything else is lexical
- **The ceiling is data** - ~19 evidence contexts and the es/pt tail (n=5-6) cap further gains; more labelled hallucinations and more contexts are the prerequisite, not a cleverer model
- **Reframes the client finding** - lexical did not fail at grounding; it failed at cross-lingual confirmation, fixed by translation plus a same-language routing feature

## Next steps

- **Promote** the lexical-only, language-routed logistic into the production grounder via a separate reviewed change; keep NLI optional/off
- **More contexts and negatives** - the binding constraint is ~19 source documents and the small es/pt tail; grow the gold before chasing further model capacity
- **Engineering** - lingua-py for language ID, a faster per-language MT engine if throughput matters
- **Refuted, do not revisit without more data** - NLI in the verdict, claim decomposition, cross-corpus transfer, deep trees, OPUS-MT
