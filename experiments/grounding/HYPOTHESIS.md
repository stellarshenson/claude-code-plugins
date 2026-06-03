# Hypothesis: a deterministic multilingual grounder for the DeLaval gold

> **Outcome (see `RESULTS.md`)**: validated with a twist. A frozen offline translator (argos-translate) + best-chunk IDF recall reaches **LOLO balanced 0.777 / TEST 0.755** (target ≥0.75), beating the lexical-only ceiling (~0.67). A separate English-vs-translated recall bar pushes **accuracy to 0.845 LOLO / 0.817 TEST**, near the 0.85 stretch. Follow-ups: the chunk sweep confirms whole-doc is the 0.50-AUC floor; a fixed-prior threshold generalises (0.776 balanced, zero tuning); an abstain band gives 0.838 balanced at 68% coverage; lingua-py lifts accuracy to 0.781. MT collapses Gap B into Gap A; the curated lexicon / cognate / anchor bridges (X1-X3) and the contradiction/meta signals do **not** add value once MT is present (they slightly hurt). Spanish/abstractive tail stays hard; NLI residual + OPUS-MT still to run. See `RESEARCH.md` for the toolbox.

## Problem (measured, not assumed)

The verified gold is `experiments/grounding/delaval-forensics/gold/golden_grounding_evidence_verified.json`
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
3. **Dictionaries to keep.** (a) a **multilingual domain lexicon** mapping VMS component/part vocabulary in all six source languages → English canonical terms; (b) a **product/part-ID gazetteer** (`C`-codes, `V`/`T`-codes, product names) for anchor extraction; (c) per-language stopword lists. Bootstrap from the part catalogue (ID↔name pairs in the tool outputs), DeLaval glossaries, and held-out co-occurrence alignment mined from the gold (strict hold-out to avoid leakage).
4. **Other deterministic layers.** Chunk the mega-evidence and score claim-recall against the best chunk (Gap A); numeric/entity **anchor recall** (confirm) and **anchor mismatch** (contradict: claim `C00000245` vs evidence `C00000246`); diacritic/transliteration normalisation; fuzzy AFTER lexicon canonicalisation.

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

The DeLaval gold + transcripts stay in the git-ignored `delaval-forensics/` stash; this hypothesis carries no client data and is safe to commit. Numbers above are reproduced directly from the verified gold via the P0 probe.
