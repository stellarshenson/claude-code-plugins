# Lexical cross-lingual grounder - final design

The deployed grounder classifies each claim as supported or hallucination using only lexical signals plus a torch-free machine-translation bridge - no semantic model in the verdict path. A deterministic contradiction layer extends it to hold on a second, contrastive corpus (VitaminC) and emits a triage flag marking claims for a future semantic stage.

## Pipeline

Eight deterministic stages, claim in → verdict + triage flag out.

- **Language detection** - lingua-py per claim and per best chunk; a `same_lang` flag marks whether the source carries a chunk in the claim's language
- **Conditional MT** - argos-translate (CTranslate2 int8, CPU) + wtpsplit SaT sentence splitter (ONNX), torch-free; fires only on heterogeneous claims (non-English claim vs English source), ~14% of the gold
- **Chunking** - recursive, 300-char chunks, 0.1 overlap (AUC-validated operating point)
- **Lexical recall** - BM25-best-chunk IDF-weighted token recall, computed direct (`r1_direct`) and translate-then-recall (`r1_mt`); the model learns which to trust
- **Supporting lexical signals** - char-ngram recall, rapidfuzz partial-ratio, anchor recall + mismatch (numbers/IDs, language-invariant), oracle-chunk and top-k consensus
- **Claim-intrinsic specificity** - anchor density from the claim alone (evidence-independent → cannot memorise the documents); the strongest generalisation feature
- **Contradiction layer** - aligned value-conflict + WordNet antonym-flip (below)
- **Verdict head** - class-balanced logistic over the feature set; LightGBM loses under the held-out splits (overfits)

## Contradiction layer

Lexical recall is blind to present-but-contradicted claims (high overlap, one fact flipped) - the failure mode on contrastive corpora. Two deterministic detectors recover it, both fuzzy-gated so they stay inert on absent-content negatives.

- **Aligned value-conflict** (`conflict_n`, `conflict_flag`, `num_edit_mag`) - claim anchors that align with the chunk on key/context but disagree in value (`100 VAC` vs `240 VAC`, `GPT-4` vs `GPT-3`); shipped as a classifier feature, free on DeLaval (fires on 0.3%)
- **WordNet antonym-flip** (`wn_antonym_flip`) - a claim content-token whose WordNet antonym sits in the best chunk while the token itself is absent (opposite-direction substitution); a deterministic population lexicon at the word-sense level, broader than a hand-curated list it replaced - fires on ~32% of VitaminC REFUTES vs 3% SUPPORTS and ~0.8% of DeLaval, active exactly where the contrastive negative lives
- **Why it holds both** - each corpus's mechanism rides on features that go quiet on the other: `same_lang`/`is_en` carry DeLaval's cross-lingual signal and are constant on English VitaminC; the contradiction features carry VitaminC's signal and are ~0 on DeLaval's absent-content negatives

## Triage flag

`semantic_candidate` = high overlap AND (value-conflict OR WordNet antonym-flip) - a deterministic label, not a verdict, marking claims a downstream semantic classifier should adjudicate. No NLI is run here.

- **Coverage / precision** - flags 23% of VitaminC at 92% REFUTES precision (50% base rate)
- **Error concentration** - holds 3× the base rate of the model's missed-hallucinations
- **Zero classifier cost** - a separate output; does not perturb the verdict

## Performance

One logistic, joint DeLaval (1260) + VitaminC (800, SUPPORTS vs REFUTES), grouped CV, per-corpus-tuned threshold (one model, domain-calibrated operating point). macro-F1.

| configuration | DeLaval | VitaminC |
|---|---|---|
| lexical base | 0.851 | 0.532 |
| shipped (value-conflict + WordNet antonym) | 0.842 | 0.685 |
| DeLaval-only reference | 0.844 (LOSO) | - |

- **Hold, not collapse** - VitaminC rises 0.532 → 0.685 while DeLaval moves 0.851 → 0.842 (−0.009, within LOSO noise on 22 sources)
- **Triage flag** - flags 26% of VitaminC at 90% REFUTES precision (50% base rate), routing the contradiction region to a future semantic stage
- **WordNet replaced a curated antonym list** - broader word-sense coverage lifted VitaminC from 0.673 (hand list) to 0.685 at equal DeLaval cost; aligned value-conflict is the free component (zero DeLaval cost)

## Throughput and footprint

- **~99 ms/claim** feature build, single-thread CPU; recall dominates at 63 ms (BM25 ×2), MT 27 ms amortised (191 ms per translated claim, 14% of claims), intrinsic + WordNet lookup ~7 ms
- **5s** one-time cold start (load SaT + first MT model); classifier fit/score negligible
- **CPU-only, torch-free** - no GPU, no semantic model in the verdict path; argos MT models ~80-100MB loaded on demand, SaT-3l small, logistic in KB
- **Dependencies** - lingua-py, argos-translate (CTranslate2), wtpsplit (ONNX), rapidfuzz, wordfreq, scikit-learn, and nltk + WordNet (~10MB, English; claims are MT'd to English) for the antonym lexicon

## Limitations

- **Irreducibly semantic residual** - VitaminC's qualitative REFUTES with no anchor and no antonym still need the semantic classifier the triage flag routes to; a general single-token-substitution detector cannot help (it cannot tell a synonym restatement from a fact-edit - that distinction is itself semantic), so deterministic lexical features bridge the contradiction gap only as far as surface opposition allows
- **Recall degenerates on single-sentence evidence** - IDF-over-corpus recall collapses to ~0 when the evidence is one chunk (VitaminC); the contradiction features are gated on fuzzy overlap instead, which stays live
- **Data-bound tail** - hallucination detection on DeLaval is capped by ~22 source contexts and the es/pt tail (n=5-6); more contexts and negatives are the prerequisite, not a cleverer model
