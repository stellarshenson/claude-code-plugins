# Hypothesis: a deterministic multilingual grounder for the private RAG gold

> **Outcome (see `RESULTS.md`)**: validated with a twist. A frozen offline translator (argos-translate) + best-chunk IDF recall reaches **LOLO balanced 0.777 / TEST 0.755** (target ≥0.75), beating the lexical-only ceiling (~0.67). A separate English-vs-translated recall bar pushes **accuracy to 0.845 LOLO / 0.817 TEST**, near the 0.85 stretch. Follow-ups: the chunk sweep confirms whole-doc is the 0.50-AUC floor; a fixed-prior threshold generalises (0.776 balanced, zero tuning); an abstain band gives 0.838 balanced at 68% coverage; lingua-py lifts accuracy to 0.781. MT collapses Gap B into Gap A; the curated lexicon / cognate / anchor bridges (X1-X3) and the contradiction/meta signals do **not** add value once MT is present (they slightly hurt). Spanish/abstractive tail stays hard; NLI residual + OPUS-MT still to run. See `RESEARCH.md` for the toolbox.
>
> **Current state (Round 9, see Round 8b/9 below)**: the shipped fixed-threshold manifold did NOT carry that Round 1 cross-lingual capability - it lived in a tuned-threshold harness. Gold v2 (survivorship bias removed) exposed the shipped manifold as an English-only hallucination detector: non-English hallucination recall (TNR) 0.000 vs English 0.710. Round 9 fix: retrain on gold v2 (restores `r1_mt`, also lifts English TNR to 0.850) **plus** a language-conditional non-English decision threshold (~0.65, keyed off `is_en`). That clears the bar and generalizes - leave-one-language-out held-out TNR es 0.74 / fr 0.64 / nb 0.65 / pt 0.60 / sv 0.93. Retrain-alone with one global threshold misses (OOF non-English TNR 0.13). Ship needs a `LexicalVerdict.confirmed` + config change - pending.

## Problem (measured, not assumed)

The verified gold is `experiments/grounding/private-rag-forensics/gold/golden_grounding_evidence_verified.json`
- 375 records `{claim, source_text, label, lang}`, **289 supported (label 1) / 86 hallucination (label 0)**.
- Evidence (`source_text`) is always an English whole-document RAG/tool dump.
- Claims span **seven languages**, not two:

| lang | n | supported | claim→evidence token recall | anchor% | id-match% |
|---|---|---|---|---|---|
| en | 276 | 201 | **0.837** | 26% | 16% |
| nb-NO | 54 | 53 | 0.241 | 24% | 9% |
| fr-FR | 14 | 14 | 0.356 | 29% | 29% |
| sv-SE | 12 | 5 | 0.222 | 8% | 0% |
| it-IT | 8 | 8 | 0.483 | 12% | 12% |
| es-ES | 6 | 4 | 0.133 | 0% | 0% |
| pt-PT | 5 | 4 | 0.225 | 0% | 0% |

The lexical grounder confirms only ~12% of the 375 (`reports/grounding_signal_on_verified_gold.md`); semantic e5 carries 328 but over-confirms (supported 0.366 vs hallucination 0.206, threshold sweep tops at 25% precision). We want a **non-LLM, deterministic, cheap** grounder that beats that.

## Core insight: this is two different gaps, not one

The single "Norwegian vs English" framing in the prior draft was wrong. The measurement splits the failure cleanly:

- **Gap A - scoring (English, 74% of claims).** English claim words ARE in the English evidence: recall **0.892 for supported vs 0.689 for hallucination** - present *and separable*. Jaccard is ~0.014 only because the evidence is a giant document dump that swamps set-overlap. So lexical's collapse here is **not** a language problem; it is a **scoring** problem - length-swamped Jaccard/BM25 over an unchunked mega-evidence. Fixable with recall-oriented, chunked, length-normalised scoring. No model, no dictionary. This is the largest and cheapest win.
- **Gap B - language (non-English, 26%, six source languages).** Recall collapses (nb-NO 0.241, es-ES 0.133). This is the genuine cross-lingual gap and needs bridges. Anchors/IDs help unevenly (fr-FR id-match 29%, but es/pt/sv 0%), so anchors are a **precision booster, not the main bridge**; a multilingual domain lexicon plus cognate/diacritic normalisation carries the bulk.

