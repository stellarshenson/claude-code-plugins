---
name: devils-advocate
description: Use this skill when the user asks to critically evaluate a document, build a devil's advocate analysis, create a scorecard, or stress-test executive communications. Triggers on phrases like "devil's advocate", "critique this", "scorecard", "pushback scenarios", "how will they attack this", "evaluate concerns".
---

# Devil's Advocate - Critical Document Analysis

Systematically critique any document from the perspective of its toughest audience. Generate structured pushback scenarios, score how well concerns are addressed, and produce actionable improvement paths - including graphical options via the `svg-infographics` skill.

## Workflow

The skill produces three artefacts in the same directory as the target document:

1. **`devils_advocate.md`** - Devil persona, concern catalogue, risk scoring, scorecard, and detailed responses
2. **`fact_repository.md`** - Verified claims harvested from source documents, contracts, data, and user-provided facts
3. **Scorecard** (embedded in `devils_advocate.md`) - Percentage-based evaluation of how well each concern is addressed

Optional: SVG infographics using the `svg-infographics` skill when visual communication would strengthen the document.

## Step 1: Build the Devil Persona

**MANDATORY**: Before generating any concerns, the devil persona must be established. The persona can come from three sources:

### Source A: User-provided seed

The user provides a seed document (evaluation, review, critique) alongside the target document. Infer the persona from the seed's tone, priorities, and concerns. Present the inferred persona to the user for confirmation before proceeding.

### Source B: User describes the persona

Ask the user these questions:

1. **Who is the reader?** (title, role, seniority - e.g. "VP of Network Operations", "board member", "procurement lead")
2. **What do they care about most?** (cost, risk, timeline, reputation, compliance, technical quality)
3. **What is their communication style?** (data-driven, gut-feel, political, legalistic)
4. **What is their default bias?** (skeptical of vendors, risk-averse, cost-focused, detail-oriented)
5. **What triggers them?** (blame-shifting, excuses, missing numbers, verbose language, finger-pointing)
6. **What decision power do they have?** (approve/reject, recommend to board, escalate, negotiate)

### Source C: No seed or persona provided

If the user invokes the skill without a seed and without describing the persona, **you must ask**. Do not proceed with generic concerns. Present two options:

1. **Describe a single persona** - "Who is the toughest reader for this document? Describe their role, priorities, and biases"
2. **Describe a group of personas** - "List 2-4 reader roles that this document must satisfy. I will build a composite devil that represents their combined concerns"

For a **group of personas**, build a composite devil: merge priorities (union of all concerns), take the harshest bias from each persona, and weight likelihood scores by which persona would most likely raise each concern. Document each contributing persona and the composite in `devils_advocate.md`.

### Persona documentation

**Document the persona** at the top of `devils_advocate.md`:

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

For composite personas, add a subsection listing each contributing persona with their individual priorities before the merged devil profile.

The persona shapes every concern. A cost-focused CFO generates different concerns than a risk-averse compliance officer. Without the persona, concerns are generic and scoring is meaningless.

## Step 2: Harvest facts into fact_repository.md

Scan all available source materials and extract verifiable claims. Each fact must have a source.

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
- Separate user-provided facts from document-extracted facts
- Include mathematical derivations where relevant (e.g. probability calculations)
- Update incrementally - never overwrite, always append and deduplicate
- When the user provides new facts during iteration, add them to the appropriate section

## Step 3: Generate concern catalogue

For each concern, score on two dimensions using a Fibonacci-like scale (1, 2, 3, 5, 8) where higher values carry disproportionate weight - forcing clear differentiation between moderate and critical concerns:

- **Likelihood** (1/2/3/5/8): How likely this persona will raise this concern
- **Impact** (1/2/3/5/8): How much damage if left unaddressed with this reader
- **Risk = Likelihood x Impact** (1-64, always positive - the devil only catalogues concerns, not strengths)

**Risk adjustment**: After generating the initial concern catalogue, review the full set and adjust risk scores where the initial Likelihood x Impact underestimates actual importance. Some concerns interact - a concern that amplifies three others deserves more weight than its standalone score suggests. Document adjustments as `Risk: N (adjusted from L x I = M, reason: ...)`. Adjusted risk remains in the 1-64 range.

