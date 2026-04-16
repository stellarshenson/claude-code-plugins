---
name: process-documents
description: Design and execute structured document processing workflows. Takes an objective description, refines it through dialogue, generates INSTRUCTIONS.md and BENCHMARK.md, creates WIP folder structure, then executes. Use when asked to process, analyze, synthesize, extract, reconstruct, or transform documents from 1-input/ into structured outputs in 3-output/.
---

# Process Documents

Meta-skill for structured document processing. Generates tailored program (INSTRUCTIONS.md + BENCHMARK.md), scaffolds WIP folder, executes. Does not process documents directly.

## Invocation

`/process-documents <objective description>`

Objective describes what to produce. Examples:
- `/process-documents reconstruct complete timeline from all court documents`
- `/process-documents draft 2-page court statement addressing mother's claims`
- `/process-documents extract and categorize all court findings by topic`

## Execution Flow

### Phase 0: Objective Refinement

**Step 0.1**: Read all files in `1-input/` - catalogue sources. Read `4-references/` for examples and universal facts. Read `.claude/CLAUDE.md` for project context.

**Step 0.2**: Present consolidated clarifying questions:

1. **End state**: final shape? Format, length, audience, language?
2. **Source scope**: which input documents? All or specific?
3. **Quality criteria**: good vs bad output? Dealbreakers?
4. **Constraints**: what must NOT appear? Tone/perspective?
5. **Grounding priority**: how strictly must claims trace to source?
6. **Format rules**: structural requirements (date format, entry format, section order)?

**Step 0.3**: Iterate follow-ups until objective is crystal clear.

**Step 0.4**: Summarize refined objective for confirmation.

### Phase 1: Program Generation

Load references:
- `references/WORKFLOW.md` - 3-phase workflow template
- `references/GROUNDING.md` - assumption verification
- `references/UNIFORMIZATION.md` - quality control
- `references/FOLDER-STRUCTURE.md` - folder conventions

Generate `INSTRUCTIONS.md` at project root:

1. **Context**: CLAUDE.md context + refined objective
2. **Directory Structure**: 1-input, 2-wip, 3-output with task-specific WIP subfolder
3. **Source Documents**: catalogue of relevant inputs
4. **Uniformization Rules**: task-specific R1, R2, R3... from:
   - Stated quality criteria
   - Domain conventions (legal citation, date formats)
   - Output format requirements
   - CLAUDE.md markdown/typography standards
5. **Workflow Steps**: 3-phase pattern (Analyze & Draft -> Verify & Ground -> Uniformize & Deliver)
6. **Phase Gates**: user review points
7. **Execution Modes**: Interactive / Semi-automated / Headless

Present for approval. Do not proceed until approved.

### Phase 2: Benchmark Generation

From approved INSTRUCTIONS.md, generate `BENCHMARK.md`:

1. **Scoring approach**: MINIMIZE penalty score (target: 0)
2. **Programmatic checks**: measurable, verifiable
   - Word count within range
   - Required sections present
   - Date format consistency
   - Forbidden patterns absent (grep-checkable)
3. **Grounding checks**: each HIGH-impact claim has source reference
4. **Rule compliance**: one checklist item per uniformization rule
5. **Subjective quality** (sparingly): only for non-measurable aspects, with rubric

Present for approval. Do not proceed until approved.

### Phase 3: Scaffolding

- Derive task name from objective (kebab-case, e.g., `timeline-reconstruction`)
- Create `2-wip/<task-name>/`
- Create `2-wip/<task-name>/README.md` manifest (empty table)
- Ask: execution mode A) Interactive, B) Semi-automated, C) Headless

### Phase 4: Execution

Execute INSTRUCTIONS.md step by step per mode.

- Show progress after each step
- All WIP in `2-wip/<task-name>/`
- At each phase gate, display deliverables, wait for approval
- After Phase 3, evaluate against BENCHMARK.md
- Deliver final to `3-output/`
- Update manifests in both locations

## Rules

- Never modify `1-input/`
- Intermediate artifacts in `2-wip/<task-name>/`
- Only final documents in `3-output/`
- `4-references/examples/` = format guidance, never copy content
- `4-references/facts/` = grounding anchors (legal provisions, precedents)
- Every factual claim needs source reference
- INSTRUCTIONS.md and BENCHMARK.md need explicit approval before execution
- Phase gates MANDATORY in interactive and semi-automated modes
- INSTRUCTIONS.md must be self-contained - inline task-specific rules, never just reference files
