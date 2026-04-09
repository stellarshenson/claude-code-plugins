---
name: setup
description: Set up devil's advocate persona and fact repository for a target document. Use when starting a new critical analysis. Builds the devil persona (role, biases, triggers) and harvests verified facts from source materials.
---

# Devil's Advocate - Setup

Build the devil persona and fact repository before any evaluation begins. This is always the first step.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout setup. Create tasks for identifying target, building persona, harvesting facts. Mark each in_progress when starting, completed when done.

## Artefacts produced

1. **`devils_advocate.md`** - Devil persona definition
2. **`fact_repository.md`** - Verified claims from source materials

Place both alongside the target document.

## Step 1: Identify the target document

Ask the user which document to evaluate. Read it in full.

## Step 2: Build the Devil Persona

**MANDATORY**: The persona must be established before any concerns are generated.

### Source A: User-provided seed

The user provides a seed document (evaluation, review, critique) alongside the target. Infer the persona from the seed's tone, priorities, and concerns. Present the inferred persona for confirmation.

### Source B: User describes the persona

Ask ALL of these in ONE message (do not ask one at a time):

"Describe the toughest reader for this document:
1. Who are they? (role, seniority)
2. What do they care about most? (cost, risk, timeline, compliance, quality)
3. Style? (data-driven, gut-feel, political, legalistic)
4. Default bias? (skeptical, risk-averse, cost-focused)
5. What triggers them? (blame-shifting, excuses, missing numbers)
6. What can they do? (approve, reject, escalate)"

### Source C: No seed or persona

**You must ask.** Do not proceed with generic concerns. Ask in ONE message:

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
- Update incrementally - never overwrite, always append

## When done

Tell the user: "Persona and fact repository ready. Run `/devils-advocate:evaluate` to generate the baseline scorecard."
