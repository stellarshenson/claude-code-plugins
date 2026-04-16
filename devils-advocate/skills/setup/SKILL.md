---
name: setup
description: Set up devil's advocate persona and fact repository for a target document. Use when starting a new critical analysis. Builds the devil persona (role, biases, triggers) and harvests verified facts from source materials.
---

# Devil's Advocate - Setup

Build persona and fact repository. Always first step.

## Task Tracking

**MANDATORY**: Use TaskCreate/TaskUpdate for identifying target, building persona, harvesting facts. Mark in_progress/completed.

## Artefacts produced

1. **`devils_advocate.md`** - persona definition
2. **`fact_repository.md`** - verified claims

Place alongside target document.

## Step 1: Identify target document

Ask user which document. Read in full.

## Step 2: Build Devil Persona

**MANDATORY**: Persona BEFORE concerns.

### Source A: User-provided seed

Seed document (evaluation, review) alongside target. Infer persona from tone, priorities. Confirm with user.

### Source B: User describes persona

Ask ALL in ONE message:

"Describe the toughest reader for this document:
1. Who are they? (role, seniority)
2. What do they care about most? (cost, risk, timeline, compliance, quality)
3. Style? (data-driven, gut-feel, political, legalistic)
4. Default bias? (skeptical, risk-averse, cost-focused)
5. What triggers them? (blame-shifting, excuses, missing numbers)
6. What can they do? (approve, reject, escalate)"

### Source C: No seed or persona

**MUST ask.** Never proceed with generic concerns. One message:

"No persona provided. Either:
(a) Describe toughest reader (role, priorities, biases), OR
(b) List 2-4 roles and I'll build a composite devil"

For groups: merge priorities (union), harshest bias per persona, weight likelihood by which persona raises each concern.

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

Scan sources. Extract verifiable claims with sources.

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
- Separate user-provided from document-extracted
- Incremental - append, never overwrite

## When done

Tell user: "Persona and fact repository ready. Run `/devils-advocate:evaluate` for the baseline scorecard."
