# Lexical cross-lingual grounder - final design

The deployed grounder classifies each claim as supported or hallucination using only lexical signals plus a torch-free machine-translation bridge - no semantic model in the verdict path. A deterministic contradiction layer extends it to hold on a second, contrastive corpus (VitaminC) and emits a triage flag marking claims for a future semantic stage.

## Claim extraction (upstream)

The grounder scores a claim that an upstream stage has already pulled from the agent's answer; it is extraction-agnostic and takes the claim text however it was produced. Extraction is two steps - sentence/claim segmentation, then filter + classify - and the solution moved from a pure-regex baseline to a neural segmenter, with an optional LLM extractor in production:

- **Sentence / claim segmentation** - originally a regex sentence split; the research replaced it with **SaT** (`sat-3l-sm`), a torch-free neural segmenter, which beat the regex split on the held-out claims (macro-F1 up, LLM-as-judge 15/1) and is the preferred segmenter. It is served as a native OpenVINO INT8 model (`document_processing.sat`, LATENCY hint, no onnxruntime) and also drives the MT bridge's sentence splitting (`lexical_mt.py`), where it replaced argos's torch-based stanza segmenter - the stack's last torch dependency. The regex split (`document_processing/extract.py` `_SENT_SPLIT_RE`) remains the fully-offline fallback
- **Filter + classify (deterministic)** - the `extract.py` heuristic (exposed as `document-processing extract-claims`): strip markdown and citation furniture, drop hedges and verb-less fragments, classify survivors into quote / numeric / attribution / assertion. No model
- **LLM extractor (optional, production)** - a language model pulls the load-bearing claims from the answer when available, handling phrasing the heuristic splits poorly; the deterministic path remains the fallback

So the historical pipeline was regex-only segmentation + the deterministic filter; the current solution uses the SaT neural segmenter (with the optional LLM extractor in production). The grounding research and the gold labels were built on this deterministic path - the `claude -p` Haiku/Sonnet model is the labelling judge, not the extractor.

## Pipeline

Nine deterministic stages, claim in → verdict + triage flag out.

- **Language detection** - lingua-py per claim and per best chunk; a `same_lang` flag marks whether the source carries a chunk in the claim's language
- **Conditional MT** - argos-translate (CTranslate2 int8, CPU) + a native OpenVINO INT8 SaT sentence splitter (`document_processing.sat`, LATENCY hint, no onnxruntime), torch-free; fires only on heterogeneous claims (non-English claim vs English source), ~23% of the live 2752 gold (the language tail grew to ten+ languages)
- **Chunking** - recursive, 300-char chunks, 0.1 overlap (AUC-validated operating point)
- **Lexical recall** - BM25-best-chunk IDF-weighted token recall, computed direct (`r1_direct`) and translate-then-recall (`r1_mt`); the model learns which to trust. The in-context IDF is soft-floored with a `wordfreq` background rarity (`w = max(in-context, λ·background)`, λ=0.5) so recall stays honest on a single-chunk source, where the in-context IDF would otherwise collapse to a constant
- **Distinctive-content coverage** - `unmatched_rarity` / `max_unmatched`: the background-rarity-weighted fraction of the claim's content tokens absent from the best chunk; separates "distinctive token present" from "only common tokens overlap", the signal aggregate recall cannot isolate
- **Supporting lexical signals** - char-ngram recall, rapidfuzz partial-ratio, anchor recall + mismatch (numbers/IDs, language-invariant), oracle-chunk and top-k consensus
- **Claim-intrinsic specificity** - anchor density from the claim alone (evidence-independent → cannot memorise the documents); the strongest generalisation feature
- **Contradiction layer** - aligned value-conflict + WordNet antonym-flip (below)
- **Verdict head** - class-balanced logistic over the feature set; LightGBM loses under the held-out splits (overfits)

## Contradiction layer

Lexical recall is blind to present-but-contradicted claims (high overlap, one fact flipped) - the failure mode on contrastive corpora. Two deterministic detectors recover it, both fuzzy-gated so they stay inert on absent-content negatives.

