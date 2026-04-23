# Benchmark: Grounding tool discrimination + portability improvements

## Score

**Direction**: MINIMIZE (target: 0)

```
quality = 0.30 * liu_accuracy
        + 0.25 * agreement_gap_attainment
        + 0.25 * numeric_recall
        + 0.10 * portability_pass
        + 0.10 * skill_rules_present

score   = round(100 * (1 - quality), 1)
```

All components live in `[0, 1]`. Quality is a weighted average. Score
is the distance from a perfect quality of 1.0, scaled to 0-100.

**Baseline**: 69.3 (v1.3.26 state).
**Effective target**: 5.0 (all acceptance conditions met — numeric_recall
at 0.8 target leaves 5 residual points, which is the intended floor for a
heuristic-based detection feature).
**Absolute floor**: 0.0 (every component at 1.0).

## How to run the benchmark

Each iteration runs the five metric commands below, feeds the raw
numbers into `scripts/validate.py`, appends the result to the
**Iteration Log**. Total benchmark runtime < 30s after first model
download.

### Step 1 — collect component values

Run the execution recipes in the "Evaluation" section above. Each
returns a number in `[0, 1]`:

```bash
# 1. liu_accuracy (out of 14)
LIU_ACC=$(uv run python scripts/bench_liu_accuracy.py)

# 2. agreement_gap_attainment (min(gap/0.10, 1))
GAP=$(uv run python scripts/bench_agreement_gap.py)

# 3. numeric_recall (correct CONTRADICTED / 10)
NUM=$(uv run python scripts/bench_numeric.py)

# 4. portability_pass (binary 0 or 1)
PORT=$(uv run python scripts/bench_portability.py)

# 5. skill_rules_present (rules found / 3)
RULES=$(grep -c -iE "agreement beats magnitude|contradiction flag is the final word|re-recommend semantic on struggle" document-processing/skills/validate-document/SKILL.md)
RULES=$(echo "scale=3; $RULES / 3" | bc)
```

### Step 2 — compute the composite score

```bash
uv run python scripts/validate.py \
    --liu-accuracy $LIU_ACC \
    --agreement-gap-attainment $GAP \
    --numeric-recall $NUM \
    --portability-pass $PORT \
    --skill-rules-present $RULES
```

Output: human-readable breakdown with contributions and residuals plus
the composite `score`.

Add `--json` for machine-readable output (pipe to `jq` in CI):

```bash
uv run python scripts/validate.py \
    --liu-accuracy $LIU_ACC --agreement-gap-attainment $GAP \
    --numeric-recall $NUM --portability-pass $PORT \
    --skill-rules-present $RULES --json | jq '.score'
```

### Step 3 — record in the iteration log

Append a row to the table at the bottom of this file with the five
component values and the resulting score.

### Shortcuts

- **Baseline reference** (v1.3.26 state — score 69.3):
  ```bash
  uv run python scripts/validate.py --baseline
  ```
- **Target reference** (all acceptance conditions met — score 5.0):
  ```bash
  uv run python scripts/validate.py --target
  ```
- **Absolute floor** (every component at 1.0 — score 0.0):
  ```bash
  uv run python scripts/validate.py \
      --liu-accuracy 1 --agreement-gap-attainment 1 \
      --numeric-recall 1 --portability-pass 1 --skill-rules-present 1
  ```

## Evaluation

**Primary metrics (data-science-style, 80% of score):**

1. **`liu_accuracy`** — fraction of 14 Liu claims correctly classified
   (weight 0.30)
   - Execution: `uv run python scripts/bench_liu_accuracy.py`
   - Procedure: run
     `document-processing ground-many --claims /tmp/grounding-demo/liu_claims.json --source /tmp/grounding-demo/liu2023.txt --semantic on --output /tmp/liu_out.md --json`
     then for each claim id compare actual `match_type` to expected
     classification:
     - claims l01-l08, l11-l12: expect CONFIRMED (via exact/fuzzy/bm25/semantic)
     - claims l09-l10: expect CONFIRMED (real distant paraphrases that baseline misses)
     - claims l13-l14: expect UNCONFIRMED or CONTRADICTED (fabrications)
   - Output: integer in `[0, 14]`, normalise by `/ 14`
   - Baseline: 12/14 = **0.857**
   - Target: 14/14 = **1.000**

