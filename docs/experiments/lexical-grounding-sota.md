# Lexical cross-lingual grounder - final design

The deployed grounder classifies each claim as supported or hallucination using only lexical signals plus a torch-free machine-translation bridge - no semantic model in the verdict path. A deterministic contradiction layer extends it to hold on a second, contrastive corpus (VitaminC) and emits a triage flag marking claims for a future semantic stage.

## Pipeline

Eight deterministic stages, claim in → verdict + triage flag out.

- **Language detection** - lingua-py per claim and per best chunk; a `same_lang` flag marks whether the source carries a chunk in the claim's language
- **Conditional MT** - argos-translate (CTranslate2 int8, CPU) + wtpsplit SaT sentence splitter (ONNX), torch-free; fires only on heterogeneous claims (non-English claim vs English source), ~23% of the live 2752 gold (the language tail grew to ten+ languages)
- **Chunking** - recursive, 300-char chunks, 0.1 overlap (AUC-validated operating point)
- **Lexical recall** - BM25-best-chunk IDF-weighted token recall, computed direct (`r1_direct`) and translate-then-recall (`r1_mt`); the model learns which to trust
- **Supporting lexical signals** - char-ngram recall, rapidfuzz partial-ratio, anchor recall + mismatch (numbers/IDs, language-invariant), oracle-chunk and top-k consensus
- **Claim-intrinsic specificity** - anchor density from the claim alone (evidence-independent → cannot memorise the documents); the strongest generalisation feature
- **Contradiction layer** - aligned value-conflict + WordNet antonym-flip (below)
- **Verdict head** - class-balanced logistic over the feature set; LightGBM loses under the held-out splits (overfits)

## Contradiction layer

Lexical recall is blind to present-but-contradicted claims (high overlap, one fact flipped) - the failure mode on contrastive corpora. Two deterministic detectors recover it, both fuzzy-gated so they stay inert on absent-content negatives.

- **Aligned value-conflict** (`conflict_n`, `conflict_flag`, `num_edit_mag`) - claim anchors that align with the chunk on key/context but disagree in value (`100 VAC` vs `240 VAC`, `GPT-4` vs `GPT-3`); shipped as a classifier feature, free on DeLaval (fires on 0.3%)
- **WordNet antonym-flip** (`wn_antonym_flip`) - a claim content-token whose WordNet antonym sits in the best chunk while the token itself is absent (opposite-direction substitution); a deterministic population lexicon at the word-sense level, broader than a hand-curated list it replaced - fires on ~32% of VitaminC REFUTES vs 3% SUPPORTS and ~1.8% of DeLaval, active exactly where the contrastive negative lives
- **Why it holds both** - each corpus's mechanism rides on features that go quiet on the other: `same_lang`/`is_en` carry DeLaval's cross-lingual signal and are constant on English VitaminC; the contradiction features carry VitaminC's signal and are ~0 on DeLaval's absent-content negatives

## Triage flag

`semantic_candidate` = high overlap AND (value-conflict OR WordNet antonym-flip) - a deterministic label, not a verdict, marking claims a downstream semantic classifier should adjudicate. No NLI is run here.

- **Coverage / precision** - flags 23% of VitaminC at 92% REFUTES precision (50% base rate)
- **Error concentration** - holds 3× the base rate of the model's missed-hallucinations
- **Zero classifier cost** - a separate output; does not perturb the verdict

## Performance

One logistic, joint DeLaval (2752) + VitaminC (800, SUPPORTS vs REFUTES), grouped CV, per-corpus-tuned threshold (one model, domain-calibrated operating point). macro-F1.

| configuration | DeLaval | VitaminC |
|---|---|---|
| lexical base | 0.832 | 0.555 |
| shipped (value-conflict + WordNet antonym) | 0.825 | 0.661 |

- **Hold, not collapse** - VitaminC rises 0.555 → 0.661 while DeLaval moves 0.832 → 0.825 (−0.007, within LOSO noise)
- **Triage flag** - flags 26% of VitaminC at 90% REFUTES precision (50% base rate), routing the contradiction region to a future semantic stage
- **WordNet replaced a curated antonym list** - broader word-sense coverage; aligned value-conflict is the free component (near-zero DeLaval cost)
- **Replicates across data growth** - the hold-vs-collapse pattern held as the gold grew 1260 → 2631 → 2752 (VitaminC +0.10-0.13, DeLaval −0.01 every run); absolutes shift slightly on the larger, more language-diverse set
- **Pure-lexical ceiling reached** - a round-3 deep-research sweep of parser-free structural mechanisms (role reversal, scoped negation, quantifier mismatch) found all three absent at usable density in VitaminC; the remaining residual is irreducibly semantic and routed to the (deferred) heavy stage via the triage flag

## Throughput and footprint