**Concern template**:
```markdown
## N. "[Concern as the devil would phrase it - in their voice]"

**Likelihood: N** | **Impact: N** | **Risk: N**

**Their take**: What the devil thinks and feels. Write as them, using their priorities and triggers.

**Reality**: The factual counter. Reference fact_repository.md entries.

**Response**: How to address it - either in the document or verbally.
```

**Concern categories to always evaluate** (persona-weighted):
- **Accuracy gaps** - targets missed, metrics below expectation
- **Trust signals** - defensive tone, finger-pointing, excuse-making, blame-shifting
- **Cognitive load** - too many numbers, verbose language, overstructure
- **Omissions** - missing data, hidden bad numbers, selective presentation
- **Forward-looking** - what happens next, upgrade path, production readiness
- **Legal/contractual** - SOW compliance, clause coverage, sign-off risk
- **Professional responsibility** - vendor expertise, best practices, duty of care

**No negative risk scores.** The concern catalogue captures only concerns - things the devil would challenge. Strengths and mitigating factors belong in the "Reality" and "Response" fields of each concern, not as separate entries with negative scores. A well-addressed concern scores high on the scorecard (reducing residual risk), which is how positive factors are captured.

## Step 4: Evaluate the target document (Scorecard)

The scorecard evaluates **quality of addressing**, not just presence. For each concern, score 0-100% based on how effectively the document handles it from the devil's perspective.

### Evaluation criteria per concern

Each score reflects three dimensions:

1. **Coverage** - Is the concern addressed at all? Where in the document?
2. **Quality** - How well is it addressed? Does it convince the devil or leave gaps?
3. **Side effects** - Does addressing this concern create or worsen other concerns?

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

**Reasoning column must reference specific text from the document** - not generic statements. Quote the exact phrases that address (or fail to address) the concern.

### Overall score calculation

**Objective**: Minimise the document score (total residual risk). Lower is better.

- **Residual risk per concern** = `risk x (1 - score)`
- **Document score** = sum of all residual risks (this is the number used in filenames and tracking)
- **Total risk** = sum of risk across all concerns (theoretical maximum if nothing is addressed)

The document score is the **total residual risk** - the raw sum of unaddressed risk. We optimise by **minimising** this number. A perfect document scores 0. The starting score equals the total absolute risk.

**File naming convention**: `<name>-v<NN>_<score>.md` where score is the rounded document score (total residual risk). Example: `pcp-rnd-v02_54.md` means version 02 with residual risk of 54.

**Biggest gaps**: List the 5 concerns with highest residual risk. These are the optimisation targets for the next iteration.

### Optimisation framing

The scorecard is an **optimisation problem**:
- **Objective**: minimise total residual risk
- **Constraints**: cross-concern tensions (fixing one may worsen another)
- **Decision variables**: text changes, structural changes, visual additions, content additions/removals
- **Trade-offs**: every change must be evaluated for its net effect across ALL concerns, not just the one being targeted

## Step 5: Explore options

For each high-residual concern, propose 2-4 concrete options:

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

