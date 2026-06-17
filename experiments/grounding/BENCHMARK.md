# Benchmark - cross-lingual grounding experiment

Running scoreboard for every hypothesis tested on the 375-record verified gold. Tracks results, gains vs baseline, regressions, and notes. Updated as experiments complete.

**Primary metric: macro-F1** (mean of supported-F1 and hallucination-F1). The classes are imbalanced (289 supported / 86 hallucination), so accuracy flatters a "mostly grounded" predictor - the majority baseline scores 0.771 accuracy but **macro-F1 0.435 with hallucination-F1 0.000** (it never catches a hallucination). Accuracy is kept as a secondary column.

**Targets**: macro-F1 as high as possible. Status (LIVE 1260 gold): **best model is a lexical-only, language-routed logistic + a claim-intrinsic `specificity` feature - macro-F1 0.845 (leave-one-source-out) / 0.793 (leave-one-language-out), hallucination-F1 0.81 - with NO semantic model**. Plus a `quote_flag` precision-0.98 supported confirm. See Rounds 5-6. (Earlier rounds on the stale 375 snapshot: depth-2 GBT 0.775 - superseded by the 856 re-run, where more data + language-routed lexical features made NLI and trees unnecessary.)

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

Tested whether feature interactions / nonlinear separation beat the 1-D recall floor. **Linear interactions do not; depth-2 tree interactions do** (see the A6 capacity sweep below).

| hypothesis | macroF1 | hal-F1 | verdict |
|---|---|---|---|
| floor: LR[r1] | 0.731 | 0.57 | 1-D logistic ≈ recall_split |
| A1 language×recall interaction (linear) | 0.691 | 0.49 | **REFUTED** - worse than its no-interaction twin (0.714); a *linear* interaction overfits out-of-fold |
| A3 r1×nli_contra product (linear) | 0.726 | 0.63 | **REFUTED** - identical to twin (0.728); the "right-topic-wrong-fact" cell is n=10 at 0.20 hal-rate < 0.23 base, doesn't exist |
| A5 continuous-NLI logistic | 0.728 | 0.63 | linear; below recall_split |
| **A2 depth-2 GBT {recall,NLI,anchors}** | **0.775** | **0.66** | **CONFIRMED** - mean of 5 seeds ±0.013, beats recall_split on macro-F1, hal-F1, and accuracy (0.861) |
| C1 oracle-chunk | 0.701 | - | **retrieval is NOT the bottleneck** - oracle loss −0.029 (recall-max picks spurious chunks); kills C2-doc/C4 |
| C6 anchor-as-veto | 0.687 | 0.59 | neutral - only 3 false-vetoes, few mismatches fire |

## A6 capacity ceiling (the explanatory result, plots/05_capacity_ceiling.png)

LOLO macro-F1 vs model capacity, with in-fold (resubstitution) overlay:

| model | LOLO macroF1 | hal-F1 | acc | in-fold | overfit gap |
|---|---|---|---|---|---|
| LR[r1] | 0.731 | 0.57 | 0.827 | 0.753 | +0.02 |
| LR[r1,nli] | 0.728 | 0.63 | 0.760 | 0.750 | +0.02 |
| Bayesian calibrator (bambi/PyMC) | 0.733 | 0.63 | 0.771 | - | - |
| LR+interactions (linear) | 0.691 | 0.49 | 0.819 | 0.761 | +0.07 |
| **GBT depth-2** | **0.785** | 0.66 | 0.861 | 0.909 | +0.12 |
| GBT depth-4 | 0.733 | 0.56 | 0.851 | 0.996 | +0.26 |

**Model class is the lever, not the fitting method**: the production Bayesian calibrator (`fit_calibrator`, bambi/PyMC) is a Bayesian *logistic* - a hyperplane - so it lands at the linear-logistic level (0.733) and cannot carve the recall×NLI interaction the depth-2 GBT captures (0.775). The calibrator's worth is calibrated uncertainty, not higher accuracy.

