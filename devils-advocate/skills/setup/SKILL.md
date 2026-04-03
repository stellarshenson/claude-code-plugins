---
name: setup
description: Set up devil's advocate persona and fact repository for a target document. Use when starting a new critical analysis. Builds the devil persona (role, biases, triggers) and harvests verified facts from source materials.
---

# Devil's Advocate - Setup

Build the devil persona and fact repository before any evaluation begins. This is always the first step.

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

Ask:

1. **Who is the reader?** (title, role, seniority)
2. **What do they care about most?** (cost, risk, timeline, reputation, compliance, technical quality)
3. **What is their communication style?** (data-driven, gut-feel, political, legalistic)
4. **What is their default bias?** (skeptical, risk-averse, cost-focused, detail-oriented)
5. **What triggers them?** (blame-shifting, excuses, missing numbers, verbose language)
6. **What decision power do they have?** (approve/reject, recommend, escalate, negotiate)

### Source C: No seed or persona

**You must ask.** Do not proceed with generic concerns. Offer:

1. **Single persona** - "Who is the toughest reader?"
2. **Group of personas** - "List 2-4 reader roles for a composite devil"

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
