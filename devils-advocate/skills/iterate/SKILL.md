---
name: iterate
description: Re-evaluate document after corrections (auto or user-made) and produce updated scorecard. Can apply corrections autonomously or simply re-score a document the user has already modified.
---

# Devil's Advocate - Iterate

Re-evaluate the document and produce an updated scorecard. Two modes:

1. **Auto-correct**: Claude applies corrections from the scorecard's recommended options, then re-scores
2. **Re-score only**: User has already made corrections - just re-evaluate against the existing concern catalogue

**Prerequisites**: `devils_advocate.md` must contain a scorecard. If not, run `/devils-advocate:evaluate` first.

## FIRST: Ask the user

"Did you make corrections yourself, or should I apply corrections from the scorecard?"

- **User made corrections**: skip to Step 2 (re-evaluate). The user points to the updated document.
- **Auto-correct**: proceed with Step 1 (apply corrections) then Step 2 (re-evaluate).

## Step 1: Apply corrections (auto-correct mode only)

1. **Copy** current version as `<name>_v<NN+1>.md` (working copy)
2. **Apply** the recommended options from the scorecard's top gaps
3. **Track cross-concern tensions**: some fixes create new problems
   - Answering "why" may increase finger-pointing
   - Adding evidence may increase verbosity
   - Stronger language may worsen tone

## Step 2: Re-evaluate

Read the updated document (auto-corrected or user-modified) in full.

1. **Re-score** each concern against the new text
2. **Document score changes**: "Score changed from X% to Y% because [specific change]"
3. **Identify new concerns** introduced by changes - add to catalogue
4. **Recalculate overall score**
5. If auto-correct mode: **rename** working copy to `<name>_v<NN+1>_<score>.md`

## Step 3: Embed scorecard

**MANDATORY**: Every versioned document ends with an embedded scorecard:

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

Append new scorecard version. Keep previous scorecards for comparison.

**Propose options** for remaining high-residual concerns.

## Stopping criteria

Stop iterating when:
- Residual risk below 10% of total absolute risk
- Top remaining gaps have residual < 3.0 each
- Further corrections need scope changes beyond the document
- User accepts current score

The score must decrease each iteration. If not, corrections are creating new problems - stop and reassess.

## When done

Report: "Iteration complete. Score: [old] -> [new]. Top gaps: [list]. Run `/devils-advocate:iterate` again or accept current state."
