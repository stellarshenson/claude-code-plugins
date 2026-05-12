---
description: Update an existing document processing output - re-verify, apply corrections, add new source material
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "what to update and why, e.g. 'add new hearing transcript to timeline'"
---

# Document Processing - Update

Invoke the `document-processing:update` skill. It updates an existing `3-output/` document with new information, corrections, re-applied rules, or re-verification against updated sources - and **always re-runs the grounding CLI on the changed content before declaring done** (step 5 of the skill is a gate, not optional).

## When to use

- New source document added to `1-input/` - re-run affected sections
- User found errors in `3-output/` document - correct and re-verify
- Grounding audit failed - fix unconfirmed claims
- Uniformization rules changed - re-apply to existing output
- Additional context available - enrich existing document

## Flow

1. The skill identifies what exists (`3-output/`, `2-wip/`, `INSTRUCTIONS.md`, `BENCHMARK.md`), asks what changed and which document, then does a targeted update (default) or a full re-run via the `process` skill
2. Mandatory grounding pass via the `grounding` skill: `document-processing extract-claims` on the changed doc -> review `claims.json` -> `document-processing batch-ground --claims ... --source <each 1-input/ source> --output validation/grounding-report.md` -> `document-processing check-consistency --document <doc> --output validation/consistency-report.md`; fix every UNCONFIRMED / CONTRADICTED claim and consistency finding
3. Re-verify against `BENCHMARK.md`, report score delta
4. WIP manifest updated with what changed, when, and the post-update grounding score

## When NOT to use this

- Building a new deliverable from scratch -> use `/document-processing:process`
- Validating a document you did not produce here -> use `/document-processing:validate`
- Bare claim grounding -> use `/document-processing:grounding`
