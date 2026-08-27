# Execution and ablation

Procedural detail for running hypotheses as agents, ablating survivors into a SOTA design, and keeping the comparison current. SKILL.md carries the rules; this doc carries the how.

## Agent-based execution
A hypothesis test - or a whole batch - is run by a spawned execution agent, never inline in the writing session. The writing/planning session theorises; the agent executes.
- **Selected model** - the execution agent runs on a chosen model; default the best available executor (opus), ask the user when cost or scale warrants, let them change it; once chosen the model stands for the campaign, not re-asked per wave
- **Fully primed** - the agent gets the hypothesis's Experiment block verbatim: artefacts and their provenance, harness / apparatus, the operating point, the pre-registered acceptance bar and diagnostic kill-gate, and the return schema (measured numbers + guardrail readings + the execution model it ran on)
- **One hypothesis or the batch** - run a single hypothesis test, or spawn the whole `E<batch>` as a fleet (one agent per hypothesis); stagger large fleets to ~6-8 concurrent with a retry pass to avoid rate limits
- **Record what ran** - the returned numbers land in the immutable Result; the execution model lands in the Experiment `model:` line - the model is part of the regime
- **Kill cheaply** - an agent that hits the diagnostic kill-gate (precondition absent) returns the killed verdict without finishing the build

## Ablation to SOTA
Once a batch has survivors, suggest an ablative study before finalizing the SOTA design - it is the step that turns "these levers each helped" into "this is the design, and here is each part's marginal worth".
- **What to ablate** - the strongest single hypothesis, or all survivors combined into the candidate design; turn OFF one component at a time, hold the rest fixed, measure the drop
- **Marginal contribution** - each component's worth is the metric delta when it is removed; a component whose removal costs nothing is dropped from the SOTA design
- **Record as a round** - the ablation is its own round (`E<batch>-H<n>` with an `-ablation` slug, or a dedicated batch); the removed-component arms are its hypotheses, each pre-registered like any other
- **SOTA carries survivors of ablation** - the SOTA doc keeps only components with positive marginal contribution; the ablation round is its evidence
- **Suggest, do not impose** - offer the ablation and its arms; the user decides whether to run it

## Key metrics and the executive summary
The comparison is only as good as the axes it scores on; define them once and keep them live.
- **Build the comparison metrics** - name the axes every hypothesis is judged on (each carrying the naive baseline's reading as the floor); these are the columns of the research-at-a-glance table and the ablation
- **Update every round** - each recorded round refreshes the research-at-a-glance table and the executive-summary headline, so the doc always states the current best and the gain trajectory
- **Headline first** - the executive summary leads with the current winning result and its delta over the naive baseline, then the per-hypothesis at-a-glance rows (id + slug, lever, predicted, result, verdict)
