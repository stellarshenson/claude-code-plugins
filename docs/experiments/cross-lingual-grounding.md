# Deterministic cross-lingual grounding on the DeLaval gold

Experiment on the `experiment/grounding` branch testing whether a non-LLM grounder can raise grounding accuracy on a real cross-lingual dataset without training any model on it. Artefacts: `experiments/grounding/{harness.py, HYPOTHESIS.md, RESEARCH.md, RESULTS.md}`; the labelled gold and transcripts stay in a git-ignored stash.

## Situational overview

The lexical grounder confirmed only ~12% of supported claims on a 375-record client gold; re-profiling overturned the team's "semantic is required" conclusion.

- **Dataset** - 375 verified records `{claim, source_text, label, lang}`, 289 supported / 86 hallucination, evidence always an English whole-document dump
- **Seven languages, not two** - en 276, nb 54, fr 14, sv 12, it 8, es 6, pt 5; the prior framing assumed Norwegian-vs-English
- **Two distinct gaps** - English (74%) claims have their support present (token recall 0.892 supported vs 0.689 hallucination, separable) but the score is swamped by the mega-evidence; non-English recall genuinely collapses (nb 0.24, es 0.13)
- **Noisy label** - the `lang` field disagrees with re-detected language on 65 of 375 records (Swedish-tagged rows are English)

## Executive summary

A frozen offline translator plus best-chunk IDF recall clears the target with no model trained on the data.

- **Headline** - argos-translate + best-chunk recall reaches leave-one-language-out balanced accuracy 0.777, held-out test 0.791 accuracy / 0.755 balanced
- **Target met** - balanced-accuracy guard was ≥0.75; majority-class floor is 0.771 accuracy / 0.500 balanced
- **MT is the lever** - per-language LOLO: nb 0.40 → 0.93, fr 0.50 → 0.81, it 0.88 → 1.00
- **Accuracy path** - a separate recall bar for native-English vs translated claims reaches 0.845 LOLO / 0.817 test accuracy, near the 0.85 stretch
- **Lexical-only ceiling** - ~0.67 balanced without translation
- **Residual** - Spanish/Portuguese abstractive tail stays hard (es 0.33 on n=6)

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
- **Simplicity won by constraint, not by nature** - forbidding any learned weighting left only hand-set weights and per-fold thresholds, which lost to the single best signal; this is a deliberately weak model, not proof that one signal suffices
- **Linear boundaries only** - the calibrator and every combiner are interaction-free; a logistic hyperplane cannot represent "trust bm25 when same-language, trust NLI when cross-lingual"; no nonlinear manifold was ever learned
- **Language was a router, not a feature** - detected language only hard-switched thresholds; as a feature with interaction terms it could contextually down-weight signals, which was never tested
- **Claims extraction untested** - claims average 2.35 sentences and were grounded whole; atomic splitting + aggregation was never built, so a multi-fact claim with one fabricated fact still scores as mostly grounded
- **Anti-overfit is not no-modeling** - the rule bans fitting the test data, not modeling feature interactions; conflating the two is what produced the weak model
- **Tiny negative class** - 86 hallucinations total, es/pt at n=5-6; any high-capacity learner will overfit, so leave-one-language-out plus low capacity is mandatory

## Conclusions

Deterministically this is a translation problem followed by a recall-scoring problem, not one the lexical bridges solve.

- **Translate-then-recall wins** - a frozen translator plus best-chunk IDF recall is cheap (CPU-only, no training) and clears the balanced-accuracy bar
- **Simplest signal wins** - once MT closes the language gap, the lexicon, cognate, anchor, contradiction and meta layers are neutral-to-harmful (char-ngram floor admits hallucinations, contradiction gate over-fires)
- **Accuracy gap** - 0.791 sits below the 0.85 stretch, held back by the English slice and the small abstractive tail
- **Hard residual** - Spanish/Portuguese anchor-less prose may still need a semantic layer; n=5-6 makes those cells noisy
- **Reframes the client finding** - lexical did not fail at grounding generally, only at cross-lingual confirmation; the cheap fix is translation, not a richer lexical stack

## Next steps

The open levers all target the weak-model and untested-extraction gaps above.

- **Learned interaction model under LOLO** - fit a shallow gradient-boosted tree or interaction-logistic over all signals + language + cross terms, trained on six languages and scored on the seventh; the direct test of whether feature interactions beat the 1-D recall floor without fitting the test data
- **Language as a feature** - add `is_en` / `cross_lingual` plus interaction terms (`is_en × bm25`, `cross_lingual × nli_entail`) so the model down-weights signals contextually instead of hard routing
- **Atomic claims extraction** - split multi-fact claims, ground each sub-claim, aggregate (all-supported → grounded, any-contradicted → contradicted), re-run the tournament
- **Larger gold** - es/pt at n=5-6 are too small to trust interaction terms; re-test on a bigger multilingual sample first
- **Promotion** - if a learned, LOLO-validated balance holds, propose translate-then-recall + NLI in the production grounder via a separate reviewed change
- **Done so far** - chunk sweep, lingua-py, English two-threshold, fixed-prior, abstain band, NLI residual, OPUS-MT engine; metric moved to macro-F1 (see BENCHMARK.md)
