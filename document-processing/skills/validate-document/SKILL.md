---
name: validate-document
description: Validate a document against its source material for grounding, then check tone, style, length and format compliance. Use when asked to validate, verify, check grounding, or audit a document against a source.
---

# Document Validation Skill

Two phases: (1) source grounding - extract claims, verify each; (2) compliance - tone, style, length, format.

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
2. **Search source** for confirming evidence
3. **Mark status**:
   - CONFIRMED - supporting fragment found (quote it)
   - UNCONFIRMED - no evidence in source
   - CONTRADICTED - source contradicts (quote both)
   - INFERRED - reasonable inference, not directly stated (explain)
   - NOT APPLICABLE - structural/editorial, not fact-based

**Output** (`grounding-report.md`):

```markdown
# Source Grounding Report

**Document**: <path>
**Source(s)**: <path(s)>
**Date**: <date>

## Claims

### 1. <short claim summary>
**Claim**: "<exact text from document>"
**Status**: CONFIRMED
**Source**: "<supporting fragment from source>"

### 2. <short claim summary>
**Claim**: "<exact text from document>"
**Status**: UNCONFIRMED
**Source**: No supporting evidence found
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
