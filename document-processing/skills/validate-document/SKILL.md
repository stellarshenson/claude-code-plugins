---
name: validate-document
description: Validate a document against its source material for grounding, then check tone, style, length and format compliance. Use when asked to validate, verify, check grounding, or audit a document against a source.
---

# Document Validation Skill

Validate document against source material in two phases: (1) source grounding - extract claims, verify each against source; (2) compliance - tone, style, length, format rules.

## Phase 0: Gather Criteria

Collect from user before starting. Ask if not provided.

**Required:**
- **Document to validate**: path to document being checked
- **Source document(s)**: path(s) to source material for grounding

**Optional (ask if unspecified, offer defaults):**
- **Word count range**: min-max words (default: no constraint)
- **Tone**: e.g. first-person narrative, formal, technical, conversational (default: infer from document)
- **Style rules**: patterns to enforce or prohibit (default: none)
- **Target audience**: who document written for (default: general)
- **Section format rules**: bullet points, section lengths, heading structure (default: none)
- **Focus rules**: content excluded or prioritized (default: none)
- **Format rules**: encoding, spacing, links policy (default: UTF-8, single line spacing, no links)
- **Custom rules**: project-specific rules as key-value pairs

Store all criteria for both phases.

## Phase 1: Setup

Create `validation/` directory in project root (working directory). All validation artifacts go here.

```
validation/
├── criteria.md              <- collected criteria summary
├── grounding-report.md      <- Phase 2 output
├── compliance-checklist.md  <- Phase 3 output
├── validation-summary.md    <- Phase 4 output
└── <filename>_corrected.<ext> <- Phase 5 output (best-effort corrected copy)
```

Write `criteria.md` with collected criteria formatted clearly.

## Phase 2: Source Grounding Check

Extract every factual claim, assertion, attribution, number, date, quote from document. For each:

1. **State claim** exactly as in document
2. **Search source** for confirming evidence
3. **Mark status**:
   - CONFIRMED - supporting source fragment found (quote fragment)
   - UNCONFIRMED - no supporting evidence in source
   - CONTRADICTED - source contradicts claim (quote both)
   - INFERRED - reasonable inference, not directly stated (explain reasoning)
   - NOT APPLICABLE - structural/editorial, not fact-based

**Output format** (`grounding-report.md`):

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

UNCONFIRMED/CONTRADICTED claims: list concrete corrections.

## Phase 3: Compliance Checklist

Check document against all collected criteria. Generate `compliance-checklist.md`:

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

Use Python scripts for measurable checks (word count, point length, link detection) - never eyeball.

## Phase 4: Validation Summary

Generate `validation-summary.md` combining both phases:

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

Always produce corrected copy with fixable issues resolved after validation:

1. Copy original to `validation/<filename>_corrected.<ext>` (e.g. `report.md` -> `validation/report_corrected.md`)
2. Apply corrections from grounding report and compliance checklist:
   - UNCONFIRMED claims: rephrase to align with source or remove
   - CONTRADICTED claims: fix to match source evidence
   - Compliance failures: fix formatting, trim length, adjust tone
3. Re-run both checks (grounding + compliance) against corrected version
4. Update `validation-summary.md` with post-correction status
5. Present summary to user with diff of changes

## Important Notes

- **Never modify source document(s)** - read-only reference
- **All artifacts in `validation/`** - no scattered files
- **Python for measurements** - scripts for word counts, pattern matching, never manual
- **Quote evidence** - actual text from source/document, not just "confirmed"
- **Be specific** - violations cite exact offending text with location
- **Preserve originals** - corrected version always separate file in `validation/` with `_corrected` suffix. Overwrite original only on explicit user request
