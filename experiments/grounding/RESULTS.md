# Results: rival deterministic grounders on the private RAG gold

> **Metric note**: the classes are imbalanced (289/86), so the primary metric is now **macro-F1** (the majority predictor scores 0.771 accuracy but macro-F1 0.435 / hallucination-F1 0.000). The live F1 scoreboard is `BENCHMARK.md`; the tables below report the accuracy/balanced view from the first runs and remain valid - F1-tuned thresholds give the same ordering (recall_split leads).


Tournament over the 375 verified gold records (289 supported / 86 hallucination, 7 claim languages, English evidence). Every number is **out-of-fold**: thresholds are chosen on a held-out fold, never on the records they score. No learner is fit to the 375. Aggregate counts only - no client data. Reproduce with `python harness.py --tournament [--mt] --ablation`.

## Metric

- **Headline: leave-one-language-out (LOLO)** - for each detected language, thresholds are tuned on the other six and the held-out language is scored; all 375 predictions are out-of-fold.
- **TEST** - stratified 50/50 dev→test, only the test half reported.
- **Guard: balanced accuracy** (mean of per-class recall). Majority-always-grounded = **0.771 acc / 0.500 balanced**; the bar is to beat that and the e5-semantic baseline at balanced ≥0.75.

## Headline finding

A **frozen offline translator (argos-translate) + best-chunk IDF recall** reaches **LOLO balanced 0.777, TEST 0.791 acc / 0.755 balanced** - clearing the ≥0.75 balanced target with zero model trained on the data. MT collapses the cross-lingual gap (Gap B) into the same-language recall problem (Gap A); once it does, the *simplest* signal wins and every extra deterministic layer slightly hurts.

## Tournament - lexical only (no MT)

| combiner | LOLO acc | LOLO bal | sup-rec | hal-rec | TEST acc | TEST bal |
|---|---|---|---|---|---|---|
| routed | 0.693 | **0.666** | 0.72 | 0.62 | 0.665 | 0.689 |
| tree | 0.613 | **0.655** | 0.58 | 0.73 | 0.623 | 0.692 |
| recall_contra | 0.640 | **0.648** | 0.63 | 0.66 | 0.634 | 0.683 |
| recall_only | 0.683 | **0.631** | 0.73 | 0.53 | 0.675 | 0.688 |
| weighted | 0.595 | **0.598** | 0.59 | 0.60 | 0.592 | 0.671 |
| global | 0.619 | **0.581** | 0.65 | 0.51 | 0.639 | 0.595 |

Lexical-only tops out at ~0.67 balanced. English is fine; the non-English slice is not rescued (see per-language).

## Tournament - with MT bridge (argos-translate, frozen)

| combiner | LOLO acc | LOLO bal | sup-rec | hal-rec | TEST acc | TEST bal |
|---|---|---|---|---|---|---|
| recall_only | 0.725 | **0.777** | 0.68 | 0.87 | 0.791 | 0.755 |
| tree | 0.717 | **0.723** | 0.71 | 0.73 | 0.712 | 0.727 |
| routed | 0.760 | **0.718** | 0.80 | 0.64 | 0.712 | 0.727 |
| recall_contra | 0.744 | **0.715** | 0.77 | 0.66 | 0.712 | 0.727 |
| weighted | 0.693 | **0.707** | 0.68 | 0.73 | 0.665 | 0.719 |
| global | 0.688 | **0.634** | 0.73 | 0.53 | 0.691 | 0.629 |

Featurize 44s for 375 records (~118 ms/claim including MT of the 99 non-English claims, translated once). The MT model load is a one-time ~5s/language download.

## Per-language LOLO accuracy: lexical vs +MT

| lang | n | lexical | +MT |
|---|---|---|---|
| en | 280 | 0.77 | 0.71 |
| no | 40 | 0.40 | **0.93** |
| fr | 16 | 0.50 | **0.81** |
| sv | 10 | 0.60 | 0.70 |
| it | 8 | 0.88 | **1.00** |
| es | 6 | 0.17 | 0.33 |
| pt | 5 | 0.40 | 0.60 |

