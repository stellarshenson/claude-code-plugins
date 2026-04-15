---
name: evaluate
description: Generate baseline devil's advocate evaluation. Produces concern catalogue with risk scores and scorecard. Requires setup to have been run first (devils_advocate.md and fact_repository.md must exist).
---

# Devil's Advocate - Evaluate (Baseline)

Generate concern catalogue and scorecard. Run after setup.

## Task Tracking

**MANDATORY**: Use Claude Code task tracking (TaskCreate/TaskUpdate) throughout evaluation. Create tasks per step (read context, generate catalogue, score, create v01). Mark in_progress when starting, completed when done.

**Prerequisites**: `devils_advocate.md` (persona) and `fact_repository.md` must exist. Otherwise tell user to run `/devils-advocate:setup` first.

## Step 1: Read context

Read target document, `devils_advocate.md` (persona), `fact_repository.md` (facts) in full.

## Step 2: Generate concern catalogue

Per concern, score two dimensions, Fibonacci scale (1, 2, 3, 5, 8):

- **Likelihood** (1-8): how likely persona raises it
- **Impact** (1-8): damage if unaddressed
- **Risk = Likelihood x Impact** (1-64)

**Risk adjustment**: after initial catalogue, review full set. Adjust where interactions amplify importance. Document: `Risk: N (adjusted from L x I = M, reason: ...)`.

**Concern template**:
```markdown
### N. "[Concern as the devil would phrase it]"

**Likelihood: N** | **Impact: N** | **Risk: N**

**Their take**: what devil thinks. Write as them.

**Reality**: factual counter. Reference fact_repository.md.

**Response**: how to address it.
```

**Categories to always evaluate** (persona-weighted):
- Accuracy gaps, trust signals, cognitive load, omissions
- Forward-looking, legal/contractual, professional responsibility

**No negative risk scores.** Strengths go in "Reality" and "Response", not as separate entries.

## Step 3: Scorecard

Score 0-100% per concern based on how well document handles it.

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
- **Document score** = sum of all residuals (minimise this)
- **Reasoning MUST reference specific text** from document

**Top gaps**: 5 concerns with highest residual. Optimisation targets.

## Step 4: Explore options

Per high-residual concern, propose 2-4 options:

```markdown
### Concern #N: [name] (residual: X)

**Option A**: [specific change]
- Expected effect: #N +15%, #12 -5%

**Option B**: [structural change]
- Expected effect: #N +20%

**Recommendation**: [which and why]
```

## Step 5: Execution mode

ASK user: "How should I run scoring? Two options:

1. **In-session** (default) - evaluate here in conversation. See reasoning live, challenge scores, iterate together
2. **Standalone** - evaluation via `claude -p` subprocess. Faster, no conversation overhead, final scorecard only

Initial evaluations: in-session recommended - calibrates devil's perspective. Re-scoring iterations, persona established: standalone faster."

- **In-session**: proceed with Steps 2-4 above in conversation
- **Standalone**: construct prompt with persona + fact repository + target document content, run via `claude -p --model sonnet`, parse output scorecard, append to `devils_advocate.md`

## Step 6: Embed scorecard in target document + rename

**MANDATORY**: Scored document must carry own scorecard and residual in filename.

1. Copy original target document as `<name>_v01.md` (first version)
2. Embed scorecard at end of `<name>_v01.md`:
   ```markdown
   ---

   ## Document Scorecard (Devil's Advocate)

   **Persona**: [devil role and key bias]
   **Score**: [total residual risk] (lower = better, max [total absolute risk])

   | # | Concern | Risk | Score | Residual | How addressed |
   |---|---------|------|-------|----------|---------------|
   | 1 | [name] | [risk] | [0-100%] | [residual] | [specific text] |
   ```
3. **RENAME** to `<name>_v01_<score>.md` where score = rounded total residual
4. Example: `report_v01.md` -> `report_v01_89.md`

Original document NOT modified. `_v01_<score>.md` file = first scored snapshot.

## When done

Tell user: "Baseline evaluation complete. Score: [N] out of [max]. Run `/devils-advocate:iterate` to improve and re-score."

**Baseline already low** (< 30% of max): "Rather impressive start, I must say. The devil's struggling to find proper ammunition - score [N] out of [max]. Still, gaps worth closing."

**Baseline high** (> 70% of max): "Right. The devil has quite a lot to say. Score [N] out of [max] - real work to do here, but that's precisely what this exercise is for."
