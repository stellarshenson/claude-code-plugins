---
name: process-documents
description: Design and execute structured document processing workflows. Takes an objective description, refines it through dialogue, generates INSTRUCTIONS.md and BENCHMARK.md, creates WIP folder structure, then executes. Use when asked to process, analyze, synthesize, extract, reconstruct, or transform documents from 1-input/ into structured outputs in 3-output/.
---

# Process Documents

A meta-skill for structured document processing. When invoked, it does not directly process documents. Instead it generates a tailored processing program (INSTRUCTIONS.md + BENCHMARK.md) for the specific objective, scaffolds the WIP folder, then executes.

## Invocation

`/process-documents <objective description>`

The objective describes what to produce from the input documents. Examples:
- `/process-documents reconstruct complete timeline from all court documents`
- `/process-documents draft 2-page court statement addressing mother's claims`
- `/process-documents extract and categorize all court findings by topic`

## Execution Flow

### Phase 0: Objective Refinement

**Step 0.1**: Read all files in `1-input/` to catalogue available source material. Read `4-references/` for examples and universal facts. Read `.claude/CLAUDE.md` for project context.

**Step 0.2**: Present a single consolidated set of clarifying questions to the user:

1. **End state**: What does the final document look like? Format, length, audience, language?
2. **Source scope**: Which input documents to use? All, or specific ones?
3. **Quality criteria**: What makes this output good vs bad? What are the dealbreakers?
4. **Constraints**: What must NOT appear? What tone/perspective?
5. **Grounding priority**: How strictly must claims be traceable to source documents?
6. **Format rules**: Any specific structural requirements (date format, entry format, section order)?

**Step 0.3**: Iterate on follow-up questions if user's answers reveal ambiguity. Continue until the objective is crystal clear.

**Step 0.4**: Summarize the refined objective back to the user for confirmation.

### Phase 1: Program Generation

Load reference documents:
- `references/WORKFLOW.md` - 3-phase workflow template
- `references/GROUNDING.md` - assumption verification methodology
- `references/UNIFORMIZATION.md` - quality control methodology
- `references/FOLDER-STRUCTURE.md` - folder conventions

Generate `INSTRUCTIONS.md` at project root containing:

1. **Context**: From CLAUDE.md project context + user's refined objective
2. **Directory Structure**: Project's 1-input, 2-wip, 3-output with task-specific WIP subfolder
3. **Source Documents**: Catalogue of input files relevant to this task
4. **Uniformization Rules**: Task-specific R1, R2, R3... derived from:
   - User's stated quality criteria
   - Domain conventions (legal citation requirements, date formats)
   - Output format requirements
   - Project-level markdown and typography standards from CLAUDE.md
5. **Workflow Steps**: Following the 3-phase pattern from WORKFLOW.md (Analyze & Draft -> Verify & Ground -> Uniformize & Deliver)
6. **Phase Gates**: User review points between phases
7. **Execution Modes**: Interactive / Semi-automated / Headless

Present INSTRUCTIONS.md to user for approval. Do not proceed until approved.

### Phase 2: Benchmark Generation

Based on approved INSTRUCTIONS.md, generate `BENCHMARK.md` at project root containing:

1. **Scoring approach**: MINIMIZE penalty score (target: 0)
2. **Programmatic checks**: Measurable criteria that can be verified by inspection or counting
   - Word count within range
   - Required sections present
   - Date format consistency
   - Forbidden patterns absent (grep-checkable)
3. **Grounding checks**: Each HIGH-impact claim has source reference
4. **Rule compliance**: One checklist item per uniformization rule (R1, R2, R3...)
5. **Subjective quality** (sparingly): Only for genuinely non-measurable aspects, with rubric and scale

Present BENCHMARK.md to user for approval. Do not proceed until approved.

### Phase 3: Scaffolding

- Derive task name from the objective (kebab-case, e.g., `timeline-reconstruction`)
- Create `2-wip/<task-name>/` directory
- Create `2-wip/<task-name>/README.md` manifest (initially empty table)
- Ask user to select execution mode: A) Interactive, B) Semi-automated, C) Headless

### Phase 4: Execution

Execute INSTRUCTIONS.md step by step following the selected execution mode.

- Show progress indicators after each step
- Create all WIP artifacts in `2-wip/<task-name>/`
- At each phase gate (in interactive/semi-automated modes), display deliverables summary and wait for approval
- After Phase 3 completion, evaluate final output against BENCHMARK.md
- Deliver final document to `3-output/`
- Update manifests in both `2-wip/<task-name>/` and `3-output/`

## Rules

- Never modify files in `1-input/`
- All intermediate artifacts go to `2-wip/<task-name>/`
- Only final documents go to `3-output/`
- `4-references/examples/` provides format guidance only - never copy content from examples
- `4-references/facts/` provides grounding anchors for universal facts (legal provisions, precedents)
- Every factual claim must have a source reference (grounding)
- INSTRUCTIONS.md and BENCHMARK.md require explicit user approval before execution
- Phase gates are mandatory in interactive and semi-automated modes
- The generated INSTRUCTIONS.md must be self-contained - inline all task-specific rules, do not just point to reference files
