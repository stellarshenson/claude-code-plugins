---
name: update
description: Update an existing processed document in 3-output/ - add a new source to 1-input/, apply corrections found in the output, re-apply changed uniformization rules, or re-verify against updated sources. Always re-runs the grounding CLI on the changed content before declaring done. Use when asked to update the document, add a new source to the timeline, re-verify after sources changed, or apply corrections to an output.
---

# Update Skill

Update existing processed document with new info, corrections, or re-verification against updated sources. **Every update ends with mandatory CLI-grounding pass on changed content** - no silent skip - any content change can introduce ungrounded claim.

## Pre-flight install (MANDATORY - run every session, no asking)

```bash
python3 -c "import stellars_claude_code_plugins" 2>/dev/null || python3 -m pip install --user --upgrade stellars-claude-code-plugins
```

No-op when package importable; auto-installs when missing OR when stale shim on PATH but package uninstalled in active Python. Never ask - just run the line.

## When to use

- New source document added to `1-input/` - re-run affected sections
- User found errors in `3-output/` document - correct and re-verify
- Grounding audit failed - fix unconfirmed claims
- Uniformization rules changed - re-apply to existing output
- Additional context available - enrich existing document

## Steps

1. **Identify what exists**: Read `3-output/` for the current document, `2-wip/` for the processing history, `INSTRUCTIONS.md` and `BENCHMARK.md` for the original program.

2. **ASK user**:
   - What changed? (new source, found error, rule change, enrichment)
   - Which output document to update?
   - Full re-run or targeted update?

3. **Targeted update** (default - faster):
   - Read the existing output document
   - Apply the specific change (new source integration, error correction, rule reapplication)
   - Re-run uniformization on affected sections
   - Update the document in place (versioned backup to `2-wip/<task-name>/<filename>_prev.md` first)

4. **Full re-run** (if structural changes needed):
   - Update `INSTRUCTIONS.md` with new context
   - Re-execute from Phase 1 of the `process` skill using existing + new sources
   - Produces new version in `3-output/`

5. **MANDATORY grounding pass** (every update, no exception): run the grounding CLI on the updated content via the `grounding` skill -
   - `document-processing extract-claims --document <updated doc> --output validation/claims.json`, review `validation/claims.json`
   - `document-processing ground --manifest validation/claims.json --source <src1> --source <src2> ... --output validation/grounding-report.md` (one `--source` per `1-input/` source; pass `--semantic` to enable the semantic + NLI layers, opt-in per call, unless the user declined for this session; see the `grounding` skill)
   - `document-processing check-consistency --document <updated doc> --output validation/consistency-report.md`
   Fix any UNCONFIRMED / CONTRADICTED claim and any consistency finding before declaring done. Apply the `grounding` skill's verdict rules.

6. **Re-verify against benchmark**: Run `BENCHMARK.md` evaluation against the updated document. Report the score delta.

## Rules

- Always create a backup of the current output before modifying: copy to `2-wip/<task-name>/<filename>_prev.md`
- New source documents go to `1-input/` first - never process from arbitrary locations
- Grounding is re-run on any content change - this is not optional and not "if time permits"; step 5 is a gate
- `1-input/` stays read-only; never modify source material
- Update the WIP manifest with what changed, when, and the post-update grounding score
- The grounding mechanics live in the `grounding` skill - this skill calls them, never re-implements them
