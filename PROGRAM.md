# Program: Grounding tool discrimination + portability improvements

## Objective

Widen the grounding tool's confidence separation between real distant
paraphrases and plausible fabrications from the current ~0.02 cosine gap
to ≥ 0.10 (measured on the Liu 2023 14-claim test set), eliminate
silent confirmation of numeric/named-entity mismatches, and make
embedding-model swaps work without threshold re-tuning. No regression in
existing tests, backward-compatible CLI, token-savings story preserved.

## Current State

- Version v1.3.26 ships `document-processing` CLI with 4 layers (regex,
  Levenshtein, BM25, optional E5 semantic).
- Liu 2023 14-claim test baseline: **10/14 CONFIRMED**, of which 0
  false-positives, 2 false-negatives (legitimate distant paraphrases
  scoring 0.838-0.840 just below 0.85 semantic threshold), 2 correct
  rejections (fabrications scoring 0.825-0.842).
- Discrimination gap between real paraphrase and fabrication: **0.02
  cosine** — too tight to act on without reading the pointer.
- Number / named-entity claims are not cross-checked between claim and
  passage — "42 nodes" vs "12 nodes" passes all layers.
- Thresholds are absolute numbers (0.85, 0.4, etc.) tuned for
  E5-small. Swapping models (BGE, mpnet, mmBERT) produces wrong
  classifications at the same thresholds.
- No non-English test exists for the multilingual default.
- Token savings measured: 64% on SVG article, 86% on Liu paper.
- Existing tests: 360/360 pass (baseline corrected from earlier 370 miscounting; verified via `uv run pytest tests/ --collect-only -q`).

## Work Items

Planner sequences per dependencies. All work items MUST NOT change
public CLI flag shape (additions only).

### Scoring improvements

- **Top-K semantic hits + cross-layer agreement score** (hypothesis H1)
  - Scope: `stellars_claude_code_plugins/document_processing/grounding.py`,
    `stellars_claude_code_plugins/document_processing/semantic.py`,
    `stellars_claude_code_plugins/document_processing/cli.py`, tests.
  - Acceptance: `GroundingMatch` gains `semantic_top_k: list[SemanticHit]`
    (top-3 by default) and `agreement_score: float` defined as a weighted
    combination of exact / fuzzy / bm25 / semantic that rewards
    layer agreement. Any layer firing alone at threshold contributes
    less than two layers firing together below threshold. Liu test
    real-vs-fake gap ≥ 0.10 on `agreement_score`.
  - Predict: gap widens from 0.02 (current `semantic_score`) to ≥ 0.10
    (new `agreement_score`). Claims 9, 10 move to CONFIRMED. Claims 13,
    14 stay UNCONFIRMED.
  - Outcome: agent gets a single reliable confidence signal + 3
    alternative pointers for borderline cases.
  - Depends on: none.

