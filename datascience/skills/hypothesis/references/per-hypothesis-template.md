# Per-hypothesis template (canonical, from quantized-inference)

The field set every hypothesis carries, the naming/ordinal scheme, and when the Experiment block earns its place over a shared Setup. Mirror `examples/quantized-inference-experiments.md`.

Each hypothesis opens with a one-paragraph **overview** (why this hypothesis, what it tests or converts), then - only when the regime has a story worth telling - an **unlabelled lever-detail paragraph** (what is exercised and why that isolates the effect; the setup narrative in prose, no byte counts - its position identifies it, no `Lever detail:` prefix), then the fixed bullet set. A one-toggle hypothesis on a shared Setup needs no lever-detail paragraph. The prediction makes the hypothesis falsifiable - the gap between predicted and measured is the finding. The overview, lever-detail, and Experiment block together MUST let a reader reproduce and independently test the hypothesis from the doc alone - the exact artefacts, parameters, data location, harness / commands, and operating point are written down, never left to the conversation transcript or to reverse-engineering the code. A hypothesis a reader cannot re-run without the transcript is under-specified.

- **Hypothesis** - one causal claim: `because <mechanism + observed precondition>, <intervention> will <measurable outcome ≥ threshold> while <guardrail holds>`
- **Lever** - one line: the single knob changed and the context held fixed, e.g. "GGUF quant level (q4 / q8 / fp16) at fixed model, card, harness" or "annealing temperature at fixed alloy and furnace"; a one-clause provenance hint when the lever is an artefact with an origin (a model, dataset, reagent, instrument, corpus) - "obtained `<id>`" / "produced here" - never a bare label that hides where it came from; the setup story goes in the lever-detail paragraph, the exact regime in Experiment - never dump the full regime into this bullet
- **Mechanism** - how the lever acts, one or two concrete clauses
- **Prediction** - expected outcome and direction before running, e.g. "DR ≥ 1.5x, margin widens"
- **Acceptance bar** - pre-registered pass/fail numbers, distinct from the prediction, e.g. "DR ≥ 1.5x baseline and V = 0"
- **Pre-experiment (probe)** (optional) - a cheap screen run before the full Experiment to read the hypothesis's potential: the quick measurement plus an explicit *generous* go/no-go gate (a low bar sized to avoid false negatives, not the acceptance bar). Clears the gate → commit the expensive Experiment; fails it → defer or drop without spending the run. A series of such probes may itself be definitive and retire the full Experiment. Generous by design, and distinct from the diagnostic kill-gate (a strict precondition that refutes) - this one screens for potential to save cost; omit the bullet where no cheap screen exists
- **Experiment** - the regime, recorded so it re-runs, as `<br>`-separated lowercase-labelled sub-lines whose labels fit the problem (a GPU study uses `setup:` / `models:` / `harness:` / `baseline:`; a lab or field study `apparatus:` / `materials:` / `sample:` / `procedure:` / `control:`; a data study `dataset:` / `method:` / `split:` / `source:`); include the labels that bear on the hypothesis, skip the rest - decided case-by-case. Invariants when they apply: the execution artefact (the notebook / script / protocol that runs THIS hypothesis, never a shared doc-level one that runs a different workload), the provenance of any artefact used - produced / collected here (how) or obtained externally (exact identity) - so a label never hides where a thing came from, the source / prior work the hypothesis derives from (a paper → digest + original, see the source rule), and the model an agent runs the experiment on. When the author alone knows a field, ask - never invent a plausible identity, path, parameter, or number
- **Result** - measured numbers, including the swept parameter and the guardrail reading; `<br>` may separate logical blocks (decode vs prefill), the text otherwise byte-identical - a recorded Result is immutable, only a line break may be added
- **Verdict** - one of Ships / Kept / Promoted / Dropped / Refuted / Refuted (null) / Killed-at-gate, with the number that justifies it
- **Log** (optional) - a dated log of changes to THIS hypothesis - re-runs, fixes, threshold changes - one `log:` line per event, append-only, newest at the bottom: `log: YYYY-MM-DD - <change> - <result>`. Plain: date, change, result; a line may run longer when the change needs the detail - the why, what broke, what it means. The first Result and Verdict stay as recorded; a change that flips the verdict becomes a new round

Log rendered under a hypothesis (append-only, newest at the bottom):

```markdown
- **Log**
  - log: 2026-07-10 - first run, b128 - 2,910 tok/s, Refuted
  - log: 2026-07-14 - re-ran after fixing the tokenizer padding that truncated long inputs - 3,050 tok/s, up from 2,910 but still under the 1.15x bar, verdict holds
  - log: 2026-07-20 - batch 256 - 1.18x vLLM, clears the bar, new round E31-H120
```

## Naming and ordinal

Name each `E<batch>-H<n>` (docdistance uses `E01-H1`); the name states what is tested, never "try X". `E<batch>` groups 2-5 hypotheses.
- **Global ordinal `<n>`** - one ascending series across all bundles, never reset (E1-H1..H3, E2-H4..H6); unique per hypothesis, trackable across the log
- Keep the `E<batch>` prefix for context; only `H<n>` runs globally; sub-variants fold in as their own ordinal, never a letter suffix
- **Slug per hypothesis** - each hypothesis carries a 2-3 part kebab-case slug naming what it tests (`turbomind-throughput`, `amx-cpu-kernels`), written after the numeric id: `E30-H106 turbomind-throughput`; the slug aids memory, it is not the identity
- **Numeric id is primary** - refer to a hypothesis by its numeric id (`E30-H106`); add the slug where space allows (prose mentions, an id cell with room, section headings), drop it where it does not fit (dense table cells, repeated references)
- **Batch slug (optional)** - an `E<batch>` may carry a 3-part slug for what the round focuses on (`E30 graph-theory-levers`), shown in the round's section heading (`## E30 - graph-theory-levers`); optional, never required

## Experiment block vs shared Setup

Reproducibility lives at whichever level is honest; the block flexes to the document's problem, never a rigid mandated field set.
- **Shared Setup suffices** - a batch where every hypothesis differs by one toggle over one baseline (docdistance: one notebook, one encoder) - the document-level Setup carries reproducibility, the per-hypothesis Experiment block is redundant, omit it
- **Experiment block earns its place** - a hypothesis that owns its regime - produces or obtains an artefact (a model, dataset, sample), fits a component, runs its own procedure, data, or apparatus - the shared Setup cannot describe it; carry the block and let the Lever name the provenance
- **A per-hypothesis Setup line already in a doc** (as some logs use) is the Experiment block under another name - enrich that line with the execution artefact, source paper, and unambiguous provenance rather than adding a second block
- Prose has two homes - the unlabelled lever-detail paragraph before the bullets (the setup story), and, where a `<br>` sub-line cannot carry a fact cleanly, inside the Experiment bullet