The curve is the classic scissors: in-fold rises monotonically to 0.996 (memorisation) while **LOLO peaks at depth-2** (0.785, above recall_split's 0.755) then falls. Depth-2 axis-aligned tree interactions over {recall, NLI, anchors} are exactly the capacity the 86 negatives can fund; deeper trees and free-form linear interactions overfit. **Corrected conclusion**: feature interactions DO help, but only as shallow trees - the round-2 "1-D is enough" read was an artefact of testing only linear interactions.

C8 diversity: error-correlation phi(R1,NLI)=0.47, phi(R1,anchor)=0.04, phi(NLI,anchor)=−0.14; R1-OR-NLI ensemble macro-F1 0.737, the anchor channel is too sparse to add (triple majority 0.677). The GBT wins by learning the R1×NLI combination nonlinearly that the OR-rule and linear models cannot.

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

The learned coefficients tell the story: `r1: 0.0, nli_e: 0.02, nli_c: -3.03`. VitaminC (short English FEVER sentences) is an **NLI-dominant** domain and learns to ignore recall; private RAG is a **recall-dominant** cross-lingual domain. The balance learned off-target is the wrong balance, so transfer collapses. Honest conclusion: the correct signal weighting is domain-specific and cannot be borrowed.

## Synthesis - what beats the simple model

One mechanism beats it, two do not:

- **Feature interactions via a depth-2 GBT** - **CONFIRMED**: macro-F1 0.775 (±0.013), hal-F1 0.66, acc 0.861, beating `recall_split` on all three. Linear interactions overfit; the win is specifically *shallow tree* interactions over {recall, NLI, anchors}.
- **Claim decomposition** (clause-split, k-of-n) - **refuted**: over-flags paraphrased supported clauses, no net hal-F1 gain.
- **Cross-corpus transfer** (VitaminC) - **refuted**: mis-weights signals (NLI-dominant source vs recall-dominant target).

The **A6 capacity ceiling** governs everything: the 86 negatives (LOLO removes a language each fold) fund exactly the depth-2 GBT and nothing larger - deeper trees and free linear interactions overfit (in-fold → 0.996, LOLO falls). Recommendation: ship `recall_split` (macro-F1 0.755) when a transparent rule is required; deploy the **depth-2 GBT fit under LOLO** (macro-F1 0.775, hal-F1 0.66) when a learned model is acceptable. Pushing materially past 0.78 needs **more labelled data**, not more capacity.

## Round 5 - lexical-only, language-routed grounder (LIVE gold, NO NLI)

The dataset was refreshed to the live gold, now **1260 records, 794 supported / 466 hallucination, 22 source contexts** (grew 375 → 856 → 1260 mid-experiment). Dropped NLI (a semantic scorer); built per-claim + per-chunk language detection (lingua), a `same_lang` flag, and dual lexical recall (`r1_direct` = claim vs chunks as-is; `r1_mt` = translate-then-recall), then learned the verdict. Validated under leave-one-language-out (LOLO) AND leave-one-source-out (LOSO).

| model (1260, no NLI) | LOLO macroF1 | LOLO hal-F1 | LOSO macroF1 | LOSO hal-F1 |
|---|---|---|---|---|
| **LR (lexical, language-routed)** | **0.779** | 0.70 | **0.837** | **0.80** |
| LR + interactions | 0.773 | 0.69 | 0.833 | 0.79 |
| LGBM d1 (class_weight=balanced) | 0.751 | 0.65 | 0.837 | 0.80 |
| LGBM d2 | 0.586 | 0.36 | 0.836 | 0.80 |
| LGBM d4 | 0.526 | 0.26 | 0.826 | 0.78 |

Replication across the 856 → 1260 growth: LR (lexical) LOSO 0.829 → **0.837** (hal-F1 0.78 → 0.80) - rock-stable; LOLO 0.807 → 0.779 (English is now 86% of the data, so the English-out fold trains on ~178 non-English rows - an extreme split that LOSO avoids, which is why LOSO is the metric to trust). LGBM overfits LOLO at every growth; LR matches or beats it everywhere.

Reference (1260): `recall_split` and the NLI-including model remain below the lexical-only logistic; majority macro-F1 ~0.39.

**Findings:**
- **Lexical-only beats NLI** - LR over the language-routed lexical features (0.807 / hal-F1 0.75) tops the NLI-including model (0.797 / 0.72). The `same_lang` flag + dual recall + anchors replace what NLI was providing. Dropping the semantic model gained accuracy, simplicity, and speed.
- **The win is the features, not the model class** - a plain logistic is best; the LGBM overfits under LOLO and worsens with depth (d1 0.743 → d4 0.537). Holding out English trains on only ~143 non-English rows, which a tree memorises and a regularised linear model survives.
- **LOSO ≥ LOLO (0.83 vs 0.81)** - context leakage is NOT inflating results; the harder axis is an unseen language, not an unseen document. The ~19-context worry is allayed.
- **Same-language coverage** validates the routing: en 96%, fr 46%, sv 50% match a same-language chunk (no MT); no 5%, it 10%, es/pt low (need MT).

**New recommendation**: ship the **lexical-only, language-routed logistic** (per-chunk language detection + `same_lang` + `r1_direct`/`r1_mt` + anchors) - macro-F1 0.807, hal-F1 0.75, no semantic model, beats every prior config on the live 856 gold.

## Round 6 - mechanism-general features (don't memorise the text)

Three features designed to capture the *way* claims are (un)supported, not the dataset's surface text. Acceptance gate: must raise leave-one-source-out (LOSO) without widening the LOLO↔LOSO gap. LR over the lexical features, 1260 gold.

| model | LOLO macroF1 | LOLO hal-F1 | LOSO macroF1 | LOSO hal-F1 |
|---|---|---|---|---|
| base (lexical) | 0.779 | 0.70 | 0.837 | 0.80 |
| base + H1 rarity | 0.782 | 0.71 | 0.834 | 0.80 |
| base + H2 span | 0.780 | 0.70 | 0.838 | 0.80 |
| **base + H3 claim-intrinsic** | **0.793** | **0.72** | **0.845** | **0.81** |
| base + all | 0.789 | 0.71 | 0.838 | 0.80 |

- **H3 `specificity` (anchor density from the claim ALONE) wins** - lifts both splits (LOSO 0.837 → 0.845, LOLO 0.779 → 0.793) and narrows the LOLO↔LOSO gap (0.058 → 0.052), the signature of generalisation not memorisation. It is evidence-independent by construction, so it cannot stick to the 22 documents. Strongest new standardized coefficient (+0.96). **Ship it.**
- **H2 `quote_flag` is a precision-0.982 supported detector** - a ≥40-char contiguous verbatim span fires on 109/1260 claims at 98.2% supported (base 63%); a usable high-confidence confirm rule, though it does not move aggregate F1 (high precision, low coverage, recall-redundant when pooled).
- **H1 background-rarity gap** - correctly signed (−0.86) but redundant with recall (recall AUC 0.878 already captures content presence); net neutral, drop.
- **base + all < base + H3** - the redundant features dilute; parsimony wins.

**New best**: lexical-only logistic + claim-intrinsic `specificity` - **LOSO macro-F1 0.845 / hal-F1 0.81**, with `quote_flag` as a precision-0.98 supported confirm.

## Round 7 - claim-segmentation competition (SaT vs regex), two signals

Tested wtpsplit SaT for claim extraction against the current regex clause-split, scored two ways: **our metric** (grounding macro-F1, LOLO + LOSO, min-recall + any-contradicted) and an **LLM-as-judge** that catches segmentation artefacts the metric cannot see. Non-English claims translated via the new torch-free `mt.py` (CTranslate2 + SaT).

| segmentation | units/claim | LOLO macroF1 | LOLO hal-F1 | LOSO macroF1 | LOSO hal-F1 |
|---|---|---|---|---|---|
| whole-claim (no split) | 1.0 | 0.723 | 0.61 | 0.772 | 0.72 |
| regex clause-split (current) | 1.49 | 0.764 | 0.70 | 0.764 | 0.70 |
| **SaT (wtpsplit)** | 1.52 | **0.776** | **0.71** | **0.776** | **0.71** |

**LLM-judge** (16 multi-fact claims, randomized A/B): **SaT 15, regex 1, tie 0**.

- **SaT wins both signals** - ≥ regex on macro-F1 everywhere (LOLO 0.776 vs 0.764), and 15-1 on the LLM judge. Zero-risk swap: neutral-to-better on the metric, decisively cleaner units
- **The LLM judge is the artefact signal** - regex strips `and`/`but` and garbles clauses ("T01 converts X **the** T03..."); the metric can't see this (a mangled unit still recalls tokens), the judge can
- **Decomposition now helps - reverses Round 3** - on the small 856 set clause-split hurt; on the live 1260 (466 negatives) it lifts hallucination detection (hal-F1 0.61 → 0.71) because "split + any-contradicted-wins" catches a fabricated clause whole-claim recall masks. Another small-data conclusion that didn't survive more data
- **Caveats** - the macro-F1 gain over whole-claim is large on LOLO (+0.053) but small on LOSO (+0.004), and this is within the simple min-recall rule, not the full lexical model (0.845). SaT is validated as the better claim-extraction method; folding it into the full model is the open follow-up

## Recommendation (all 9 hypotheses tested - superseded by Round 5/6/7)

- **Ship**: argos-translate MT bridge + best-chunk recall, English/translated two-threshold (`recall_split`) - best macro-F1 0.755 TEST and accuracy 0.817, cheapest path
- **Add for hallucination detection**: the `recall OR NLI` ensemble - best hallucination-F1 0.64 and balanced 0.808, parameter-free, rescues the es/pt tail
- **Drop**: the lexicon / cognate / anchor bridges and the contradiction/meta stack (hurt once MT is present); OPUS-MT (worse + 9x slower than argos)
- **Optional**: lingua-py (small accuracy gain), abstain band (when precision matters more than coverage)

## Notes

- All headline numbers out-of-fold (LOLO) or held-out (TEST); no learner fit to the 375; thresholds tuned to maximise macro-F1 on the fold only.
- Accuracy vs macro-F1 mostly agree now that thresholds are F1-tuned; recall_split leads on both.
- Client gold/transcripts git-ignored; this file carries aggregate numbers only.

## Round 7 - batch-adaptive operating point (max-gap / Jenks), 2026-06-10

Unsupervised per-batch threshold cuts on the shipped high-manifold `p_high`, batch = sub-dataset kind. Notebook: `notebooks/03-kj-H12-maxgap-batch-experiment.ipynb`; data: `data/processed/grounding_combined.parquet` (gitignored). Macro-F1:

| strategy | articles | private_rag | vitaminc | mean |
|---|---|---|---|---|
| fixed (shipped 0.4) | 0.797 | 0.829 | 0.695 | 0.774 |
| tuned per-corpus (supervised ref) | 0.903 | 0.831 | 0.702 | 0.812 |
| maxgap | 0.816 | 0.419 | 0.346 | 0.527 |
| maxgap bottom-half | 0.816 | 0.419 | 0.676 | 0.637 |
| jenks (jenkspy, k=2) | 0.762 | 0.794 | 0.697 | 0.751 |
| maxgap + gap floor >= 0.02 | 0.816 | 0.829 | 0.695 | 0.780 |

**Verdict: REJECTED at corpus granularity.** Large dense corpora are unimodal (largest gap 0.001-0.013 = noise; cuts land at 0.047/0.954, flipping 350-770 verdicts). A gap-significance floor degrades gracefully to fixed and only fires on the bimodal 42-claim articles batch (+0.019 mean) - the pre-registered benchmark-overfit falsifier. Surviving signal: per-NATURAL-group cuts on the 63 mixed-label groups (n>=4) beat fixed (articles 0.843 vs 0.808, traces 0.642 vs 0.609) - follow-up hypothesis is per-trace cuts with an unsupervised guard, scored on all traces including single-class.

## Round 8 - claim-extraction mechanism (A1), 2026-06-11

Extraction head-to-head on the 639 raw private RAG answer documents (trace cache; module `mechanisms.py`, logs `logs/round8-*.log`). Gates killed A2 (atomic-fact scoring), H-B (alignment-profile) and H-C (negation flag) pre-build; A1 survived.

| variant | claims/doc | inflation | gold coverage | en accept | nb accept | it accept |
|---|---|---|---|---|---|---|
| shipped (regex + EN verb gate) | 13.03 | 1.00 | 1.000 (circular) | 0.908 | 0.496 | 0.145 |
| gate-only (regex + agnostic gate) | 14.74 | 1.13 | 0.997 | - | - | - |
| SaT + agnostic gate | 17.13 | 1.31 | 0.990 | - | - | - |

Accept columns = per-language verb-gate acceptance rate of length-passing sentences (diagnostic). Scoring benchmarks (0.817 / 0.691 / 0.808) unaffected this round - they consume pre-extracted claims. Open follow-ups: sampled dual-judge precision pass on newly admitted sentences; gold v2 rebuild through the new extractor.

## Round 8b - gold v2 re-baseline (survivorship bias removed), 2026-06-11

Gold rebuilt through the H13 front door (`gold_v2.py`), dual-judged (Haiku+Sonnet), 5,912 rows / 84% trace coverage. Shipped HIGH manifold, fixed threshold 0.40.

| slice | n | macro-F1 | balanced acc | supported recall | halluc recall (TNR) |
|---|---|---|---|---|---|
| overall | 5,912 | 0.802 | - | - | - |
| inherited | 3,619 | 0.782 | - | - | - |
| judged-new | 2,293 | 0.821 | - | - | - |
| english | 4,569 | 0.803 | 0.797 | 0.884 | 0.710 |
| non-english | 1,343 | 0.472 | 0.498 | 0.997 | 0.000 |

Finding: shipped manifold is an English-only hallucination detector - non-English TNR 0.000 (confirms 1,339/1,343, catches 0/139 hallucinations). v1's 0.817 was an English-only score in disguise; v1 gold under-represented non-English because the anglocentric extractor dropped those claims pre-judging. Extraction precision of new admissions: 48.8% real claims, 32.7% noise. Round 9 candidate: retrain manifold on the non-English negative population gold v2 now exposes.

## Round 9 - cross-lingual retrain (H17), non-EN hallucination recall, 2026-06-17

Gold v2 + VitaminC + aug, HIGH manifold, honest held-out (5-fold OOF + LOLO). Retrain in experiment-copy config only; shipped weights untouched.

| manifold / operating point | non-EN TNR | non-EN bal-acc | EN TNR | EN bal-acc |
|---|---|---|---|---|
| shipped HIGH (baseline) | 0.000 | 0.498 | 0.710 | 0.797 |
| retrained, single global threshold (OOF) | 0.129 | 0.548 | 0.850 | 0.821 |
| retrained + non-EN threshold 0.65 (OOF) | 0.676 | 0.736 | 0.710* | 0.797* |
| retrained + non-EN threshold 0.70 (OOF) | 0.748 | 0.753 | 0.710* | 0.797* |

\* English keeps its own (shipped/retrained) threshold; the non-EN threshold applies only to `is_en=0` claims.

LOLO at non-EN threshold 0.65 (held-out language never trained on): es 0.743, fr 0.643, nb 0.647, pt 0.600, sv 0.929 - all clear the 0.30 ship bar (vs 0.000 at the global threshold). Pre-registered bar: non-EN TNR >= 0.30 AND EN bal-acc drop <= 0.01 AND VitaminC drop <= 0.01. Retrain-alone MISSES (0.13); retrain + language-conditional threshold CLEARS with generalization. Ship requires a `LexicalVerdict.confirmed` + config change - held for approval.

## Round 9 - ship calibration guard (HIGH, english thr 0.290 / non-english thr 0.750)

`round9.py shipcal`, shipped vs recalibrated HIGH across all corpora.

| corpus | n | shipped F1 | recal F1 | shipped bal/TNR | recal bal/TNR |
|---|---|---|---|---|---|
| gold_en | 4569 | 0.803 | 0.817 | 0.797 / 0.710 | 0.820 / 0.804 |
| gold_non_en | 1343 | 0.472 | 0.606 | 0.498 / 0.000 | 0.767 / 0.813 |
| articles (held-out EN) | 42 | 0.797 | 0.816 | 0.861 / 0.833 | 0.931 / 1.000 |
| vitaminc | 800 | 0.695 | 0.680 | 0.695 / 0.703 | 0.680 / 0.662 |

At vit x1, 3 of 4 corpora improve (both real English sets + non-English fixed); VitaminC -0.015 breaches the 0.01 guard. VitaminC up-weight sweep (gold_ne x3, vit x{1,3,5,8}, macro-F1 delta vs shipped):

| vit | gold_en | gold_non_en | vitaminc | articles |
|---|---|---|---|---|
| x1 | +0.015 | +0.134 | -0.015 | +0.019 |
| x3 | +0.003 | +0.138 | +0.003 | +0.019 |
| x5 | -0.013 | +0.142 | +0.019 | -0.089 |
| x8 | -0.044 | +0.147 | +0.016 | -0.059 |

**vit x3 clears every corpus** (all hold/improve, VitaminC recovered).

## Round 9 - SHIPPED (threshold-only, weights untouched)

Recalibration broke two English e2e precision tests and proved unnecessary: shipped HIGH weights already rank non-English hallucinations below support. Shipped weights + non-EN threshold sweep (gold v2 non-EN slice, held-out for the shipped weights):

| non-EN thr | TNR | TPR | bal-acc |
|---|---|---|---|
| 0.40 (global, shipped) | 0.165 | 0.963 | 0.564 |
| 0.70 (shipped) | 0.748 | 0.761 | 0.754 |

**Ship = shipped HIGH block + `threshold_non_en: 0.70`** - one config line, English byte-identical, non-English TNR 0.000 -> 0.748, generalising per-language (es 0.80 / fr 0.71 / nb 0.71 / pt 0.65 / sv 0.93). Pre-registered bar cleared on every axis with zero English blast radius.

## Round 10 - synthetic translation data (H18), real non-EN slice, global threshold

Synthetic = 1,053 verified non-English negatives (120 English negatives x 9 langs via claude -p, Sonnet-verified). Train-only; eval on real gold v2 non-EN.

| training | global-thr TNR | TPR | LOLO global-thr TNR (held-out lang) |
|---|---|---|---|
| shipped | 0.000 | 0.997 | fr 0.000 / nb 0.000 (Round 9) |
| retrain, no synthetic | 0.158 | 0.973 | - |
| retrain + synthetic | 0.683 | 0.768 | es 0.71 / fr 0.79 / pt 0.60 / nb 0.71 / sv 0.71 |

Synthetic negatives let a single global threshold reach non-EN TNR 0.68 and generalise to unseen languages - retiring the language-conditional `threshold_non_en` patch. Ship of the synthetic-retrained weights deferred (needs the Round 9 English no-regression guard).
