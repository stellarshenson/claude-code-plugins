---
name: run
description: Run the full devil's advocate workflow end-to-end. Setup persona, evaluate baseline, then iterate corrections until residual risk is acceptable. Use when the user wants the complete analysis in one go.
---

# Devil's Advocate - Critical Document Analysis

Critique a document from its toughest audience. Generate pushback, score responses, produce improvements. Visuals via `svg-infographics`.

## Install (MANDATORY for visuals)

```bash
pip install stellars-claude-code-plugins
```

Ships `svg-infographics` CLI used for generating pushback-response visuals. Required when any concern triggers a visual option (cognitive load, number exhaustion, metric confusion). Verify: `svg-infographics --help`.

## Task Tracking

**MANDATORY**: Use TaskCreate/TaskUpdate for setup, evaluation, each iteration. Mark in_progress/completed.

## Workflow

Three artefacts in target document directory:

1. **`devils_advocate.md`** - persona, concerns, scoring, responses
2. **`fact_repository.md`** - verified claims from sources + user input
3. **Scorecard** - embedded in `devils_advocate.md`

Optional: SVG infographics via `svg-infographics` skill.

## Step 1: Build Devil Persona

**MANDATORY**: Persona BEFORE concerns. Three sources:

### Source A: User-provided seed

Seed document (evaluation, review) alongside target. Infer persona from tone, priorities. Confirm with user.

### Source B: User describes persona

Ask:

1. **Who is the reader?** (title, role, seniority)
2. **What do they care about?** (cost, risk, timeline, reputation, compliance, technical quality)
3. **Communication style?** (data-driven, gut-feel, political, legalistic)
4. **Default bias?** (skeptical, risk-averse, cost-focused, detail-oriented)
5. **Triggers?** (blame-shifting, excuses, missing numbers, verbose language)
6. **Decision power?** (approve/reject, recommend, escalate, negotiate)

### Source C: No seed or persona

**MUST ask**. Never proceed with generic concerns. Offer:

1. **Single persona** - "Who is the toughest reader? Role, priorities, biases?"
2. **Group of personas** - "List 2-4 roles. I'll build a composite devil"

**Group**: merge priorities (union), take harshest bias per persona, weight likelihood by which persona raises each concern. Document each contributor and composite.

### Persona documentation

Top of `devils_advocate.md`:

```markdown
# Devil's Advocate - [Project Name]

## The Devil

**Role**: [title and context]
**Cares about**: [2-3 priorities in order]
**Style**: [how they process information]
**Default bias**: [their starting stance]
**Triggers**: [what makes them react negatively]
**Decision**: [what they can do with the document]
**Source**: [seed-inferred / user-described / composite from N personas]

---
```

Composite: add subsection per contributing persona before merged profile.

Persona shapes every concern. Without it: generic concerns, meaningless scoring.

## Step 2: Harvest facts into fact_repository.md

Scan sources, extract verifiable claims. Every fact MUST have source.

**Structure**:
```markdown
# Fact Repository - [Project Name]

Verified claims sourced from contracts, test data, project history, and stakeholder input.
No interpretation - just facts.

## Contract clauses
> *"Exact quote from contract/SOW"*
- Source: [document name, section/line reference]

## User-provided facts
- [Fact as stated by user]
- Source: user input, [date or session reference]

## Data facts
- [Metric or measurement with source]
- Source: [test report, dataset, analysis output]

## Historical facts
- [Decision, event, or timeline fact]
- Source: [meeting notes, email, git history]
```

**Rules**:
- Verbatim quotes for contract clauses - never paraphrase legal text
- Separate user-provided from document-extracted facts
- Include mathematical derivations where relevant
- Incremental - append and deduplicate, never overwrite
- User gives new facts during iteration: append to right section

## Step 3: Generate concern catalogue

Per concern, Fibonacci scale (1, 2, 3, 5, 8):

- **Likelihood** (1/2/3/5/8): chance persona raises it
- **Impact** (1/2/3/5/8): damage if unaddressed
- **Risk = Likelihood x Impact** (1-64, always positive)