- **Self-calibrated percentile thresholds** (hypothesis H3)
  - Scope: `semantic.py`, `grounding.py`.
  - Acceptance: `SemanticGrounder` samples N=200 random chunk-pair
    cosines at index time, stores the distribution. Semantic match
    threshold becomes "top 2% of corpus distribution" by default;
    absolute `--semantic-threshold` still overrides. Swapping E5-small
    for `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
    on the Liu test produces the same claim classifications without
    threshold changes.
  - Predict: thresholds become model-agnostic. Removes manual
    per-model tuning.
  - Outcome: users can swap embedding models freely without silent
    quality regressions.
  - Depends on: none.

- **Self-score sanity check** (hypothesis H7)
  - Scope: `semantic.py`, `grounding.py`.
  - Acceptance: each `GroundingMatch` with semantic signal reports
    `semantic_ratio = semantic_score / claim_self_score`, where
    `claim_self_score` is cosine of the claim against itself wrapped as
    a passage. Reported in CLI output and JSON.
  - Predict: agents and callers can calibrate borderline matches
    per-claim instead of relying on absolute score.
  - Outcome: supplementary diagnostic signal. Does not change match_type
    directly but helps agent judge marginal cases.
  - Depends on: none.

### Safety features

- **Numeric + named-entity mismatch detection** (hypothesis H2)
  - Scope: new module
    `stellars_claude_code_plugins/document_processing/entity_check.py`,
    wired into `grounding.py`.
  - Acceptance: extract numbers (incl. ranges, units, percentages),
    dates, and capitalised multi-word named entities from claim AND
    winning passage. Populate
    `GroundingMatch.numeric_mismatches: list[tuple[str, str]]` and
    `entity_mismatches: list[tuple[str, str]]`. When either non-empty,
    `match_type = "contradicted"` (new variant) regardless of other
    scores. A new 10-seed mismatch test set achieves ≥ 8/10 correct
    CONTRADICTED classifications.
  - Predict: high-stakes fabrication class ("42 nodes" vs "12 nodes",
    "H100" vs "A100") caught before it ships.
  - Outcome: CONTRADICTED verdict is new and distinct from UNCONFIRMED
    — flags active disagreement between claim and source.
  - Depends on: none (independent layer).

### Retrieval tuning

- **BM25-guided semantic re-ranking** (hypothesis H4)
  - Scope: `semantic.py`.
  - Acceptance: when both BM25 and semantic are active, take top-20
    BM25 candidates and re-rank those by semantic cosine rather than
    scanning the full chunk set. Falls back to full-semantic if BM25
    returns nothing. Semantic recall on Liu test does not drop; false
    positives on a long-corpus test (planned new fixture) measurably
    reduced.
  - Predict: on sources > 10k tokens, fewer unrelated passages win
    top-1 via spurious topical similarity.
  - Outcome: more precise semantic hits on long sources.
  - Depends on: H1 (top-K structure already in place).

- **Chunk-boundary expansion on borderline claims** (hypothesis H5)
  - Scope: `semantic.py`, `chunking.py`.
  - Acceptance: when best semantic hit is within 0.05 of the semantic
    threshold, expand the window to include prev + next chunks,
    re-embed merged context, re-rank top-K. `GroundingMatch` gains
    `expanded: bool` indicating a borderline-mode hit. Liu claim #5
    (currently semantic 0.855, borderline) either confirmed more firmly
    or correctly left unconfirmed via expanded context.
  - Predict: reduces recall loss on boundary-straddling claims. Only
    triggers on ~5-15% of claims; no added cost for clear-cut cases.
  - Outcome: boundary-straddling supported claims no longer silently
    missed.
  - Depends on: H3 (threshold needed to define "borderline").

### Test coverage

- **Multilingual smoke test** (hypothesis H6)
  - Scope: new test fixture + `tests/test_document_processing.py`.
  - Acceptance: bilingual test fixture (English claim, French passage
    on the same topic). Skipped when `[semantic]` extras not installed.
    Wired into default CI. Passes on
    `intfloat/multilingual-e5-small`.
  - Predict: future model-default changes that break multilingual are
    caught in CI.
  - Outcome: multilingual promise becomes verified rather than claimed.
  - Depends on: none.

### Skill updates

- **Rule: "agreement beats magnitude"** (hypothesis H8)
  - Scope: `document-processing/skills/validate-document/SKILL.md`.
  - Acceptance: explicit rule that confidence = agreement across
    layers, NOT peak score on a single layer. Include example: "claim
    with only semantic 0.90, lexical all zero = read the pointer, do
    not auto-confirm."
  - Predict: agents stop over-trusting semantic-only hits.
  - Outcome: UNCONFIRMED is handled correctly in practice.
  - Depends on: H1 (agreement score must exist first).

- **Rule: "contradiction flag is the final word"** (hypothesis H9)
  - Scope: `document-processing/skills/validate-document/SKILL.md`.
  - Acceptance: explicit rule that `numeric_mismatches` or
    `entity_mismatches` non-empty = CONTRADICTED verdict, overriding
    any positive score. Include a numeric-mismatch example in the
    report template.
  - Predict: no CONFIRMED with mismatches slipping through.
  - Outcome: agents cannot override CONTRADICTED to CONFIRMED.
  - Depends on: H2.

- **Rule: "re-recommend semantic on struggle" (strengthen)** (hypothesis H10)
  - Scope: `document-processing/skills/validate-document/SKILL.md`.
  - Acceptance: existing rule tightened to require EXPLICIT user
    consent ask (not silent auto-enable) when > 25% UNCONFIRMED or any
    claim in the 0.5-0.85 fuzzy + 0.2-0.5 BM25 "almost grounded" zone.
    Include exact user-message template.
  - Predict: users who declined semantic but would benefit get a
    second offer, with consent.
  - Outcome: no silent escalation; user stays in control.
  - Depends on: none.

## Exit Conditions

Iterations stop when ANY of these is true:

1. **Benchmark score stagnation (primary)** — no improvement in the
   benchmark composite score for 2 consecutive iterations.
2. Scope completion — all work items meet their acceptance conditions.
3. Effective optimum — score reaches the pre-declared floor (see
   BENCHMARK.md).

## Constraints

- **CLI surface is backward-compatible.** Existing flags on
  `document-processing ground` and `ground-many` keep current
  semantics. New fields on `GroundingMatch` are additive.
- **Settings schema additive only.** `.stellars-plugins/settings.json`
  keys may be added but none renamed or removed.
- **Core layer math unchanged.** Regex, Levenshtein partial-ratio,
  BM25 Okapi, and cosine-on-L2-normalised-embeddings all stay.
  Improvements come from combination logic, not new math.
- **No LLM reranking as a default layer.** Token-savings story must
  hold; semantic layer stays deterministic.
- **No forced heavy deps.** `torch` / `transformers` / `faiss` /
  `pyarrow` remain in the `[semantic]` optional extra.
- **360 existing tests must still pass.** New tests added, none
  deleted or relaxed.
- **No default-model swap** that would require re-downloading weights
  for existing users. `intfloat/multilingual-e5-small` stays default.
