# Document Processing Workflow

Every document processing task runs three phases. Phase 1 produces draft - extract and synthesize from source documents. Phase 2 verifies draft against source material, catches unsupported claims and errors. Phase 3 applies uniformization rules, produces final polished output.

## Phase 1: Analyze & Draft

### Step 1.1: Read Source Materials
- Read all relevant input documents from `1-input/`
- Read reference materials from `4-references/` (examples for format guidance, facts for grounding anchors)
- Identify structure, key entities, dates, themes
- Catalogue what each source document contains
- Note document types (court rulings, correspondence, reports, transcriptions)


### Step 1.2: Create Analysis Plan
- Based on the objective, outline what information to extract
- Define the structure the output document needs
- Identify which sources are most relevant for which sections
- Note potential gaps where sources may not cover needed information

### Step 1.3: Generate Initial Draft
- Produce the first version of the target document
- Follow the structure defined in the analysis plan
- Include source references inline (document name, page/section)
- Save as `2-wip/<task-name>/<task-name>-draft-v1.md`

### Step 1.4: Generate Supplementary Sections
- If the output has structured sections (summaries, indices, annotations), generate them
- Each supplementary section gets its own draft artifact in WIP
- Save as `2-wip/<task-name>/<task-name>-<section-name>-draft.md`

### Phase 1 Gate
Display deliverables summary. In interactive/semi-automated mode, wait for user review before proceeding.

```
Phase 1 Complete: Analyze & Draft
Artifacts created:
- <task-name>-draft-v1.md
- <task-name>-<section>-draft.md (if applicable)
```

## Phase 2: Verify & Ground

### Step 2.1: Extract Assumptions
- Read the draft line by line
- For each factual claim, classify: DIRECT QUOTE / PARAPHRASE / INFERENCE / INTERPRETATION / UNSUPPORTED
- Focus on HIGH and MEDIUM impact claims (see GROUNDING.md for severity levels)
- Save as `2-wip/<task-name>/<task-name>-assumptions.md`

### Step 2.2: Verify Against Sources
- For each claim in the assumptions register, locate the supporting evidence in source documents
- Use the `grounding` skill / `document-processing ground` for the lexical pass - it returns per-claim scores plus line/column/paragraph/page/context, so you cite without rereading source. Add disciplined generative interpretation only when all lexical layers miss AND the claim is a synthesis/inference
- Then `document-processing check-consistency --document <draft> --output 2-wip/<task-name>/<task-name>-consistency-report.md` - the third step of the grounding chain: the draft checked against itself for divergences no source comparison can see (`42 users` here, `50 users` there)
- Quote the relevant source passage
- Set status: VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / CONTRADICTED
- Determine action: Keep / Revise / Remove / Qualify

### Step 2.3: Correct and Revise
- Apply all corrections from the assumptions register
- Fix ungrounded claims: remove unsupported assertions, strengthen weak references
- Add source qualifiers where needed ("According to the court ruling of...")
- Save corrected draft as `2-wip/<task-name>/<task-name>-draft-v2.md`

### Step 2.4: Generate Grounding Report
- Summarize verification results
- Count: total claims, verified, partially verified, unverified, contradicted
- List all corrections made
- Flag remaining risks
- Save as `2-wip/<task-name>/<task-name>-grounding-report.md`; the self-consistency findings are already in `<task-name>-consistency-report.md`

### Phase 2 Gate
Display verification summary. In interactive/semi-automated mode, wait for user review.

```
Phase 2 Complete: Verify & Ground
Claims verified: X/Y (Z contradictions found, W corrections applied)
Artifacts created:
- <task-name>-assumptions.md
- <task-name>-grounding-report.md
- <task-name>-consistency-report.md
- <task-name>-draft-v2.md
```

## Phase 3: Uniformize & Deliver

### Step 3.1: Apply Uniformization Checklist
- Evaluate the corrected draft against each task-specific rule (R1, R2, R3...)
- Measure actual values (word count, violation count, pattern matches)
- Record findings in checklist format
- Save as `2-wip/<task-name>/<task-name>-uniformization-checklist.md`

### Step 3.2: Execute Corrections
- Apply all required changes from the checklist
- Work through rules in priority order
- Each correction references the specific rule it addresses

### Step 3.3: Final Verification
- Re-run the full checklist on the corrected document
- Update all measurements
- Every rule must show PASS status

### Step 3.4: Deliver to Output
- Write final document to `3-output/<output-filename>.md`
- Update `3-output/README.md` manifest
- Update `2-wip/<task-name>/README.md` manifest

### Phase 3 Gate
Display final summary.

```
Phase 3 Complete: Uniformize & Deliver
All rules passed: R1 R2 R3 ...
Output: 3-output/<filename>.md
```

## Execution Modes

Ask user to select before execution begins:

**A) Interactive** - stop after every phase, display deliverables, wait for approval. Allows course correction.

**B) Semi-automated** - execute steps within each phase without stopping. Stop at phase boundaries for review.

**C) Headless** - execute all phases without interruption. Stop only at the end to present final output.

## Progress Indicators

After each step, display:

```
Phase: X of 3
Step: Y of Z (<step name>)
Progress: [progress bar]
Next: Step Y+1 - <next step name>
```

## INSTRUCTIONS.md Generation Template

When the skill generates a task-specific INSTRUCTIONS.md, it follows this skeleton:

```markdown
# <Task Title>

## Context
[From CLAUDE.md + user's objective description]

## Directory Structure
[Project's 1-input, 2-wip, 3-output with task-specific subfolder]

## Source Documents
[Catalogue of input files relevant to this task]

## Uniformization Rules
### R1: <Rule Name>
[Measurable criteria, examples]
### R2: <Rule Name>
[Measurable criteria, examples]
...

## Workflow

### Phase 1: Analyze & Draft
[Task-specific steps derived from the template above]

### Phase 2: Verify & Ground
[Task-specific verification steps]

### Phase 3: Uniformize & Deliver
[Task-specific uniformization steps]

## Execution
Select mode: A) Interactive, B) Semi-automated, C) Headless
```
