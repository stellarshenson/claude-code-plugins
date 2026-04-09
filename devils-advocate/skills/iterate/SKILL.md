---
name: iterate
description: Improve document based on devil's concerns, create versioned file, re-score, rename with residual. Clear 4-step workflow - improve, version, score, rename. Re-scores in place when user made changes outside Claude.
---

# Devil's Advocate - Iterate

One iteration cycle: improve the document, create a versioned copy, score it, rename with the residual.

**Prerequisites**: `devils_advocate.md` must contain a scorecard with top gaps. Run `/devils-advocate:evaluate` first if not.

## Step 1: Decide how to improve

ASK the user:

"Top concerns by residual risk:
[list top 5 from latest scorecard]

How to address them?
1. **Your suggestions** - tell me what to change
2. **Auto-apply** - I apply the recommended options from the scorecard
3. **Planning mode** - discuss each concern before changing
4. **You already edited** - skip to re-scoring (you made changes outside Claude)

Which? (or mix: 'auto for #1-3, discuss #4')"

## Step 2: Apply changes + create version

**If user chose 1, 2, or 3** (AI makes changes):

1. Determine next version number by scanning existing `<name>_v*.md` files
2. Copy current document as `<name>_v<NN>.md` (NO score suffix yet - that comes after scoring)
3. Apply changes to the versioned copy:
   - Mode 1: apply user's specific suggestions
   - Mode 2: apply recommended options from scorecard top gaps
   - Mode 3: apply agreed changes from planning discussion
4. Track which concerns each change targets
5. Track cross-concern tensions (fixing one may worsen another)

**If user chose 4** (user already edited):
- Skip to Step 3. No versioned copy - the user's document IS the current state.

## Step 3: Score

Re-read the document (versioned copy or user-edited original) in full.

ASK: "Score in-session or standalone (claude -p)?"
- **In-session**: score each concern here, show reasoning
- **Standalone**: run scoring via `claude -p` with persona + document content

For each concern:
1. Re-score 0-100% against the current text
2. Document: "Score changed from X% to Y% because [specific text change]"
3. Identify new concerns introduced by changes - add to catalogue
4. Recalculate total residual risk

## Step 4: Finalize version

**If AI made changes** (versioned copy exists):

1. Embed scorecard at the end of the versioned document:
   ```markdown
   ---

   ## Document Scorecard (Devil's Advocate)

   **Persona**: [devil role and key bias]
   **Score**: [total residual risk] (lower = better, max [total absolute risk])

   | # | Concern | Risk | Score | Residual | How addressed |
   |---|---------|------|-------|----------|---------------|
   | 1 | [name] | [risk] | [0-100%] | [residual] | [specific text] |
   ```

2. **RENAME** the file: `<name>_v<NN>.md` -> `<name>_v<NN>_<score>.md`
   - Score = rounded total residual risk
   - Example: `report_v02.md` -> `report_v02_34.md`
   - The `_<score>` suffix is MANDATORY. A file without it is incomplete.

3. Progression: `report_v01_89.md` -> `report_v02_34.md` -> `report_v03_12.md`

**If user edited outside Claude**:
- No file rename. Update `devils_advocate.md` only.

## Step 5: Update devils_advocate.md

ALWAYS (both modes):
1. Append new scorecard version to `devils_advocate.md`
2. Keep previous scorecards for comparison
3. Propose options for remaining high-residual concerns

## Step 6: Report + continue or stop

Report: "Iteration complete. Score: [old] -> [new]. Top gaps: [list]."

Check stopping criteria:
- Residual risk < 10% of total absolute risk -> **STOP**: "Target reached."
- Top gaps all < 3.0 residual -> **STOP**: "All concerns adequately addressed."
- Score didn't improve vs previous iteration -> **STOP**: "Stagnation - corrections creating new problems."
- User says stop -> **STOP**

If not stopping: "Continue with another `/devils-advocate:iterate`."

**Score drops >20%**: celebrate. "Jolly good show! From [old] to [new] - the devil's running out of ammunition."
