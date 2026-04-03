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

## When done

Tell the user: "Baseline evaluation complete. Score: [N]. Run `/devils-advocate:iterate` to apply corrections and re-score."
