# Benchmark - cross-lingual grounding experiment

Running scoreboard for every hypothesis tested on the 375-record verified gold. Tracks results, gains vs baseline, regressions, and notes. Updated as experiments complete.

**Primary metric: macro-F1** (mean of supported-F1 and hallucination-F1). The classes are imbalanced (289 supported / 86 hallucination), so accuracy flatters a "mostly grounded" predictor - the majority baseline scores 0.771 accuracy but **macro-F1 0.435 with hallucination-F1 0.000** (it never catches a hallucination). Accuracy is kept as a secondary column.

**Targets**: macro-F1 as high as possible; accuracy > 0.80 (secondary). Status: **accuracy target MET** (recall_split 0.845 LOLO / 0.817 TEST); **best macro-F1 0.755 TEST** (recall_split).

**Baselines**: majority-always-grounded macro-F1 0.435 / acc 0.771; lexical-only (no MT) macro-F1 ~0.66; e5-semantic (team report) ~25% precision ceiling.

## Scoreboard - macro-F1 headline (MT bridge on unless noted)

| # | experiment | LOLO macroF1 | sup-F1 | hal-F1 | LOLO acc | TEST macroF1 | TEST acc | notes |
|---|---|---|---|---|---|---|---|---|
| base | majority always-1 | 0.435 | 0.87 | 0.00 | 0.771 | - | - | never catches hallucination - why F1 |
| - | lexical-only recall_only | ~0.66 | - | - | 0.683 | - | 0.675 | non-English not rescued |
| MT | recall_only + MT | **0.751** | 0.90 | 0.60 | 0.845 | 0.732 | 0.791 | MT closes Gap B |
| #1 | recall_split (en/translated bars) | **0.751** | 0.90 | 0.60 | 0.845 | **0.755** | **0.817** | best TEST F1 + accuracy >0.80 |
| #7 | fixed-prior recall τ=0.40 | (see table) | - | - | - | - | - | zero tuning ≈ tuned |
| #8 | abstain band (lo.30 hi.55) | - | - | - | - | - | - | macroF1-on-covered, 68% coverage |
| #6 | recall_only + MT + lingua | ~0.74 | - | - | 0.781 | - | 0.785 | mismatch 65→44; over-splits nb/nn |
| #2 | chunk sweep (word AUC) | - | - | - | - | - | - | 0.50 whole-doc → 0.728 char/150 |
| #4 | NLI-alone (entailment, argmax) | 0.644 | 0.72 | 0.57 | 0.659 | - | - | parameter-free; hal-recall 0.99 |
| #5 | recall OR NLI ensemble (τ0.4) | 0.737 | 0.83 | **0.64** | 0.773 | - | - | best hal-F1 + balanced 0.808; rescues tail |
| #3 | OPUS-MT (mul-en), recall_split | 0.739 | 0.90 | 0.58 | 0.835 | 0.734 | 0.796 | **worse than argos + ~9x slower** (1037 vs 118 ms/claim) |

## Hypothesis status