MT lifts every non-English language. English dips slightly under LOLO because the recall threshold, now tuned on MT-boosted folds, shifts - net balanced accuracy still rises sharply (hallucination recall 0.53 → 0.87).

## Ablation ladder under MT (LOLO balanced)

| rung | LOLO bal | delta |
|---|---|---|
| recall_only | 0.777 | - |
| recall_contra | 0.715 | -0.061 |
| global (+ bridge + meta) | 0.634 | -0.081 |
| weighted | 0.707 | +0.073 |

The "best-chunk recall alone explains the win" hypothesis is **confirmed and then some**: once MT closes the language gap, adding the contradiction gate, the cognate/anchor bridge floor, and the meta-claim inversion all *reduce* balanced accuracy. The char-ngram bridge floor admits hallucinations (high background); the contradiction gate over-fires. The clean recommendation is MT + recall threshold, nothing else.

## Honest limitations

- **Accuracy 0.791 < the 0.85 stretch.** The balanced-accuracy guard (0.755-0.777) is met; raw accuracy is held back by the English slice and the tiny abstractive tail.
- **Spanish/Portuguese tail stays hard** (es 0.33 on n=6). These are abstractive prose claims with no anchors; even MT leaves residual structural mismatch. With n=6/5 the per-language numbers are noisy.
- **MT is a frozen model**, not pure lexical - reported in its own tier. It is not fit to the 375 (honours the anti-overfit rule) but it is a neural component; the lexical-only ceiling (~0.67 balanced) is the honest pure-lexical result.
- **Chunk point fixed** at recursive/300/0.1 (validated, not swept exhaustively here); `--sweep` ranks operating points by AUC of recall separation.
- langdetect is the language detector; lingua-py (per RESEARCH.md) would reduce the 65/375 noisy-`lang` disagreements further.

## Follow-up experiments

Run on the same gold, same anti-overfit protocol, MT bridge on unless noted.