- **Aligned value-conflict** (`conflict_n`, `conflict_flag`, `num_edit_mag`) - claim anchors that align with the chunk on key/context but disagree in value (`100 VAC` vs `240 VAC`, `GPT-4` vs `GPT-3`); shipped as a classifier feature, free on private RAG (fires on 0.3%)
- **WordNet antonym-flip** (`wn_antonym_flip`) - a claim content-token whose WordNet antonym sits in the best chunk while the token itself is absent (opposite-direction substitution); a deterministic population lexicon at the word-sense level, broader than a hand-curated list it replaced - fires on ~32% of VitaminC REFUTES vs 3% SUPPORTS and ~1.8% of private RAG, active exactly where the contrastive negative lives
- **Why it holds both** - each corpus's mechanism rides on features that go quiet on the other: `same_lang`/`is_en` carry private RAG's cross-lingual signal and are constant on English VitaminC; the contradiction features carry VitaminC's signal and are ~0 on private RAG's absent-content negatives

## Triage flag

`semantic_candidate` = high overlap AND (value-conflict OR WordNet antonym-flip) - a deterministic label, not a verdict, marking claims a downstream semantic classifier should adjudicate. No NLI is run here.

- **Coverage / precision** - flags 23% of VitaminC at 92% REFUTES precision (50% base rate)
- **Error concentration** - holds 3× the base rate of the model's missed-hallucinations
- **Zero classifier cost** - a separate output; does not perturb the verdict

## Performance

One logistic, joint private RAG (2752) + VitaminC (800, SUPPORTS vs REFUTES), grouped CV, per-corpus-tuned threshold (one model, domain-calibrated operating point). macro-F1.

| configuration | private RAG | VitaminC |
|---|---|---|
| lexical base | 0.832 | 0.555 |
| value-conflict + WordNet antonym | 0.825 | 0.661 |
| shipped (+ length-robust recall + distinctive-content + short-source aug) | 0.817 | 0.691 |

- **Hold, not collapse** - VitaminC rises 0.555 → 0.691 while private RAG moves 0.832 → 0.817 (−0.015 total, within LOSO noise); the short-source fix (below) added the last +0.030 on VitaminC
- **Short-source regime fixed** - a 12-case probe of 1-line-source inputs rose 10/12 → 11/12: a `wordfreq` background-IDF recall floor (revives recall where the in-context IDF collapses on a single chunk), the `unmatched_rarity` distinctive-content feature, and truncation-derived short-source training rows; the fix also lifts the single-sentence VitaminC corpus (+0.030), the same degenerate regime
- **Triage flag** - flags 26% of VitaminC at 90% REFUTES precision (50% base rate), routing the contradiction region to a future semantic stage
- **WordNet replaced a curated antonym list** - broader word-sense coverage; aligned value-conflict is the free component (near-zero private RAG cost)
- **Replicates across data growth** - the hold-vs-collapse pattern held as the gold grew 1260 → 2631 → 2752 (VitaminC +0.10-0.13, private RAG −0.01 every run); absolutes shift slightly on the larger, more language-diverse set
- **Pure-lexical ceiling reached** - a round-3 deep-research sweep of parser-free structural mechanisms (role reversal, scoped negation, quantifier mismatch) found all three absent at usable density in VitaminC; the remaining residual is irreducibly semantic and routed to the (deferred) heavy stage via the triage flag
- **Cross-lingual hallucination detection (Round 9)** - the macro-F1 table above is English-dominant and concealed a blind spot. Rebuilding the gold without the anglocentric claim extractor (gold v2, 5,912 rows) exposed the shipped HIGH manifold as English-only: non-English hallucination recall (TNR) 0.000 vs English 0.710, confirming 1,339 of 1,343 non-English claims and catching 0 of 139 non-English hallucinations. The shipped weights already rank non-English hallucinations below support (via the MT-bridge `r1_mt`) - they just lacked a cut that used it, because the global 0.40 threshold is calibrated to the 77%-English bulk. Fix: a language-conditional decision threshold (`threshold_non_en: 0.70`, keyed off the existing `is_en` feature) lifts non-English TNR to 0.748 at support recall 0.761, generalising per-language (es 0.80 / fr 0.71 / nb 0.71 / pt 0.65 / sv 0.93), with English byte-identical (weights unchanged, all e2e tests pass). One config line, no weight change, no new feature
- **Synthetic cross-lingual negatives (Round 10)** - the language-conditional cut is a patch over English-trained weights; the durable fix is to give the weights a real multilingual negative population. `synth_mt.py` translates English negatives into 9 languages via `claude -p` (Haiku translate, Sonnet fidelity-verify, ~7 of 1,060 drifted translations dropped), keeping the English evidence and marking every row synthetic with provenance (train-only). With 1,053 verified synthetic negatives a SINGLE global threshold reaches real-slice non-English TNR 0.683 (vs 0.158 for the same retrain without synthetic, 0.000 shipped), and it generalises to unseen languages - leave-one-language-out at the global cut es 0.71 / fr 0.79 / pt 0.60 / nb 0.71 / sv 0.71. The signal now lives in the weights, so `threshold_non_en` can be retired. Round 11 doubled the synthetic set to 2,119 (TNR 0.683 → 0.712, diminishing) and installed the de back-translation bridge
- **Ship the durable fix, single global cut (Round 12)** - the reconciliation: keep the synthetic-retrained weights but raise the single global cut to 0.50 (swept against the two English e2e precision tests through the real pipeline - 0.45 and below over-confirm, 0.50 clears). At that operating point real gold v2 gives gold_en F1 0.803 → 0.810 (English *up*, e2e green), non-English TNR 0.78 at TPR 0.66, VitaminC F1 0.695 → 0.699 and articles 0.797 → 0.816 both holding. Shipped: the HIGH manifold block is the synthetic-retrained weights at `threshold: 0.5` with `threshold_non_en` removed - one honest threshold for both regimes, the cross-lingual signal carried by the weights, not a language-special-cased cut

