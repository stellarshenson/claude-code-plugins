# Hypothesis: improving the document-processing grounding tool

## Context

The three-layer grounding tool (regex + Levenshtein + BM25) plus optional
fourth semantic layer (multilingual-e5-small + FAISS) was shipped in
v1.3.26. End-to-end test on Liu 2023 "Lost in the Middle" paper (14
claims, 18 pages):

- 10/14 CONFIRMED
- 4 UNCONFIRMED — of which **2 were fabricated** (correctly rejected) and
  **2 were legitimate distant paraphrases** (false negatives at threshold
  0.85 semantic cosine)
- Discrimination gap between real distant paraphrases (0.838-0.840) and
  fabrications (0.825-0.842) is only 0.02 cosine — **tight**

## Observed weaknesses

1. **Tight semantic discrimination** — small model (118M E5) cannot
   separate genuine distant paraphrase from plausible fabrication by
   score alone.
2. **False negatives on legitimate paraphrases** — threshold 0.85 is too
   strict for E5-small; lower threshold would let fabrications through.
3. **Model-dependent thresholds** — 0.85 works for E5; would be wrong
   for mmBERT, BGE, or any future swap. Non-portable.
4. **Semantic-only false positives** — semantic fires 0.85+ on topical
   passages with zero lexical overlap (0 BM25, low fuzzy). Current tool
   accepts. Pattern looks like hallucination.
5. **Numeric / named-entity claims pass without value check** — a claim
   "42 nodes" against a source saying "12 nodes" scores high on all
   layers but the claim is false.
6. **Chunk-boundary miss** — claim supported by two sentences split
   across a chunk boundary can be missed.
7. **Multilingual promise unverified** — default is a multilingual
   model, but no non-English test exists.

## Hypothesis

Combining the core improvements below will:

- Reduce the false-negative rate (legitimate paraphrases incorrectly
  UNCONFIRMED) by > 50%.
- Reduce the false-positive rate (fabrications incorrectly CONFIRMED) to
  near zero on number / named-entity claims.
- Make thresholds portable across embedding models (no hand-tuning per
  model).

Improvements are numbered H1-H10 and grouped by priority tier.

### Tier 1 (ship together, highest impact)

### H1. Top-K semantic + cross-layer agreement score

**Claim:** a score that rewards agreement across exact / fuzzy / bm25 /
semantic layers discriminates real-but-distant paraphrase from
fabrication better than the current max-of-layers score. Returning top-3
semantic hits instead of top-1 gives the agent more pointers when
confidence is marginal.

**Predicted effect:** on the Liu test, claims 9 and 10 (legitimate
distant paraphrases currently UNCONFIRMED) should light up at least one
lexical layer weakly; agreement score will push them above threshold.
Claims 13 and 14 (fabrications) have only semantic firing — agreement
score keeps them UNCONFIRMED. Gap between real and fake widens from
0.02 to ≥ 0.10.

### H2. Numeric + named-entity mismatch detection → CONTRADICTED

**Claim:** for any claim containing a number, date, or named entity, the
tool extracts those values from the claim AND from the winning passage.
Mismatches downgrade the verdict to CONTRADICTED regardless of other
scores.

**Predicted effect:** catches fabrication class where scores are high
but critical values are wrong ("42 nodes" vs "12 nodes", "H100" vs
"A100"). Current tool passes these silently.

### H3. Self-calibrated per-corpus thresholds

**Claim:** at index time, sample pairwise cosine distribution of the
corpus chunks. Thresholds become percentile-based — top 2% of the
corpus distribution for "semantic confirm" rather than an absolute 0.85
number.

**Predicted effect:** swapping embedding models no longer requires
re-tuning thresholds. Each model auto-calibrates to its own
distribution. The Liu test with mmBERT (where every score was 0.95+)
would correctly leave fabrications UNCONFIRMED because top 2% within
the mmBERT distribution is actually 0.995+.

### Tier 2 (noise reduction + recall)

### H4. BM25-guided semantic re-ranking

**Claim:** most genuine semantic hits have at least some lexical
overlap with the claim. Taking the top-20 BM25 candidates and
re-ranking THEM semantically (instead of scanning all chunks) reduces
false positives from semantic on long sources while preserving recall
on paraphrases.

**Predicted effect:** on long documents (> 10K tokens), fewer unrelated
passages enter semantic contention. Fabrications that rely on semantic
topical similarity to noise passages no longer win top-1. Measured via
fewer UNCONFIRMED fabrications creeping into CONFIRMED on a larger
corpus test.

### H5. Chunk-boundary expansion on borderline claims

**Claim:** a claim supported by two sentences that span a chunk
boundary can be missed. When the best semantic hit scores within 0.05
of the threshold, expand the window to include the neighbouring chunks
(prev + next), re-embed the merged context, re-rank.

**Predicted effect:** reduces recall loss on boundary-straddling claims
without adding cost to the clear-cut cases. Only triggers on borderline
(~5-15% of claims).

### Tier 3 (safety net + portability verification)

### H6. Multilingual smoke test

**Claim:** the default model is multilingual-e5-small but no
non-English source has been tested. A tiny bilingual CI test
(English claim → French passage about the same topic) proves the
multilingual promise and catches regressions on future model-default
changes.

**Predicted effect:** catches silent breakages when the default model
is swapped to a non-multilingual one. No runtime impact.

### H7. Self-score sanity check

**Claim:** compute the claim's cosine similarity against a synthetic
"perfect" passage (the claim itself wrapped in `passage: `). That
self-score is the upper bound for this claim. Report `semantic_score /
self_score` as a calibrated ratio; below 0.85 of self-score = weak
match.

