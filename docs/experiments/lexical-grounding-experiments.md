# Deterministic cross-lingual grounding on the private RAG gold

Experiment on the `experiment/grounding` branch: build a non-LLM grounder that classifies each claim as supported or hallucination on a real cross-lingual dataset, without training any model on the test fold. The current best is a **lexical-only logistic** (translate the claim, then word recall) - no semantic model. This document is the canonical writeup (hypotheses, setup, results, conclusions for every round). Supporting artefacts: `experiments/grounding/{harness.py, lab.py, round9.py, synth_mt.py, RESEARCH.md, RESULTS.md, BENCHMARK.md}`; the labelled gold and transcripts stay in a git-ignored stash.

## Situational overview

The lexical grounder confirmed only ~12% of supported claims on the client gold; re-profiling overturned the team's "semantic is required" conclusion - and the final model needs no semantic layer at all.

- **Dataset (live)** - 2752 verified records `{claim, source_text, label, lang, user_id, trace_id}` (parquet, dual-judge verified from 639 production conversations), **1966 supported / 786 hallucination (29%)**, evidence always an English-dominant document dump. The gold grew 375 → 856 → 1260 → 2631 → 2752 mid-experiment; several conclusions changed with it (the depth-2 GBT that won on 375 overfits on the larger sets)
- **Cohort caveat (evaluated pooled)** - the 29% hallucination rate is `~10% organic + a QA/test cohort's adversarial sessions`: two test accounts hold 1118 records / 623 of the 786 hallucinations (79%) at a 56% rate, vs 10% for the 1634 organic records. We evaluate on the pooled set (comparable to prior runs); a `user_id` split is available but not used. 95% of hallucinations are English; 28% assert a specific number/spec
- **Ten+ languages** - English dominant (~77%), then fr (10%) / no / es / nl / pt / it / sv / de (det-lang adds af/ca noise on short claims)
- **75 independent contexts** - 75 distinct `source_text` blobs at 2752 (was ~22 at 1260); claims sharing a source are correlated, so leave-one-source-out is the trustworthy split and is now far stronger
- **Two gaps** - English claims have their support present but the score is swamped by the mega-evidence; non-English recall collapses unless the claim is translated or a same-language chunk exists

## Executive summary

A purely lexical model (translate the claim, then lexical recall) is the best, beating every model that used the NLI semantic layer.

**Research at a glance** - the full hypothesis sweep across two corpora, with datasets and outcomes (detail in the sections below and `BENCHMARK.md`):

| Experiment / hypothesis | Dataset | Key result | Conclusion |
|---|---|---|---|
| MT bridge (argos) + best-chunk recall | private RAG gold 375→1260 | non-EN LOLO nb 0.40→0.93, fr 0.50→0.81, it 0.88→1.00 | **Kept** - translation is the cross-lingual lever |
| Chunk size / overlap sweep | private RAG | class-separation AUC 0.50 whole-doc → 0.728 char/150 | recursive 300-char / 0.1 operating point |
| Per-chunk language routing (`same_lang`) | private RAG 1260 | +0.002 LOSO over always-translate | efficiency lever, not accuracy |
| NLI semantic layer / recall-OR-NLI ensemble | private RAG 375 | macro-F1 0.737, hal-F1 0.64, rescues es/pt tail | **Dropped** - lexical features supersede it |
| Cross-corpus calibrator transfer (fit on VitaminC) | VitaminC → private RAG | macro-F1 0.594; coefs `nli_c −3.03, r1 0.0` | **Refuted** - signal weighting is domain-specific |
| Claim decomposition (clause / sentence split) | private RAG 856 / 1260 | hurts at 856, SaT split helps at 1260 (hal-F1 0.61→0.71) | size-dependent; regex split refuted, SaT kept |
| Model class: logistic vs depth-2 GBT vs Bayesian | private RAG 375 / 856 / 1260 | GBT 0.775 at 375; linear wins at 1260 (GBT 0.74→0.54) | **Linear ships** - GBT overfits as data grows |
| Claim-intrinsic `specificity` (mechanism-general) | private RAG 1260 | LOSO 0.837 → 0.845, narrows LOLO↔LOSO gap | **Ships** - strongest generalisation feature |
| Verbatim `quote_flag` (≥40-char span) | private RAG 1260 | 98.2% supported precision on the 109 it fires for | **Ships** - precision-1 supported confirm |
| Background-rarity gap (`wordfreq`) | private RAG 1260 | redundant with recall on multi-sentence sources | null then - revived in R5 (regime-specific) |
| SaT vs regex claim segmentation (LLM-as-judge) | private RAG 1260 | SaT wins macro-F1 + LLM-judge 15 / 1 | **SaT preferred** |
| Cross-corpus probe: run grounder on VitaminC | VitaminC dev 1200 | macro-F1 collapses to 0.586 (~coin-flip) vs 0.837 on private RAG | NFL boundary - contrastive negatives need a contradiction signal |
| R1 contradiction: value-conflict, direction-flip, interaction, polarity | private RAG + VitaminC joint | VitaminC 0.532 → 0.673, private RAG holds 0.841 | value-conflict + direction **ship**; interaction, polarity **refuted** |
| R2 contradiction: minimal-substitution, numeric-comparison, WordNet antonym | private RAG + VitaminC joint | VitaminC 0.555 → 0.661, private RAG 0.832 → 0.825; triage 90% prec | **WordNet ships** (replaces curated list); subst + numeric **null** |
| R3 contradiction: relation/role reversal, scoped negation, quantifier mismatch | VitaminC probe | absent at usable density (shared-entities 5%, negation 0%, quantifier 4%) | **all null** - pure-lexical contradiction signal is saturated |
| R4 normalisation: Snowball-stemmed recall | private RAG 2752 + VitaminC joint | +0.002 both corpora (within noise), +~35 ms/claim latency | **rejected** - char n-grams already capture morphology; not worth the recall pass |
| R5 short-source: length-robust recall + distinctive-content + truncation augmentation | private RAG 2752 + VitaminC + short-source aug | probe 10/12 → 11/12; private RAG 0.825 → 0.817, VitaminC 0.661 → 0.691 | **ships** - background-IDF recall floor + `unmatched_rarity` + regime augmentation, all learned |
| R8 multilingual claim extraction + gold v2 rebuild | private RAG 639 answers / gold v2 5,912 | anglocentric verb-gate rejects en 9% vs nb 50% / it 86%; unbiased gold exposes non-EN TNR 0.000 | extraction fix **kept**; A2 atomic / H-B alignment / H-C negation **killed** at gates |
| R9 cross-lingual blind spot: language-conditional threshold | gold v2 non-EN 139 neg | shipped manifold caught 0/139 non-EN hallucinations; `threshold_non_en 0.70` → TNR 0.748, English byte-identical | **Ships** - operating point, not signal |
| R10 synthetic non-EN negatives by `claude -p` translation | gold v2 + 1,053 synthetic | single global threshold reaches real non-EN TNR 0.683, LOLO 0.60-0.79 | **Validated offline** - weights learn the boundary; ship gated on EN guard |
| R11 synthetic data doubling + de back-translation | gold v2 + 2,119 synthetic | TNR 0.683 → 0.712 (+0.029, diminishing); de bridge installed, null on metric (no de in eval) | scales but bends - next gain is source diversity, not volume |
| R12 ship the durable fix: single global cut | gold v2 + 2,119 synthetic | global 0.50: gold_en F1 0.803→0.810, non-EN TNR 0.78, VitaminC/articles hold, English e2e green | **Ships** - synthetic-retrained weights retire `threshold_non_en` |

