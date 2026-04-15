---
name: setup
description: Set up devil's advocate persona and fact repository for a target document. Use when starting a new critical analysis. Builds the devil persona (role, biases, triggers) and harvests verified facts from source materials.
---

# Devil's Advocate - Setup

Build devil persona and fact repository before any evaluation. Always first step.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout setup. Create tasks for identifying target, building persona, harvesting facts. Mark in_progress when starting, completed when done.

## Artefacts produced

1. **`devils_advocate.md`** - devil persona definition
2. **`fact_repository.md`** - verified claims from source materials

Place both alongside target document.

## Step 1: Identify target document

Ask user which document to evaluate. Read in full.

## Step 2: Build Devil Persona

**MANDATORY**: Persona established BEFORE any concerns generated.

### Source A: User-provided seed

User provides seed document (evaluation, review, critique) alongside target. Infer persona from seed's tone, priorities, concerns. Present inferred persona for confirmation.

### Source B: User describes persona

Ask ALL of these in ONE message (not one at a time):

"Describe the toughest reader for this document:
1. Who are they? (role, seniority)
2. What do they care about most? (cost, risk, timeline, compliance, quality)
3. Style? (data-driven, gut-feel, political, legalistic)
4. Default bias? (skeptical, risk-averse, cost-focused)
5. What triggers them? (blame-shifting, excuses, missing numbers)
6. What can they do? (approve, reject, escalate)"

### Source C: No seed or persona

**MUST ask.** Never proceed with generic concerns. Ask in ONE message:

"No persona provided. Please either:
(a) Describe the toughest reader (role, priorities, biases) in a few sentences, OR
(b) List 2-4 reader roles and I'll build a composite devil from their combined concerns"

For groups: merge priorities (union), take harshest bias from each, weight likelihood by which persona raises each concern.

### Persona documentation

Write to `devils_advocate.md`:

```markdown
# Devil's Advocate - [Project Name]

## The Devil

**Role**: [title and context]
**Cares about**: [2-3 priorities in order]
**Style**: [how they process information]
**Default bias**: [their starting stance]
**Triggers**: [what makes them react negatively]
**Decision**: [what they can do with the document]
**Source**: [seed-inferred / user-described / composite]

---
```

## Step 3: Harvest facts into fact_repository.md

Scan all available source materials. Extract verifiable claims with sources.

```markdown
# Fact Repository - [Project Name]

Verified claims sourced from codebase analysis.
No interpretation - just facts.

## Document facts
- [Claim with source reference]
- Source: [document, section/line]

## User-provided facts
- [Fact as stated by user]
- Source: user input

## Data facts
- [Metric or measurement]
- Source: [report, dataset]
```

**Rules**:
- Verbatim quotes for legal/contract text
- Separate user-provided from document-extracted facts
- Incremental updates - never overwrite, always append

## When done

Tell user: "Persona and fact repository ready. Run `/devils-advocate:evaluate` to generate the baseline scorecard."
