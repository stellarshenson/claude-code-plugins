---
name: validate-document
description: Validate a document against its source material for grounding, then check tone, style, length and format compliance. Use when asked to validate, verify, check grounding, or audit a document against a source.
---

# Document Validation Skill

Two phases: (1) source grounding - extract claims, verify each; (2) compliance - tone, style, length, format.

## Install (MANDATORY)

```bash
pip install stellars-claude-code-plugins
```

Ships `document-processing` CLI with deterministic three-layer grounding (regex exact + Levenshtein fuzzy + BM25 passage ranking). All three scores reported on every call, with line/column/paragraph/page/context for every hit. Verify: `document-processing --help`. Without install no programmatic grounding — manual search only.

## Check semantic-grounding consent (MANDATORY every run)

Before running grounding, read `./.stellars-plugins/settings.json` (project-local, sibling to `.claude/`) to see whether the user has consented to semantic grounding:

```bash
test -f .stellars-plugins/settings.json && cat .stellars-plugins/settings.json
```

If the file does not exist, run `document-processing setup` — this prompts the user once, writes the answer, and never prompts again. Do NOT silently enable semantic; it requires optional deps (`pip install 'stellars-claude-code-plugins[semantic]'`) and downloads a ~150 MB model on first use.

Read the `semantic_enabled` field:

- `semantic_enabled: true` → pass `--semantic on` to every `document-processing ground` / `ground-many` call. The tool adds a 4th layer (ModernBERT + FAISS) that catches claims where wording AND terms diverge but meaning aligns. Useful for long or abstract sources.
- `semantic_enabled: false` (default) → pass `--semantic off` or omit the flag. Three lexical layers only.
- Missing file → run `document-processing setup` and proceed per user's answer.

### Never blindly trust scores. Verify generatively when in doubt

Scores = signals, not truth. Every layer can be fooled:

- Exact: hits unrelated substring with same word order
- Fuzzy: high on character overlap with opposite meaning ("3-6 hours" vs "36 hours")
- BM25: high on shared terms with no logical link
- Semantic: high on topically-similar passage that doesn't support the claim

**Tool always gives a pointer — line, column, paragraph, page, context snippet — even on UNCONFIRMED.** Use it. Jump to the location, read the passage, judge. No full re-scan needed. That is the whole point.

Verify generatively when ANY of:

- Borderline score: winning layer within 0.05 of threshold (fuzzy 0.85-0.90, bm25 0.40-0.50, semantic 0.85-0.90)
- Layer disagreement: semantic ≥0.85 but lexical low (fuzzy <0.6, bm25 <0.3)
- Location off: tool points at a passage nowhere near where the claim should live
- Numerical / named-entity claims: models blur "3 seconds" vs "3 minutes". Always read
- Medium score on fake-sounding claim: reject unless the named entity appears in the quoted passage

Output verdict: cite the quoted passage + state supports / contradicts / topical-only. Never override CONFIRMED without evidence. Never accept CONFIRMED without reading.

### When to RE-RECOMMEND semantic to the user

If `semantic_enabled` is `false` AND the three-layer pass leaves many UNCONFIRMED claims (rule of thumb: **>25% unconfirmed** or **any unconfirmed claim with fuzzy 0.5-0.85 AND bm25 0.2-0.5** — the "almost grounded" zone), stop and recommend semantic to the user explicitly:

> The grounding pass left N/M claims UNCONFIRMED and several are in the "almost grounded" zone (paraphrased meaning, diverged wording). Enabling semantic grounding (ModernBERT + FAISS) would likely catch these. To enable:
>
> 1. `pip install 'stellars-claude-code-plugins[semantic]'`
> 2. `document-processing setup --force` and answer yes
>
> This downloads a ~150 MB model on first use. Re-run the grounding with `--semantic on` afterwards.

Do NOT silently enable it — ask the user first, they already declined once. Offer, wait for consent, then proceed.

## Phase 0: Gather Criteria

Ask if not provided.

**Required:**
- **Document to validate**: path
- **Source document(s)**: path(s) for grounding

**Optional (offer defaults):**
- **Word count range**: min-max (default: no constraint)
- **Tone**: first-person, formal, technical, conversational (default: infer)
- **Style rules**: patterns to enforce or prohibit (default: none)
- **Target audience**: default: general
- **Section format rules**: bullets, section lengths, heading structure (default: none)
- **Focus rules**: content excluded or prioritized (default: none)
- **Format rules**: encoding, spacing, links (default: UTF-8, single spacing, no links)
- **Custom rules**: key-value pairs