![Progressive gains across hypothesis rounds - VitaminC climbs 0.53 to 0.69 as deterministic contradiction features are added while private RAG holds ~0.85, then round 3 plateaus at lexical saturation](images/progressive-gains.svg)

- **Best model** - lexical-only logistic over translate-then-recall features + claim-intrinsic `specificity` + the contradiction layer: **macro-F1 0.827 (leave-one-source-out, the trustworthy split) / 0.769 (leave-one-language-out), hallucination-F1 0.76** on the live 2752 gold, no semantic model (was 0.845 / 0.793 on 1260; absolutes shift slightly on the larger, more language-diverse pooled set)
- **Beats NLI** - the NLI-including model and the lexical `recall_split` rule both score below it; dropping NLI gained accuracy, simplicity, and speed
- **The lever is MT + recall (+ specificity), not the language routing** - translate-then-recall alone scores 0.835 LOSO; the per-chunk `same_lang` flag + dual recall add only ~+0.002; a plain logistic wins, gradient-boosted trees overfit the language-held-out folds
- **Precision-1 confirm** - `quote_flag` (a ≥40-char verbatim span in the evidence) flags supported at 98.2% precision on the 109 claims it fires for
- **Replicated across data growth** - leave-one-source-out held 0.829 (856) → 0.837 (1260) → 0.845 with `specificity` → 0.827 on the live 2752 (with 75 source contexts, up from ~22); stability across five data sizes is the best evidence the result is real, not a snapshot artefact
- **Metric** - macro-F1 (imbalance-robust); the majority predictor reads ~0.71 accuracy but macro-F1 ~0.41 with hallucination-F1 0.000
- **Residual** - hallucination detection is data-bound on the smallest language tails (da/pt at n=8-10)
- **Contradiction layer holds a second corpus** - a deterministic value-conflict feature + WordNet antonym-flip lifts the lexical-blind VitaminC contrastive set (joint macro-F1 0.555 → 0.661) while private RAG holds (0.832 → 0.825), plus a `semantic_candidate` triage flag (26% of VitaminC at 90% REFUTES precision); the hold-vs-collapse pattern replicated as the gold grew 1260 → 2631 → 2752; the full final design is in `lexical-grounding-sota.md`
- **Lexical lever is exhausted** - round 3 probed three parser-free structural mechanisms (role reversal, scoped negation, quantifier mismatch) - all absent at usable density in VitaminC (a clean triple null); round 4 added Snowball-stemmed recall - +0.002 within noise (char n-grams already capture morphology) and rejected for latency. Value-conflict + WordNet antonym + the recall/specificity backbone is the reachable pure-lexical ceiling; the residual is irreducibly semantic and needs the latency-deferred component (counter-fitted vectors / NLI), routed by the triage flag

**Performance results** - average per-claim end-to-end breakdown (lexical + MT, no semantic; live 2752 gold, CPU single-thread, torch-free). MT fires only on heterogeneous claims (non-English claim vs English source), so its per-claim cost is amortised across all 2752.

| Stage | Total | Avg / claim | Notes |
|---|---|---|---|
| MT (argos) | 237.3s | 86.22 ms | 369.6 ms per translated claim, fires on 642/2752 = 23% |
| Recall (BM25 ×2) | 189.7s | 68.92 ms | BM25 rebuilt per claim, direct + MT pass |
| Claim-intrinsic (lingua + specificity + WordNet) | 20.5s | 7.44 ms | language ID + anchor density + antonym lookup |
| Anchor (numbers/IDs) | 3.1s | 1.14 ms | language-invariant |
| **Feature build (total)** | **455.0s** | **165.3 ms** | sum of the above per claim |
| Classifier fit + score | 8.1s | negligible | logistic, amortised at inference |
| Cold start (load SaT + 1 MT model) | 5.4s | one-time | not per-claim |

- **Throughput** - ~165 ms/claim end to end (≈6 claims/s single-thread); MT now leads at 86 ms (the heterogeneous tail is 23% of claims, ~370 ms each), recall 69 ms
- **Quality at this operating point** - LOSO macro-F1 0.827 / hal-F1 0.76 / sup-F1 0.89 / acc 0.854; LOLO macro-F1 0.769 / hal-F1 0.65 / sup-F1 0.88 / acc 0.826
- **MT cost rose with the data** - 77% of claims are English and skip translation; the 23% heterogeneous tail carries a ~370 ms cost and now dominates latency
- **Footprint** - CPU-only, no torch, no GPU, no semantic; argos MT models ~80-100MB each loaded on demand, SaT-3l small, nltk/WordNet ~10MB, logistic in KB
- **Headroom** - recall rebuilds BM25 per claim across 75 distinct sources; caching BM25 per source is a recall speedup left on the table

## Methodology

Per-claim lexical signals (word recall with and without translation, anchors, claim-intrinsic shape), then a learned verdict head; no semantic scorer.

- **Language detection** - per claim and per source chunk (lingua-py on short text; langdetect fallback); a `same_lang` flag marks whether the best chunk is in the claim's language
- **Dual lexical recall** - `r1_direct` (claim vs chunks as-is - the same-language path) and `r1_mt` (translate claim → English via argos, then recall - the cross-language path); the model learns which to trust
- **Supporting lexical features** - char-ngram recall, rapidfuzz partial-ratio, anchor recall + anchor mismatch (numbers/IDs, language-invariant), oracle-chunk and top-k consensus recall
- **Mechanism-general features** - `specificity` (anchor density from the claim alone, evidence-independent → cannot memorise the documents) and `quote_flag` (≥40-char verbatim span = near-deterministic support); only aggregate / normalised / claim-intrinsic features, never raw tokens or document identity
- **Verdict head** - a logistic over the lexical feature set; LightGBM was raced against it (`class_weight='balanced'`) but lost under leave-one-language-out
- **Metric** - macro-F1 headline, hallucination-F1 watched separately
- **Two cross-validation splits** - no learner touches the fold it scores
- **LOLO (leave-one-language-out)** - hold out a language, train on the other six, score it; tests generalisation to an unseen language
- **LOSO (leave-one-source-out)** - hold out all claims from one of the 75 source documents, train on the rest, score it; tests generalisation to unseen evidence and blocks memorising the correlated contexts
- **LOSO is the headline split** - English is ~77% of the data, so the LOLO English-out fold trains on a small non-English slice and is artificially harsh

