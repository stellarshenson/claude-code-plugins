# Experiments log - section order

Mirror `examples/quantized-inference-experiments.md` (per-hypothesis regime - lever-detail paragraph + `<br>` Experiment - the primary reference), `examples/wmd-docdistance-experiments.md` (compact, shared Setup), or `examples/lexical-grounding-experiments.md` (long multi-round arc).

- **Title + marker + overview** - H1, then `**Canonical Experiments Document**`, then one paragraph: what the experiment is, the branch/artefacts, where the data lives
- **Problem overview** - dataset (size, labels, class balance, domain/language spread, exact counts), caveats (cohort effects, what the split does and does not test), the core difficulty; facts only - a reader grasps the problem from this section alone
- **Executive summary** - headline result first; the research-at-a-glance table (one row per hypothesis: id + slug, lever, mechanism, predicted, result, verdict); key findings (beats X, lever is Y, replicated across Z, residual W); the baseline/performance table anchored on the naive baseline; a gain-trajectory diagram only if it earns its place; define the key comparison metrics (the axes every hypothesis is scored on) and refresh this section and its table every round so it always states the current best - see `references/execution-and-ablation.md`
- **Methodology and metrics** - the metrics each lever moves, each carrying the naive baseline's reading (e.g. `baseline +0.79`); define and describe the naive baseline here - the simplest reasonable method (raw embeddings + cosine, majority class, lexical overlap), named, what it does, its per-metric score - the floor every hypothesis must beat; then the verdict head, the cross-validation splits, the guardrails
- **Setup** - data/fixtures, dependencies, operating point, execution vehicle (notebook/CLI), reproducibility - exact enough to re-run
- **Hypothesis rounds/batches** - one section per `E<batch>` / `R<round>`; opens with one line - what the batch tests and the standing guardrails every hypothesis in it holds, so no block restates them - then a subsection per hypothesis, then a per-batch results table and benchmarks
- **Lessons learned** - generalisable insights, not a result restatement
- **Conclusions** - what ships and why
- **Next steps** - open threads; a "refuted, do not revisit" list
