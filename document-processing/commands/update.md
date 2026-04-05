---
description: Update an existing document processing output - re-verify, apply corrections, add new source material
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "what to update and why, e.g. 'add new hearing transcript to timeline'"
---

# Document Processing - Update

Update an existing processed document with new information, corrections, or re-verification against updated sources.

## When to use

- New source document added to `1-input/` - re-run affected sections
- User found errors in `3-output/` document - correct and re-verify
- Grounding audit failed - fix unconfirmed claims
- Uniformization rules changed - re-apply to existing output
- Additional context available - enrich existing document

## Steps

1. **Identify what exists**: Read `3-output/` for the current document, `2-wip/` for the processing history, `INSTRUCTIONS.md` and `BENCHMARK.md` for the original program

2. **ASK user**:
   - What changed? (new source, found error, rule change, enrichment)
   - Which output document to update?
   - Full re-run or targeted update?

3. **Targeted update** (default - faster):
   - Read the existing output document
   - Apply the specific change (new source integration, error correction, rule reapplication)
   - Re-run grounding check on affected sections only
   - Re-run uniformization on affected sections
   - Update the document in place (versioned backup to `2-wip/`)

4. **Full re-run** (if structural changes needed):
   - Update INSTRUCTIONS.md with new context
   - Re-execute from Phase 1 using existing + new sources
   - Produces new version in `3-output/`

5. **Re-verify**: Run BENCHMARK.md evaluation against the updated document. Report score delta.

## Rules

- Always create a backup of the current output before modifying: copy to `2-wip/<task-name>/<filename>_prev.md`
- New source documents go to `1-input/` first - never process from arbitrary locations
- Grounding must be re-checked for any content changes
- Update the WIP manifest with what changed and when
