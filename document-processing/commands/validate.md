---
description: Validate a document against rules and against its source - grounding plus tone/style/length/format compliance
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "path to document to validate, and source material to check against"
---

# Validate Document

Invoke the `document-processing:validate` skill. It runs two layers:

1. **Grounding** - extract every claim, verify each against the source(s) via the grounding CLI (delegated to the `grounding` skill), plus an intra-document self-consistency check
2. **Compliance** - tone, style, length, format, focus, and any custom rules supplied as criteria

Produces artifacts in `validation/`: `criteria.md`, `claims.json`, `grounding-report.md`, `consistency-report.md`, `compliance-checklist.md`, `validation-summary.md`, and a best-effort `<filename>_corrected.<ext>`.

## When NOT to use this

- Bare claim grounding with no compliance layer -> use `/document-processing:grounding`
- Building a new deliverable from sources -> use `/document-processing:process`
- Updating an existing output -> use `/document-processing:update`

## Authoring compliance rules

The `validate` skill asks for criteria (word range, tone, style rules, focus rules, format rules, custom rules). If the user is unsure how to phrase them, load the rule examples shipped under `examples/` (plugin root) - real, in-use validation rule-sets that show what "the final output must look like X" criteria look like in practice (measurable ranges, exclusion lists with example quotes, a falsifiable test). Adapt the shape, not the content.
