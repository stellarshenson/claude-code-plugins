---
name: evaluate
description: Generate baseline devil's advocate evaluation. Produces concern catalogue with risk scores and scorecard. Requires setup to have been run first (devils_advocate.md and fact_repository.md must exist).
---

# Devil's Advocate - Evaluate (Baseline)

Generate the concern catalogue and scorecard. Run after setup.

**Prerequisites**: `devils_advocate.md` (persona) and `fact_repository.md` must exist. If not, tell the user to run `/devils-advocate:setup` first.

## Step 1: Read context

Read the target document, `devils_advocate.md` (persona), and `fact_repository.md` (facts) in full.

## Step 2: Generate concern catalogue

For each concern, score on two dimensions using Fibonacci scale (1, 2, 3, 5, 8):

- **Likelihood** (1-8): How likely this persona raises it
- **Impact** (1-8): How much damage if unaddressed
- **Risk = Likelihood x Impact** (1-64)

**Risk adjustment**: After initial catalogue, review the full set. Adjust where interactions amplify importance. Document: `Risk: N (adjusted from L x I = M, reason: ...)`.

**Concern template**:
```markdown
### N. "[Concern as the devil would phrase it]"

**Likelihood: N** | **Impact: N** | **Risk: N**

**Their take**: What the devil thinks. Write as them.

**Reality**: The factual counter. Reference fact_repository.md.

**Response**: How to address it.
```

**Categories to always evaluate** (persona-weighted):
- Accuracy gaps, trust signals, cognitive load, omissions
- Forward-looking, legal/contractual, professional responsibility

**No negative risk scores.** Strengths go in "Reality" and "Response", not as separate entries.

## Step 3: Scorecard

Score 0-100% per concern based on how well the document handles it.

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
- **Reasoning must reference specific text** from the document

**Top gaps**: List 5 concerns with highest residual. These are optimisation targets.

## Step 4: Explore options

For each high-residual concern, propose 2-4 options:

```markdown
### Concern #N: [name] (residual: X)

**Option A**: [specific change]
- Expected effect: #N +15%, #12 -5%

**Option B**: [structural change]
- Expected effect: #N +20%

**Recommendation**: [which and why]
```

## Step 5: Execution mode

ASK the user: "How should I run the scoring? Two options:

1. **In-session** (default) - I evaluate right here in this conversation. You see my reasoning live, can challenge scores, and we iterate together
2. **Standalone** - I run the evaluation via `claude -p` as an independent subprocess. Faster, no conversation overhead, but you only see the final scorecard

For initial evaluations, in-session is recommended so you can calibrate the devil's perspective. For re-scoring iterations where the persona is established, standalone is faster."

- **In-session**: proceed with Steps 2-4 above in the conversation
- **Standalone**: construct a prompt with persona + fact repository + target document content, run via `claude -p --model sonnet`, parse the output scorecard, append to `devils_advocate.md`

## When done

Tell the user: "Baseline evaluation complete. Score: [N] out of [max]. Run `/devils-advocate:iterate` to improve and re-score."

**If baseline score is already low** (< 30% of max): "Rather impressive start, I must say. The devil's struggling to find proper ammunition - score [N] out of [max]. Still, there are gaps worth closing."

**If baseline score is high** (> 70% of max): "Right. The devil has quite a lot to say. Score [N] out of [max] - there's real work to do here, but that's precisely what this exercise is for."
