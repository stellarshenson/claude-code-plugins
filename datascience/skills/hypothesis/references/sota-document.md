# SOTA document - section order

The full conclusion-doc shape; mirror `examples/wmd-docdistance-sota.md`. Drop a section only when the design has nothing for it. Each bullet names its own must-have.

- **Title + marker** - H1, then `**Canonical SOTA Document**`, before the Abstract
- **Abstract** - one dense paragraph: what it is, the foundational result it adapts (inline footnote + digest link) and exactly what it swaps vs keeps, the headline number, a closing "this is the conclusion doc, the log is its evidence" cross-link
- **Problem** - why the task is hard: the coarse/blind baseline, the missing signal, the property the solution must satisfy; exact terms
- **Solution** - the lift in one sentence, then the load-bearing readouts: one-line interpretation (what the number means, its range, the normalized form e.g. closeness `= 1 − d/max`); the I/O contract ("two texts in → one distance, a verdict, the alignment") stated before any maths; reproducibility-as-strength where it beats a non-deterministic baseline; the headline result
- **Pipeline / components** - the stages, input → verdict; one bullet per stage naming its model / cost / output
- **Mechanism / theory** (mandatory) - why the design works: the principle it rests on, cited to the paper with a digest link; prose + separated LaTeX (arxiv style), with "why not <obvious alternative>" worked inline; enough to ground the design, not a literature review
- **Performance** - a shipped-vs-baseline table, one row per measure at the operating point; bullets that name the metric that improved AND the one that regressed, with why the tradeoff is accepted
- **Setup** (when performance is reported) - hardware named, models, workload, thread pinning for the single-core unit
- **Methods of measurement** - how each figure is taken: warmup, reps, single-stream, what each number means, caveats
- **Throughput / footprint** - the single-core benchmark (ms/unit, tokens/s, end-to-end on a named workload), the per-core deployment unit (e.g. AWS Lambda ≈ 1 vCPU per 1769 MB), latency, footprint, dependencies
- **Limitations** - honest residuals; separate intrinsic-to-the-fixture from a defect of the method
- **FAQ** - a "why not <X>?" entry for every obvious alternative, each killed with one concrete disqualifier (no metric, needs logits, non-deterministic, too coarse)
- **Implementation** - notebooks, experiments-doc link, the shipped functions/library, the validation artefact
- **Conclusions** - the bounded readout restated: range, verdict rule, use scenario, operating point, headline performance
- **Bibliography** - footnote-anchor pattern (`<span id="refN">…</span>` paired with `[<sup>refN</sup>](#refN)` at first use), each ref with its digest path
- **Appendix: reference build** (default on, drop only if the user declines) - the recipe to build the reference implementation of the SOTA from scratch: environment, dependencies + versions, build / compile / install commands in order, the exact steps to reproduce the shipped artefact, and a smoke check that it works; where a build recipe already lives as its own doc (e.g. `docs/<name>-build-recipe.md`), link it rather than duplicate