Two corrections the data forced:
- **The `lang` field is noisy** - sv-SE holds English-looking claims and only 5/12 are supported; language must be **re-derived**, not trusted.
- **The disclaimer/refusal sub-hypothesis is dead** - 0 of 86 negatives match refusal phrasing (`fant ikke`, `not found`, ...). Negatives are **assertive fabrications**, so a refusal classifier buys nothing here; drop it.

## Goal (falsifiable)

**Headline metric: accuracy** - fraction of the 375 where the grounder verdict matches the gold label (verdict `grounded` → label 1; `contradicted`/`unconfirmed` → label 0).

> A deterministic, model-free grounder reaches **≥85% accuracy** on the 375 verified gold, at **balanced accuracy ≥0.75**, <50 ms/claim, zero model - beating the e5 semantic baseline and the trivial majority-class scorer.

Guard: the set is 289 supported / 86 negative, so an "always grounded" scorer already scores **77.1% accuracy**. Accuracy alone is therefore gameable - **balanced accuracy** (mean of per-class recall) is the paired guard so the grounder must actually catch hallucinations, not just predict the majority.

Two diagnostic sub-targets feed the headline:
- **A (English, 74%)** - recall-oriented chunked scoring recovers present-but-unscored support, lifting English supported-recall from ~12% to **≥70%**.
- **B (cross-lingual, 26%)** - anchors **OR** multilingual lexicon **OR** cognate/diacritic fuzzy lift non-English supported-recall from ~12% to **≥50%**, at false-flag ≤ semantic.

Strong prior for A: recall 0.837 means the evidence already contains the words; only the scorer is blind. Weaker prior for B: anchor density is modest, so lexicon coverage is the lever.

## The four requested components

1. **Enhanced claims extraction.** Claims average **2.35 sentences (max 26)** - multi-fact. Split into atomic claims (raises per-fact recall and stops one false fact poisoning a true paragraph), each carrying its anchors `(text, {numbers, units, ids, entities})`. No disclaimer tagging (data shows it is unneeded).
2. **Language recognition.** Per claim (and per evidence span), detect language with a deterministic statistical detector (`lingua` / `fasttext-langid` / `langdetect`, ~ms). Re-derive - do not trust `lang`. Route: detected-English → Gap-A recall scorer; detected non-English → Gap-B bridge pipeline. Expect en dominant, then nb/fr/sv/it/es/pt.
3. **Dictionaries to keep.** (a) a **multilingual domain lexicon** mapping product component/part vocabulary in all six source languages → English canonical terms; (b) a **product/part-ID gazetteer** (alphanumeric part codes, product names) for anchor extraction; (c) per-language stopword lists. Bootstrap from the part catalogue (ID↔name pairs in the tool outputs), private RAG glossaries, and held-out co-occurrence alignment mined from the gold (strict hold-out to avoid leakage).
4. **Other deterministic layers.** Chunk the mega-evidence and score claim-recall against the best chunk (Gap A); numeric/entity **anchor recall** (confirm) and **anchor mismatch** (contradict: a part code in the claim vs a different code in the evidence); diacritic/transliteration normalisation; fuzzy AFTER lexicon canonicalisation.

## Experiment plan (on the verified gold, same 375, same metrics as the project reports)