Store all criteria.

## Phase 1: Setup

Create `validation/` in project root. All artifacts here.

```
validation/
├── criteria.md              <- collected criteria summary
├── grounding-report.md      <- Phase 2 output
├── compliance-checklist.md  <- Phase 3 output
├── validation-summary.md    <- Phase 4 output
└── <filename>_corrected.<ext> <- Phase 5 output (best-effort corrected copy)
```

Write `criteria.md`.

## Phase 2: Source Grounding Check

Extract every factual claim, assertion, attribution, number, date, quote. For each:

1. **State claim** exactly as in document
2. **Run grounding tool FIRST — primary approach.** The `document-processing` CLI is the agent's primary grounding method. Use `document-processing ground` for single claims or `document-processing ground-many` for batches. The tool runs THREE layers independently (regex exact, Levenshtein fuzzy, BM25 passage ranking) and reports all three scores plus line/column/paragraph/page/context for every hit — no rereading the source. **Secondary approach: disciplined generative interpretation** — only when all three lexical layers fail and the claim is semantic (e.g. a summary, synthesis, or cross-passage inference). Do not skip the tool; run it first, then add generative interpretation on top when lexical signal is absent
3. **Mark status** based on tool output:
   - CONFIRMED - `match_type=exact` (score 1.0) → quote `exact_matched_text` at `exact_location`
   - CONFIRMED (fuzzy) - `match_type=fuzzy` (fuzzy_score ≥ threshold) → quote `fuzzy_matched_text` at `fuzzy_location`, note paraphrase tolerance used
   - CONFIRMED (topical / BM25) - `match_type=bm25` (token-recall ≥ bm25_threshold) → quote `bm25_matched_text` (the winning passage) at `bm25_location`, note that wording differs but terms align
   - UNCONFIRMED - `match_type=none` (all three scores below their thresholds) → no lexical evidence in source; consider generative interpretation only if semantic claim, otherwise remove/rephrase
   - CONTRADICTED - source directly contradicts (manual call; re-run with the contradicting phrase to cite location)
   - INFERRED - reasonable inference, not directly stated (explain; tool confirms absence of verbatim)
   - NOT APPLICABLE - structural/editorial, not fact-based (skip tool)

### Using the grounding CLI

Batch pass — builds `grounding-report.md` in one shot:

```bash
# claims.json: list of strings or [{"claim": "...", "id": "..."}]
# Pass --semantic on if settings.semantic_enabled == true
document-processing ground-many \
  --claims validation/claims.json \
  --source docs/source.md \
  --output validation/grounding-report.md \
  --threshold 0.85 \
  --bm25-threshold 0.5 \
  --semantic on     # omit or use 'off' when settings disables it
```

Single-claim probe — useful for on-demand checks during review:

```bash
document-processing ground \
  --claim "Kubernetes runs on 12 nodes" \
  --source docs/architecture.md \
  --json
```

All three scores (exact + fuzzy + bm25) come back on every call even when only one fires — use the layered signal to distinguish verbatim quotes, paraphrases, and topical claims from fabrications.

### Tool output maps to status

| Tool output | Status |
|-------------|--------|
| `exact_score=1.0` | CONFIRMED |
| `fuzzy_score ≥ threshold`, `exact_score=0` | CONFIRMED (fuzzy) — note paraphrase |
| `bm25_score ≥ bm25_threshold`, `exact=0`, `fuzzy<threshold` | CONFIRMED (topical) — note wording differs, same terms |
| `semantic_score ≥ semantic_threshold`, lexical all below | CONFIRMED (semantic) — meaning matches, wording + terms diverge. Only fires when `--semantic on` |
| all layers below thresholds | UNCONFIRMED (quote best available for diagnostics) |

Priority when multiple layers hit: exact > fuzzy > bm25 > semantic.

The tool also returns `exact_location` / `fuzzy_location` / `bm25_location` with `line_start`, `column_start`, `paragraph`, `page`, `context_before`, `context_after` — cite these directly in the report instead of rereading the source file. This saves tokens and keeps citations precise.

### When to reach for generative (secondary) grounding

Only when all three lexical layers return `none` AND the claim is semantic (summary, synthesis, cross-passage inference). Disciplined: still cite WHICH passages contributed and acknowledge absence of verbatim/paraphrase/term match. Do not let generative interpretation override a lexical UNCONFIRMED for factual claims — that is fabrication territory.

