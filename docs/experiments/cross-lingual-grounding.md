# Deterministic cross-lingual grounding on the DeLaval gold

Experiment on the `experiment/grounding` branch testing whether a non-LLM grounder can raise grounding accuracy on a real cross-lingual dataset without training any model on it. Artefacts: `experiments/grounding/{harness.py, HYPOTHESIS.md, RESEARCH.md, RESULTS.md}`; the labelled gold and transcripts stay in a git-ignored stash.

## Situational overview

The lexical grounder confirmed only ~12% of supported claims on a 375-record client gold; re-profiling overturned the team's "semantic is required" conclusion.

- **Dataset** - 375 verified records `{claim, source_text, label, lang}`, 289 supported / 86 hallucination, evidence always an English whole-document dump
- **Seven languages, not two** - en 276, nb 54, fr 14, sv 12, it 8, es 6, pt 5; the prior framing assumed Norwegian-vs-English
- **Two distinct gaps** - English (74%) claims have their support present (token recall 0.892 supported vs 0.689 hallucination, separable) but the score is swamped by the mega-evidence; non-English recall genuinely collapses (nb 0.24, es 0.13)
- **Noisy label** - the `lang` field disagrees with re-detected language on 65 of 375 records (Swedish-tagged rows are English)

## Executive summary

A frozen translator plus best-chunk recall solves the cross-lingual gap; a depth-2 tree over {recall, NLI, anchors} is the best model - all without training on the gold (metric: macro-F1, imbalance-robust).

- **Best model** - depth-2 gradient-boosted tree, fit under leave-one-language-out: macro-F1 0.775 (5-seed mean ±0.013), hallucination-F1 0.66, accuracy 0.861
- **Simple baseline** - argos-translate + best-chunk recall (`recall_split`): macro-F1 0.755, accuracy 0.817; the transparent fallback
- **MT is the dominant lever** - per-language LOLO accuracy nb 0.40 → 0.93, fr 0.50 → 0.81, it 0.88 → 1.00; lexical-only ceiling ~0.67 balanced
- **Imbalance matters** - 289/86, so accuracy misleads: majority predictor reads 0.771 accuracy but macro-F1 0.435 with hallucination-F1 0.000
- **Refuted** - linear interactions, claim decomposition, cross-corpus transfer (all overfit or mis-weight)
- **Residual** - Spanish/Portuguese abstractive tail stays hard (n=5-6, noisy)

## Methodology

Rival deterministic signals, each one scalar per record, combined by transparent no-fit rules and scored out-of-fold.

- **Recall signals** - asymmetric, claim-anchored, best-chunk IDF recall under three token representations: words, character 3-5 grams (cognate-robust), phonetic consonant skeleton
- **Cross-lingual bridges** - anchor recall + anchor mismatch (language-invariant numbers/IDs), curated lexicon canonicalisation, cognate/orthographic fuzzy
- **Creative signals** - locale-aware number containment (decimal-comma), multilingual negation-flip contradiction, meta-claim inversion (absence claim grounded when evidence truly lacks the thing)
- **MT bridge** - optional frozen argos-translate, non-English claim → English before recall
- **Metric** - accuracy headline, balanced accuracy guard (mean per-class recall) since 289/86 makes "always grounded" score 0.771
- **Anti-overfit rule** - no learner fit to the 375; thresholds from fixed priors, a 50/50 dev→test split, or leave-one-language-out (tune on six languages, score the seventh out-of-fold)

## Setup

Pure reuse of production code plus three experiment-only dependencies; one fixed chunk operating point.

- **Reused** - `grounding.py` token recall + chunking, `chunking.py recursive_chunk`, `entity_check.py` number/entity extraction and mismatch
- **Dependencies** - `langdetect` (language re-derivation), `argos-translate` (frozen MT, one-time ~5s/language CPU download)
- **Operating point** - recursive chunking, 300-char chunks, 0.1 overlap, validated by a threshold-free AUC/Cohen's d separation sweep
- **Commands** - `--profile`, `--baselines`, `--sweep <signal>`, `--tournament [--mt]`, `--ablation [--mt]`, `--write`
- **Output discipline** - aggregate counts only, no client text, RESULTS.md committable

## Execution

The tournament runs every combiner under leave-one-language-out and a 50/50 split, lexical-only and with MT, plus an ablation ladder.

- **Lexical-only** - tops at ~0.67 LOLO balanced; English handled, non-English not rescued
- **With MT** - `recall_only` reaches 0.777 LOLO balanced, 0.755 test balanced; hallucination recall 0.53 → 0.87
- **Ablation under MT** - recall_only 0.777, +contradiction -0.061, +bridge/meta -0.081: every added layer hurts
- **Cost** - featurise 375 records in 44s, ~118 ms/claim including translation of the 99 non-English claims (translated once)

