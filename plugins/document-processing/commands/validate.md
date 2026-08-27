---
description: Validate a document against rules and against its source - grounding plus tone/style/length/format compliance
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, AskUserQuestion]
argument-hint: "path to document to validate, and source material to check against"
---

# Validate Document

Invoke `document-processing:validate` skill. Runs two layers:

1. **Grounding** - extract every claim, verify each against source(s) via grounding CLI (delegated to `grounding` skill), plus intra-document self-consistency check
2. **Compliance** - tone, style, length, format, focus, plus any custom rules supplied as criteria

Produces artifacts in `validation/`: `criteria.md`, `claims.json`, `grounding-report.md`, `consistency-report.md`, `compliance-checklist.md`, `validation-summary.md`, plus best-effort `<filename>_corrected.<ext>`.

## When NOT to use this

- Bare claim grounding, no compliance layer -> use `/document-processing:grounding`
- Building new deliverable from sources -> use `/document-processing:process`
- Updating existing output -> use `/document-processing:update`

## Authoring compliance rules

`validate` skill asks for criteria (word range, tone, style rules, focus rules, format rules, custom rules). User unsure how to phrase them? Load rule examples shipped under `examples/` (plugin root) - real, in-use validation rule-sets showing what "final output must look like X" criteria look like in practice (measurable ranges, exclusion lists with example quotes, falsifiable test). Adapt shape, not content.
