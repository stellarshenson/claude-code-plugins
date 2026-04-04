---
name: iterate
description: Re-evaluate document after corrections and produce updated scorecard. Creates versioned files when AI makes changes. Re-scores in place when user made changes outside Claude.
---

# Devil's Advocate - Iterate

Re-evaluate the document and produce an updated scorecard. Called after `improve` applies changes.

**Prerequisites**: `devils_advocate.md` must contain a scorecard. If not, run `/devils-advocate:evaluate` first.

## Determine mode

Two modes based on who made the changes:

- **AI made changes** (came from `improve` skill): a versioned copy `<name>_v<NN+1>.md` exists with corrections applied. Re-score it, add embedded scorecard, rename with score suffix.
- **User made changes outside Claude**: no versioned copy. Re-read the original document in its current state, re-score against the existing concern catalogue, update `devils_advocate.md` with new scorecard.

## Step 1: Re-evaluate

Read the document (versioned copy or current original) in full.

1. **Re-score** each concern against the current text
2. **Document score changes**: "Score changed from X% to Y% because [specific text change]"
3. **Identify new concerns** introduced by changes - add to catalogue
4. **Update cross-concern tension notes**
5. **Recalculate overall score** - total residual risk

## Step 2: Versioned file handling

**If AI made changes** (versioned copy exists):
- Embed scorecard at end of the versioned document (see format below)
- Rename to `<name>_v<NN+1>_<score>.md` where score is rounded residual risk
- This creates the audit trail: `report_v01_89.md` -> `report_v02_34.md` -> `report_v03_12.md`

**If user made changes outside Claude**:
- Do NOT create a versioned copy
- The user's document IS the current state
- Only update `devils_advocate.md` with the new scorecard

## Step 3: Embed scorecard (versioned files only)

**MANDATORY**: Every AI-created versioned document ends with:

```markdown
---

## Document Scorecard (Devil's Advocate)

**Persona**: [devil role and key bias]
**Score**: [total residual risk] (lower = better, max [total absolute risk])

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | [name] | [risk] | [0-100%] | [residual] | [specific text reference] |
```

## Step 4: Update devils_advocate.md

**ALWAYS** (both modes): append new scorecard version to `devils_advocate.md`. Keep previous scorecards for comparison across versions.

**Propose options** for remaining high-residual concerns - these feed into the next `improve` cycle.

## Stopping criteria

Report whether stopping criteria are met:
- Residual risk below 10% of total absolute risk
- Top remaining gaps have residual < 3.0 each
- Score stopped improving (stagnation - same or worse than previous iteration)
- User accepts current score

The score must decrease each iteration. If not, corrections are creating new problems - stop and reassess.

## When done

Report: "Iteration complete. Score: [old] -> [new]. Top gaps: [list]."

If stopping criteria met: "Stopping criteria reached. Accept current state or continue with `/devils-advocate:improve`."

If not met: "Continue with `/devils-advocate:improve` to address remaining gaps."

**When score drops significantly** (>20% improvement): celebrate with creative British-style cheers.
