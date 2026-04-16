---
name: evaluate
description: Generate baseline devil's advocate evaluation. Produces concern catalogue with risk scores and scorecard. Requires setup to have been run first (devils_advocate.md and fact_repository.md must exist).
---

# Devil's Advocate - Evaluate (Baseline)

Generate concern catalogue and scorecard. Run after setup.

## Task Tracking

**MANDATORY**: Use TaskCreate/TaskUpdate per step (read context, generate catalogue, score, create v01). Mark in_progress/completed.

**Prerequisites**: `devils_advocate.md` and `fact_repository.md` must exist. Otherwise: tell user to run `/devils-advocate:setup`.

## Step 1: Read context

Read target document, `devils_advocate.md`, `fact_repository.md` in full.

## Step 2: Generate concern catalogue

Fibonacci scale (1, 2, 3, 5, 8):

- **Likelihood** (1-8): chance persona raises it
- **Impact** (1-8): damage if unaddressed
- **Risk = Likelihood x Impact** (1-64)

**Risk adjustment**: review full set. Adjust where interactions amplify. Document: `Risk: N (adjusted from L x I = M, reason: ...)`.

**Concern template**:
```markdown
### N. "[Concern as the devil would phrase it]"

**Likelihood: N** | **Impact: N** | **Risk: N**

**Their take**: what devil thinks. Write as them.

**Reality**: factual counter. Reference fact_repository.md.

**Response**: how to address it.
```

**Categories** (persona-weighted):
- Accuracy gaps, trust signals, cognitive load, omissions
- Forward-looking, legal/contractual, professional responsibility

**No negative risk scores.** Strengths go in "Reality" and "Response".

## Step 3: Scorecard

Score 0-100% per concern.

| Score | Devil's reaction |
|-------|-----------------|
| 95-100% | "I have no issue" |
| 80-94% | "Fine, but I noticed..." |
| 60-79% | "Doesn't fully answer" |
| 40-59% | "This is a problem" |
| 20-39% | "You're hiding something" |
| 0-19% | "Makes it worse" |

**Scorecard format** (append to `devils_advocate.md`):

```markdown
## Scorecard v01 ([document name] as-is)

| # | Concern | Risk | Score | Residual | Reasoning |
|---|---------|------|-------|----------|-----------|
| 1 | [name] | 25 | 85% | 3.75 | [specific text reference + quality assessment] |
```

- **Residual** = `risk x (1 - score)`
- **Document score** = sum of residuals (minimise)
- **Reasoning MUST quote specific text**

**Top gaps**: top 5 residuals.

## Step 4: Explore options

Per high-residual concern, 2-4 options:

```markdown
### Concern #N: [name] (residual: X)

**Option A**: [specific change]
- Expected effect: #N +15%, #12 -5%

**Option B**: [structural change]
- Expected effect: #N +20%

**Recommendation**: [which and why]
```

## Step 5: Execution mode

ASK: "How to run scoring?

1. **In-session** (default) - evaluate in conversation. See reasoning live, challenge scores
2. **Standalone** - via `claude -p` subprocess. Faster, final scorecard only

Initial evaluations: in-session calibrates devil. Re-scoring iterations: standalone faster."

- **In-session**: run Steps 2-4 in conversation
- **Standalone**: construct prompt (persona + facts + target), run `claude -p --model sonnet`, parse scorecard, append to `devils_advocate.md`

## Step 6: Embed scorecard + rename

**MANDATORY**: Scored document carries scorecard and residual in filename.

1. Copy original as `<name>_v01.md`
2. Embed at end:
   ```markdown
   ---

   ## Document Scorecard (Devil's Advocate)

   **Persona**: [devil role and key bias]
   **Score**: [total residual risk] (lower = better, max [total absolute risk])

   | # | Concern | Risk | Score | Residual | How addressed |
   |---|---------|------|-------|----------|---------------|
   | 1 | [name] | [risk] | [0-100%] | [residual] | [specific text] |
   ```
3. **RENAME** to `<name>_v01_<score>.md`
4. Example: `report_v01.md` -> `report_v01_89.md`

Original NOT modified.

## When done

Tell user: "Baseline complete. Score: [N] out of [max]. Run `/devils-advocate:iterate` to improve."

**Baseline low** (< 30% of max): "Rather impressive start. Devil's struggling - score [N] out of [max]. Gaps worth closing still."

**Baseline high** (> 70% of max): "Devil has a lot to say. Score [N] out of [max] - real work to do."
