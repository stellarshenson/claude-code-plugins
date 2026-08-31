---
name: process
description: Build a structured deliverable FROM source files - reconstruct a timeline, draft a statement, assemble a catalogue, synthesize a position paper from 1-input/ sources into a traceable 3-output/ document. Generates a tailored INSTRUCTIONS.md + BENCHMARK.md, scaffolds 2-wip/, runs analyze, draft, verify, uniformize, deliver. NOT for checking an existing document against a source (use the `validate` skill) and NOT for bare claim grounding (use the `grounding` skill) - this skill produces a new document.
---

# Process - Structured Document Build

Meta-skill for structured document production. Generates tailored program (INSTRUCTIONS.md + BENCHMARK.md), scaffolds WIP folder, runs the five-stage build flow. Does not process documents directly - orchestrates.

**Scope boundary.** This skill *builds* deliverable from sources. Not the verification path: validating finished document against source for grounding + tone/style/format compliance = `validate` skill; running grounding CLI over claims (single or batch via `source_map.yaml`) = `grounding` skill. Verify & Ground phase below *invokes* `grounding` skill rather than re-implementing grounding.

## Pre-flight install (MANDATORY - run every session, no asking)

Always run this single line BEFORE invoking `document-processing`. The upgrade always runs; a version mismatch blocks:

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

**Run the CLI without touching the caller's project.** The gate above puts it on PATH, so the bare command name is the whole invocation. `uv run` instead resolves whatever project the working directory sits in and writes `uv.lock` and `.venv` into it, so if you reach for uv pass `--no-project` (`uv run --no-project <cli> ...`) - it skips project discovery, leaves the tree untouched and still finds the same PATH binary. `--no-sync` and `--frozen` are not substitutes; both still create `.venv`.

Never ask the user whether to install - just run the line.

## Invocation

`/document-processing:process <objective description>`

Objective describes what to produce. Examples:
- `/document-processing:process reconstruct complete timeline from all court documents`
- `/document-processing:process draft 2-page court statement addressing mother's claims`
- `/document-processing:process extract and categorize all court findings by topic`

## Execution Flow

### Stage 0: Objective Refinement

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

### Stage 1: Program Generation

Load references:
- `references/WORKFLOW.md` - 3-phase workflow template
- `references/GROUNDING.md` - assumption classification + verification methodology for the draft (DIRECT QUOTE / PARAPHRASE / INFERENCE / INTERPRETATION / UNSUPPORTED)
- `references/UNIFORMIZATION.md` - quality control
- `references/FOLDER-STRUCTURE.md` - folder conventions

For CLI-assisted grounding of HIGH-impact claims during Phase 2 (Verify & Ground), invoke the **`grounding`** skill / `document-processing ground` - it carries the deterministic three-layer lexical grounder (+ optional semantic), the OCR fallback chain, and the verdict rules. `references/GROUNDING.md` is the classification methodology; the `grounding` skill is the operational tool.

When deriving uniformization rules, load the real rule-set examples in `${CLAUDE_PLUGIN_ROOT}/examples/` - a full in-use `INSTRUCTIONS.md` with measurable rules R0-R4 (no-fluff, length range with a preferred band, focus exclusions with example quotes, text format, list-section format) plus a worked uniformization checklist. Use them to make every rule *measurable* (word ranges, per-bullet word counts, exclusion lists with example quotes, a falsifiable "does this sentence change what the reader knows" test). Adapt the shape, not the content.

Generate `INSTRUCTIONS.md` at project root:

1. **Context**: CLAUDE.md context + refined objective
2. **Directory Structure**: 1-input, 2-wip, 3-output with task-specific WIP subfolder
3. **Source Documents**: catalogue of relevant inputs
4. **Uniformization Rules**: task-specific R1, R2, R3... from:
   - Stated quality criteria
   - Domain conventions (legal citation, date formats)
   - Output format requirements
   - CLAUDE.md markdown/typography standards
   - The rule-set examples in `${CLAUDE_PLUGIN_ROOT}/examples/` (shape reference)
5. **Workflow Steps**: 3-phase pattern (Analyze & Draft -> Verify & Ground -> Uniformize & Deliver)
6. **Phase Gates**: user review points
7. **Execution Modes**: Interactive / Semi-automated / Headless

Present for approval. Do not proceed until approved.

### Stage 2: Benchmark Generation

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

### Stage 3: Scaffolding

- Derive task name from objective (kebab-case, e.g., `timeline-reconstruction`)
- Create `2-wip/<task-name>/`
- Create `2-wip/<task-name>/README.md` manifest (empty table)
- Ask: execution mode A) Interactive, B) Semi-automated, C) Headless

### Stage 4: Execution

Execute INSTRUCTIONS.md step by step per mode.

- Show progress after each step
- All WIP in `2-wip/<task-name>/`
- At each phase gate, display deliverables, wait for approval
- After the inner Phase 3 (Uniformize & Deliver), evaluate against BENCHMARK.md
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
