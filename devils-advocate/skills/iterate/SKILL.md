---
name: iterate
description: Improve document based on devil's concerns, create versioned file, re-score, rename with residual. Clear 4-step workflow - improve, version, score, rename. Re-scores in place when user made changes outside Claude.
---

# Devil's Advocate - Iterate

One cycle: improve, version, score, rename with residual.

## Task Tracking

**MANDATORY**: Use TaskCreate/TaskUpdate per step (decide, apply, score, finalize, update). Mark in_progress/completed.

**Prerequisites**: `devils_advocate.md` must have scorecard with top gaps. Otherwise run `/devils-advocate:evaluate` first.

## Step 1: Decide how to improve

ASK:

"Top concerns by residual risk:
[list top 5 from latest scorecard]

How to address them?
1. **Your suggestions** - tell me what to change
2. **Auto-apply** - I apply recommended options from scorecard
3. **Planning mode** - discuss each concern before changing
4. **You already edited** - skip to re-scoring (external edits)

Which? (or mix: 'auto for #1-3, discuss #4')"

## Step 2: Apply changes + create version

**If user chose 1, 2, or 3** (AI makes changes):

1. Determine next version - scan existing `<name>_v*.md`
2. Copy current as `<name>_v<NN>.md` (no score suffix yet)
3. Apply changes:
   - Mode 1: user's suggestions
   - Mode 2: recommended options from top gaps
   - Mode 3: agreed changes from planning
4. Track concerns each change targets
5. Track cross-concern tensions

**If user chose 4**: skip to Step 3. User's document IS current state.

## Step 3: Score

Re-read document in full.

ASK: "Score in-session or standalone (claude -p)?"
- **In-session**: score here, show reasoning
- **Standalone**: run via `claude -p` with persona + document

Per concern:
1. Re-score 0-100% against current text
2. Document: "Score X% -> Y% because [specific text change]"
3. Add new concerns from changes
4. Recalculate total residual

## Step 4: Finalize version

**If AI made changes** (versioned copy exists):

1. Embed scorecard at end:
   ```markdown
   ---

   ## Document Scorecard (Devil's Advocate)

   **Persona**: [devil role and key bias]
   **Score**: [total residual risk] (lower = better, max [total absolute risk])

   | # | Concern | Risk | Score | Residual | How addressed |
   |---|---------|------|-------|----------|---------------|
   | 1 | [name] | [risk] | [0-100%] | [residual] | [specific text] |
   ```

2. **RENAME**: `<name>_v<NN>.md` -> `<name>_v<NN>_<score>.md`
   - Score = rounded total residual
   - Example: `report_v02.md` -> `report_v02_34.md`
   - `_<score>` MANDATORY

3. Progression: `report_v01_89.md` -> `report_v02_34.md` -> `report_v03_12.md`

**If user edited externally**: no rename. Update `devils_advocate.md` only.

## Step 5: Update devils_advocate.md

Always:
1. Append new scorecard version
2. Keep previous scorecards
3. Propose options for remaining high-residual concerns

## Step 6: Report + continue or stop

Report: "Iteration complete. Score: [old] -> [new]. Top gaps: [list]."

Stopping criteria:
- Residual < 10% of total absolute risk -> **STOP**: "Target reached."
- Top gaps all < 3.0 -> **STOP**: "All concerns adequately addressed."
- Score didn't improve -> **STOP**: "Stagnation - corrections creating new problems."
- User says stop -> **STOP**

Otherwise: "Continue with another `/devils-advocate:iterate`."

**Score drops >20%**: "Jolly good show! From [old] to [new] - devil's running out of ammunition."