## Setup

- **Data** - live 2752-record gold (parquet), git-ignored stash; features cached (git-ignored)
- **Dependencies (experiment-only)** - `lingua-language-detector`, `argos-translate` (frozen MT bridge), `rapidfuzz`, `scikit-learn`, `lightgbm`, `wordfreq`
- **MT quality** - argos is good enough: technical anchors (numbers, IDs, product names, UI strings) survive translation intact, errors are word-level (dropped/confused nouns) and cosmetic, and many "non-English" claims are langdetect misfires (near-passthrough); the routing ablation confirms MT is not the bottleneck
- **Operating point** - recursive chunking, 300-char chunks, 0.1 overlap (validated by a threshold-free AUC/Cohen's d separation sweep: whole-doc is the 0.50 floor, ~150-300 chars near-optimal)
- **Commands** - `python lab.py lexgbm` (the current model), `harness.py --tournament --mt` (the rule baseline), `lab.py final` (capacity ladder)

## How we got here

The result arrived in stages, several of which reversed earlier conclusions.

- **MT is the cross-lingual lever** - a frozen translator lifts every non-English language (per-language LOLO accuracy nb 0.40 → 0.93, fr 0.50 → 0.81, it 0.88 → 1.00); without it the non-English claims do not ground
- **Metric switch** - the 1858/773 imbalance makes accuracy misleading; macro-F1 became primary (majority predictor: ~0.71 accuracy but macro-F1 ~0.41, hallucination-F1 0.000)
- **Per-chunk language routing is ~free on accuracy** - the source carries claim-language chunks for a subpopulation (French claims match a French chunk 46%, sv 50%), but an ablation showed `same_lang` + dual recall add only ~+0.002 LOSO over "always translate then recall" (0.835 → 0.837); MT is good enough that routing buys efficiency (skip translation for same-language claims), not accuracy
- **Lexical-only beats NLI** - giving the model recall + anchors + claim-intrinsic specificity replaces what NLI was providing; the semantic layer became unnecessary

## Model class: lexical-LR vs GBT vs Bayesian calibration

The decisive factors are the features and the dataset size, not the fitting method.

- **Lexical-only logistic** (live 1260) - macro-F1 0.845 source-out / 0.793 language-out, the best; the lexical recall features carry the signal
- **Gradient-boosted trees** - on the old 375 snapshot (86 negatives) a depth-2 GBT won (0.775); on the live 856+ (307+ negatives) trees **overfit** the language-held-out folds and lose (LGBM 0.74 → 0.54 as depth rises), while the linear model wins - the conclusion flipped with more data (the capacity-ceiling scissors, `plots/05_capacity_ceiling.png`)
- **Bayesian calibration** (production `fit_calibrator`, bambi/PyMC logistic) - a Bayesian logistic is a hyperplane, so it lands at the linear level (0.733 on the 375 snapshot) and adds calibrated uncertainty, not capacity
- **Leave-one-source-out ≥ leave-one-language-out** (0.845 vs 0.793) - context leakage is not inflating results; the harder generalisation is to an unseen language

The capacity-ceiling scissors (375 snapshot, in-fold = resubstitution, the overfit gap is the tell):

| model | LOLO macro-F1 | hal-F1 | in-fold | overfit gap |
|---|---|---|---|---|
| LR[r1] | 0.731 | 0.57 | 0.753 | +0.02 |
| LR[r1,nli] | 0.728 | 0.63 | 0.750 | +0.02 |
| Bayesian calibrator (bambi/PyMC) | 0.733 | 0.63 | - | - |
| LR + linear interactions | 0.691 | 0.49 | 0.761 | +0.07 |
| **GBT depth-2** | **0.785** | 0.66 | 0.909 | +0.12 |
| GBT depth-4 | 0.733 | 0.56 | 0.996 | +0.26 |

In-fold rises monotonically to 0.996 (memorisation) while LOLO peaks at depth-2 then falls - the model class is the lever, not the fitting method, and on the larger live gold even depth-2 overfits and the linear model wins outright.

## What we tried

- **Kept** - the MT bridge (argos per-language), word recall, anchors, char-ngram, fuzzy, claim-intrinsic specificity, the aligned value-conflict feature, the WordNet antonym-flip, a logistic head; the per-chunk routing / dual recall is kept for efficiency, not accuracy
- **Dropped / refuted** - NLI entailment (superseded by lexical recall + specificity), claim decomposition (over-flags supported clauses), cross-corpus calibrator transfer (VitaminC mis-weights), oracle-chunk (retrieval is not the bottleneck), linear interaction terms and deep trees (overfit), OPUS-MT engine (worse and ~9x slower than argos), polarity/negation-XOR (wrong-signed on private RAG - fires on 9% of supported), curated antonym lexicon (superseded by WordNet), general minimal-substitution and numeric-comparison (null - can't separate synonym restatement from fact-edit deterministically), batch-adaptive thresholds (max-gap / Jenks, round 7 - no gap structure at corpus scale, unguarded cuts destroy two corpora 0.829→0.419, a gap floor just reduces to the fixed threshold), atomic-fact scoring and alignment-profile pooling (round 8 - killed at the multi-sentence error-concentration gate, ratio 0.93 < 1.5)

## Contradiction features: joint hold-vs-collapse

Hypothesis arc testing whether deterministic features can lift the contrastive corpus (VitaminC, where the lexical grounder collapses to 0.586) without degrading private RAG. Protocol: one logistic trained on the joint private RAG (1260) + VitaminC (800, SUPPORTS vs REFUTES) table, grouped CV, scored per corpus; acceptance is two-sided (VitaminC up AND private RAG holds). Mechanism not data - every contradiction feature is overlap-gated so it stays inert on absent-content negatives.

- **H1 aligned value-conflict** - claim anchors that align with the chunk but disagree in value (`find_mismatches`, graded); shipped - free on private RAG (0.3% fire), +0.032 VitaminC
- **H2 antonym/direction-flip** - curated opposite-direction lexicon; fires on 62% of VitaminC REFUTES vs 6% SUPPORTS and 0.4% of private RAG - the lever (+0.14 VitaminC), at a ~0.01 private RAG false-fire cost as a hard feature
- **H3 conflict × overlap interaction** - inert; the IDF recall it multiplies is degenerate (~0) on VitaminC single-sentence evidence
- **Refuted in passing** - polarity/negation-XOR (wrong-signed on private RAG); the contradiction features were initially killed by gating on the degenerate recall - re-gated on fuzzy, which stays live on single-chunk evidence

Results (macro-F1 per corpus, per-corpus-tuned threshold - one model, domain-calibrated operating point):

| configuration | private RAG | VitaminC |
|---|---|---|
| lexical base | 0.851 | 0.532 |
| + value-conflict (H1) | 0.851 | 0.564 |
| + direction-flip (H2) | 0.840 | 0.610 |
| + all | 0.841 | 0.673 |

- **Hold, not collapse** - VitaminC 0.532 → 0.673 while private RAG 0.851 → 0.841 (−0.010, within LOSO noise)
- **Triage flag** - `semantic_candidate` (high overlap AND conflict/direction) flags 23% of VitaminC at 92% REFUTES precision, 3× error concentration, zero classifier cost - routes the irreducibly semantic residual to a future stage rather than guessing
- **Conclusion** - value-conflict ships as a feature; direction-flip is the strong VitaminC lever; round 2 (below) supersedes the curated direction list with WordNet

## Contradiction features, round 2: close the residual

Three more hypotheses (web-researched: VitaminC's contrastive negative is a single localized token edit - a number, entity, date, or antonym) targeting the residual the round-1 features miss. Same protocol and two-sided acceptance.

- **R2-H1 minimal-substitution** (general "one salient token differs in a matching context") - **null**; it fires on supported synonym restatements too (it cannot tell a synonym swap from a fact-edit - that distinction is itself semantic), so it adds zero VitaminC and, folded into the triage flag, bloated it to 85% coverage at base-rate precision
- **R2-H2 numeric comparison / date conflict** (near-value swap, year disjointness, beyond exact equality) - **null**; redundant with the round-1 exact value-conflict on this data
- **R2-H3 WordNet antonym-flip** (deterministic word-sense antonym lexicon replacing the curated list) - **ships**; broader coverage (REFUTES 32% vs SUPPORTS 3%, private RAG 0.8%) at equal precision

Results (macro-F1 per corpus, per-corpus-tuned threshold; the ablation below was run on the 1260 snapshot):

| configuration | private RAG | VitaminC |
|---|---|---|
| round-1 (curated direction) | 0.841 | 0.673 |
| wn replaces direction | 0.842 | 0.687 |
| round-1 + wn (augment) | 0.839 | 0.694 |
| + subst + num-rel (R2-H1/H2) | 0.825 | 0.663 |
| **shipped (conflict + WordNet)** | **0.842** | **0.685** |

- **WordNet ships, replacing the curated direction lexicon** - private RAG holds (0.842), VitaminC 0.673 → 0.685, one principled population resource instead of a hand list; cost is an `nltk` + WordNet dependency (~10MB, English; claims are MT'd to English)
- **The deterministic contradiction signal saturates** - value-conflict + antonym opposition is the reachable surface signal; the general single-token substitution and numeric-comparison axes add nothing, because separating a synonym restatement from a fact-edit is irreducibly semantic
- **Re-validated on the live 2752 gold** - the shipped config holds both corpora at the larger size: **private RAG 0.832 → 0.825, VitaminC 0.555 → 0.661** (base → shipped), same hold-vs-collapse pattern; triage flag steady at 26% / 90% REFUTES precision; the final design is in `lexical-grounding-sota.md`

## Contradiction features, round 3: the lexical ceiling (null)

A deep-research round (web-authorised; key papers in `experiments/grounding/references/`) testing whether the round-2 residual can be closed with **pure-lexical, parser-free** features - the bar is a lightweight lexical classifier, so embeddings, NLI, cross-encoders, and even a statistical parser are deferred for latency. Probe-first discipline: measure each candidate's firing rate on a balanced VitaminC sample before any wiring.

- **R3-H1 relation/role reversal** (parser-free entity-order swap) - **null**; only 13% of REFUTES have ≥2 entities and **5% have ≥2 shared entities**, so the role-swap mechanism is structurally absent (VitaminC edits values/words, not entity roles)
- **R3-H2 proximity-scoped negation** (locality window, fixing round-1's scope-blind XOR) - **null**; **0% of REFUTES carry a negation cue** - nothing to scope
- **R3-H3 quantifier/scope-cue mismatch** - **null**; only 4% have a quantifier and it is wrong-signed (fires more on SUPPORTS)

- **Conclusion - the pure-lexical contradiction signal is saturated** - value-conflict (numeric/entity edits, which the dataset confirms is 28% of hallucinations) + WordNet antonym opposition is the reachable ceiling. The remaining residual is the synonym-vs-fact-edit distinction, which static embeddings cannot make (antonyms and synonyms are distributionally close - Nguyen 2016) and only a counter-fitted lookup (Mrkšić 2016) or an NLI/cross-encoder could; all are deferred for latency. The `semantic_candidate` triage flag already routes that residual to a future heavy stage. Research write-ups: `references/{vitaminc_2021,counter_fitting_2016,antonym_synonym_2016}.md`

## Normalisation, round 4: stemming (near-null, rejected)

The user's idea: heavier text normalisation - stemming and spelled-out number canonicalisation - to lift the recall backbone rather than chase contradiction. A codebase map first established that the pipeline already normalises heavily (lowercase, NFKD accent-strip, punctuation, char n-grams, locale-robust numbers); the genuine gaps were stemming (none anywhere) and spelled numbers (digit-only).

- **R4-H1 Snowball-stemmed recall** (symmetric - the same analyzer stems claim AND chunks) - added `r1_stem` to the joint and re-ran on 2752: **+0.002 on both corpora (private RAG 0.825 → 0.827, VitaminC 0.661 → 0.663), within LOSO noise.** Predicted and confirmed: the char n-gram feature already matches morphological variants (`configure`/`configures`/`configuration` share `configur`), so stemming is redundant; the gain lands on the already-near-ceiling supported side, not the hard hallucination class. Rejected - it is a third BM25 recall pass (~+35 ms/claim) for no real gain, failing the latency bar
- **R4-H2 spelled-out number canonicalisation** - skipped: the bigger lever (stemming) was null, and genuine spelled-quantity coverage is low (the 2.8% / 7.9% raw counts are inflated by "one" as a pronoun), so a narrower numeric feature cannot move macro-F1
- **Conclusion - the pure-lexical lever is exhausted** - across four rounds the deterministic lexical ceiling is value-conflict + WordNet antonym + the recall/specificity backbone; normalisation adds nothing because the existing analyzers already extract the surface signal. The next real gain requires the latency-deferred semantic stage, gated by the triage flag

## Short-source regime, round 5: length-robust recall + distinctive-content (ships)

Once the grounder shipped as the default mode, a failure surfaced on very short single-source inputs (a 1-2 sentence claim vs a 1-line source): supported claims rejected (orchard present in the source but scored 0), fabrications confirmed (unrelated tiny strings). A 12-case short-source probe (measurement-only, never trains, never enters CV) made it falsifiable. The mechanism is exact: in-context BM25 IDF degenerates at N=1 chunks (`log(N−df+0.5)−log(df+0.5)` floors every token to one weight), so the manifold's dominant signal - `top3` recall at standardized coef +2.79 - collapses to 0; supporteds become unconfirmable and the verdict falls to miscalibrated weights.

- **R5-H1 length-robust recall** - soft-floor the in-context IDF with a `wordfreq` background rarity, `w(t) = max(in-context, λ·background)`, λ=0.5; it only bites when in-context has collapsed (on multi-sentence sources the distinctive token's in-context weight already dominates). Revives recall on 1-chunk sources (orchard r1 0.000 → 0.665). **Alone it regresses the probe 10/12 → 8/12** - revived recall hands partial credit to common-token overlap, so absent-content negatives become false positives
- **R5-H2 distinctive-content feature** (`unmatched_rarity`, `max_unmatched`) - background-rarity-weighted fraction of the claim's content absent from the best chunk. **Not null**, revising the round-2 finding: standardized coef −0.58 on the benchmark, separating supported 0.41 / hallucination 0.65 - but weakly learned, because the benchmark has no short-source rows where it is the deciding signal
- **R5-H3 truncation augmentation** - the load-bearing piece: short-source training rows derived by truncating each gold source to one sentence (positives keep the max-overlap evidence sentence, negatives a low-overlap one; label inherited from gold, only source length changes; tagged with their own CV group so they never leak into held-out folds). Recalibrates the manifold for the degenerate regime; the rarity coef strengthens to −0.84
- **The three together ship** - probe **10/12 → 11/12**: orchard FN fixed (recall revived), every absent-content fabrication correctly rejected. Gate A holds two-sided - private RAG 0.825 → 0.817 (−0.008, LOSO noise), **VitaminC 0.661 → 0.691** (+0.030; the blend legitimately lifts the contrastive corpus, whose single-sentence evidence is the same degenerate regime). The one remaining probe miss is a spelled-out-number value-conflict ("fifty" vs "twelve" hectares) - the orthogonal round-4 H2 gap, not the short-source issue
- **Conclusion** - the short-source regime is fixed by *learned* recalibration (background-IDF recall floor + distinctive-content feature + regime augmentation), not a hand-set threshold; real sentence-vs-document grounding is unaffected, and the same fix lifts VitaminC. It revises the round-2 "background-rarity null": the signal was null only on multi-sentence sources; in the degenerate regime it is the load-bearing discriminator

## Mechanism round, round 8: claims extraction and evidence pooling (diagnostic gates)

With the threshold levers exhausted (round 7 below, refuted), round 8 targeted the scoring *unit* with three pre-registered mechanism candidates, each guarded by a diagnostic gate measured *before* any build - a cheap way to kill a phantom target. One survived and reshaped the gold.

- **A1 multilingual claim extraction (KEPT)** - the shipped `extract_claims()` used an English-only verb gate (copula list + -s/-ed/-ing suffixes); on 639 raw answer documents it rejected 9.2% of English sentences but 50.4% of Norwegian, 85.5% of Italian, 55.1% of German - silently dropping non-English claims before they were ever judged. A language-agnostic content gate alone doubles Norwegian admissions at 1.13x inflation and 0.997 gold coverage; SaT boundaries add more (1.31x at 0.990). This front-door defect is what motivated the gold v2 rebuild
- **A2 atomic-fact scoring (KILLED at gate)** - decompose multi-sentence claims into SaT facts, score each against its own best chunk. Gate: errors must concentrate in multi-sentence claims (≥30%, error-rate ratio >1.5). Measured: share of errors in multi-sentence claims 27.0% vs 28.5% of claims, ratio 0.93 - no concentration, killed pre-build
- **H-B alignment-profile features (KILLED)** - `r1_union` / dispersion / `max_run` over the chunk set instead of best-chunk max-pooling; shared A2's error-concentration gate and died with it
- **H-C negation-scope feature (KILLED at gate)** - gate: negation-cue asymmetry in ≥25% of VitaminC errors; measured 3.7% (non-errors 1.8%) - negation is not the VitaminC failure mode, confirming round 3's 0%-negation null now on the live gold
- **Conclusion** - the diagnostic-gate discipline (measure the precondition before building) killed three of four mechanisms cheaply; the survivor, A1 multilingual extraction, exposed that the gold itself carried the extractor's survivorship bias - rebuilt as gold v2 (round 8b: re-extract every answer through the SaT + language-agnostic gate, inherit the verified label on fuzzy-matches, dual-judge the rest; 5,912 rows, new-admission extraction precision 48.8% real claims), the unbiased benchmark round 9 acts on

## Cross-lingual blind spot, round 9: the English-only hallucination detector (ships a language-conditional threshold)

The macro-F1 headline above is English-dominant and concealed a blind spot. The old gold was built *through* an anglocentric claim extractor (an English-only verb gate that dropped non-English sentences before judging), so the benchmark had almost no non-English negatives to be wrong about. Rebuilding the gold without that gate (gold v2, 5,912 rows: claims re-extracted through a SaT + language-agnostic gate, dual-judged by Haiku + Sonnet) and scoring the shipped HIGH manifold per language exposed the failure - non-English hallucination recall (TNR) 0.000 vs English 0.710, confirming 1,339 of 1,343 non-English claims and catching 0 of 139 non-English hallucinations. Balanced accuracy 0.498 (a coin flip) hid behind 0.894 "confirm-everything" accuracy on a 90%-positive slice.

- **Setup** - HIGH features cached for all gold v2 rows; per-feature AUC on the non-English slice; honest evaluation by 5-fold out-of-fold (every row gets a held-out prediction) plus leave-one-language-out; pre-registered ship bar (non-EN TNR ≥ 0.30, English balanced-acc drop ≤ 0.01, VitaminC drop ≤ 0.01)
- **R9-H1 the defect is the weights, not the features** - on the non-English slice the shipped features already rank hallucination below support (`r1_mt` AUC 0.806, `r1_best` 0.803, `unmatched_rarity` 0.802 inverted; per-language `r1_best` AUC 0.72-0.89). The English-dominant training left `r1_mt` near-zero because on English it is collinear with `r1_direct` (translation is a no-op), so the recall weight landed on `r1_direct`, which is ~0 for both non-English classes
- **R9-H2 retraining misses at a global threshold** - retraining on gold v2 restores `r1_mt` and *improves* English (TNR 0.710 → 0.850), but reaches only OOF non-English TNR 0.13 at a single global cut and LOLO collapses (fr/nb held-out 0.000). The global threshold is calibrated to the 77%-English bulk; `r1_mt` ranks non-English hallucinations below support but their absolute probabilities clear that cut
- **R9-H3 a language-conditional threshold is the operating-point fix** - keyed off the `is_en` feature already in the pipeline, a separate non-English cut converts the AUC-0.80 ranking into catches: held-out non-English TNR 0.748 at support recall 0.761, generalising per-language (LOLO es 0.74 / fr 0.64 / nb 0.65 / pt 0.60 / sv 0.93 vs 0.000 at the global cut)
- **Ships threshold-only, weights untouched** - the recalibrated weights broke two English precision e2e tests (the gold-v2-optimal English cut 0.29 over-confirms borderline fabrications vs the shipped 0.40) and were unnecessary: the *shipped* weights already separate non-English, reaching TNR 0.748 at a 0.70 non-English cut with no weight change. The ship is one config line, `threshold_non_en: 0.70` on `lexical_manifolds.high`, applied via `LexicalVerdict.threshold_for(feat)`; English is byte-identical (gold_en, VitaminC, held-out articles, all e2e tests unchanged)
- **Conclusion** - the shipped grounder was an English-only hallucination detector; the unbiased gold exposed it and a language-conditional decision threshold over the existing weights fixes it with zero English blast radius. The weight recalibration is a tradeoff (better gold-en macro-F1, worse English precision) and stays an experiment, not a ship

Results - shipped weights, non-English decision-threshold sweep on the held-out gold v2 non-English slice (the shipped weights never trained on these negatives):

| non-EN threshold | TNR (catch) | TPR (confirm) | balanced-acc |
|---|---|---|---|
| 0.40 (global, shipped) | 0.165 | 0.963 | 0.564 |
| 0.65 | 0.669 | 0.807 | 0.738 |
| **0.70 (shipped)** | **0.748** | **0.761** | **0.754** |
| 0.75 | 0.806 | 0.718 | 0.762 |

Per-language at 0.70: es 0.80 / fr 0.71 / nb 0.71 / pt 0.65 / sv 0.93 / it 0.71 / nl 1.00 TNR. The weight-recalibration alternative (rejected for ship) at vit-balanced oversampling held every corpus (gold_en +0.003, gold_non_en +0.138, vitaminc +0.003, articles +0.019 macro-F1) but lowered the English decision threshold to 0.29, over-confirming borderline fabrications and breaking two English precision e2e tests.

## Synthetic cross-lingual negatives, round 10: the weights learn the boundary (validated offline)

The round-9 ship is a threshold patch over English-trained weights - it works because the `r1_mt` ranking transfers, but the weights still see only 139 real non-English negatives across 16 languages (sv 14, nl 5, da 2). The durable fix is to give the weights a real multilingual negative population by translation, so a single global threshold works again.

- **Setup** - `synth_mt.py` (select / translate / verify / build) translates 120 English negatives (gold v2 English hallucinations) into 9 languages via `claude -p` - Haiku translates, Sonnet fidelity-verifies (same numbers / entities / polarity) - keeping the English evidence unchanged; the verify gate dropped ~7 of 1,060 drifted translations, keeping 1,053 verified synthetic negatives, each marked `origin="synthetic_mt"` with full provenance (source ids, target_lang, translator/verifier model, verified flag) and held train-only; every metric is on the real gold v2 non-English slice (`origin != synthetic_mt`)
- **Translate the claim, keep English evidence** - reproduces the production regime (non-English claim vs English tool-output) and the exact `r1_mt` round-trip the grounder runs at inference (argos back-translates the claim, recall against English evidence), so the synthetic pairs train the same feature distribution and the support/hallucination signal survives the round trip
- **R10-H1 synthetic lets a single global threshold work** - retrain + 1,053 synthetic reaches real-slice non-English TNR 0.683 at its own macro-F1 cut, vs 0.158 for the same retrain without synthetic and 0.000 shipped; the language-conditional patch is no longer required
- **R10-H2 it generalises to unseen languages** - LOLO at the global threshold, held-out language excluded from BOTH real and synthetic training: es 0.71 / fr 0.79 / pt 0.60 / nb 0.71 / sv 0.71, against 0.000 in round 9. Synthetic negatives from *other* languages teach a transferable cross-lingual boundary - not per-language memorisation
- **Cost and limits** - support recall 0.768 at the global cut (rejects 23% of supported non-English claims), comparable to the shipped patch; the gain is durability, the signal living in the weights rather than a special-cased threshold. de back-translation model absent, degrading `r1_mt` for the 117 German rows at extraction; synthetic sources are gold-domain omission negatives only (no VitaminC contrastive type yet)
- **Conclusion** - the data mechanism is validated: translated, fidelity-verified non-English negatives let the weights carry the cross-lingual signal so a single global threshold reaches TNR 0.68 and generalises across unseen languages. Shipping the synthetic-retrained weights is deferred behind the round-9 English no-regression guard (recalibration breaks English precision e2e tests)

Results - real gold v2 non-English slice, single global threshold (synthetic is train-only):

| training | global-threshold non-EN TNR | TPR | LOLO at global threshold (held-out lang) |
|---|---|---|---|
| shipped weights | 0.000 | 0.997 | fr 0.000 / nb 0.000 (round 9) |
| retrain, no synthetic | 0.158 | 0.973 | - |
| **retrain + 1,053 synthetic** | **0.683** | 0.768 | es 0.71 / fr 0.79 / pt 0.60 / nb 0.71 / sv 0.71 |

## Synthetic data scale, round 11: doubling the negatives (validated offline)

Round 10 validated the data mechanism on one batch. Round 11 tests whether more of the same translated negatives keep lifting the non-English ceiling, or whether the curve has flattened.

- **Setup** - `synth_mt.py` gained a `SYNTH_BATCH` knob: each batch selects a fresh slice of English negatives (skipping every claim used by prior batches, sids namespaced `b2s*`), namespaces its intermediates, and `build` globs all batches into the single `synthetic_mt.parquet`. Batch 2 = the next 120 gold v2 English negatives (zero overlap with batch 1, 1,811 distinct available), translated into the same 9 languages, Sonnet-verified (drop rate held: de 119/120, most 117-120), giving 1,066 new verified rows → 2,119 total, all train-only
- **R11-H1 more data still helps, with diminishing return** - retrain + 2,119 synthetic reaches real-slice non-English TNR 0.712 at its global cut, vs 0.683 at 1,053 (+0.029 for 2× the data); the gain is real but the curve is bending - data quantity alone is approaching its ceiling for this omission-negative source
- **R11-H2 generalisation holds and tightens** - LOLO at the global threshold (held-out language excluded from BOTH real and synthetic train): es 0.800 / fr 0.821 / pt 0.700 / nb 0.706 / sv 0.929, every language up on round 10 - the larger multilingual negative population transfers, not memorises
- **R11-H3 de back-translation installed - correctness fix, null on the metric** - `argospm install translate-de_en` closed the round-10 gap where every German claim skipped `r1_mt` at extraction; re-extracting with the bridge active drops the skip count to 0 and properly bridges the 236 de training rows, but the global-threshold TNR holds at 0.712 (within noise, LOLO shuffles inside tiny-n folds). The real gold v2 non-English eval slice carries **zero de negatives** (139 negatives are fr 28 / es 35 / pt 20 / nb 17 / sv 14 / it 7 / nl 5 / da 2 / tail), so the de fix can only improve de *training* feature quality, not a measurable eval number - it removes a known extraction defect without a headline move
- **Conclusion** - doubling the synthetic negatives moves real-slice TNR 0.683 → 0.712 and lifts every LOLO language; the mechanism scales but with diminishing return, pointing the next gain at source *diversity* (VitaminC contrastive negatives) rather than more of the same omission type. de back-translation is now installed, so the synthetic de rows bridge correctly going forward

Results - real gold v2 non-English slice, single global threshold (synthetic is train-only):

| training | global-threshold non-EN TNR | TPR | LOLO at global threshold (held-out lang) |
|---|---|---|---|
| retrain + 1,053 synthetic (round 10) | 0.683 | 0.768 | es 0.71 / fr 0.79 / pt 0.60 / nb 0.71 / sv 0.71 |
| **retrain + 2,119 synthetic (round 11)** | **0.712** | 0.719 | es 0.80 / fr 0.82 / pt 0.70 / nb 0.71 / sv 0.93 |

## Ship the durable fix, round 12: synthetic-retrained weights, single global threshold (ships)

Rounds 10-11 validated the data mechanism offline; round 12 reconciles it with the English no-regression guard and ships it into the library, retiring the round-9 language-conditional threshold. The blocker was that the gold-v2 recalibration broke two English precision e2e tests (the recalibrated English cut over-confirms borderline fabrications). The fix is to keep the synthetic-retrained weights but raise the single global cut until English clears, rather than dropping a permissive English threshold.

- **Setup** - `round9.py shipsynth` fits the HIGH manifold on gold v2 + VitaminC (×3) + short-source aug + 2,119 synthetic non-English negatives, emits the block at one global threshold (no `threshold_non_en`). Swept the global cut against the two English e2e tests through the real `ground()` pipeline: 0.45 and below fail (over-confirm), **0.50 and above pass** - so 0.50 is the smallest cut that keeps English green
- **R12-H1 a single global cut now satisfies both regimes** - at the shipped global 0.50, real gold v2: gold_en F1 0.803 → 0.810 (English *up*, e2e tests green), non-English TNR 0.78 at TPR 0.66, VitaminC F1 0.695 → 0.699 (holds), articles 0.797 → 0.816 (up). One threshold, both regimes - `threshold_non_en` retired
- **The weights carry the signal, not the threshold** - the synthetic negatives moved the cross-lingual boundary into the weights (intercept −1.05 → −4.92, more conservative; `r1_best` and `same_lang` up), so the global cut no longer has to be special-cased by language; the round-9 patch was an operating-point workaround, this is the structural fix
- **Cost** - non-English support recall 0.66 (rejects 34% of supported non-English claims) vs the round-9 patch's 0.76; the durable fix trades a little non-English support recall for a single honest operating point and English gains. de back-translation now installed, so de claims bridge at inference
- **Shipped** - shipped config HIGH block = synthetic-retrained weights + `threshold: 0.5`, `threshold_non_en` removed; the `threshold_for` plumbing stays for back-compat (returns the global cut when no non-EN threshold is set). Full suite 651 passed, 9 pre-existing pytensor `CompileError` unrelated; the round-9 shipped-config threshold test flipped to assert the single-global-cut state

Results - real gold v2, shipped single global threshold 0.50 (synthetic-retrained weights):

| slice | shipped (R9: EN 0.40 / non-EN 0.70) | R12 single global 0.50 |
|---|---|---|
| gold_en F1 | 0.803 | **0.810** |
| gold_ne (non-EN) TNR / TPR | 0.42 / 0.90 @0.70 | **0.78 / 0.66** |
| vitaminc F1 | 0.695 | **0.699** |
| articles F1 | 0.797 | **0.816** |

## Lessons learned

- **Features beat model class** - the gain came from the lexical recall + claim-intrinsic features, not from a nonlinear learner; a regularised logistic is the right head for these few-context data
- **Conclusions are dataset-size dependent** - growing the data (375 → 856 → 1260, 86 → 466 negatives) flipped "depth-2 GBT wins" into "linear wins, trees overfit"; never trust a single-snapshot conclusion on a small set
- **The right split matters** - leave-one-language-out and leave-one-source-out measure different generalisations; here unseen-language is the harder one, and the few-context worry was wrong-signed (source-out scored higher, not lower)
- **Imbalance hides failure** - 0.64 accuracy looked fine while macro-F1 was 0.39 and hallucination-F1 0.00; pick the imbalance-robust metric first
- **A semantic model was not required** - good lexical features with translate-then-recall matched and beat NLI on this task
- **The win is matched to omission-type hallucinations, not contrastive ones** - run unchanged on VitaminC (contrastive English fact-verification, negatives lexically near-identical to the evidence with one fact flipped), the lexical grounder collapses to macro-F1 0.586 (SUPPORTS vs REFUTES, ~coin-flip) from 0.837 on private RAG; private RAG hallucinations are absent/fabricated specifics that drop recall, VitaminC REFUTES are present-but-contradicted so recall stays high and the lexical stack is structurally blind; contradiction detection is where NLI earns its place (mirrors the A4 transfer: VitaminC is NLI-dominant, private RAG recall-dominant)
- **Most of that gap is deterministically bridgeable** - a contradiction layer (aligned value-conflict feature + antonym/direction-flip triage, fuzzy-gated) trained jointly lifts VitaminC 0.532 → 0.673 while private RAG holds (0.851 → 0.841, within LOSO noise); `direction_flip` fires on 62% of REFUTES vs 6% of SUPPORTS and 0.4% of private RAG - active only where the contrastive negative lives, the mirror of `same_lang`/`is_en` which carry private RAG's mechanism and go quiet on English VitaminC; one model holds both because each corpus's signal rides on features inert on the other (final design in `lexical-grounding-sota.md`)
- **Triage beats forcing a verdict** - where deterministic features cannot settle support-vs-contradiction, a `semantic_candidate` flag (high overlap AND a conflict/direction signal) marks the claim for a downstream semantic stage: 23% of VitaminC at 92% REFUTES precision, 3× error concentration, zero classifier cost - the irreducibly semantic residual is routed, not guessed
- **MT good enough makes routing ~free** - always-translate-then-recall matches the per-chunk `same_lang` routing on the source-out split (0.835 vs 0.837); the routing's value is cost (skip translation for same-language claims), not accuracy; better MT would mostly help the abstractive es/pt tail
- **Claim-intrinsic features generalise** - `specificity` (anchor density from the claim alone) lifted the source-out split and narrowed the LOLO↔LOSO gap precisely because it cannot see the evidence, so it learns the way claims are checkable, not the documents' text; the strongest single-feature add
- **A verbatim span is a precision-1 confirm** - a long contiguous restatement is near-deterministic support (98.2%), whereas the same words scattered across a document are not
- **Anti-overfit is not no-modeling** - the rule bans fitting the test fold, not modeling; the win was a model fit honestly under LOLO/LOSO
- **A feature can be non-null yet unlearnable** - `unmatched_rarity` carried a real −0.58 benchmark coefficient but could not fix the short-source regime, because the manifold's dominant recall signal collapses to 0 there and no training row exposes the regime; the fix was regime augmentation (truncated short sources), not a stronger feature. "Null on the benchmark" can mean "the regime where it pays off is absent from training," not "useless"
- **Fix the regime, not with a threshold** - the short-source failure was tempting to patch with a fixed recall damp; instead a learned background-IDF floor + a distinctive-content feature + regime-coverage augmentation let the manifold recalibrate itself, which generalises (it also lifted VitaminC) where a hand-set constant would not

## Conclusions

- **Ship the lexical-only logistic** - translate-then-recall + anchors + claim-intrinsic `specificity` (with per-chunk language detection + `same_lang` kept for efficiency); macro-F1 0.845 (source-out), hal-F1 0.81, no semantic model, cheap and CPU-only; `quote_flag` as a precision-0.98 supported confirm
- **Translation is the only neural component** - a frozen argos bridge, used where a same-language chunk is absent; everything else is lexical
- **The ceiling is data** - the source contexts grew to 75 (from ~22), which stabilised leave-one-source-out; the residual is now the small language tail (da/pt/de at n=10-22), where leave-one-language-out dips - more labelled data in those languages is the prerequisite, not a cleverer model
- **Reframes the client finding** - lexical did not fail at grounding; it failed at cross-lingual confirmation, fixed by translation (the same-language routing is an efficiency lever, not an accuracy one)
- **Bounded scope, deploy accordingly** - the lexical win is task-specific: it holds across private RAG's data growth but does not transfer to a contrastive benchmark (VitaminC macro-F1 0.586); use it where hallucinations are fabricated or omitted specifics, keep NLI available for present-but-contradicted negatives
- **Short-source regime fixed by learned recalibration (R5)** - on a 1-chunk source the in-context IDF collapses and the dominant recall feature dies; a `wordfreq` background-IDF floor revives recall, the `unmatched_rarity` distinctive-content feature discriminates, and truncation augmentation recalibrates the manifold for the regime. Probe 10/12 → 11/12, private RAG holds (0.825 → 0.817), VitaminC lifts (0.661 → 0.691); ships in the library lexical mode. The residual miss is a spelled-out-number value-conflict, left to the deferred numeric-normalisation work
- **Cross-lingual blind spot found and fixed (R9, superseded by R12)** - the English-dominant benchmark hid that the shipped manifold caught 0 of 139 non-English hallucinations; an unbiased gold (gold v2) exposed it. R9 shipped a language-conditional decision threshold (`threshold_non_en: 0.70`, keyed off `is_en`) over the unchanged weights - non-English TNR 0.000 → 0.748, English byte-identical. R12 then retired that patch: the synthetic-retrained weights carry the signal so one global cut works. The patch was the fast fix, the retrain is the durable one
- **Synthetic translation data is the durable cross-lingual fix - now shipped (R10-R12)** - `claude -p`-translated, fidelity-verified non-English negatives let a single global threshold reach real-slice TNR 0.683 at 1,053 rows and 0.712 at 2,119 (R11 doubling, +0.029) with LOLO generalisation 0.70-0.93. R12 ships it: the synthetic-retrained weights at a single global cut 0.50 keep English e2e tests green (English F1 *up* 0.803 → 0.810), catch non-English at TNR 0.78, hold VitaminC and articles - so `threshold_non_en` is retired and the cross-lingual signal lives in the weights. The mechanism scales with diminishing return - the next gain is source diversity, not volume

## Next steps

- **Promote** the lexical-only logistic into the production grounder via a separate reviewed change; keep NLI optional/off
- **More negatives in the language tail** - source contexts grew to 75 (constraint loosened); the binding constraint is now the small da/pt/de language tail; grow those before chasing further model capacity
- **Diversify synthetic sources, not just volume (R11 follow-on)** - doubling the omission-negative set gave diminishing return (+0.029 TNR); add VitaminC contrastive negatives so the synthetic population covers the contradiction failure mode, before generating a third batch of the same type. de back-translation (`translate-de_en`) is now installed - the German `r1_mt` bridge fires, though the real eval slice has no de negatives to score it
- **Get real de negatives into the eval slice** - the gold v2 non-English negatives carry zero de; the de synthetic training rows and bridge are untestable on the honest slice until de hallucinations are judged into gold, so de coverage is currently a train-side correctness claim only
- **Recover the non-English support recall (R12 follow-on)** - the durable fix trades non-English TPR down to 0.66 (rejects 34% of supported non-English claims) for the single global cut; better MT on the abstractive es/pt tail or a non-English support-side feature could lift it without re-splitting the threshold
- **Engineering** - lingua-py for language ID, a faster per-language MT engine if throughput matters
- **Refuted, do not revisit without more data** - NLI in the verdict, claim decomposition, cross-corpus transfer, deep trees, OPUS-MT
