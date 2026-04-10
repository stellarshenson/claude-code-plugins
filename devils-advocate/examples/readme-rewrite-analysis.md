# Devil's Advocate - README Rewrite Program

## The Devil

**Role**: Senior developer evaluating whether to adopt this plugin system for their own Claude Code workflows
**Cares about**: (1) Understanding what this does in under 60 seconds, (2) Seeing concrete examples that prove it works, (3) Finding accurate technical information they can trust
**Style**: Skimmer. Reads the first paragraph, scans headers, looks for code blocks. If confused after 30 seconds, moves on.
**Default bias**: Skeptical of "autonomous" claims. Assumes marketing until proven otherwise. Wants to see the mechanism, not the promise.
**Triggers**: Buzzwords without substance, outdated information (kills trust immediately), walls of text, missing "how do I actually use this?" section
**Decision**: Star/fork the repo or close the tab
**Source**: user-described persona (toughest audience for a README)

---

## Concern Catalogue

### 1. "I still don't understand what this actually does after reading the intro"

**Likelihood: 8** | **Impact: 8** | **Risk: 64**

**Their take**: The PROGRAM says to "explain YAML-driven orchestration engine concept" but doesn't specify what the reader should understand after reading. If the README says "YAML-driven orchestration engine with FSM phases and multi-agent coordination" - that's jargon soup. What does it DO for me? Does it make my code better? How? The problem statement ("AI agents cut corners") is good - but if the README leads with architecture instead of value proposition, the skimmer closes the tab.

**Reality**: The autobuild README already has a good "What it solves" section with concrete problems (shallow fixes, scope creep, lost context). The PROGRAM mentions "frame as pull-based enforcement" which is the right concept but needs to be the FIRST thing, not buried.

**Response**: PROGRAM should explicitly state: the opening paragraph must answer "what does this do for me?" before any technical explanation. The "What it solves" framing from autobuild/README.md should be the model.

### 2. "The PROGRAM doesn't distinguish must-have from nice-to-have sections"

**Likelihood: 5** | **Impact: 5** | **Risk: 25**

**Their take**: Everything is listed as a work item with equal weight. "Header and badges" is low priority, "Building a new plugin" is medium - but for a 3-iteration autobuild run, what gets done first? If iteration 1 wastes time on badge formatting while the core plugin descriptions are wrong, the README improves minimally. The PROGRAM should sequence work items by reader impact: problem statement first, plugin descriptions second, everything else third.

**Reality**: The PROGRAM does assign priority (low/high/medium) but doesn't sequence them. Autobuild follows its own phase lifecycle (RESEARCH -> HYPOTHESIS -> PLAN -> IMPLEMENT) so the implementer will plan its own sequence. But without explicit priority in the program, the planner might not get it right.

**Response**: PROGRAM should state explicit iteration targets: iteration 1 = core content (what/why/plugins), iteration 2 = architecture + usage, iteration 3 = polish + accuracy verification.

### 3. "The BENCHMARK doesn't measure reader experience"

**Likelihood: 8** | **Impact: 5** | **Risk: 40**

**Their take**: The benchmark checks presence ("section exists") and formatting ("no emojis", "no em-dashes") but never asks: "Can a new user understand what this project does after reading just the first 3 paragraphs?" There's no benchmark item for information hierarchy - does the README lead with value, then mechanism, then usage? The fuzzy scales (Accuracy, Completeness, Clarity, Flow) are too abstract. "Clarity: 0-10" with no rubric means the evaluator assigns whatever feels right.

**Reality**: The 4 fuzzy scales ARE meant to capture this, but without rubrics they're subjective. Clarity and Flow specifically should measure reader experience, but the benchmark doesn't define what 8/10 clarity looks like vs 5/10.

**Response**: Add rubric definitions for each fuzzy scale. Add a specific benchmark item: "First 3 paragraphs explain what the project does, what problem it solves, and how to get started."

### 4. "No benchmark item for the README being self-consistent"

**Likelihood: 5** | **Impact: 8** | **Risk: 40**

**Their take**: The whole reason for this rewrite is that the README has wrong numbers (115 tests). The benchmark checks "test count is 212" but doesn't check other potential inconsistencies: does the architecture diagram match actual directory structure? Do the listed Makefile targets match the actual Makefile? Do the slash commands shown actually work? If iteration 2 adds a beautiful architecture section but the directory paths are wrong, the benchmark might not catch it because each item is checked in isolation.

**Reality**: Section 1 (Accuracy) does have items for test count, version, plugins, skills, workflow types, architecture, and Makefile. But these are presence checks, not consistency checks. The benchmark could verify: "every file path shown in the README exists on disk", "every command shown in usage examples is valid".

**Response**: Add benchmark item: "Every file path, command, and code example in README.md is verified against actual codebase."

### 5. "devils-advocate plugin description might be too detailed for a README"

**Likelihood: 5** | **Impact: 3** | **Risk: 15**

**Their take**: The PROGRAM wants the README to describe "Risk scoring: Likelihood x Impact (Fibonacci 1-8, max 64), residual = risk x (1 - score)". That's implementation detail. A README reader wants to know: "this plugin critiques your documents and scores how well concerns are addressed." The math belongs in the plugin's own README, not the top-level repo README. Same risk for autobuild - explaining all 8 phases with their lifecycle transitions is too much for a repo README.