## Follow-up experiments

Same gold and protocol, MT on unless noted; these probe the accuracy stretch and robustness.

- **Chunk sweep** - word-recall separation AUC runs 0.500 (whole-doc, the failure floor) to 0.728 (char/150/0.10); the 300/recursive point is 0.724, so chunking matters and the operating point is near-optimal
- **English two-threshold** - separate native-English vs translated recall bars reach 0.845 LOLO / 0.817 test accuracy, the best of the field; trades hallucination recall (0.50) for supported recall (0.95)
- **Fixed-prior** - recall at a fixed τ=0.40 with zero tuning scores 0.776 balanced, matching the held-out-tuned result - the threshold is not delicately fit
- **Abstain band** - a three-way verdict with a fixed 0.30-0.55 band covers 68% of records at 0.838 balanced on the covered set
- **lingua-py** - cuts the noisy-language disagreement 65 → 44 and lifts recall accuracy 0.725 → 0.781; over-splits Norwegian and misfires on a few short claims
- **NLI residual** - multilingual entailment (parameter-free) catches 99% of hallucinations alone; the recall-OR-NLI ensemble reaches macro-F1 0.737 / balanced 0.808 with the best hallucination-F1 0.64, rescuing the tail (es 0.33 → 0.50, pt 0.60 → 0.80, no 0.82 → 0.95)
- **OPUS-MT engine** - opus-mt-mul-en scores macro-F1 0.734 TEST vs argos 0.755 and is ~9x slower (1037 vs 118 ms/claim); argos per-language models win, hypothesis refuted

## Metric note

The classes are imbalanced (289 supported / 86 hallucination), so the primary metric is macro-F1, not accuracy. The majority-always-grounded predictor scores 0.771 accuracy but macro-F1 0.435 with hallucination-F1 0.000 - it never catches a fabrication, which accuracy hides. Best macro-F1 is recall_split at 0.755 TEST; full F1 scoreboard in `BENCHMARK.md`.

## What we tried

Every signal, combiner, and variant run, with its verdict.

- **Recall representations** - word IDF best-chunk recall (kept, the protagonist); char 3-5 gram (dropped, high hallucination floor); phonetic skeleton (dropped, collision-prone)
- **Cross-lingual bridges** - anchor recall + mismatch (dropped under MT); curated lexicon canonicalisation (not built, MT made it moot); cognate/orthographic fuzzy (dropped)
- **Creative signals** - locale number containment (folded into anchors); negation-flip contradiction (dropped, over-fires); meta-claim inversion (dropped, hurt)
- **MT bridge** - argos-translate per-language models (kept, the lever); OPUS opus-mt-mul-en (rejected, worse and ~9x slower)
- **NLI** - mDeBERTa multilingual entailment (kept for hallucination detection in the ensemble)
- **Combiners** - recall_only (winner), recall_split (best accuracy + macro-F1), recall_contra / tree / global / weighted (all lost), recall-OR-NLI (best hallucination-F1)
- **Chunking** - swept size × overlap × strategy; 300-char recursive near-optimal, whole-doc is the floor
- **Language ID** - langdetect (default), lingua-py (small gain, over-splits Norwegian)
- **Splits** - stratified 50/50, leave-one-language-out (headline), fixed-prior (zero tuning)
- **Metric** - accuracy → macro-F1 once the 289/86 imbalance was accounted for

## Lessons learned

What the experiment taught beyond the numbers, including its own limitations.