- **P0 - profile (largely done).** Language histogram, per-language recall/anchor/id-match (table above), refusal density (0/86), atomicity (2.35 sent/claim). Confirms the two-gap split and kills the refusal idea.
- **P1 - Gap A recall scorer.** Chunk evidence; score supported vs hallucination English claims by length-normalised claim-recall against best chunk; sweep threshold; confusion matrix. Target: exploit the 0.892/0.689 separation.
- **P2 - anchors.** Regex + gazetteer extractor; anchor-recall as a standalone signal; anchor-mismatch as a contradiction signal.
- **P3 - multilingual lexicon.** Mine + curate source-lang→EN lexicon; canonicalise both sides; BM25/recall on canonical terms for the six non-English groups.
- **P4 - cognate fuzzy.** Diacritic strip + orthographic rules + fuzzy on residual cognates.
- **P5 - combine, ablate, calibrate.** Union verdict; report **accuracy + balanced accuracy + confusion matrix** vs (a) majority-class 77.1%, (b) current lexical, (c) e5 semantic 328/375, (d) NLI; ablate which bridge dominates; calibrate with the grounder's class-balanced Bayesian verdict (`fit_calibrator(balance="balanced")`) against the 86-negative imbalance.

**Acceptance:** overall **accuracy ≥85%** and **balanced accuracy ≥0.75** on the 375 (beating majority 77.1% and semantic); diagnostics: English supported-recall ≥70% via recall scoring, non-English supported-recall ≥50% via bridges; false-flag ≤ semantic; <50 ms/claim; no model.

## Risks / falsifiers

- Gap A may already be 80% solved by chunked recall alone - then most of the "lexical fails" story is just a mis-scored scorer, and the deterministic win is bigger and cheaper than expected (a useful, publishable result).
- Low anchor density (es/pt/sv 0% id-match) → anchors do not help those languages; lexicon coverage is the bottleneck.
- Lexicon mined from gold risks leakage → strict hold-out.
- Cognate-fuzzy false positives across Romance languages; short-claim language-detection errors.
- Honest null for Gap B: if non-English supported claims are anchor-sparse abstractive prose, the deterministic bridge cannot reach 50% and semantic stays required for the cross-lingual tail - itself a finding.

## Note

The private RAG gold + transcripts stay in the git-ignored `private-rag-forensics/` stash; this hypothesis carries no client data and is safe to commit. Numbers above are reproduced directly from the verified gold via the P0 probe.

---

# Hypothesis H12 - batch-adaptive operating point (max-gap / Jenks)

Claim: the pre-fork cascade's `adaptive_gap` cut (sort batch scores, threshold at the largest gap), applied unsupervised to the manifold's `p_high` per sub-dataset batch, recovers distant-paraphrase false-rejects without touching features or weights. Motivation: that mechanism scored 0.93 macro-F1 on the article fixtures where the manifold scores 0.81.

