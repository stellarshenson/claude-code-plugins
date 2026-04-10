# devils-advocate

Critical document analysis plugin for Claude Code. Systematically critiques documents from the perspective of their toughest audience using structured pushback scenarios, risk scoring, and iterative improvement.

Unlike qualitative tools like [grill-me](https://github.com/mattpocock/skills/tree/main/grill-me) (Socratic interview producing shared understanding) or [Devil's Advocate Protocol](https://mcpmarket.com/tools/skills/devil-s-advocate-protocol) (one-shot adversarial reasoning), this plugin takes a semi-data-science approach: a custom persona is built for each scenario - deviously inferred from existing conversations, emails, or meeting transcripts so the devil knows exactly how your stakeholder thinks before you do (or described manually if you prefer a fair fight), every concern gets a Fibonacci risk score (1-64), each iteration produces a measurable residual, and the score trajectory (89 -> 34 -> 12) shows convergence. Versioned files with embedded scorecards create an audit trail. The math decides priority, not gut feel.

## Skills

| Skill | Description |
|-------|-------------|
| `devils-advocate:setup` | Build devil persona + harvest fact repository |
| `devils-advocate:evaluate` | Generate concern catalogue + baseline scorecard |
| `devils-advocate:iterate` | Decide how to address concerns, apply changes, create versioned file, re-score, rename with residual |
| `devils-advocate:run` | Full workflow: setup -> evaluate -> iterate loop |

## Workflow

```
/devils-advocate:run          # Full workflow with improvement loop
```

Or step by step:

```
/devils-advocate:setup       # 1. Build persona, harvest facts
/devils-advocate:evaluate    # 2. Generate concerns + baseline scorecard
/devils-advocate:iterate     # 3. Improve, version, re-score (repeat)
```

## Improvement loop

The `iterate` cycle repeats until residual risk is acceptable:

1. **Decide** how to address top concerns: your suggestions, auto-apply, or planning mode
2. AI applies changes -> creates versioned file `<name>_v<NN>_<score>.md`
3. Re-scores all concerns against the new text
4. Check: stop if residual < 10% of total, or stagnation, or user accepts

If the user edits the document outside Claude, run `iterate` directly - it re-scores the current state and updates `devils_advocate.md` without creating a versioned copy.

## Artefacts

- `devils_advocate.md` - persona, concerns, scorecards (accumulated across iterations)
- `fact_repository.md` - verified claims with sources
- `<name>_v<NN>_<score>.md` - versioned corrections with embedded scorecard (AI changes only)

## Scoring

- **Risk** = Likelihood x Impact (Fibonacci scale 1-8, max 64)
- **Score** = 0-100% per concern (how well addressed)
- **Residual** = Risk x (1 - Score)
- **Document score** = sum of residuals (minimise)

## Example: Real-world analysis

From a [knowledge graph CLI design document](https://github.com/stellarshenson/knowledge-graph-foundry) analysis across 6 iterations:

**Persona**: Senior backend engineer, 15+ years in production data pipelines. Skeptical of agent-heavy designs, prefers deterministic pipelines, suspicious of LLM-in-the-loop for infrastructure decisions.

**10 concerns identified** with risk scores from 6 (OWL reasoning complexity) to 25 (missing confidence model for extracted triples):

| # | Concern | Risk | v1 | v6 | Residual |
|---|---------|------|-----|-----|----------|
| 5 | Missing confidence model for triples | 25 | 15% | 92% | 2.0 |
| 1 | Agents overused vs deterministic pipelines | 20 | 40% | 90% | 2.0 |
| 3 | LLM normalization = silent corruption risk | 16 | 55% | 90% | 1.6 |
| 2 | Optional features presented as core | 15 | 45% | 95% | 0.75 |
| 4 | Schema inference produces unstable schemas | 12 | 60% | 90% | 1.2 |
| 9 | No data volume estimates or perf targets | 12 | 5% | 92% | 0.96 |

**Score trajectory**: 88.9 -> 27.8 -> 22.6 -> 20.4 -> 17.8 -> 15.5 across 6 versions

Each iteration targeted the highest-residual concern. The math decided priority - concern #5 (missing confidence, residual 21.3) was addressed before #2 (optional features, residual 8.3) because its residual was 2.5x higher. Versioned documents (`DESIGN_v02.md` through `DESIGN_v06_16.md`) track exactly what changed and why at each step.

### Examples

| Example | Persona | Target | Concerns | Score |
|---------|---------|--------|----------|-------|
| [Executive pushback](examples/executive-pushback-analysis.md) | VP reviewing vendor deliverable, reads tone before facts | Executive summary with missed KPI | 21 concerns, 8 iterations | 269 -> 2 |
| [README rewrite](examples/readme-rewrite-analysis.md) | Senior dev evaluating adoption, skimmer | PROGRAM.md + BENCHMARK.md | 7 concerns | 121.3 baseline |
| [kg-builder condensed](examples/kg-builder-design-analysis.md) | Senior backend engineer, skeptical of agents | Architecture design doc | 2 shown (of 10) | 88.9 -> 15.5 |
| [kg-builder full](examples/kg-builder-full-analysis.md) | Same | Same | All 10, 6 scorecards | 88.9 -> 15.5 |

The executive pushback example is the richest - 21 concerns evolving across 8 iterations, a positive concern (#15 SOW quotes reduce risk), concerns about tone and structure ("this reads like excuses", "I stopped reading after the third percentage"), and the full score trajectory from 269 to 2 including SVG infographics replacing text-based numbers in the final version.