**Risk adjustment**: after initial catalogue, review full set. Adjust where concerns interact. Document as `Risk: N (adjusted from L x I = M, reason: ...)`. Stay in 1-64.

**Concern template**:
```markdown
## N. "[Concern as the devil would phrase it - in their voice]"

**Likelihood: N** | **Impact: N** | **Risk: N**

**Their take**: what devil thinks and feels. Write as them, using their priorities and triggers.

**Reality**: factual counter. Reference fact_repository.md entries.

**Response**: how to address - in document or verbally.
```

**Categories to always evaluate** (persona-weighted):
- **Accuracy gaps** - targets missed, metrics below expectation
- **Trust signals** - defensive tone, blame-shifting, excuses
- **Cognitive load** - too many numbers, verbose, overstructure
- **Omissions** - missing data, hidden bad numbers, selective framing
- **Forward-looking** - what next, upgrade path, production readiness
- **Legal/contractual** - SOW compliance, clause coverage, sign-off risk
- **Professional responsibility** - vendor expertise, best practices, duty of care

**No negative risk scores.** Concerns only. Strengths go in "Reality" and "Response". Well-addressed concern scores high on scorecard.

## Step 4: Evaluate target document (Scorecard)

Scorecard = **quality of addressing**, not presence. 0-100% per concern.

### Evaluation criteria

1. **Coverage** - addressed at all? Where?
2. **Quality** - convinces devil or leaves gaps?
3. **Side effects** - creates or worsens other concerns?

### Scoring scale

| Score | Meaning | Devil's reaction |
|-------|---------|-----------------|
| 95-100% | Fully addressed, exemplary | "I have no issue with this" |
| 80-94% | Well addressed, minor gaps | "Fine, but I noticed..." |
| 60-79% | Partially addressed, notable gaps | "This doesn't fully answer my question" |
| 40-59% | Weakly addressed, significant exposure | "This is a problem" |
| 20-39% | Poorly addressed, makes devil suspicious | "You're hiding something" |
| 0-19% | Not addressed or actively harmful | "This makes it worse" |

### Scorecard format

```markdown
## Scorecard

| # | Concern | Risk | Score | Reasoning |
|---|---------|------|-------|-----------|
| 1 | [short name] | 25 | 85% | [specific text/element that addresses it + quality assessment + any side effects] |
```

**Reasoning MUST quote specific text**. No generic statements.

### Overall score

**Minimise** document score (total residual risk). Lower = better.

- **Residual per concern** = `risk x (1 - score)`
- **Document score** = sum of all residuals
- **Total risk** = sum of all risk (theoretical max)

Perfect = 0. Starting = total absolute risk.

**File naming**: `<name>_v<NN>_<score>.md`. Example: `pcp_rnd_v02_54.md`.

**Biggest gaps**: top 5 residuals. Next iteration targets.

### Optimisation framing

- **Objective**: minimise total residual risk
- **Constraints**: cross-concern tensions
- **Variables**: text, structure, visuals, content
- **Trade-offs**: evaluate net effect across ALL concerns

## Step 5: Explore options

Per high-residual concern, propose 2-4 options:

```markdown
### Concern #N: [name] (residual: X.X)

**Option A**: [specific text change or addition]
- Expected effect: #N +15%, #12 -5% (net: +10%)

**Option B**: [structural change]
- Expected effect: #N +20%, #16 -10% (net: +10%)

**Option C**: [SVG infographic]
- Expected effect: #N +25%, #10 +10%, #14 +10% (net: +45%)

**Recommendation**: [which option and why]
```