- **Batch unit** - sub-dataset kind: private_rag 2,752 / vitaminc 800 / articles 42; one empirical threshold per corpus
- **Variants** - max-gap midpoint, max-gap bottom-half (cascade's variant), Jenks 2-class (`jenkspy`)
- **Guards** - batch >= 4 else fixed; gap-significance floor, swept not hand-set
- **Baseline** - shipped fixed threshold 0.4; label-tuned per-corpus threshold as supervised reference
- **Predicted** - cut lands near the label-tuned threshold on bimodal corpora; articles rises toward 0.93; private_rag holds ~0.817
- **Falsifiers** - unimodal corpus distribution → largest gap is noise, cut worse than fixed; bottom-half prior fails to transfer; wins-on-articles-only = benchmark overfit, reject
- **Non-goals** - no feature/weight changes, no production adoption this round
- **Experiment** - `notebooks/03-kj-H12-maxgap-batch-experiment.ipynb` over `data/processed/grounding_combined.parquet` (gitignored; `build_combined.py`)

## Outcome (Round 7) - REJECTED at corpus granularity

Unimodal falsifier fired; full tables in `BENCHMARK.md` Round 7 and the notebook.

- **No gap structure at corpus scale** - largest gap 0.001-0.013 = noise; cuts land at 0.047 / 0.954, flipping 350-770 verdicts
- **Unguarded max-gap destroys two corpora** - private_rag 0.829 → 0.419, vitaminc 0.695 → 0.346
- **Jenks stable but never beats fixed** - mean 0.751 vs fixed 0.774
- **Gap floor (any 0.02-0.15) reduces mechanism to fixed** - fires only on the bimodal 42-claim articles batch, +0.019 mean = the pre-registered overfit falsifier
- **Surviving signal** - per-natural-group cuts on 63 mixed-label groups (n >= 4) beat fixed: articles 0.843 vs 0.808, traces 0.642 vs 0.609; the cascade's mechanism lived on small per-request batches, never corpora
- **Follow-up hypothesis** - per-trace cuts with an unsupervised guard, scored on ALL traces incl. single-class; rejected unless it holds there

---

# Hypothesis H13-H16 (Round 8) - three mechanism candidates

IDs: H13 = A1 SaT extraction, H14 = A2 atomic-fact scoring, H15 = H-B alignment-profile, H16 = H-C negation flag.

Round 7 closed the threshold path; Round 8 targets mechanisms. Three pre-registered candidates, each with a diagnostic gate that can kill it before any build.

## H-A: the claim unit is wrong end-to-end (extraction + scoring)

Claim: the pipeline should extract and score atomic, language-agnostic facts, not regex-gated multi-sentence blobs. Gold claims average 2.35 sentences (max 26); every recall feature max-pools over one 300-char chunk.

**A1 - SaT multilingual claim extraction.** Shipped `extract.py` uses regex sentence split + an English-only verb gate (copula list + `-s/-ed/-ing` suffixes); non-English claims fail the gate. Replace with SaT segmentation (already shipped in `document_processing/sat.py`) + a language-agnostic content gate.

- **Measurement** - extraction recall vs verified gold claims on original private RAG answer documents, overall and per-language; claim-count inflation as precision proxy
- **Predicted** - non-English extraction recall rises from near-zero to parity with English
- **Diagnostic gate** - measure shipped `extract_claims()` recall first; kill if > 0.9 overall AND per-language
- **Falsifier** - claim-count inflation > 2x with no recall gain = precision collapse

**A2 - atomic-fact scoring.** Decompose each claim into SaT facts, score each through the existing frozen manifold against its own best chunk, aggregate per-fact probabilities into the claim verdict. No retrain - shipped weights per fact; never train on inherited fact labels.

- **Aggregation tournament** - min-p, mean-p, length-weighted mean, noisy-AND; selector learned on training folds only
- **Predicted** - private RAG multi-sentence claims recover false-rejects (facts whose evidence sits in different chunks); fabricated facts inside long true claims surface
- **Diagnostic gate** - kill if < 30% of private RAG errors are multi-sentence claims OR multi-sentence error rate < 1.5x single-sentence
- **Falsifiers** - anaphora-broken facts over-reject the supported side; any corpus drops > 0.01

## H-B: alignment-profile features (rival to A2 - keep claim whole, fix the pooling)

Claim: the evidence signal should describe the shape of the claim-evidence alignment, not just the best chunk. Three deterministic features + manifold retrain via the established joint protocol.

- **r1_union** - IDF-weighted claim-token coverage over the union of top-k chunks (set-cover, not max)
- **dispersion** - normalised span-spread of matched token positions (supported = contiguous, fabricated = scattered)
- **max_run** - longest contiguous matched run / claim length
- **Predicted** - lifts long multi-fact claims; dispersion adds a fabrication signal max-pooling cannot see
- **Diagnostic gate** - shares A2's multi-sentence error-concentration gate
- **Falsifiers** - hallucination-F1 drops (union coverage inflates false accepts); LOSO/LOLO regression; retrained weight ~0 = redundant with oracle/top3

## H-C: negation-scope mismatch feature (target VitaminC 0.691)

Claim: an alignment-gated polarity-flip flag separates present-but-negated evidence from support. Negation cue (multilingual closed-class list) near an aligned anchor on exactly one side of the pair, gated by fuzzy > 0.5; + retrain.

- **Predicted** - VitaminC REFUTES recall rises; complements `wn_antonym_flip` (antonyms are not negation)
- **Diagnostic gate** - kill if negation-cue asymmetry < 25% of VitaminC errors or asymmetry rate in non-errors >= half the error rate
- **Falsifiers** - private RAG regresses (incidental negation over-flagging); retrained weight ~0

## Shared protocol

- **Baseline reproduction first** - 0.817 / 0.691 / 0.808 must reproduce or stop
- **Ship bar** - target-corpus gain >= +0.02 macro-F1 AND no corpus drops > 0.01
- **Stacking** - A2 x H-B evaluated together only if each survives alone
- **Non-goals** - no shipped-code changes this round; no LLM; no new heavy deps
- **Experiment** - `notebooks/04-kj-H13-H16-sat-extraction-atomic-alignment-negation.ipynb` + `experiments/grounding/mechanisms.py`

## Stage 1 gate outcomes (Round 8)

Diagnostics in `mechanisms.py`, log `logs/round8-diagnostics.log`. One amendment before running: gold claims were produced BY the shipped `extract_claims()` (`answer_claims()` in the forensics code), so A1's original gold-recall gate was circular; replaced with verb-gate rejection rate per language on the 639 raw answer documents (trace cache, 0 missing).

- **A1 - SURVIVES** - verb gate rejects 9.2% of English sentences vs nb 50.4%, it 85.5%, de 55.1%, da 46.7%, sv 46.2%, nn 40.6%, es 28.0% (length-passing sentences only). The anglocentric defect is real and large
- **A2 - KILLED** - errors do not concentrate in multi-sentence claims: share_errors_multi 27.0% vs share_claims_multi 28.5%; err-rate ratio multi/single 0.93 (needed > 1.5). Granularity mismatch falsified on private RAG (n=2752, 381 errors)
- **H-B - KILLED** - shared A2's gate per pre-registration
- **H-C - KILLED** - negation-cue asymmetry in 3.7% of VitaminC errors (needed >= 25%); non-errors 1.8%; errors split 119 false-accepts / 125 false-rejects. Negation is not the VitaminC failure mode

## Outcome (Round 8) - A1 KEPT, A2 / H-B / H-C killed at the gates

Full tables in RESULTS.md and BENCHMARK.md Round 8.

- **A1 KEPT** - verb gate is anglocentric (en 9.2% rejection vs nb 50.4%, it 85.5%); language-agnostic gate alone doubles nb admissions, recovers it from zero, 1.13x inflation, 0.997 gold coverage; SaT boundaries add more (1.31x) at 0.990 coverage
- **A2 / H-B REJECTED pre-build** - error concentration gate failed (ratio 0.93, needed > 1.5)
- **H-C REJECTED pre-build** - negation asymmetry 3.7% of VitaminC errors (needed >= 25%)
- **Follow-ups registered** - sampled dual-judge precision pass on new admissions; gold v2 re-extraction (gold carries extractor survivorship bias); ship decision: gate-only conservative, SaT+gate after precision pass

## Outcome (Round 8b) - gold v2 re-baseline, the survivorship-bias payoff

The A1 KEPT decision implied the v1 gold was itself biased - built THROUGH the anglocentric extractor, it dropped non-English claims before judging. Gold v2 (`gold_v2.py`) re-extracts every answer via the SaT + language-agnostic gate, inherits the verified label where a claim still fuzzy-matches v1 gold, and dual-judges the rest (Haiku + Sonnet, keep dual-agreed). Result: 5,912 rows, 84% trace coverage; extraction precision of new admissions 48.8% real claims / 32.7% noise. Benchmarking the shipped HIGH manifold on it:

- **Headline barely moves** - macro-F1 0.802 vs v1 0.817; English is 77% of the unbiased population and dominates
- **The split is the finding** - english balanced-acc 0.797 / hallucination recall 0.710 (healthy); non-english balanced-acc 0.498 / hallucination recall (TNR) 0.000, confirming 1,339 of 1,343 and catching 0 of 139 non-English hallucinations
- **The shipped manifold is an English-only hallucination detector** - MT recall lifts non-English support but the frozen weights, trained on English-dominant data, encode no cross-lingual negative signal; v1's 0.817 was an English score in disguise
- **Round 9 candidate** - retrain the manifold on the 139 non-English negatives gold v2 now provides (the first dataset that contains them); full tables in RESULTS.md / BENCHMARK.md Round 8b

---

# Hypothesis H17 (Round 9) - cross-lingual manifold retrain

The shipped HIGH manifold catches 0 of 139 non-English hallucinations (TNR 0.000) while English is healthy (TNR 0.710). H17 asks whether this is a weights defect curable by retraining on gold v2, or a feature defect needing a new cross-lingual signal.

## Claim

The 18 shipped features already separate non-English support from hallucination; the English-dominant training data (where `r1_mt == r1_direct`, collinear) left the cross-lingual signal unweighted. Retraining the same frozen 18-feature contract on gold v2 - the first gold containing non-English negatives - lifts non-English hallucination recall without regressing English.

- **Probe (pre-build, decides the fork)** - shipped HIGH features on the non-EN slice (139 neg + 280 sampled pos): `r1_mt` AUC 0.802 (supp 0.525 vs halluc 0.245), `r1_best` 0.802, `unmatched_rarity` 0.796 inverted (halluc 0.734 vs supp 0.431); `r1_direct` only 0.622. Features separate → the fix is a retrain, not a new feature. MT bridge fires on 82.6% of non-EN rows
- **Predicted** - non-EN TNR rises from 0.000 to meaningfully positive; English balanced-acc 0.797 / TNR 0.710 and VitaminC 0.691 hold
- **Pre-registered ship bar** - held-out non-EN TNR >= 0.30 AND English balanced-acc drop <= 0.01 AND VitaminC drop <= 0.01
- **Falsifier (generalization)** - leave-one-language-out: train without a language's negatives, measure its held-out TNR. 139 negatives across 16 languages is thin; if LOLO TNR stays ~0 while in-sample rises, the gold lacks volume to learn a transferable boundary - report, ship nothing
- **Non-goals** - no new feature (probe killed the need), no shipped-config write until accepted, no LLM, no new heavy dep

## Secondary - MT coverage (H17b)

Independent deterministic lift: install the missing argos packages (sv, nl, da, ...) so `r1_mt` fires on ~100% of non-EN rows instead of 82.6%, raising real cross-lingual recall for the thin-tail languages without any retrain.

## Protocol

- **Baseline reproduction** - shipped HIGH on gold v2 must reproduce non-EN TNR 0.000 / EN balanced-acc 0.797 or stop
- **Experiment** - `notebooks/05-kj-H17-crosslingual-manifold-retrain.ipynb` + `experiments/grounding/round9.py`; retrain writes `config_document_processing.experiment.yaml`, never the shipped config

## Outcome (Round 9) - retrain-alone MISSES, retrain + language-conditional threshold is the fix

Full tables in RESULTS.md / BENCHMARK.md Round 9. Baseline reproduced (non-EN TNR 0.000, EN bal-acc 0.797).

- **Probe confirmed at full scale** - features separate non-EN classes (r1_mt AUC 0.806, unmatched_rarity 0.802 inv); per-language r1_best AUC 0.72-0.89. The defect is the weights
- **Retrain alone MISSES the bar** - OOF non-EN TNR 0.000 -> 0.129 (bar 0.30); LOLO at the global threshold collapses (fr/nb 0.000). It does *improve* English (TNR 0.710 -> 0.850) - no regression
- **Operating-point diagnosis** - the global threshold is calibrated to the English bulk; r1_mt ranks non-EN hallucinations below supports but their absolute probabilities clear that cut. A non-EN-specific threshold (~0.65) converts the AUC-0.80 ranking into catches: OOF TNR 0.676 at TPR 0.797
- **It generalizes (LOLO at non-EN thr 0.65)** - es 0.743, fr 0.643, nb 0.647, pt 0.600, sv 0.929 held-out TNR; every unseen language clears 0.30 by 2-3x
- **H17b (MT coverage) - not the lever** - es/fr/pt/nb/sv/da packages already installed (114/139 negatives); nl (5) now installed; firing gap is mis-detection/cognates
- **The fix** - retrained weights + a language-conditional decision threshold keyed off `is_en` (already computed); deterministic, in-contract, no new feature. Shipping needs a `LexicalVerdict.confirmed` + config change - held for explicit approval. Shipped weights/config untouched this round

## Ship calibration (Round 9) - guard result

Code landed: `LexicalVerdict.threshold_non_en` + `threshold_for(feat)` (English cut when `is_en` absent/>=0.5, non-English cut otherwise); decision point `grounding.py:965` uses it; back-compat (None -> English cut everywhere). Chosen HIGH thresholds: english 0.290, non_english 0.750. No-regression guard (`round9.py shipcal`, HIGH, shipped vs recalibrated):

| corpus | shipped | recalibrated | verdict |
|---|---|---|---|
| gold_en (4569) | F1 0.803 / bal 0.797 / TNR 0.710 | F1 0.817 / bal 0.820 / TNR 0.804 | improved |
| gold_non_en (1343) | F1 0.472 / bal 0.498 / TNR 0.000 | F1 0.606 / bal 0.767 / TNR 0.813 | fixed |
| articles held-out EN (42) | F1 0.797 / bal 0.861 | F1 0.816 / bal 0.931 | improved |
| vitaminc (800) | F1 0.695 | F1 0.680 | **-0.015 (breaches the 0.01 guard)** |

Both real English corpora (gold_en, held-out articles) improve and non-English goes from broken to working; at vit x1 the only regression was VitaminC -0.015. Recovery: up-weighting VitaminC in the retrain (sweep gold_ne x3, vit x{1,3,5,8}) - **vit x3 clears every corpus**: gold_en +0.003, gold_non_en +0.138, vitaminc +0.003 (recovered), articles +0.019 (vit x5/x8 over-correct, hurting gold_en/articles). At vit x3 the recalibrated weights clear every corpus, but the ship step revealed a simpler, safer fix.

## Shipped (Round 9) - threshold-only, weights untouched

Writing the recalibrated weights broke two English e2e precision tests (`test_common_word_fabrication_not_confirmed`, `test_precision_recall_targets`): the gold-v2-optimal English threshold 0.290 is more permissive than the shipped 0.40 and over-confirms borderline English fabrications. More important, the recalibration was **unnecessary** - the *shipped* weights already rank non-English hallucinations below support (they were just never given a cut that exploited it). Shipped HIGH weights, unchanged, + a non-English threshold of **0.70**:

- non-English slice (gold v2, held-out for the shipped weights): TNR 0.748 / TPR 0.761 / bal-acc 0.754, vs TNR 0.000 at the global 0.40
- generalises per-language: es 0.80, fr 0.71, nb 0.71, pt 0.65, sv 0.93, it 0.71, nl 1.00 TNR
- English **byte-identical** to shipped (gold_en, VitaminC, articles, all e2e tests unchanged)

**Ship = shipped HIGH block unchanged + `threshold_non_en: 0.70`** (one config line). Zero English blast radius, non-English TNR 0.000 -> 0.75. The recalibration stays an experiment (it churns English and breaks precision tests for no net gain). Pre-registered bar cleared on every axis.