**Output** (`grounding-report.md`):

```markdown
# Source Grounding Report

**Document**: <path>
**Source(s)**: <path(s)>
**Date**: <date>

## Claims

### 1. <short claim summary>
**Claim**: "<exact text from document>"
**Status**: CONFIRMED (exact 1.000, fuzzy 1.000, bm25 1.000)
**Source**: "<supporting fragment from source>" @ `docs/source.md:L42:C5 ¶3 pg2`

### 2. <short claim summary>
**Claim**: "<exact text from document>"
**Status**: CONFIRMED (topical) (exact 0.000, fuzzy 0.52, bm25 0.88)
**Source**: "<winning passage from source>" @ `docs/source.md:L88 ¶5` (token-recall 0.88)
**Note**: Wording differs; same key terms found in passage.

### 3. <short claim summary>
**Claim**: "<exact text from document>"
**Status**: UNCONFIRMED (exact 0.000, fuzzy 0.62, bm25 0.20)
**Source**: No lexical evidence in source. Best fuzzy: "<nearest fragment>" @ `docs/source.md:L88 ¶5` (ratio 0.62, below threshold). Best BM25 passage @ `docs/source.md:¶12` (token-recall 0.20, below threshold)
**Recommendation**: Remove or rephrase

...

## Summary
- Total claims: X
- Confirmed: X
- Unconfirmed: X
- Contradicted: X
- Inferred: X
- Not applicable: X
- **Grounding score**: X/Y (confirmed / total factual claims)
```

UNCONFIRMED/CONTRADICTED: list concrete corrections.

## Phase 3: Compliance Checklist

Check against all criteria. Generate `compliance-checklist.md`:

```markdown
# Compliance Checklist

**Document**: <path>
**Date**: <date>

## Word Count
- [ ] Current count: XXX words
- [ ] Target range: [min]-[max]
- [ ] In range: YES/NO
- [ ] Action: [trim/expand/OK]

## Tone
- [ ] Expected: <tone description>
- [ ] Violations found: [list quotes or NONE]
- [ ] Action: [rephrase X passages / OK]

## Style Rules
For each rule provided:
- [ ] Rule: <description>
- [ ] Status: PASS/FAIL
- [ ] Violations: [list or NONE]
- [ ] Action: [fix / OK]

## Focus Rules
- [ ] Prohibited content found: [list quotes or NONE]
- [ ] Required content present: [list or YES/NO]
- [ ] Action: [remove X / add Y / OK]

## Format
- [ ] Encoding: UTF-8 YES/NO
- [ ] Paragraph spacing: correct YES/NO
- [ ] Links: [count found or NONE]
- [ ] Action: [fix / OK]

## Section Format
For each section rule:
- [ ] Rule: <description>
- [ ] Status: PASS/FAIL
- [ ] Details: [measurements]
- [ ] Action: [fix / OK]

## Custom Rules
For each custom rule:
- [ ] Rule: <description>
- [ ] Status: PASS/FAIL
- [ ] Evidence: [details]
- [ ] Action: [fix / OK]
```

Use Python scripts for measurable checks (word count, point length, links) - never eyeball.

## Phase 4: Validation Summary

Generate `validation-summary.md`:

```markdown
# Validation Summary

**Document**: <path>
**Source(s)**: <path(s)>
**Date**: <date>

## Grounding
- Claims checked: X
- Grounding score: X/Y (Z%)
- Issues: [list or NONE]

## Compliance
- Rules checked: X
- Passed: X
- Failed: X
- Issues: [list or NONE]

## Overall Verdict
[PASS / PASS WITH WARNINGS / FAIL]

## Required Actions
1. [numbered list of all required fixes, or "None - document passes all checks"]
```

## Phase 5: Apply Corrections (best effort)

Always produce corrected copy:

1. Copy original to `validation/<filename>_corrected.<ext>`
2. Apply corrections:
   - UNCONFIRMED: rephrase to align with source or remove
   - CONTRADICTED: fix to match source
   - Compliance failures: fix formatting, trim, adjust tone
3. Re-run both checks against corrected version
4. Update `validation-summary.md` with post-correction status
5. Present diff to user

## Important Notes

- **Never modify source document(s)** - read-only
- **All artifacts in `validation/`**
- **Python for measurements** - never manual
- **Quote evidence** - actual text, not "confirmed"
- **Be specific** - violations cite exact offending text with location
- **Preserve originals** - corrected version separate file with `_corrected` suffix. Overwrite only on explicit request