**Reality**: There's a balance. The top-level README should give enough detail to understand the concept but link to plugin-specific READMEs for depth. The PROGRAM doesn't mention linking to sub-READMEs at all.

**Response**: PROGRAM should specify depth level for each plugin section: "concept + key differentiators + usage example, link to plugin README for full details." The formula and phase details go in the plugin READMEs.

### 6. "No benchmark item for README length control"

**Likelihood: 3** | **Impact: 5** | **Risk: 15**

**Their take**: The PROGRAM constraint says "keep total length reasonable" but the benchmark has no way to measure this. With 9 sections (header, what it solves, plugins overview, autobuild, devils-advocate, architecture, building a plugin, install, development), each getting a paragraph plus code block, the README could easily balloon to 300+ lines. The current README is 110 lines. A 3x expansion would bury the value proposition.

**Reality**: Modus primaris already constrains verbosity. But without a line count target, the benchmark can't flag bloat.

**Response**: Add a soft target: "README should be under 200 lines" or similar. The benchmark should include a check for overall length.

### 7. "The PROGRAM doesn't mention what to REMOVE from the current README"

**Likelihood: 3** | **Impact: 3** | **Risk: 9**

**Their take**: The current README has content that might be outdated or wrong beyond just the test count. The standalone CLI usage section shows specific commands that might not match current implementation. The "Building a new plugin" section might describe an outdated process. The PROGRAM only talks about what to ADD, never what to remove or verify.

**Reality**: The PROGRAM does say "keep existing content" for some sections. But it should also say "verify existing content is still accurate" for sections being preserved.

**Response**: Add a work item: "Audit existing sections for accuracy before preserving them."

---

## Scorecard v01 (PROGRAM.md + BENCHMARK.md as-is)

| # | Concern | Risk | Score | Residual | How addressed |
|---|---------|------|-------|----------|---------------|
| 1 | Reader doesn't understand what it does | 64 | 50% | 32.0 | PROGRAM mentions "explain core problem" and "pull-based enforcement" but doesn't mandate value-first information hierarchy |
| 2 | No iteration sequencing | 25 | 40% | 15.0 | Priority labels (low/high/medium) exist but no explicit iteration targets |
| 3 | Benchmark doesn't measure reader experience | 40 | 30% | 28.0 | Fuzzy scales exist but lack rubrics. No "can reader understand in 60s" check |
| 4 | No consistency verification | 40 | 60% | 16.0 | Section 1 Accuracy has presence checks for key facts but no cross-verification |
| 5 | Plugin detail level wrong for README | 15 | 20% | 12.0 | PROGRAM requests formula-level detail. No mention of linking to plugin READMEs |
| 6 | No length control | 15 | 20% | 12.0 | Constraint says "reasonable" but benchmark has no line count check |
| 7 | No audit of existing content | 9 | 30% | 6.3 | PROGRAM says "keep existing" but not "verify existing" |

**Document score**: 121.3 (total residual risk)
**Total absolute risk**: 208
**Residual %**: 58.3%

**Top gaps**:
1. Reader understanding (32.0) - no value-first mandate in PROGRAM
2. Reader experience measurement (28.0) - no rubrics, no "understand in 60s" check
3. Consistency verification (16.0) - presence checks but not cross-checks
4. Iteration sequencing (15.0) - no explicit iteration targets
5. Plugin detail level (12.0) - too much detail for top-level README

---

## Recommended Corrections

### Concern #1: Value-first information hierarchy (residual 32.0)

Add to PROGRAM "What it solves" work item:
- "The opening paragraph MUST answer 'what does this do for me?' before any technical explanation"
- "First 3 paragraphs: problem -> solution concept -> how to get started"
- "Technical architecture comes AFTER the reader understands the value"

### Concern #3: Benchmark reader experience (residual 28.0)

Add to BENCHMARK Section 2 (Completeness):
- `[ ] First 3 paragraphs explain: what the project does, what problem it solves, how to start`
- `[ ] Each plugin section leads with value proposition before technical details`

Add rubrics to fuzzy scales:
- Clarity: 8+ means "a developer can understand the project's purpose, install it, and start using it from the README alone without consulting other files"
- Flow: 8+ means "information is ordered by reader priority: problem -> solution -> usage -> architecture -> development"

### Concern #4: Consistency verification (residual 16.0)

Add to BENCHMARK Section 1 (Accuracy):
- `[ ] Every file path shown in README exists on disk`
- `[ ] Every CLI command shown is a valid orchestrate subcommand or plugin slash command`

### Concern #2: Iteration targets (residual 15.0)

Add to PROGRAM a section:
```
## Iteration Targets
- Iteration 1: Core content - problem statement, plugin descriptions, usage examples
- Iteration 2: Architecture, building a plugin, install instructions
- Iteration 3: Polish - accuracy verification, cross-consistency, flow optimization
```

### Concern #5: Plugin detail level (residual 12.0)

Update PROGRAM plugin sections:
- "Top-level README provides concept + key differentiators + 1 usage example per plugin"
- "Link to plugin-specific README for full details (phase lifecycle, scoring formula, artefact format)"
- "The repo README is a landing page, not a reference manual"

### Concern #6: Length control (residual 12.0)

Add to BENCHMARK:
- `[ ] README.md is under 250 lines (current: 110, target: comprehensive but not bloated)`