- **MT is the dominant lever** - cross-lingual grounding here is translate-then-recall; per-language MT models beat one multilingual model on quality and speed
- **Imbalance hides failure** - 0.771 accuracy looked fine while macro-F1 was 0.435 and hallucination-F1 0.000; choose the imbalance-robust metric before drawing conclusions
- **Interactions help, but only as shallow trees** - a depth-2 gradient-boosted tree over {recall, NLI, anchors}, fit under LOLO, beats the simple model on all three metrics (macro-F1 0.775 vs 0.755, hal-F1 0.66 vs 0.64, accuracy 0.861 vs 0.817); *linear* interaction terms overfit (0.691) and *deep* trees overfit harder (in-fold 0.996, LOLO 0.733)
- **The win is nonlinear** - the `r1 × nli_contra` linear product is useless (the "right-topic-wrong-fact" cell is n=10, not enriched), but axis-aligned *tree* interactions over recall × NLI carve the boundary the hyperplane cannot; the lesson is the model class, not the absence of structure
- **Capacity ceiling is the governing law** - the scissors plot is exact: in-fold macro-F1 rises monotonically to 0.996 (memorisation) while LOLO peaks at depth-2; the 86 negatives (LOLO removes a language each fold) fund precisely a depth-2 tree and nothing larger
- **Language as a learned feature was refuted** - the `is_en × recall` *linear* interaction overfits out-of-fold; the GBT instead learns the language-conditional behaviour implicitly via recall × NLI splits
- **Claims extraction was built and refuted** - clauses, not sentences, are the unit (claims are 1.19 sentences but 136/375 carry a connective); clause-split + aggregation over-flags paraphrased supported clauses (sup-F1 0.90 → 0.86) with no hal-F1 gain
- **Cross-corpus transfer fails on domain mismatch** - weights learned on VitaminC ground on NLI-contradiction and ignore recall; DeLaval needs the opposite, so transfer collapses (macro-F1 0.594)
- **Anti-overfit is not no-modeling** - the rule bans fitting the test data, not modeling interactions; modeling them honestly under LOLO is exactly how the depth-2 GBT win was found

## Model class: GBT vs linear vs Bayesian calibration

The deciding factor is the model class, not the fitting method - the project's Bayesian calibrator is a linear hyperplane and shares the linear ceiling. All three fit {recall, NLI-entail, NLI-contra} under leave-one-language-out.

- **Linear logistic** (sklearn) - macro-F1 0.728; adding linear interaction terms makes it *worse* (0.691), the cross terms overfit the 86 negatives
- **Bayesian calibration** (production `fit_calibrator`, bambi/PyMC logistic) - macro-F1 0.733, hal-F1 0.63; the priors add regularisation and calibrated uncertainty, lifting it a hair over the bare logistic, but it is the **same hyperplane** and cannot carve the recall × NLI interaction
- **Depth-2 GBT** - macro-F1 0.775, hal-F1 0.66; axis-aligned tree splits represent "high recall AND high entailment" jointly - the boundary a hyperplane cannot
- **Takeaway** - the ~0.04 macro-F1 headroom is in the model class (shallow nonlinear), not in better-fitting a linear one; the Bayesian calibrator's value is calibrated uncertainty, not accuracy. Deeper trees overfit (capacity ceiling), so depth-2 is the operating point

## Conclusions

Deterministically this is a translation problem, then a recall-scoring problem, and a depth-2 nonlinear model squeezes the last gain the data can fund.

- **Translate-then-recall is the foundation** - a frozen translator plus best-chunk IDF recall is cheap (CPU-only, no training) and reaches macro-F1 0.755 / accuracy 0.817 on its own
- **A depth-2 GBT is the best model** - over {recall, NLI, anchors}, fit under LOLO, it reaches macro-F1 0.775 / hal-F1 0.66 / accuracy 0.861, beating the simple rule on all three; the gain is shallow tree interactions, not a richer lexical stack
- **The lexical bridges do not help** - lexicon, cognate, anchor, contradiction and meta layers are neutral-to-harmful once MT is present; decomposition and cross-corpus transfer were built and refuted
- **The ceiling is data, not model** - the 86 hallucinations fund exactly a depth-2 tree; deeper or linear models overfit (the capacity scissors). Beating ~0.78 needs more labelled data
- **Hard residual** - Spanish/Portuguese anchor-less prose stays the weak spot; n=5-6 makes those cells noisy
- **Reframes the client finding** - lexical did not fail at grounding generally, only at cross-lingual confirmation; the cheap fix is translation, then a small learned model

## Next steps

A depth-2 GBT is the best model; decomposition and transfer were refuted (see BENCHMARK.md rounds 2-4 and the capacity plot).

- **Promotion** - two ship options: `recall_split` (transparent rule, macro-F1 0.755) or the **depth-2 GBT over {recall, NLI, anchors} fit under LOLO** (macro-F1 0.775, hal-F1 0.66, accuracy 0.861) when a learned model is acceptable; propose either in the production grounder via a separate reviewed change
- **More labelled data** - the depth-2 ceiling is set by 86 hallucinations; a larger balanced multilingual gold (especially es/pt beyond n=5-6) is the prerequisite for funding any deeper model
- **Engineering** - faster per-language MT engine if throughput matters; lingua-py for language ID
- **Refuted, do not revisit without more data** - linear feature interactions, claim decomposition, cross-corpus calibrator transfer
- **Done so far** - chunk sweep, lingua-py, English two-threshold, fixed-prior, abstain band, NLI residual, OPUS-MT engine; metric moved to macro-F1 (see BENCHMARK.md)