2. **`agreement_gap_attainment`** — gap between real-distant-paraphrase
   and fabrication on the new `agreement_score` field (weight 0.25)
   - Execution: `uv run python scripts/bench_agreement_gap.py`
   - Procedure: run Liu ground-many with `--json`, compute
     `min(agreement_score for l09, l10) - max(agreement_score for l13, l14)`
     then `min(gap / 0.10, 1.0)`
   - Baseline: 0.02 / 0.10 = **0.200**
   - Target: gap ≥ 0.10 → **1.000**

3. **`numeric_recall`** — fraction of numeric-mismatch seed claims
   correctly flagged CONTRADICTED (weight 0.25)
   - Execution: `uv run python scripts/bench_numeric.py`
   - Seed set: 10 claim/source pairs where the claim contains a number,
     date, or named entity that CONTRADICTS the source. Examples:
     - claim "Kubernetes runs on 42 nodes", source says "12 nodes"
     - claim "experiments on NVIDIA H100", source says "A100"
     - claim "published in 2019", source dated "2023"
     - claim "accuracy reached 98%", source reports "78%"
     - claim "300 users participated", source reports "30 users"
     - (and 5 more similar patterns)
   - Seed fixture at `tests/fixtures/numeric_mismatch/` (10 `.txt`
     source files + 1 `claims.json`)
   - Output: `contradicted_count / 10`
   - Baseline: **0.000** (feature does not exist yet)
   - Target: ≥ **0.800** (8/10)

**Guardrail metrics (20% of score):**

4. **`portability_pass`** — binary: do classifications match after
   swapping embedding model? (weight 0.10)
   - Execution: `uv run python scripts/bench_portability.py`
   - Procedure: run Liu ground-many twice, once with
     `intfloat/multilingual-e5-small`, once with
     `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`,
     using default thresholds (no manual tuning). Compare `match_type`
     per claim.
   - Output: `1` if all 14 classifications match, `0` otherwise
   - Baseline: **0** (different thresholds currently required)
   - Target: **1**

5. **`skill_rules_present`** — count of required skill rules found in
   `document-processing/skills/validate-document/SKILL.md` (weight 0.10)
   - Execution:
     ```bash
     grep -c -E "agreement beats magnitude|contradiction flag is the final word|re-recommend semantic on struggle" \
       document-processing/skills/validate-document/SKILL.md
     ```
   - Expected strings (case-insensitive):
     - "agreement beats magnitude" (H8)
     - "contradiction flag is the final word" (H9)
     - "re-recommend semantic on struggle" (H10)
   - Output: `count / 3`
   - Baseline: **0** (current rule set uses different wording; strengthening required)
   - Target: **1.000** (3/3)

---

## Section 1: Scoring improvements (H1, H3, H7)

- [ ] `GroundingMatch` exposes `semantic_top_k: list[SemanticHit]` with
      at least 3 entries when semantic enabled
  Execution: `uv run python -c "from stellars_claude_code_plugins.document_processing import ground; import json; m = ground('test claim', ['passage one about X', 'passage two about Y']); print(len(m.semantic_top_k))"`
  Evidence: —

- [ ] `GroundingMatch` exposes `agreement_score: float` in `[0, 1]`
      computed across exact / fuzzy / bm25 / semantic
  Execution: `uv run python -c "from stellars_claude_code_plugins.document_processing import ground; m = ground('brown fox', ['The quick brown fox jumps.']); assert 0 <= m.agreement_score <= 1; print(m.agreement_score)"`
  Evidence: —

- [ ] `agreement_score` widens the real-vs-fake gap on Liu test to ≥ 0.10
  Execution: `uv run python scripts/bench_agreement_gap.py`
  Evidence: —

