---
name: process-documents
description: Design and execute structured document processing workflows. Takes an objective description, refines it through dialogue, generates INSTRUCTIONS.md and BENCHMARK.md, creates WIP folder structure, then executes. Use when asked to process, analyze, synthesize, extract, reconstruct, or transform documents from 1-input/ into structured outputs in 3-output/.
---

# Process Documents

Meta-skill for structured document processing. Does not process documents directly. Generates tailored processing program (INSTRUCTIONS.md + BENCHMARK.md) for specific objective, scaffolds WIP folder, executes.

## Invocation

`/process-documents <objective description>`

Objective describes what to produce from input documents. Examples:
- `/process-documents reconstruct complete timeline from all court documents`
- `/process-documents draft 2-page court statement addressing mother's claims`
- `/process-documents extract and categorize all court findings by topic`

## Execution Flow

### Phase 0: Objective Refinement

**Step 0.1**: Read all files in `1-input/` - catalogue available source material. Read `4-references/` for examples and universal facts. Read `.claude/CLAUDE.md` for project context.

**Step 0.2**: Present single consolidated set of clarifying questions:

1. **End state**: final document shape? Format, length, audience, language?
2. **Source scope**: which input documents? All, or specific ones?
3. **Quality criteria**: good vs bad output? Dealbreakers?
4. **Constraints**: what must NOT appear? Tone/perspective?
5. **Grounding priority**: how strictly must claims trace to source?
6. **Format rules**: structural requirements (date format, entry format, section order)?

**Step 0.3**: Iterate follow-ups if answers reveal ambiguity. Continue until objective is crystal clear.

**Step 0.4**: Summarize refined objective back to user for confirmation.

### Phase 1: Program Generation

Load reference documents:
- `references/WORKFLOW.md` - 3-phase workflow template
- `references/GROUNDING.md` - assumption verification methodology
- `references/UNIFORMIZATION.md` - quality control methodology
- `references/FOLDER-STRUCTURE.md` - folder conventions

Generate `INSTRUCTIONS.md` at project root containing:

1. **Context**: CLAUDE.md project context + user's refined objective
2. **Directory Structure**: project's 1-input, 2-wip, 3-output with task-specific WIP subfolder
3. **Source Documents**: catalogue of input files relevant to task
4. **Uniformization Rules**: task-specific R1, R2, R3... derived from:
   - User's stated quality criteria
   - Domain conventions (legal citation, date formats)
   - Output format requirements
   - Project-level markdown and typography standards from CLAUDE.md
5. **Workflow Steps**: 3-phase pattern from WORKFLOW.md (Analyze & Draft -> Verify & Ground -> Uniformize & Deliver)
6. **Phase Gates**: user review points between phases
7. **Execution Modes**: Interactive / Semi-automated / Headless

Present INSTRUCTIONS.md to user for approval. Do not proceed until approved.

### Phase 2: Benchmark Generation

From approved INSTRUCTIONS.md, generate `BENCHMARK.md` at project root containing:

1. **Scoring approach**: MINIMIZE penalty score (target: 0)
2. **Programmatic checks**: measurable criteria, verifiable by inspection or counting
   - Word count within range
   - Required sections present
   - Date format consistency
   - Forbidden patterns absent (grep-checkable)
3. **Grounding checks**: each HIGH-impact claim has source reference
4. **Rule compliance**: one checklist item per uniformization rule (R1, R2, R3...)
5. **Subjective quality** (sparingly): only for genuinely non-measurable aspects, with rubric and scale

Present BENCHMARK.md to user for approval. Do not proceed until approved.

### Phase 3: Scaffolding

- Derive task name from objective (kebab-case, e.g., `timeline-reconstruction`)
- Create `2-wip/<task-name>/` directory
- Create `2-wip/<task-name>/README.md` manifest (initially empty table)
- Ask user: execution mode A) Interactive, B) Semi-automated, C) Headless

### Phase 4: Execution

Execute INSTRUCTIONS.md step by step per selected mode.

- Show progress indicators after each step
- All WIP artifacts in `2-wip/<task-name>/`
- At each phase gate (interactive/semi-automated), display deliverables summary, wait for approval
- After Phase 3, evaluate final output against BENCHMARK.md
- Deliver final document to `3-output/`
- Update manifests in both `2-wip/<task-name>/` and `3-output/`

## Rules

- Never modify files in `1-input/`
- All intermediate artifacts in `2-wip/<task-name>/`
- Only final documents in `3-output/`
- `4-references/examples/` = format guidance only, never copy example content
- `4-references/facts/` = grounding anchors for universal facts (legal provisions, precedents)
- Every factual claim requires source reference (grounding)
- INSTRUCTIONS.md and BENCHMARK.md require explicit user approval before execution
- Phase gates mandatory in interactive and semi-automated modes
- Generated INSTRUCTIONS.md must be self-contained - inline all task-specific rules, never just point at reference files
