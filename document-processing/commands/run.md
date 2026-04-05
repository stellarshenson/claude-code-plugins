---
description: Run a document processing workflow - analyze, draft, verify, uniformize
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe what to produce from the input documents"
---

# Document Processing - Run

Execute the full process-documents workflow. The user provides an objective (what to produce from input documents), and the skill generates INSTRUCTIONS.md + BENCHMARK.md, scaffolds WIP folders, then executes.

## Flow

1. Invoke `document-processing:process-documents` skill with the user's objective
2. The skill handles: objective refinement -> program generation -> benchmark generation -> scaffolding -> execution
3. All intermediate work goes to `2-wip/<task-name>/`
4. Final output goes to `3-output/`

## Prerequisites

- `1-input/` directory with source documents
- Optionally `4-references/` with examples and facts

## Examples

```
/document-processing:run reconstruct complete timeline from all court documents
/document-processing:run draft response addressing mother's claims using evidence from hearings
/document-processing:run extract and categorize all findings by topic with source citations
/document-processing:run synthesize expert opinions into unified position paper
```