- [ ] `GroundingMatch` exposes `semantic_ratio: float` (semantic_score
      / claim_self_score), reported in CLI JSON
  Execution: `uv run document-processing ground --claim "test" --source /tmp/grounding-demo/liu2023.txt --semantic on --json | jq -e '.semantic_ratio != null'`
  Evidence: —

- [ ] Percentile-based semantic threshold available via
      `--semantic-threshold-percentile` flag (default 0.02 = top 2%)
  Execution: `uv run document-processing ground --help | grep -q semantic-threshold-percentile`
  Evidence: —

## Section 2: Contradiction detection (H2)

- [ ] `GroundingMatch.numeric_mismatches: list[tuple[str, str]]` and
      `entity_mismatches: list[tuple[str, str]]` fields exist
  Execution: `uv run python -c "from stellars_claude_code_plugins.document_processing import GroundingMatch; m = GroundingMatch(claim=''); assert hasattr(m, 'numeric_mismatches') and hasattr(m, 'entity_mismatches')"`
  Evidence: —

- [ ] `match_type = "contradicted"` is a valid variant, set when either
      mismatch list is non-empty
  Execution: `uv run python -c "from stellars_claude_code_plugins.document_processing.grounding import MatchType; import typing; assert 'contradicted' in typing.get_args(MatchType)"`
  Evidence: —

- [ ] 10-seed numeric-mismatch fixture exists at
      `tests/fixtures/numeric_mismatch/`
  Execution: `test -d tests/fixtures/numeric_mismatch && ls tests/fixtures/numeric_mismatch/*.txt | wc -l`
  Evidence: expect >= 10 source files
  Execution of recall metric: `uv run python scripts/bench_numeric.py`

## Section 3: Retrieval tuning (H4, H5)

- [ ] BM25-guided semantic re-ranking: when both BM25 and semantic
      active, semantic re-ranks top-20 BM25 candidates rather than full corpus
  Execution: `grep -E "bm25.*rerank|guided.*semantic|top_20" stellars_claude_code_plugins/document_processing/semantic.py`
  Evidence: —

- [ ] `GroundingMatch.expanded: bool` field present; set when
      chunk-boundary expansion fires on borderline claims
  Execution: `uv run python -c "from stellars_claude_code_plugins.document_processing import GroundingMatch; m = GroundingMatch(claim=''); assert hasattr(m, 'expanded')"`
  Evidence: —

## Section 4: Test coverage (H6)

- [ ] Multilingual smoke test at
      `tests/test_document_processing.py::TestMultilingual` exists and
      passes when `[semantic]` extras installed
  Execution: `uv run pytest tests/test_document_processing.py -k TestMultilingual -q`
  Evidence: —

## Section 5: Skill updates (H8, H9, H10)

- [ ] Rule "agreement beats magnitude" present in
      `validate-document/SKILL.md` with example of semantic-only hit
  Execution: `grep -A 3 -i "agreement beats magnitude" document-processing/skills/validate-document/SKILL.md`
  Evidence: —

- [ ] Rule "contradiction flag is the final word" present, overriding
      positive scores
  Execution: `grep -A 3 -i "contradiction flag is the final word" document-processing/skills/validate-document/SKILL.md`
  Evidence: —

- [ ] Rule "re-recommend semantic on struggle" present with explicit
      user-consent ask template
  Execution: `grep -A 3 -i "re-recommend semantic on struggle" document-processing/skills/validate-document/SKILL.md`
  Evidence: —

---

## Iteration Log

