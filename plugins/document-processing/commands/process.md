---
description: Build a structured deliverable from input documents - analyze, draft, verify, uniformize, deliver
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe what to produce from the input documents"
---

# Document Processing - Process

Invoke `document-processing:process` skill with user objective. Skill refines objective, generates `INSTRUCTIONS.md` + `BENCHMARK.md` (each for user approval), scaffolds WIP folder, then runs four-phase workflow.

## Flow

1. Invoke `process` skill with user objective
2. Skill handles: objective refinement -> program generation -> benchmark generation -> scaffolding -> execution (Analyze & Draft -> Verify & Ground -> Uniformize & Deliver)
3. Verify & Ground phase invokes `grounding` skill for CLI-assisted claim grounding
4. All intermediate work -> `2-wip/<task-name>/`
5. Final output -> `3-output/`

## Prerequisites

- `1-input/` directory with source documents
- Optionally `4-references/` with examples and facts

## When NOT to use this

- Validating finished document against its source -> use `/document-processing:validate`
- Bare claim grounding (single claim or batch) -> use `/document-processing:grounding`
- Updating existing `3-output/` document -> use `/document-processing:update`

## Examples

```
/document-processing:process reconstruct complete timeline from all court documents
/document-processing:process draft response addressing mother's claims using evidence from hearings
/document-processing:process extract and categorize all findings by topic with source citations
/document-processing:process synthesize expert opinions into unified position paper
```
