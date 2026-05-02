# Showcase

Real production output from the plugins in this marketplace. Direct links to existing artefacts, not marketing prose. Click through if you want proof a tool actually works on real material.

## svg-infographics: production diagrams

Ten examples picked from the [`svg-infographics/examples/`](../svg-infographics/examples/) set (68 total). Every coordinate Python-calculated, every colour from a CSS theme class, every file passes the six validators (overlaps / contrast / alignment / connectors / CSS / collisions).

| File | Type | Notes |
|------|------|-------|
| [architecture_overview_titan_industries.svg](../svg-infographics/examples/architecture_overview_titan_industries.svg) | Architecture overview | Multi-layer stack with manifold connectors converging on a shared platform spine |
| [delivery_model_optima_manufacturing.svg](../svg-infographics/examples/delivery_model_optima_manufacturing.svg) | Delivery model | Card grid with phase-staged headers, light/dark dual mode |
| [hybrid_architecture_nexus.svg](../svg-infographics/examples/hybrid_architecture_nexus.svg) | Hybrid architecture | L-chamfer routing through obstacles, container-scoped paths |
| [methodology_flow_meridian.svg](../svg-infographics/examples/methodology_flow_meridian.svg) | Process flow | Phase progression with leader-mode callouts |
| [delivery_timeline_meridian.svg](../svg-infographics/examples/delivery_timeline_meridian.svg) | Timeline | Phase bars with milestones, headline + subtitle typography |
| [03_mature_retrieval_pipeline.svg](../svg-infographics/examples/03_mature_retrieval_pipeline.svg) | Pipeline diagram | Sankey-style manifold ribbon merging 4 sources into 1 spine |
| [06_hybrid_scorecard.svg](../svg-infographics/examples/06_hybrid_scorecard.svg) | Scorecard | Numeric grid with per-cell colour mapping, accessible contrast |
| [17_fibonacci_scoring.svg](../svg-infographics/examples/17_fibonacci_scoring.svg) | Risk matrix | Likelihood x impact matrix with risk-banded fills |
| [header_banner_apex_financial.svg](../svg-infographics/examples/header_banner_apex_financial.svg) | Header banner | Title + decorative graphics under the 20% horizontal rule |
| [card_grid.svg](../svg-infographics/examples/card_grid.svg) | Generic card grid | Reference layout for the 4-card-row pattern, with anchor labels |

Plus the rest of `svg-infographics/examples/` (68 SVGs total, mix of pipelines, scorecards, timelines, headers, embroidery / decoration tiers, and per-client themed variants).

## devils-advocate: worked analyses

Four end-to-end critical analyses ship in [`devils-advocate/examples/`](../devils-advocate/examples/). Each opens with the devil persona, then the concern catalogue with Fibonacci risk scores, then the per-iteration scorecard showing residual convergence.

| File | Target | Trajectory |
|------|--------|-----------|
| [executive-pushback-analysis.md](../devils-advocate/examples/executive-pushback-analysis.md) | Executive summary defending a missed KPI | 21 concerns, 8 iterations, residual 269 -> 2 |
| [readme-rewrite-analysis.md](../devils-advocate/examples/readme-rewrite-analysis.md) | PROGRAM.md + BENCHMARK.md drafts | 7 concerns, baseline 121.3 |
| [kg-builder-design-analysis.md](../devils-advocate/examples/kg-builder-design-analysis.md) | Architecture design doc | 10 concerns, 88.9 -> 15.5 (2 fully shown) |
| [kg-builder-full-analysis.md](../devils-advocate/examples/kg-builder-full-analysis.md) | Same target as above | All 10 concerns + 6 scorecards, 88.9 -> 15.5 |

## autobuild: real iteration trajectories

Pulled verbatim from [`.claude/JOURNAL.md`](../.claude/JOURNAL.md) - this repo's own development log.

- **Document-grounding optimisation** (entry 114): six-iteration `autobuild` cycle with composite benchmark + 3-fold cross-validation on three held-out academic papers (Liu 2023, Ye 2024, Han 2024). Final mean accuracy **1.0** with zero overfit gap, score arc `69.3 -> 5.0`. PROGRAM, BENCHMARK, hypothesis + falsifiers, lessons learned, CV results all archived under [`references/grounding-optimisation/`](../references/grounding-optimisation/) - read `OPTIMIZATION_SUMMARY.md` for the headline + chart, `report.md` for the full forensic
- **svg-infographics quartermaster forensics** (entry 124): audited 6 prior Claude Code sessions, identified 231 occurrences of "false positive" rationalisation across the corpus, shipped 4 corrective work items in one release: flag-driven preflight rule-pull pattern, mandatory connector direction declaration, stubby-arrow validator (40/60 rule), and the single ship-ready `finalize` gate
- **document-processing forensics** (entry 123): seven work items shipped from a forensic-review plan in one release combining correctness fixes (binary-source rejection, lexical co-support detection, cross-source provenance, four-signal verification flag) with workflow additions (claim extraction, intra-doc consistency check, batch orchestrator + slash command)

## document-processing: grounding receipt

Cross-validated grounding pipeline with **mean accuracy 1.0 across 3 folds** on three held-out academic papers, zero overfit gap. Detailed results, CV harness, calibration data, hypothesis log, and forensic report all live under [`references/grounding-optimisation/`](../references/grounding-optimisation/):

| File | What it contains |
|------|-----------------|
| [PROGRAM.md](../references/grounding-optimisation/PROGRAM.md) | Objective, scope, work-item breakdown, exit conditions |
| [BENCHMARK.md](../references/grounding-optimisation/BENCHMARK.md) | Composite score formula, programmatic checks, CV protocol |
| [hypothesis.md](../references/grounding-optimisation/hypothesis.md) | 10 hypotheses with falsifiers, predicted vs measured deltas |
| [report.md](../references/grounding-optimisation/report.md) | Forensic write-up of every iteration |
| [calibration_cv.json](../references/grounding-optimisation/calibration_cv.json) | Raw 3-fold CV result data (accuracy, precision, recall per fold) |
| [lessons_learned.md](../references/grounding-optimisation/lessons_learned.md) | What survived contact with reality |
| [OPTIMIZATION_SUMMARY.md](../references/grounding-optimisation/OPTIMIZATION_SUMMARY.md) | Headline summary + score arc chart |

## Production feedback (in users' own words)

After running the v1.4.14 boolean cutout tool on a 9-bar chart with a lightning-glyph hole punched through each bar (10 px breathing-room margin):

> "The boolean tool replaced ~25 manually-computed rect splits per row with 9 declarative cutout calls. Much cleaner. Output was multipolygon paths (2 disconnected islands per bar) with curved edges that follow the lightning's actual silhouette - not approximated rectangular gaps. One-step cutout-with-margin. Deterministic warning tokens that block until acknowledged caught two intentional conditions and forced a conscious ack rather than silently producing weird output. In-place rewrite via `--replace-id` kept the SVG structure intact. Output validates clean - `svg-infographics validate` 0 issues, contrast AAA 6/6 text pass."

## Long-form articles

- [Your AI Agent Will Cut Corners. Here's How to Stop It](https://medium.com/@konradwitowskijele/your-ai-agent-will-cut-corners-heres-how-to-stop-it-40f3bc7a4762) - the autobuild thesis
- [Stop Fixing Your AI's SVGs](https://medium.com/towards-artificial-intelligence/stop-fixing-your-ai-svgs-715df70ccca0) - the svg-infographics thesis
