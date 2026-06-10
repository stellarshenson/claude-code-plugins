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