- [x] **H-recall** - best-chunk IDF recall separates the classes (Gap A): confirmed, AUC 0.72-0.73
- [x] **H-MT** - a frozen translator collapses Gap B into Gap A: confirmed, per-language no/fr/it → 1.00 LOLO
- [x] **H-split (#1)** - separate en/translated bars: best TEST macro-F1 0.755 + accuracy 0.817
- [x] **H-chunk (#2)** - chunk granularity controls separation: confirmed, whole-doc = 0.50 AUC floor
- [x] **H-fixed (#7)** - a fixed threshold generalises: confirmed
- [x] **H-abstain (#8)** - abstaining raises precision on the covered set: confirmed
- [x] **H-lingua (#6)** - better language ID lifts accuracy 0.725 → 0.781
- [x] **H-NLI (#4/#5)** - NLI rescues the abstractive tail: confirmed - ensemble macro-F1 0.737, best hal-F1 0.64 / balanced 0.808, per-language es 0.33→0.50, pt 0.60→0.80, no 0.82→0.95
- [x] **H-opus (#3)** - OPUS-MT translates better than argos: **REFUTED** - opus-mt-mul-en scores macro-F1 0.739 LOLO / 0.734 TEST vs argos 0.751 / 0.755, and is ~9x slower (1037 vs 118 ms/claim); argos per-language models win on quality and speed

## Gains

- **F1 reframing** is itself a finding: accuracy 0.771 → macro-F1 0.435 for the majority predictor exposes that accuracy was hiding zero hallucination detection
- MT bridge: lexical-only ~0.66 → 0.751 LOLO macro-F1; per-language no 0.40 → 1.00 LOLO accuracy under F1-tuning
- English two-threshold: best TEST macro-F1 0.755 and accuracy 0.817 (>0.80)
- F1-tuned thresholds also lifted the tail: es LOLO 0.33 → 0.67, pt → 0.80

## Regressions / things that hurt

- **Bridge/meta stack under MT** - `global` macro-F1 0.630 vs recall_only 0.751; the char-ngram bridge floor admits hallucinations (hal-F1 0.43)
- **Contradiction gate under MT** - `recall_contra`/`weighted` below recall_only; over-fires once MT is present
- **OPUS first run** - silent no-op (pipeline task unavailable) returned the lexical-only numbers; caught only because per-language matched the no-MT baseline
- **lingua over-splitting** - Norwegian → nb/nn, a few short-claim misfires; net positive
- **es/pt tail** - n=5-6, noisy; NLI ensemble is the lever there

## Round 2 - interactions + wildcards (LOLO, learned models)

Tested whether feature interactions / nonlinear separation beat the 1-D recall floor. **They do not** - the 375 with 86 negatives is effectively 1-dimensional under LOLO.

| hypothesis | macroF1 | hal-F1 | verdict |
|---|---|---|---|
| floor: LR[r1] | 0.731 | 0.57 | 1-D logistic ≈ recall_split |
| A1 language×recall interaction | 0.691 | 0.49 | **REFUTED** - worse than its no-interaction twin (0.714) and the floor; overfits out-of-fold |
| A3 r1×nli_contra product | 0.726 | 0.63 | **REFUTED** - identical to twin (0.728); the "right-topic-wrong-fact" cell is n=10 at 0.20 hal-rate < 0.23 base, doesn't exist |
| A5 continuous-NLI logistic | 0.728 | 0.63 | below recall_split 0.751; continuous NLI no better than the OR-ensemble |
| C1 oracle-chunk | 0.701 | - | **retrieval is NOT the bottleneck** - oracle loss −0.029 (recall-max picks spurious chunks); kills C2-doc/C4 |
| C6 anchor-as-veto | 0.687 | 0.59 | neutral - only 3 false-vetoes, few mismatches fire |

**Conclusion**: learned and interaction models *underperform* the hand-routed `recall_split` (0.751). The simple model wins not by constraint but because the data cannot fund more capacity - the A6 capacity ceiling sits at ~1 feature. Live mechanisms remaining: A4 (learn the balance off-target on VitaminC) and Theme B (claim decomposition - an orthogonal lever on hallucination-F1).

## Round 3 - claim decomposition (Theme B, LOLO)

Tested whether splitting multi-fact claims and aggregating beats whole-claim grounding. **It does not** - decomposition over-flags paraphrased supported clauses.

| unit / aggregation | macroF1 | hal-F1 | sup-F1 | verdict |
|---|---|---|---|---|
| whole-claim | 0.752 | 0.61 | 0.90 | baseline (≈ recall_split) |
| sentence-split | 0.739 | 0.58 | 0.89 | no-op-to-harmful (claims are 1 sentence) |
| clause-split, any-contradicted | 0.732 | 0.60 | 0.86 | **REFUTED** - sup-F1 drops, hal-F1 flat |
| clause-split, k-of-n | 0.714 | 0.60 | 0.83 | **REFUTED** - worst |

146/375 claims split into >1 clause; min-over-clauses recall false-flags supported claims whose clauses are legitimately paraphrased, and the hal-F1 gain the decomposition was meant to deliver never materialises (B7 honesty-check falsifier confirmed). The whole-claim 1-D recall model is robust at this dataset size.

## Round 4 - cross-corpus transfer (A4, learn the balance off-target)

Fit the {recall, nli_entail, nli_contra} logistic on a balanced 390-record VitaminC slice, froze it, applied to the gold at a fixed threshold (zero gold fit).

| rule | macroF1 | hal-F1 | sup-F1 | verdict |
|---|---|---|---|---|
| VitaminC-frozen @0.5 | 0.594 | 0.34 | 0.85 | **REFUTED** - domain mismatch |
| VitaminC-frozen @0.4 | 0.581 | 0.30 | 0.86 | **REFUTED** |

The learned coefficients tell the story: `r1: 0.0, nli_e: 0.02, nli_c: -3.03`. VitaminC (short English FEVER sentences) is an **NLI-dominant** domain and learns to ignore recall; DeLaval is a **recall-dominant** cross-lingual domain. The balance learned off-target is the wrong balance, so transfer collapses. Honest conclusion: the correct signal weighting is domain-specific and cannot be borrowed.

## Synthesis - what beats the simple model (nothing, here)

All three advanced mechanisms tested across rounds 2-4 are **refuted** on this 375-record gold:

- **Feature interactions** (language×recall, r1×nli_contra) - overfit the 86 negatives under LOLO, score below the 1-D floor
- **Claim decomposition** (clause-split, k-of-n) - over-flags paraphrased supported clauses, no net hal-F1 gain
- **Cross-corpus transfer** (VitaminC) - mis-weights signals (NLI-dominant source vs recall-dominant target)

The **A6 capacity ceiling is confirmed**: with 86 hallucinations (and LOLO removing a language each fold), the data funds ~1 feature. The deliverable recommendation is unchanged and now well-defended: ship the simple **translate-then-recall** model (`recall_split`, macro-F1 0.755) and add the parameter-free **recall-OR-NLI** ensemble for hallucination detection (hal-F1 0.64). Beating this needs **more labelled data**, not a cleverer model.

## Recommendation (all 9 hypotheses tested)

- **Ship**: argos-translate MT bridge + best-chunk recall, English/translated two-threshold (`recall_split`) - best macro-F1 0.755 TEST and accuracy 0.817, cheapest path
- **Add for hallucination detection**: the `recall OR NLI` ensemble - best hallucination-F1 0.64 and balanced 0.808, parameter-free, rescues the es/pt tail
- **Drop**: the lexicon / cognate / anchor bridges and the contradiction/meta stack (hurt once MT is present); OPUS-MT (worse + 9x slower than argos)
- **Optional**: lingua-py (small accuracy gain), abstain band (when precision matters more than coverage)

## Notes

- All headline numbers out-of-fold (LOLO) or held-out (TEST); no learner fit to the 375; thresholds tuned to maximise macro-F1 on the fold only.
- Accuracy vs macro-F1 mostly agree now that thresholds are F1-tuned; recall_split leads on both.
- Client gold/transcripts git-ignored; this file carries aggregate numbers only.