## Throughput and footprint

- **~165 ms/claim** feature build, single-thread CPU on the 2752 gold; MT now leads at 86 ms amortised (~370 ms per translated claim, 23% of claims), recall 69 ms (BM25 ×2), intrinsic + WordNet lookup ~7 ms
- **5s** one-time cold start (load SaT + first MT model); classifier fit/score negligible
- **CPU-only, torch-free** - no GPU, no semantic model in the verdict path; argos MT models ~80-100MB loaded on demand, SaT-3l small, logistic in KB
- **Dependencies** - lingua-py, argos-translate (CTranslate2), SaT (native OpenVINO INT8 + tokenizers), rapidfuzz, scikit-learn, and nltk + WordNet (~10MB, English; claims are MT'd to English) for the antonym lexicon

## Limitations

- **Irreducibly semantic residual** - VitaminC's qualitative REFUTES with no anchor and no antonym still need the semantic classifier the triage flag routes to; a general single-token-substitution detector cannot help (it cannot tell a synonym restatement from a fact-edit - that distinction is itself semantic), so deterministic lexical features bridge the contradiction gap only as far as surface opposition allows
- **Single-sentence recall, mitigated not perfect** - the in-context IDF still degenerates on a one-chunk source, now soft-floored by the `wordfreq` background rarity so recall and the distinctive-content feature stay honest; the contradiction features remain fuzzy-gated as a second path
- **Spelled-out-number value-conflict** - the residual short-source miss: "fifty hectares" vs "twelve hectares" reads as a near-match because the value-conflict feature is digit-based; spelled-number canonicalisation is deferred (round-4 H2, low coverage)
- **Data-bound tail** - the source contexts grew to 69 (from ~22), stabilising leave-one-source-out; the residual is the small language tail (da/pt/de at n=8-18) where leave-one-language-out dips, so more labelled data in those languages is the prerequisite, not a cleverer model
- **Cross-lingual signal now lives in the shipped weights (Round 12)** - the Round 9 fix was a per-language decision threshold over English-trained weights, a fast patch that worked because the MT-bridge `r1_mt` ranking transfers. Rounds 10-11 manufactured a real multilingual negative population (2,119 `claude -p`-translated, fidelity-verified synthetic negatives) and Round 12 ships the retrain: the synthetic-retrained weights at a single global cut 0.50 keep the English e2e precision tests green (English F1 *up* 0.803 → 0.810), catch non-English at TNR 0.78, and hold VitaminC and articles, so `threshold_non_en` is retired. de back-translation (`translate-de_en`) is installed - the German bridge fires at inference; the honest eval slice still carries no de negatives, so de remains a train-side correctness claim

## Implementation

The grounder is consolidated into the library's existing grounding framework (`src/stellars_claude_code_plugins/document_processing/`) as the default **lexical mode**, exposed to the user as one knob - a solution tier (low / medium / high). Each tier is an indivisible bundle of algorithms plus the manifold trained for exactly that bundle, fit on the joint private RAG + VitaminC gold. One new module, one verbatim MT copy, one test file; surgical hooks into `ground()` and config.

- **Mode, not engine** - the public knob is `calibration.mode` (`lexical` default, `semantic` reserved for the heavy stage); `load_calibration_from_config` resolves it to an internal verdict-head selector. The deterministic cascade and the bambi calibrated head are internal heads reachable only via an explicit `engine:` override or the `calibrated_verdict=` API - the user never selects an algorithm, only a tier
- **Solution tiers** - one parameterised feature path selected by the `lexical_effort` knob, ordered by cost: **low** (13 features - word + char-ngram recall, fuzzy, anchors, specificity, value-conflict, distinctive-content), **medium** (16 - low + lingua language detection and WordNet antonym-flip), **high** (18 - medium + argos MT translate-then-recall, the full cross-lingual stack); each tier loads only its own ordered feature subset and the manifold trained against it
- **Short-source robustness** - the recall features soft-floor the in-context IDF with a `wordfreq` background rarity (revives recall when a single-chunk source collapses the in-context weights), and `unmatched_rarity` / `max_unmatched` isolate distinctive-content coverage; both are in every tier. The manifolds are trained with truncation-derived short-source rows (below) so they read the degenerate regime correctly
- **Module** - `document_processing/lexical.py` holds the consolidated feature pipeline, reusing `grounding._tokenize`, `chunking.recursive_chunk` and the `entity_check` helpers rather than duplicating them; the torch-free MT bridge is copied verbatim to `lexical_mt.py`
- **Verdict head** - a per-tier frozen-weight logistic `LexicalVerdict` (intercept + per-feature weights + feature order + threshold + optional `threshold_non_en` + 300/0.1 chunk operating point) persisted in config under `calibration.lexical_manifolds.<tier>` and applied at inference as a dot-product through a sigmoid; `threshold_for(feat)` picks the English vs non-English cut by the `is_en` feature (absent on LOW -> English cut, full back-compat); no scikit-learn at runtime, sklearn imported only on the `fit_lexical_manifold` training path
- **MT as the high tier** - cross-lingual recall (`r1_mt`, `r1_best`) runs through the torch-free `lexical_mt.py` (CTranslate2 int8 + native-OpenVINO-INT8 SaT), the highest-cost tier; the synthetic-retrained high manifold collapses `r1_direct` (−3.72) and trusts the translate-then-recall pair (`r1_mt` +1.37 / `r1_best` +4.08) on the non-English tail, with a conservative intercept (−4.92) so one global cut holds both regimes
- **Joint training + short-source augmentation** - the three manifolds are fit on private RAG 2752 gold plus VitaminC dev (SUPPORTS→1, REFUTES→0, NEI dropped), so every tier holds both the omission-type (private RAG) and contrastive (VitaminC) negatives; the fit also adds truncation-derived short-source rows (each source cut to one sentence - the max-overlap evidence sentence for supported, a low-overlap one for hallucination; label inherited, source length the only change) so the manifold learns the degenerate single-chunk regime without a hand-set threshold
- **Training CLI** - `document-processing train-lexical --effort {low,medium,high} --data PATH [--data ...]` fits one tier from one or more labelled datasets and writes the frozen weights into config via the same `lexical.py` extraction; `--data` is repeatable and concatenated; the short-source augmentation is applied automatically; `--help` documents the dataset contract (columns `claim`, `source_text`, `label` 1=supported/0=hallucination, optional `lang`; parquet or jsonl) and enforces a floor of >= 200 rows with >= 40 of each class, rejecting smaller sets with a clear error; client data is read in place and never copied or committed
- **Dependencies in core** - all tier deps ship with the package (lingua, nltk/WordNet, scikit-learn for the fit path, pyarrow, wordfreq for the background rarity, and the MT stack - argos / CTranslate2 / openvino + tokenizers for the SaT segmenter / sentencepiece / sacremoses / subword-nmt); there is no optional extra and no onnxruntime, so all three tiers work out of the box. Each feature still neutralises (0.0) with a warning if its dep is somehow unimportable, and the training path hard-errors
- **Grounding hook** - `ground()` gains one resolver (`_config_lexical_verdict`) plus one branch; `ground_batch` extends its adaptive_gap guard; the deterministic and calibrated paths are unchanged
- **Test** - `tests/test_lexical_grounding.py` exercises a tier end to end through the public `ground()` API plus the shipped manifold on VitaminC (downloaded on demand, skip on no network) and private RAG (skip-if-absent, parquet git-ignored, client data never committed)

| tier | features | algorithm bundle (all deps ship in core) |
|---|---|---|
| low | 13 | recall (wordfreq-floored), char-ngram, fuzzy, anchors, specificity, value-conflict, distinctive-content |
| medium | 16 | low + lingua language id + nltk/WordNet antonym-flip |
| high | 18 | medium + argos MT translate-then-recall (CTranslate2 + OpenVINO-INT8 SaT) |