- **Chunk sweep (exp#2)** - word-recall AUC of class separation ranges **0.500 at whole-doc** (the Jaccard-blind floor, confirming the diagnosis) to **0.728 at char/150/0.10**; the recursive/300/0.1 operating point used here is 0.724. Chunking matters a lot; going below 300 chars buys ~0.004. Whole-doc reproduces the original failure.
- **English two-threshold, `recall_split` (exp#1)** - a separate recall bar for native-English vs translated claims reaches **LOLO accuracy 0.845, TEST 0.817 acc / 0.765 balanced** - the best accuracy of the field. It maximises accuracy by trading hallucination recall (0.50) for supported recall (0.95); pick it when accuracy is the target, `recall_only` when balanced is.
- **Fixed-prior, zero tuning (exp#7)** - `recall_only` at a fixed τ=0.40 over all 375, no fold, scores **0.717 accuracy / 0.776 balanced** - essentially the tuned LOLO result. A zero-config deployment generalises; the threshold is not delicately fit.
- **Abstain band (exp#8)** - a three-way verdict (grounded / abstain / contradicted) with a fixed 0.30-0.55 band covers 68% of records at **balanced 0.838 on the covered set**. Abstaining on the low-separation middle buys precision at a known coverage cost.
- **lingua-py language ID (exp#6)** - swapping langdetect for lingua-py cuts the noisy-`lang` disagreement 65 → 44 and lifts `recall_only` LOLO accuracy 0.725 → **0.781** (balanced ~0.768). It over-splits Norwegian into nb/nn and misfires on a few short claims, but the net is positive.
- **NLI residual (exp#4/#5)** - multilingual NLI entailment (mDeBERTa, parameter-free argmax) on the best chunk: NLI-alone scores macro-F1 0.644 and catches **99% of hallucinations**. The **`recall OR NLI` ensemble reaches macro-F1 0.737 with the best hallucination-F1 (0.64) and balanced 0.808** - no tuning - and rescues the tail recall misses: es 0.33 → 0.50, pt 0.60 → 0.80, sv 0.70 → 0.80, no 0.82 → 0.95. NLI is a small model, reported in its own tier.
- **OPUS-MT (exp#3)** - benchmarked as an alternate engine (`--mt-engine opus`, Helsinki-NLP/opus-mt-mul-en) against argos; see BENCHMARK.md for the head-to-head.

## Takeaway

The private RAG cross-lingual grounding problem is, deterministically, a **translation problem followed by a recall-scoring problem** - not a problem the curated lexicon / cognate / anchor bridges solve on their own. A frozen offline translator plus best-chunk IDF recall is cheap (~120 ms/claim, no GPU, no training) and clears the balanced-accuracy bar; the elaborate deterministic bridge stack does not add value once MT is present.

## Round 7 - batch-adaptive thresholds (max-gap / Jenks)

The pre-fork cascade's `adaptive_gap` idea (cut the batch's score distribution at its largest gap) was re-tested on the shipped manifold's probabilities with batch = sub-dataset kind. It fails there: corpus-scale probability distributions are unimodal, the largest gap is noise, and the unguarded cut destroys private_rag (0.829 → 0.419) and vitaminc (0.695 → 0.346). Jenks natural breaks (jenkspy) is more stable but never beats the fixed threshold. With a gap-significance floor the mechanism reduces to "fixed everywhere except genuinely bimodal small batches" - it fires only on the 42-claim articles fixture (+0.019 mean), the pre-registered overfit falsifier, so corpus-level adoption is rejected. The one genuine finding: on mixed-label natural groups (per article, per trace, n >= 4) per-group cuts beat the fixed threshold by ~0.03 macro-F1 - the cascade's mechanism lived on small per-request batches, never corpora. Full tables in BENCHMARK.md Round 7 and the notebook.

## Round 8 - mechanism hypotheses with diagnostic gates, 2026-06-11

Three pre-registered mechanism candidates (Round 8, see `docs/experiments/lexical-grounding-experiments.md`), each with a kill-gate measured before any build. Diagnostics + mechanism in `mechanisms.py`; logs `logs/round8-*.log`.

**Gates killed two of three before a line of mechanism code.** A2 (atomic-fact scoring): errors do NOT concentrate in multi-sentence claims (27.0% of errors vs 28.5% of claims; multi/single error-rate ratio 0.93, needed > 1.5) - the granularity-mismatch story is falsified on private RAG, taking H-B (alignment-profile features) with it per the shared gate. H-C (negation-scope flag): negation-cue asymmetry in only 3.7% of VitaminC errors (needed >= 25%) - negation is not the VitaminC failure mode.

**A1 (SaT multilingual claim extraction) survived and confirmed a real defect.** The shipped `extract_claims()` verb gate is English-only; on the 639 raw answer documents (trace cache) it rejects 9.2% of length-passing English sentences but nb 50.4%, it 85.5%, de 55.1%, da 46.7%, sv 46.2%, es 28.0%. Head-to-head over the same 639 docs:

| variant | claims/doc | inflation | gold coverage | nb claims | it claims |
|---|---|---|---|---|---|
| shipped (regex + verb gate) | 13.03 | 1.00 | 1.000 (circular) | 126 | ~0 |
| gate-only (regex + lang-agnostic gate) | 14.74 | 1.13 | 0.997 | 252 | 122 |
| SaT + lang-agnostic gate | 17.13 | 1.31 | 0.990 | 266 | 169 |

The language-agnostic gate alone doubles Norwegian admissions and recovers Italian from zero at 13% inflation and 99.7% gold-claim coverage. SaT boundaries admit ~16% more again but cost ~1% gold coverage (different sentence boundaries break fuzzy matching of old gold claims - benign or real, needs the precision pass). Falsifier (inflation > 2x with no recall gain) did not fire.

**Methodological finding**: the gold dataset itself carries survivorship bias - it was built THROUGH the anglocentric extractor, so non-English claims are under-represented in gold exactly where the grounder is weakest. A gold v2 (re-extract with the new front door, re-judge) is the registered follow-up; it will shift all benchmark numbers because the claim population changes.

**Recommendation**: ship the language-agnostic gate (conservative, pure win); hold SaT boundaries until a sampled dual-judge precision pass on the newly admitted sentences settles whether the extra admissions are load-bearing claims or noise.

## Round 8b - gold v2 re-baseline, the survivorship-bias payoff, 2026-06-11

The v1 gold was built THROUGH the anglocentric extractor (entry: A1 / H13), so non-English claims were dropped before judging. Gold v2 re-extracts every answer through the SaT + language-agnostic front door, inherits the verified label on claims that still fuzzy-match a v1 gold claim (partial_ratio >= 90), and dual-judges the rest (Haiku + Sonnet, SUPPORTED / UNSUPPORTED / NOT_A_CLAIM; keep only dual-agreed). Pipeline: `gold_v2.py` (units / judge / build / bench), data in the gitignored forensics stash.

- **Dataset** - 5,912 rows (3,619 inherited + 2,293 new dual-agreed) over 639 traces; 84% of traces dual-judged (449/535 with new claims; judging is flaky `claude -p`, retried to convergence then stopped)
- **Extraction precision of new admissions** - of the sentences the new front door admits that the verb gate dropped: 48.8% are real checkable claims, 32.7% NOT_A_CLAIM (noise), rest judge-split. The looser gate trades precision for the cross-lingual recall it buys
- **Headline barely moves** - macro-F1 0.802 (v1 was 0.817). English is 77% of the unbiased population and dominates the average

The split is the finding:

| slice | n | acc | balanced acc | supported recall | hallucination recall (TNR) |
|---|---|---|---|---|---|
| english | 4,569 | 0.815 | 0.797 | 0.884 | 0.710 |
| non-english | 1,343 | 0.894 | 0.498 | 0.997 | 0.000 |

**The shipped manifold is an English-only hallucination detector.** On non-English it confirms 1,339 of 1,343 claims and catches 0 of 139 hallucinations (TN=0, FP=139) - balanced accuracy 0.498 is an exact coin flip. High accuracy (0.894) is the "confirm everything" score on a 90%-positive slice, not capability. The MT bridge lifts non-English *supported* recall (r1_mt is a support feature) but the frozen weights - trained on English-dominant private RAG + English VitaminC - encode no cross-lingual hallucination signal. v1 gold concealed this entirely: it had almost no non-English claims to be wrong about.

**Implication**: the cross-lingual capability the earlier MT-bridge experiments validated (RESULTS.md Round 1, balanced ~0.78) lived in a tuned-threshold experiment harness, not the shipped fixed-0.40 manifold. To ship real multilingual hallucination detection the manifold must be retrained on a non-English negative population - which gold v2 now provides (139 non-English negatives, up from ~handful). Registered as the Round 9 candidate.

## Round 9 (H17) - cross-lingual retrain: the fix is a threshold, not the weights alone, 2026-06-17

Driver `round9.py` (features / audit / eval / threshold / retrain), gold v2 + VitaminC (400/label) + short-source aug = 7,212 rows, HIGH features cached. Retrain writes `config_document_processing.experiment.yaml` only; shipped config untouched. Honest evaluation: 5-fold out-of-fold (every gold row gets a held-out prediction) plus leave-one-language-out (train without a language's negatives entirely).

**Stage 1 - features separate, confirmed at full scale.** On the 1,343 non-EN rows the shipped features already rank hallucination below support: `r1_mt` AUC 0.806, `r1_best` 0.803, `unmatched_rarity` 0.802 (inverted), `max_unmatched` 0.663 (inverted); surface overlap weak cross-lingually (`r1_direct` 0.592). Per base-language `r1_best` AUC is consistently strong - fr 0.866, it 0.893, nb 0.806, es 0.791, sv 0.762, pt 0.722 (nl 0.514 at n=5). MT bridge fires on 82.4% of non-EN rows. The defect is the weights, not the features.

**Stage 2 - retrain.** Gold v2 + VitaminC + aug, non-EN oversampled 3x; HIGH manifold now weights `r1_mt +2.36` (shipped ~0, killed by English collinearity where `r1_mt==r1_direct`), `r1_direct -4.37`, threshold 0.35.

**Stage 3 - the retrain alone misses, and the diagnosis is the operating point:**

| manifold | non-EN TNR | non-EN bal-acc | EN TNR | EN bal-acc |
|---|---|---|---|---|
| shipped HIGH (baseline) | 0.000 | 0.498 | 0.710 | 0.797 |
| retrained, OOF, single global threshold | 0.129 | 0.548 | 0.850 | 0.821 |

The retrain *improves English* (TNR 0.710 -> 0.850) but non-EN TNR 0.13 is well below the pre-registered 0.30 bar, and LOLO at the global threshold collapses (fr 0.000, nb 0.000). Cause: `r1_mt` ranks non-EN hallucinations below supports (AUC 0.80) but their absolute probabilities still sit above a threshold calibrated to the English bulk. Sweeping a **non-EN-specific** threshold on the OOF probabilities (English keeps its own) converts the ranking into catches:

| non-EN threshold | TNR (catch) | TPR (confirm) | bal-acc |
|---|---|---|---|
| 0.45 | 0.295 | 0.924 | 0.610 |
| 0.50 | 0.396 | 0.903 | 0.649 |
| 0.65 | 0.676 | 0.797 | 0.736 |
| 0.70 | 0.748 | 0.758 | 0.753 |

**And it generalizes.** LOLO at a fixed non-EN threshold of 0.65 (held-out language never in training): es TNR 0.743, fr 0.643, nb 0.647, pt 0.600, sv 0.929 - every unseen language clears the 0.30 bar 2-3x, against 0.000 at the global threshold. The fix is deterministic and in-contract: retrained weights + a language-conditional decision threshold keyed off `is_en`, which the pipeline already computes. No new feature, no LLM.

**Stage 4 - MT coverage is not the lever.** argos packages for es/fr/pt/nb/sv/da were already installed, covering 114 of 139 non-EN negatives; only nl (5 negatives) was missing (now installed). The 82.4% firing gap is mis-detection / cognate translations and the long tail, not the high-volume languages.

**Verdict.** H17 as pre-registered (retrain, one threshold) MISSES the bar (OOF non-EN TNR 0.13). The retrain plus a non-English threshold (~0.65) is the real fix - LOLO non-EN TNR 0.60-0.93 at TPR 0.50-0.87, English held/improved. Shipping it needs a shipped-code change (`LexicalVerdict.confirmed` picks the threshold by `is_en`; config carries a non-EN threshold) - held for explicit approval; shipped weights and config untouched this round.

### Ship calibration + no-regression guard

Code landed (`LexicalVerdict.threshold_non_en` / `threshold_for`, `grounding.py:965`, back-compat). Chosen HIGH thresholds: english 0.290 (macro-F1-tuned on the EN slice), non_english 0.750 (balanced-acc knee). `round9.py shipcal` benchmarks shipped vs recalibrated HIGH on every corpus:

| corpus | shipped | recalibrated |
|---|---|---|
| gold_en (4569) | F1 0.803 / bal 0.797 / TNR 0.710 | F1 0.817 / bal 0.820 / TNR 0.804 |
| gold_non_en (1343) | F1 0.472 / bal 0.498 / TNR 0.000 | F1 0.606 / bal 0.767 / TNR 0.813 |
| articles held-out EN (42) | F1 0.797 / bal 0.861 / TNR 0.833 | F1 0.816 / bal 0.931 / TNR 1.000 |
| vitaminc (800) | F1 0.695 / bal 0.695 / TNR 0.703 | F1 0.680 / bal 0.680 / TNR 0.662 |

Both real English corpora (gold_en, held-out articles) improve, non-English goes 0.000 -> 0.813 TNR, and the recalibrated EN gold matches the shipped's old private-RAG F1 (0.817). The lone regression at vit x1 is VitaminC -0.015, a synthetic English fact-verification benchmark outside the deployment's traffic - it breaches the pre-registered 0.01 VitaminC guard.

**Recovery - VitaminC up-weight sweep.** The gold-v2 retrain dilutes the English contrastive-REFUTES signal VitaminC tests; replicating VitaminC rows before the fit restores it. Sweep (gold_ne x3, vit x{1,3,5,8}), macro-F1 delta vs shipped:

| vit | gold_en | gold_non_en | vitaminc | articles |
|---|---|---|---|---|
| x1 | +0.015 | +0.134 | **-0.015** | +0.019 |
| **x3** | **+0.003** | **+0.138** | **+0.003** | **+0.019** |
| x5 | -0.013 | +0.142 | +0.019 | -0.089 |
| x8 | -0.044 | +0.147 | +0.016 | -0.059 |

**vit x3 clears every corpus** - all four hold or improve, VitaminC recovers to +0.003, non-English keeps +0.138. vit x5/x8 over-correct, collapsing articles (over-fitting the VitaminC contrastive regime).

### Shipped - threshold-only (weights untouched)

The recalibrated weights would have shipped, but the ship step found a simpler fix. Writing them broke two English e2e precision tests (the gold-v2-optimal English threshold 0.290 over-confirms borderline fabrications vs the shipped 0.40), and the recalibration turned out to be unnecessary: the **shipped weights already rank non-English hallucinations below support**. Shipped HIGH weights unchanged + a non-English threshold sweep on the gold-v2 non-EN slice (held-out for the shipped weights, which never trained on these negatives):

| non-EN thr | TNR | TPR | bal-acc |
|---|---|---|---|
| 0.40 (global) | 0.165 | 0.963 | 0.564 |
| 0.65 | 0.669 | 0.807 | 0.738 |
| **0.70** | **0.748** | **0.761** | **0.754** |
| 0.75 | 0.806 | 0.718 | 0.762 |

Per-language at 0.70: es 0.80 / fr 0.71 / nb 0.71 / pt 0.65 / sv 0.93 / it 0.71 / nl 1.00 TNR - generalises with no weight change. **Ship = shipped HIGH block + `threshold_non_en: 0.70`**, one config line, English byte-identical (gold_en / VitaminC / articles / all e2e tests unchanged), non-English TNR 0.000 -> 0.748. The recalibration remains an experiment - it churns English and breaks precision tests for no net gain. The 4 calibration-engine test failures in this env are pre-existing (pytensor C-compile, unrelated).

## Round 10 (H18) - synthetic non-English negatives by translation, 2026-06-17

`synth_mt.py` (select / translate / verify / build) translated 120 English negatives (gold v2 English hallucinations) into 9 languages via `claude -p` - Haiku translates, Sonnet verifies fidelity (same numbers / entities / polarity). The verify gate dropped ~7 drifted translations, keeping 1,053 verified synthetic non-English negatives across da/de/es/fr/it/nb/nl/pt/sv. Every row carries `origin="synthetic_mt"` + source ids + target_lang + verified flag and lives in the gitignored stash; train-only, all metrics on the real gold v2 non-English slice.

| training | global-thr real non-EN TNR | TPR |
|---|---|---|
| shipped weights (0.40) | 0.000 | 0.997 |
| retrain, no synthetic (0.35) | 0.158 | 0.973 |
| retrain + 1,053 synthetic (0.45) | 0.683 | 0.768 |

The headline: a **single global threshold** now catches 68% of real non-English hallucinations - the language-conditional `threshold_non_en` patch is no longer required. Round 9's retrain-alone reached only 0.158 at the global cut; the synthetic negatives are what lets the weights, not a special-cased threshold, carry the cross-lingual signal. LOLO at the global threshold (held-out language excluded from both real and synthetic training) confirms transfer to unseen languages: es 0.714, fr 0.786, pt 0.600, nb 0.706, sv 0.714 (vs 0.000 in Round 9). Cost: support recall 0.768 at the global cut (rejects 23% of supported non-English claims), comparable to the shipped patch. Limitation: de back-translation model absent, so 117 de synthetic rows had degraded `r1_mt`; synthetic sources are gold-domain only (no VitaminC contrastive type). Shipping the synthetic-retrained weights needs the Round 9 English no-regression guard (recalibration breaks English precision e2e tests) - deferred; this round proves the data mechanism.
