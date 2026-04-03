---
name: iterate
description: Apply corrections to the target document and re-score. Each iteration produces a versioned copy with embedded scorecard. Run after evaluate to improve the document score.
---

# Devil's Advocate - Iterate

Apply corrections from the evaluation and re-score. Each call produces one versioned correction pass.

**Prerequisites**: `devils_advocate.md` must contain a scorecard with options. If not, tell the user to run `/devils-advocate:evaluate` first.

## Step 1: Read context

Read the target document (or latest versioned copy), `devils_advocate.md` (scorecard + options), and `fact_repository.md`.

## Step 2: Apply corrections

1. **Copy** current version as `<name>_v<NN+1>.md` (working copy)
2. **Apply** the recommended options from the scorecard's top gaps
3. **Track cross-concern tensions**: some fixes create new problems
   - Answering "why" may increase finger-pointing
   - Adding evidence may increase verbosity
   - Stronger language may worsen tone

## Step 3: Re-evaluate

1. **Re-read** the updated document in full
2. **Re-score** each concern against the new text
3. **Document score changes**: "Score changed from X% to Y% because [specific change]"
4. **Identify new concerns** introduced by changes - add to catalogue
5. **Recalculate overall score**
6. **Rename** working copy to `<name>_v<NN+1>_<score>.md`

## Step 4: Embed scorecard

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

## Step 5: Update devils_advocate.md

Append new scorecard version. Keep previous scorecards for comparison.

**Propose options** for remaining high-residual concerns (same format as evaluate).

## Stopping criteria

Stop iterating when:
- Residual risk below 10% of total absolute risk
- Top remaining gaps have residual < 3.0 each
- Further corrections need scope changes beyond the document
- User accepts current score

## Version chain example

```
report.md                    # original (untouched)
report_v01_89.md             # baseline with scorecard
report_v02_34.md             # first correction
report_v03_12.md             # second correction
devils_advocate.md           # all scorecards accumulated
fact_repository.md           # updated incrementally
```

The score must decrease each iteration. If not, corrections are creating new problems - stop and reassess.

## When done

Report: "Iteration complete. Score: [old] -> [new]. Top gaps: [list]. Run `/devils-advocate:iterate` again or accept current state."