- **~165 ms/claim** feature build, single-thread CPU on the 2752 gold; MT now leads at 86 ms amortised (~370 ms per translated claim, 23% of claims), recall 69 ms (BM25 ×2), intrinsic + WordNet lookup ~7 ms
- **5s** one-time cold start (load SaT + first MT model); classifier fit/score negligible
- **CPU-only, torch-free** - no GPU, no semantic model in the verdict path; argos MT models ~80-100MB loaded on demand, SaT-3l small, logistic in KB
- **Dependencies** - lingua-py, argos-translate (CTranslate2), wtpsplit (ONNX), rapidfuzz, scikit-learn, and nltk + WordNet (~10MB, English; claims are MT'd to English) for the antonym lexicon

## Limitations

- **Irreducibly semantic residual** - VitaminC's qualitative REFUTES with no anchor and no antonym still need the semantic classifier the triage flag routes to; a general single-token-substitution detector cannot help (it cannot tell a synonym restatement from a fact-edit - that distinction is itself semantic), so deterministic lexical features bridge the contradiction gap only as far as surface opposition allows
- **Recall degenerates on single-sentence evidence** - IDF-over-corpus recall collapses to ~0 when the evidence is one chunk (VitaminC); the contradiction features are gated on fuzzy overlap instead, which stays live
- **Data-bound tail** - the source contexts grew to 69 (from ~22), stabilising leave-one-source-out; the residual is the small language tail (da/pt/de at n=8-18) where leave-one-language-out dips, so more labelled data in those languages is the prerequisite, not a cleverer model

## Implementation

The grounder is consolidated into the library's existing grounding framework (`src/stellars_claude_code_plugins/document_processing/`) as a config-selectable lexical mode with three effort tiers, each shipping its own frozen-weight manifold fit on the joint DeLaval + VitaminC gold. One new module, one verbatim MT copy, one test file; surgical hooks into `ground()` and config.

- **Module** - `document_processing/lexical.py` holds the consolidated feature pipeline (word/char-ngram recall, fuzzy, anchors, specificity, value-conflict, language detection, WordNet antonym-flip, MT recall), reusing `grounding._tokenize`, `chunking.recursive_chunk` and the `entity_check` helpers rather than duplicating them; the torch-free MT bridge is copied verbatim to `lexical_mt.py`
- **Effort tiers** - one parameterised feature path selected by the `lexical_effort` config knob, ordered by external-model cost: **low** (11 features, core install only - word + char-ngram recall, fuzzy, anchors, specificity, value-conflict), **medium** (14 - low + lingua language detection and WordNet antonym-flip), **high** (16 - medium + argos MT translate-then-recall, the full cross-lingual stack); each tier loads only its own ordered feature subset
- **Verdict head** - a per-tier frozen-weight logistic `LexicalVerdict` (intercept + per-feature weights + feature order + threshold + 300/0.1 chunk operating point) persisted in config under `calibration.lexical_manifolds.<tier>` and applied at inference as a dot-product through a sigmoid; no scikit-learn at runtime, sklearn imported only on the `fit_lexical_manifold` training path
- **Engine reuse** - lexical mode activates on the existing `calibration.engine: lexical` string once `lexical_manifolds` are present; the bundled config ships all three manifolds live but keeps `engine: deterministic`, so the out-of-box verdict is unchanged and existing deterministic guarantees hold (opt-in via `engine: lexical`, exactly what `train-lexical` writes); the bambi `calibrated` engine is orthogonal and untouched
- **MT as the high tier** - cross-lingual recall (`r1_mt`, `r1_best`) runs through the torch-free `lexical_mt.py` (CTranslate2 int8 + wtpsplit SaT), the highest-cost tier; the high manifold collapses `r1_direct` (−2.31) and trusts the translate-then-recall pair (+2.64 / +2.66) on the non-English tail
- **Joint training** - the three manifolds are fit on DeLaval 2752 gold plus VitaminC dev (SUPPORTS→1, REFUTES→0, NEI dropped), so every tier holds both the omission-type (DeLaval) and contrastive (VitaminC) negatives
- **Training CLI** - `document-processing train-lexical --effort {low,medium,high} --data PATH [--data ...]` fits one tier from one or more labelled datasets and writes the frozen weights into config via the same `lexical.py` extraction; `--data` is repeatable and concatenated; `--help` documents the dataset contract (columns `claim`, `source_text`, `label` 1=supported/0=hallucination, optional `lang`; parquet or jsonl) and enforces a floor of >= 200 rows with >= 40 of each class, rejecting smaller sets with a clear error; client data is read in place and never copied or committed
- **Dependency extra** - the MT bridge plus lingua, nltk/WordNet, scikit-learn and pyarrow ship as an optional `[grounding-lexical]` extra (rank-bm25 and rapidfuzz are already core); low runs on the core install, medium/high skip-with-warning any missing-dep feature at inference (neutral 0.0) and hard-error in the training path
- **Grounding hook** - `ground()` gains one resolver (`_config_lexical_verdict`) plus one branch; `ground_batch` extends its adaptive_gap guard; the deterministic and calibrated paths are unchanged
- **Test** - `tests/test_lexical_grounding.py` exercises a tier end to end through the public `ground()` API plus the shipped manifold on VitaminC (downloaded on demand, skip on no network) and DeLaval (skip-if-absent, parquet git-ignored, client data never committed)

| tier | features | external deps |
|---|---|---|
| low | 11 | none (core install) |
| medium | 14 | lingua + nltk/WordNet |
| high | 16 | + argos MT (CTranslate2 + wtpsplit) |
