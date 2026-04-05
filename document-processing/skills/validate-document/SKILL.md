---
name: validate-document
description: Validate a document against its source material for grounding, then check tone, style, length and format compliance. Use when asked to validate, verify, check grounding, or audit a document against a source.
---

# Document Validation Skill

Validate any document against its source material through two phases: (1) source grounding - extract claims and verify each against the source, and (2) compliance checking - verify tone, style, length, and format rules.

## Phase 0: Gather Criteria

Before starting, collect the following from the user. If not provided, ask for them.

**Required:**
- **Document to validate**: path to the document being checked
- **Source document(s)**: path(s) to the source material the document should be grounded in

**Optional (ask if not specified, offer sensible defaults):**
- **Word count range**: min-max words (default: no constraint)
- **Tone**: e.g. first-person narrative, formal, technical, conversational (default: infer from document)
- **Style rules**: specific patterns to enforce or prohibit (default: none)
- **Target audience**: who the document is written for (default: general)
- **Section format rules**: constraints on bullet points, section lengths, heading structure (default: none)
- **Focus rules**: content that should be excluded or prioritized (default: none)
- **Format rules**: encoding, spacing, links policy, etc. (default: UTF-8, single line spacing, no links)
- **Custom rules**: any additional project-specific rules as key-value pairs

Store all criteria for use in both phases.

## Phase 1: Setup

Create a `validation/` directory in the current project root (the working directory). All validation artifacts go here.

```
validation/
├── criteria.md              <- collected criteria summary
├── grounding-report.md      <- Phase 2 output
├── compliance-checklist.md  <- Phase 3 output
├── validation-summary.md    <- Phase 4 output
└── <filename>_corrected.<ext> <- Phase 5 output (best-effort corrected copy)
```

Write `criteria.md` with all collected criteria formatted clearly.

## Phase 2: Source Grounding Check

Extract every factual claim, assertion, attribution, number, date, and quote from the document. For each claim:

1. **State the claim** exactly as it appears in the document
2. **Search the source** for confirming evidence
3. **Mark status**:
   - CONFIRMED - source fragment found that supports the claim (quote the fragment)
   - UNCONFIRMED - no supporting evidence found in source
   - CONTRADICTED - source evidence contradicts the claim (quote both)
   - INFERRED - claim is a reasonable inference but not directly stated (explain reasoning)
   - NOT APPLICABLE - claim is structural/editorial, not fact-based

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

If UNCONFIRMED or CONTRADICTED claims are found, list concrete corrections.

## Phase 3: Compliance Checklist

Check the document against all collected criteria. Generate `compliance-checklist.md`:

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

Use Python scripts for measurable checks (word count, point length, link detection) rather than eyeballing.

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

After validation, always produce a corrected copy of the document with all fixable issues resolved:

1. Copy the original document to `validation/<filename>_corrected.<ext>` (e.g. `report.md` -> `validation/report_corrected.md`)
2. Apply all corrections identified in the grounding report and compliance checklist:
   - UNCONFIRMED claims: rephrase to align with source or remove
   - CONTRADICTED claims: fix to match source evidence
   - Compliance failures: fix formatting, trim length, adjust tone
3. Re-run both checks (grounding + compliance) against the corrected version
4. Update `validation-summary.md` with post-correction status
5. Present the summary to the user with a diff of changes made

## Important Notes

- **Never modify the source document(s)** - they are read-only reference
- **All artifacts in `validation/`** - do not scatter files elsewhere
- **Python for measurements** - use scripts for word counts, pattern matching, not manual counting
- **Quote evidence** - always include the actual text from source/document, not just "confirmed"
- **Be specific** - violations must cite the exact offending text with location
- **Preserve originals** - never modify the original document. The corrected version is always a separate file in `validation/` with `_corrected` suffix. Only overwrite the original if the user explicitly requests it