**Visual options**: When a concern relates to cognitive load (#10), number exhaustion (#14), or metric confusion (#13), always include at least one SVG infographic option. Specify:
- Chart type (stacked bar, before/after, grid, classification)
- Data to visualise
- Expected score improvement across multiple concerns
- Reference the `svg-infographics` skill for implementation

## Step 6: Iterate - Versioned Corrections

Each iteration produces a new versioned copy of the target document with corrections applied, followed by a fresh re-evaluation. The original document is never modified.

### Iteration workflow

1. **Copy** the current version as the next version: `<name>_v<NN+1>.md` (working copy, score suffix added after evaluation)
2. **Apply corrections** from Step 5 to the new version only
3. **Embed the scorecard** at the end of the new version (see Embedded scorecard section)
4. **Re-read** the updated document in full
5. **Re-score** each concern against the new text with fresh evaluation
6. **Document score changes** with reasoning: "Score changed from X% to Y% because [specific text change]"
7. **Identify new concerns** introduced by changes - add them to the catalogue
8. **Update cross-concern tension notes**
9. **Recalculate overall score** - this becomes the `<score>` suffix
10. **Rename** the working copy to `<name>_v<NN+1>_<score>.md`
11. **Update** `devils_advocate.md` with the new scorecard (keep previous scorecards for comparison)

### Version chain example

```
report.md                    # original (untouched)
report_v01_89.md             # copy of original with embedded scorecard (residual 89)
report_v02_34.md             # first correction pass (residual 34)
report_v03_12.md             # second correction pass (residual 12)
devils_advocate.md           # updated in place, contains all scorecards
fact_repository.md           # updated in place
```

The score must decrease with each iteration. If it does not, the corrections are introducing new concerns or worsening existing ones - stop and reassess.

### Stopping criteria

Stop iterating when:
- Residual risk is below 10% of total absolute risk
- Top remaining gaps have residual < 3.0 each
- Further corrections would require scope changes beyond the document (e.g. new data, architectural decisions, stakeholder input)
- The user explicitly accepts the current score

### Cross-concern tension tracking

Some fixes create new problems. Document these as constraints:
- Answering "why" may increase finger-pointing
- Adding evidence may increase verbosity
- SOW quotes may increase defensive tone
- Brevity may lose supporting evidence
- Stronger language may improve factual coverage but worsen tone

## Scoring principles

**Aggression and defensiveness always punish.** Language that reads as confrontational, accusatory, or blame-shifting reduces scores on tone concerns even if it improves factual coverage. The devil notices tone before facts.

**The reader needs to know WHY.** A document that states facts without explaining reasons leaves the devil to fill in their own narrative - usually a worse one.

**Transparency beats framing.** Hiding bad numbers costs more trust than showing them with context. The devil will notice omissions and penalise harder than bad numbers shown honestly.

**Quality over presence.** A concern "addressed" with weak or generic language scores worse than one addressed with specific evidence and clear reasoning. The devil reads critically - half-answers are worse than no answer because they signal awareness without competence.

**One visual replaces three paragraphs.** SVG infographics (via the `svg-infographics` skill) are the highest-leverage improvement for cognitive load concerns:
- Stacked bars for metric breakdowns
- Before/after comparisons for value demonstration
- Grid/field visualisations for explaining composite metrics
- Classification distributions for categorisation results

## Anti-patterns

- **Do not soften concerns.** Write them as the devil would phrase them - harsh, direct, in their voice
- **Do not pre-judge which concerns matter.** Score them all; let the math decide priority
- **Do not conflate scoring with approval.** 90% means 10% residual risk, not "good enough"
- **Do not remove concerns once added.** Mark them resolved but keep them in the catalogue
- **Do not score generously.** If in doubt, score lower. Overconfident scoring is itself a risk
- **Do not use generic reasoning.** Every score must reference specific text from the target document
- **Do not optimise one concern in isolation.** Always evaluate net effect across all concerns

## Embedded scorecard in versioned documents

**MANDATORY**: Every versioned document must end with an embedded scorecard section after a horizontal rule. This makes each version self-contained - a reader can see the document AND its evaluation in one file.

**Format**:
```markdown
---

## Ocena dokumentu (Devil's Advocate Scorecard)

**Persona**: [devil role and key bias]
**Dokument score**: [total residual risk] (niższy = lepszy, maks. [total absolute risk])

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | [short name] | [risk] | [0-100%] | [residual] | [specific text/section that addresses it + quality note] |
| ... | ... | ... | ... | ... | ... |

**Top gaps**: [list 3-5 highest residual concerns with brief note on what's missing]
```

**Rules**:
- "How addressed" column must reference specific sections or phrases from the document above
- If a concern is not addressed at all, write "Not addressed" and score 0%
- Keep reasoning concise - this is a summary table, not the full analysis

## File naming

Place artefacts alongside the target document:
```
target_document.md
devils_advocate.md
fact_repository.md
```

**Versioned documents** use the naming convention:
```
<name>_v<NN>_<score>.md
```

- `<NN>` - two-digit incremental version (`v01` is the initial document with embedded scorecard, `v02` is first correction pass, etc.)
- `<score>` - rounded residual risk score after evaluation (lower is better)

Examples:
- `DESIGN_v01_89.md` - original document with first scorecard, residual risk 89
- `DESIGN_v02_28.md` - first correction pass, residual risk 28
- `DESIGN_v03_12.md` - second correction pass, residual risk 12

The `devils_advocate.md` and `fact_repository.md` artefacts are updated in place across iterations - do not create versioned copies of these. The `devils_advocate.md` accumulates all scorecards (v1, v2, v3...) for comparison across versions.