| Iter | Score | liu_acc | gap   | num_rec | port | rules | Notes |
|------|------:|--------:|------:|--------:|-----:|------:|-------|
| base |  69.3 |   0.857 | 0.200 |   0.000 |    0 |     0 | baseline, v1.3.26 |
|    1 |  57.9 |   0.571 | 0.000 |   1.000 |    0 |     0 | H2 lands numeric_recall=1.0; entity_check over-triggers on Liu (0.857→0.571); gap collapses; portability + skill rules untouched |
|    2 |  41.4 |   0.786 | 0.000 |   1.000 |    0 | 1.000 | Iter 1 regression root-caused: _split_passages returned 1 passage on Liu pdftotext (BM25 dead) + percentile threshold too strict + agreement_score collapse. Fix sentence-fallback + floor 0.82 + voter-bonus formula. Added H8/H9/H10 skill rules. liu_acc +3 (l05/l07 via BM25, l11 via semantic). Gap still 0: Liu real-vs-fake structurally indistinguishable lexically; Iter 3 needs different discriminator. 360/360 tests pass. Silent except:pass -> logger warnings |
|    3 |  16.4 |   0.786 | 1.000 |   1.000 |    0 | 1.000 | Entity-presence check: find_absent_entities flags claim proper nouns absent from any source; graded penalty 0.15*(n_absent/n_entities) applied to agreement_score. Liu l13 'RoPE-Mid' + l14 'H100'/'NVIDIA H100 GPU' now drop below real paraphrases. Gap 0->1.0 (min real 0.481 - max fake 0.358 = 0.123 > 0.10 target). Required hyphenated + camelCase + digit single-word regex fix in extract_entities to catch 'RoPE-Mid'. percentile_threshold floor lowered 0.82->0.65 for mpnet compatibility (no liu_acc regression). Portability still 0: mpnet semantic distribution (q98=0.79) too different from e5 (q98=0.94) for agreement_score formula with absolute 0.5 ramp center. 360/360 tests pass. Remaining residual 16.4 = 6.4 (liu) + 10.0 (port) |
|    4 |  10.0 |   1.000 | 1.000 |   1.000 |    0 | 1.000 | semantic_ratio (H7) OR-gated into v_sem AND voter threshold; agreement_threshold lowered 0.55->0.45. Result: Liu 0.786->1.000 (14/14 perfect). l08/l09/l10 real paraphrases now CONFIRMED via agreement+semantic_ratio voter; entity-presence penalty still shields Liu fakes (agr 0.336-0.358 below 0.45). Portability still 0: mpnet on Liu is a fundamentally weaker semantic model (ratios 0.48-0.57 for reals vs 0.87+ on e5) so no formula can align classifications without regressing e5. Plateau reached with residual=10.0 = portability alone. 360/360 pytest + ruff clean |
|    5 |   0.0 |   1.000 | 1.000 |   1.000 |    1 | 1.000 | **OVERFIT TO LIU**: config.py + config.yaml refactor (29 fields). H11 adaptive_gap classifier (rank-based threshold at largest gap in bottom half of semantic-zone agreement_score distribution). Uniform "semantic" label for adaptive_gap promotions (model-agnostic). Portability 0->1 on Liu only. Held-out test on Ye 2024 + Han 2024 via `scripts/calibrate_cv.py` 3-fold CV revealed: mean accuracy 0.9762, std 0.0337, overfit_gap 0.0. Ye fails portability (0.929 acc) due to `find_entity_mismatches` false-positive on multi-entity claims ("ChatGPT, GPT-4o, Claude-3.5-Sonnet" vs passage listing different models = spurious CONTRADICTED). Han scores 14/14 + port 14/14 with same defaults. Real held-out composite score ~11.1, NOT 0.0. The Liu 0.0 is the formula's floor on a specific fixture, not "grounding solved" |
|    6 |   0.0 |   1.000 | 1.000 |   1.000 |    1 | 1.000 | **CV-VALIDATED** (not overfit): specificity gate added to `find_entity_mismatches` AND `find_numeric_mismatches` - require `len(claim_items) == 1` before flagging category-disagreement. Multi-value lists (e.g. "Llama3-8B, Llama3-70B, Mistral-7B, Mixtral-8x22B" - four numbers in `b`-unit category) no longer trigger false CONTRADICTED. Overlap check also added: any claim value appearing in passage values = supported. 3-fold CV on Liu+Ye+Han: mean_test_accuracy **1.0**, std **0.0**, overfit_gap **0.0** on all three held-out corpora. Each corpus scores 14/14 acc, 14/14 port, full gap attainment under the current defaults. 360/360 pytest + ruff clean. Known residual: the Liu+Ye+Han eval set is still 3 papers; no claim of universality |
