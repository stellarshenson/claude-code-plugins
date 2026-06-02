---
description: Update an existing document processing output - re-verify, apply corrections, add new source material
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "what to update and why, e.g. 'add new hearing transcript to timeline'"
---

# Document Processing - Update

Invoke `document-processing:update` skill. Updates existing `3-output/` document with new info, corrections, re-applied rules, or re-verification against updated sources - and **always re-runs grounding CLI on changed content before declaring done** (step 5 of skill is gate, not optional).

## When to use

- New source document added to `1-input/` - re-run affected sections
- User found errors in `3-output/` document - correct and re-verify
- Grounding audit failed - fix unconfirmed claims
- Uniformization rules changed - re-apply to existing output
- Additional context available - enrich existing document

## Flow

1. Skill identifies what exists (`3-output/`, `2-wip/`, `INSTRUCTIONS.md`, `BENCHMARK.md`), asks what changed and which document, then does targeted update (default) or full re-run via `process` skill
2. Mandatory grounding pass via `grounding` skill: `document-processing extract-claims` on changed doc -> review `claims.json` -> `document-processing ground --manifest ... --source <each 1-input/ source> --output validation/grounding-report.md` -> `document-processing check-consistency --document <doc> --output validation/consistency-report.md`; fix every UNCONFIRMED / CONTRADICTED claim and consistency finding
3. Re-verify against `BENCHMARK.md`, report score delta
4. WIP manifest updated with what changed, when, and post-update grounding score

## When NOT to use this

- Building new deliverable from scratch -> use `/document-processing:process`
- Validating document you did not produce here -> use `/document-processing:validate`
- Bare claim grounding -> use `/document-processing:grounding`