**Predicted effect:** catches pathological cases where semantic score
is 0.90 but the claim's self-score is 0.98 — meaning the match is 92%
of maximum, still usable. Cases where semantic is 0.80 but self-score
is 0.82 — meaning match is near-maximum, high confidence.

### Tier 4 (skill-level, no tool change)

### H8. Skill rule: "agreement beats magnitude"

**Claim:** update `validate-document/SKILL.md` to tell the agent:
"confidence = agreement across layers, NOT peak score on any single
layer." A claim with semantic 0.85, fuzzy 0, bm25 0 is LESS confirmed
than a claim with semantic 0.75, fuzzy 0.65, bm25 0.45.

**Predicted effect:** agents routinely over-trust semantic-only hits.
Making the rule explicit forces them to read the pointer when only
semantic fires.

### H9. Skill rule: "contradiction flag is the final word"

**Claim:** once H2 is implemented, the skill must explicitly state
that `numeric_mismatches` or `entity_mismatches` override any positive
verdict. CONTRADICTED is not a suggestion.

**Predicted effect:** agents cannot be tempted to promote a
CONTRADICTED claim to CONFIRMED even when three other layers fire.
Prevents "the scores say yes but the numbers say no" errors.

### H10. Skill rule: "recommend semantic on struggle"

Already in the skill but under-enforced. If the three-layer pass
leaves > 25% UNCONFIRMED OR any claim in the 0.5-0.85 fuzzy + 0.2-0.5
BM25 "almost grounded" zone, the agent must offer the user the option
to enable semantic (with explicit consent). Not silent fallback.

**Predicted effect:** users who declined semantic but would benefit get
a second chance when the data warrants it. No auto-enable.

### Tier 5 (portability rescue, added Iter 5)

### H11. Gap-detection adaptive agreement threshold

**Problem restated after Iter 4:** H3's percentile-based semantic
threshold was falsified for models intrinsically weaker on the target
corpus. mpnet-base-v2 on Liu produces `semantic_ratio` 0.48-0.57 for
real paraphrases versus 0.87+ on E5-small. No absolute threshold (raw
cosine OR ratio) makes mpnet's classifications match E5's.

However, the RANK ORDERING of claims by `agreement_score` IS stable
across models: both E5 and mpnet rank Liu real paraphrases ABOVE Liu
fabricated claims (post entity-presence penalty). The discriminator
that varies is the *absolute scale*, not the *relative positioning*.

**Claim:** a per-batch adaptive threshold chosen at the LARGEST GAP in
the sorted distribution of non-exact / non-fuzzy / non-bm25
`agreement_score` values will place itself in the real-vs-fake boundary
regardless of the model's absolute scale. Classifications become
rank-based and model-agnostic.

**Predicted effect:** on the Liu 14-claim portability test, E5 and
mpnet produce IDENTICAL match_types for all 14 claims (portability_pass
= 1). On single-claim `ground` (no batch), fall back to the absolute
`agreement_threshold` parameter.

**Falsifier:** the hypothesis is FALSE if, after H11 is implemented,
the bench_portability.py test still reports 0 on E5 vs mpnet-base-v2,
OR the Liu 14-claim liu_accuracy drops below 0.90 under the adaptive
classifier.

**Scope limits:**
- Applies to `ground_many` batch mode only. Single `ground` keeps
  absolute threshold semantics (backward compat).
- When fewer than 4 claims with semantic-only agreement signal are
  present in a batch, adaptive gap detection falls back to absolute
  threshold (insufficient distribution to detect a meaningful gap).

## Explicit non-goals

The following came up in design discussion but are NOT part of this
hypothesis and should NOT be implemented:

- Bigger default semantic model (stays lightweight).
- LLM-based re-ranking as a default layer (breaks token-savings story).
- Automatic generative verification after UNCONFIRMED (breaks the "you
  must read the pointer" contract).
- Fine-tuning a custom embedding model.
- Semantic chunking via sentence embeddings (expensive, low marginal
  value over recursive chunking with overlap).

## Falsifiers

The hypothesis is FALSE if:

- After H1 is implemented, the Liu test gap between real paraphrase (#9,
  #10) and fabrication (#13, #14) does not widen measurably (< 0.05).
- After H2 is implemented, number-mismatch claims are not correctly
  flagged as CONTRADICTED on a seeded test set (< 80% recall).
- After H3 is implemented, swapping E5-small for a different
  sentence-encoder (e.g. BGE-m3 or paraphrase-multilingual-mpnet) without
  any threshold change produces different real/fake classification.

## Scope

In scope:

- Tool changes (grounding.py, semantic.py, cli.py).
- New test fixtures (Liu claims, SVG article claims, numeric mismatch
  seeds, multilingual seed).
- Skill rule updates (cross-layer agreement, contradiction handling).

Out of scope (do not change):

- The public CLI shape (`ground`, `ground-many` flags) — backward
  compatible.
- The `.stellars-plugins/settings.json` schema — additive only.
- Core layer algorithms (regex, Levenshtein, BM25, cosine) — still the
  same math.
- LLM-based reranking as a core feature — token-savings story must
  hold.

## Success metrics

- **Liu 14-claim test**: 12+ of 14 correctly classified (currently 12).
  Both fabrications remain UNCONFIRMED. Both real-but-distant
  paraphrases move to CONFIRMED.
- **Numeric-mismatch seed set** (new): ≥ 8/10 claims with wrong numbers
  correctly flagged CONTRADICTED.
- **Portability test**: swapping E5-small for
  `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` produces
  the same classification on the Liu 14-claim test without threshold
  changes.
- **Regression**: all existing 370 tests still pass.
- **Token savings**: ≥ 80% reduction vs batched generative on the Liu
  source (currently 86%) — must not regress.