**Visual options**: if concern relates to cognitive load (#10), number exhaustion (#14), or metric confusion (#13) - always include SVG option. Specify chart type, data, expected improvement, reference `svg-infographics`.

## Step 6: Iterate - Versioned Corrections

Each iteration: new versioned copy, fresh evaluation. Original untouched.

### Iteration workflow

1. **Copy** current as `<name>_v<NN+1>.md`
2. **Apply corrections** from Step 5 to new version
3. **Embed scorecard** at end
4. **Re-read** updated document
5. **Re-score** each concern against new text
6. **Document changes**: "Score X% -> Y% because [specific text change]"
7. **Identify new concerns** from changes, add to catalogue
8. **Update cross-concern tension notes**
9. **Recalculate score** - becomes `<score>` suffix
10. **Rename** to `<name>_v<NN+1>_<score>.md`
11. **Update** `devils_advocate.md` with new scorecard (keep old ones)

### Version chain example

```
report.md                    # original (untouched)
report_v01_89.md             # copy of original with embedded scorecard (residual 89)
report_v02_34.md             # first correction pass (residual 34)
report_v03_12.md             # second correction pass (residual 12)
devils_advocate.md           # updated in place, contains all scorecards
fact_repository.md           # updated in place
```

Score MUST decrease each iteration. If not: corrections are creating problems - stop and reassess.

### Stopping criteria

Stop when:
- Residual < 10% of total absolute risk
- Top remaining gaps all < 3.0
- Corrections need scope changes beyond document
- User accepts current score

### Cross-concern tensions

Some fixes break others:
- Answering "why" may increase finger-pointing
- Adding evidence may increase verbosity
- SOW quotes may increase defensive tone
- Brevity may drop supporting evidence
- Stronger language may improve facts but worsen tone

## Scoring principles

**Aggression punishes.** Confrontational, accusatory, blame-shifting language drops tone scores even if facts improve. Tone registers before facts.

**Reader needs WHY.** Facts without reasons = devil fills blanks, usually badly.

**Transparency beats framing.** Hiding bad numbers costs more trust than showing with context.

**Quality over presence.** Weak addressing scores worse than no addressing. Half-answers signal awareness without competence.

**One visual replaces three paragraphs.** SVG (via `svg-infographics`) = highest leverage for cognitive load:
- Stacked bars for metric breakdowns
- Before/after for value
- Grid/field for composite metrics
- Classification distributions

## Anti-patterns

- **Never soften concerns.** Write as devil - harsh, direct, their voice
- **Never pre-judge priority.** Let math decide
- **Never conflate scoring with approval.** 90% = 10% residual risk
- **Never remove concerns.** Mark resolved, keep in catalogue
- **Never score generously.** In doubt, score lower
- **Never use generic reasoning.** Always quote specific text
- **Never optimise in isolation.** Net effect across all concerns

## Embedded scorecard in versioned documents

**MANDATORY**: Every versioned document ends with embedded scorecard after horizontal rule.

**Format**:
```markdown
---

## Devil's Advocate Scorecard

**Persona**: [devil role and key bias]
**Document score**: [total residual risk] (lower = better, max. [total absolute risk])

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | [short name] | [risk] | [0-100%] | [residual] | [specific text/section that addresses it + quality note] |
| ... | ... | ... | ... | ... | ... |

**Top gaps**: [list 3-5 highest residual concerns with brief note on what's missing]
```

**Rules**:
- "How addressed" MUST reference specific sections/phrases
- Not addressed: write "Not addressed", score 0%
- Concise summary, not full analysis

## File naming

Alongside target:
```
target_document.md
devils_advocate.md
fact_repository.md
```

**Versioned documents**:
```
<name>_v<NN>_<score>.md
```

- `<NN>` - two-digit (`v01` = initial + scorecard, `v02` = first correction)
- `_<score>` - **MANDATORY** rounded residual. Missing = INCOMPLETE

Examples:
- `DESIGN_v01_89.md` - original + first scorecard, residual 89
- `DESIGN_v02_28.md` - first correction, residual 28
- `DESIGN_v03_12.md` - second correction, residual 12

**WRONG**: `DESIGN_v02.md` (no score suffix)

`devils_advocate.md` and `fact_repository.md` updated in place - never versioned. `devils_advocate.md` accumulates all scorecards for comparison.
