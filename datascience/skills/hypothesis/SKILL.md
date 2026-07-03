---
name: hypothesis
description: Structure and maintain hypothesis-driven research documentation - a canonical append-only experiments log (each hypothesis with setup, prediction, result, verdict) and a SOTA design doc distilling the winners. Use when the user is writing up an experiment, recording a hypothesis and its result, comparing approaches to decide which wins, defining a naive baseline, drafting a research report with a problem overview and executive summary, or concluding a state-of-the-art / final-design doc - even without the word "hypothesis". Triggers - "document this experiment", "write up the hypothesis", "experiments doc", "sota doc", "research writeup", "which approach won", "record this round", "update the experiments log", "structure my results".
allowed-tools: Read, Write, Edit, Glob, Grep, WebFetch
---

# Hypothesis

Maintain two research docs: a canonical **experiments log** (every hypothesis with setup, prediction, result, verdict) and a **SOTA document** (surviving hypotheses distilled into a final design). The log is append-only and grows across runs; the SOTA doc is rewritten when the arc converges. Built for falsifiable hypotheses, an honest problem overview, a skim-readable executive summary.

> **Style (mandatory)** - terse technical-documentation: 1-2 overview sentences then factual bullets; one fact per bullet; numbers inline; no full stop ending a bullet; no em-dashes (use ` - `), unicode arrows (→), escape `\$`. Prose only where an argument needs it. Full reference: the `technical-documentation` skill.

> **Canonical shapes** - two canonical logs, by case: `examples/quantized-inference-experiments.md` is the primary reference - the per-hypothesis-regime shape (each hypothesis owns its models / card / harness - overview + lever-detail paragraph, brief Lever, `<br>`-labelled Experiment); `examples/wmd-docdistance-*.md` is the compact / shared-Setup variant (one-toggle levers, no per-hypothesis Experiment). On any conflict with this skill's guidance (section order, layout, phrasing), follow the matching example.

## Workflow
- Pick the doc - experiments log (recording work) or SOTA doc (concluding once the arc converges)
- Read the closest `examples/` doc first, mirror its section order - do not invent structure
- Open the canonical doc before writing - find the last round, append the next
- Draft, then re-read; cut any sentence a table or number carries faster

## Model roles - theorise strong, execute deliberately
Two phases, two model choices - the plan is only as good as the model that wrote it, the result only as trustworthy as the model that ran it.
- **Theorise + plan on the strongest model** - formulating the hypothesis, mechanism, and the Experiment test-plan runs on the strongest available model, so the plan carries enough context for the agents that execute it; a thin plan from a weak model wastes the run
- **Execute on opus, ideally** - the agents or notebooks that run the experiment default to opus; when an agent runs it, the execution model is part of the regime - record it in the Experiment block
- **Ask when it matters** - offer the execution-model choice (opus / sonnet / haiku) before spawning experiment agents or a costly sweep; default opus when the user does not pick

## Canonical documents across runs
The log is one durable file many runs append to - the system of record, not a fresh writeup each session.
- **Stable location** - `docs/experiments/<project>-experiments.md` (log), `docs/<project>-sota.md` (design); one of each per track, named for the track not the date
- **Secondary-title marker** - under the H1, every canonical doc carries `**Canonical Experiments Document**` (log) or `**Canonical SOTA Document**` (design); marks the system of record so the skill recognises it beyond the filename
- **Find it first** - `Glob docs/**/*experiments*.md` and `*sota*.md`, confirm by the marker (a marked doc is canonical even if the filename misses the glob); append to it, never start a parallel doc for the track
- **Append-only** - each run adds its round at the end (`E<batch>` / `R<round>`), monotonic numbering; a recorded verdict is immutable - later evidence is a new round that supersedes it with a one-line back-reference; never renumber or rewrite an old round
- **SOTA on convergence** - rewrite the SOTA doc only when the winning design changes; it carries surviving components only
- **Cross-link the pair** - SOTA doc states the design, log proves it; each names the other by path
- **Sanitise every run** - no client/customer name (use "private dataset"); private data paths stay git-ignored

## User-facing summary tables (before and after execution)
Present two tables in the conversation - the pre-registration and the finding; this pair is the feedback that drives hypothesis testing, distinct from the in-doc research-at-a-glance table.
- **Before execution (pre-registration)** - state the planned hypotheses back to the user for sign-off; title it `Pre-registration - E<batch> (before execution)`, one row per hypothesis, columns in plain language a non-specialist reads at a glance: **ID** (`E<batch>-H<n>`), **<what is under test> (claim)** - name this column for what THIS project actually tests (a model, a method, a reagent, a personal skill); with no project-specific name, default to **Hypothesis under test (claim)** - do not hardcode a label. The cell is one relatable sentence: what is exercised and the outcome it should deliver, understandable to a non-specialist (`<thing> actually <delivers the outcome>`; domain terms are fine when glossed - see Jargon allowed below); the comparison-against goes in the Lever, the hard numbers in Prediction and Falsifier, **Lever (one knob)** - the single thing changed and what is held fixed, **Prediction** - expected direction + number, **Falsifier (acceptance bar)** - the pre-registered `Refuted unless <numeric gate>` that would sink it. The user confirms this before any run
- **After execution** - the same rows plus a **Verdict** column - Ships / Kept / Promoted / Dropped / Refuted / Killed-at-gate, each with the number that justifies it - and interpretation (what the number means; for a refuted or killed hypothesis, the specific failure and the gate it missed)
- **Always show both** - before table = what the user signs off, after table = what was learned; surface in the reply, not only in the doc
- **On request → the markdown table, not prose** - whenever the user asks for a summary / recap / status of the hypotheses or experiment, render it as a markdown pipe table (pre-registration form before any run; finding form with the Verdict column once results exist; shape in `examples/summary-table.md`), one markdown row per hypothesis - never per-hypothesis `label: value` stanzas or `────`-separated blocks. The pipe table IS the required format; a text dump of the same fields does not satisfy the request. Never make them dig it out of the doc
- **Jargon allowed, but glossed** - the claim and lever may use domain terms (engine names, quant formats, metric names) as long as each rides with a plain companion a non-specialist gets (`TurboMind (LMDeploy's optimized server) out-serves vLLM once requests pile up`); the prediction and falsifier still carry exact thresholds - the plain gloss rides alongside the jargon, it never softens the pre-registered bar
- Columns map to the per-hypothesis template (hypothesis-under-test→Hypothesis, lever→Lever, prediction→Prediction, falsifier→Acceptance bar, verdict→Verdict, interpretation→Result reading)

Concrete before/after tables to mirror - technical register (jargon carried with a plain companion) and plain named-subject register, each with pre-registration and finding forms - in `examples/summary-table.md`. Rename the claim column for what the project tests, else keep `Hypothesis under test`; Verdict is blank at pre-registration, filled by the finding.

## Experiments log - section order
Mirror `examples/quantized-inference-experiments.md` (per-hypothesis regime - lever-detail paragraph + `<br>` Experiment - the primary reference), `examples/wmd-docdistance-experiments.md` (compact, shared Setup), or `examples/lexical-grounding-experiments.md` (long multi-round arc).
- **Title + marker + overview** - H1, then `**Canonical Experiments Document**`, then one paragraph: what the experiment is, the branch/artefacts, where the data lives
- **Problem overview** - dataset (size, labels, class balance, domain/language spread, exact counts), caveats (cohort effects, what the split does and does not test), the core difficulty; facts only - a reader grasps the problem from this section alone
- **Executive summary** - headline result first; the research-at-a-glance table (one row per hypothesis: lever, mechanism, predicted, result, verdict); key findings (beats X, lever is Y, replicated across Z, residual W); the baseline/performance table anchored on the naive baseline; a gain-trajectory diagram only if it earns its place
- **Methodology and metrics** - the metrics each lever moves, each carrying the naive baseline's reading (e.g. `baseline +0.79`); define and describe the naive baseline here - the simplest reasonable method (raw embeddings + cosine, majority class, lexical overlap), named, what it does, its per-metric score - the floor every hypothesis must beat; then the verdict head, the cross-validation splits, the guardrails
- **Setup** - data/fixtures, dependencies, operating point, execution vehicle (notebook/CLI), reproducibility - exact enough to re-run
- **Hypothesis rounds/batches** - one section per `E<batch>` / `R<round>`; opens with one line, then a subsection per hypothesis, then a per-batch results table and benchmarks
- **Lessons learned** - generalisable insights, not a result restatement
- **Conclusions** - what ships and why
- **Next steps** - open threads; a "refuted, do not revisit" list

## Per-hypothesis template (canonical, from quantized-inference)
Each hypothesis opens with a one-paragraph **overview** (why this hypothesis, what it tests or converts), then - only when the regime has a story worth telling - an **unlabelled lever-detail paragraph** (what is exercised and why that isolates the effect; the setup narrative in prose, no byte counts - its position identifies it, no `Lever detail:` prefix), then the fixed bullet set. A one-toggle hypothesis on a shared Setup needs no lever-detail paragraph. The prediction makes the hypothesis falsifiable - the gap between predicted and measured is the finding.
- **Hypothesis** - one causal claim: `because <mechanism + observed precondition>, <intervention> will <measurable outcome ≥ threshold> while <guardrail holds>`
- **Lever** - one line: the single knob changed and the context held fixed, e.g. "GGUF quant level (q4 / q8 / fp16) at fixed model, card, harness" or "annealing temperature at fixed alloy and furnace"; a one-clause provenance hint when the lever is an artefact with an origin (a model, dataset, reagent, instrument, corpus) - "obtained `<id>`" / "produced here" - never a bare label that hides where it came from; the setup story goes in the lever-detail paragraph, the exact regime in Experiment - never dump the full regime into this bullet
- **Mechanism** - how the lever acts, one or two concrete clauses
- **Prediction** - expected outcome and direction before running, e.g. "DR ≥ 1.5x, margin widens"
- **Acceptance bar** - pre-registered pass/fail numbers, distinct from the prediction, e.g. "DR ≥ 1.5x baseline and V = 0"
- **Experiment** - the regime, recorded so it re-runs, as `<br>`-separated lowercase-labelled sub-lines whose labels fit the problem (a GPU study uses `setup:` / `models:` / `harness:` / `baseline:`; a lab or field study `apparatus:` / `materials:` / `sample:` / `procedure:` / `control:`; a data study `dataset:` / `method:` / `split:` / `source:`); include the labels that bear on the hypothesis, skip the rest - decided case-by-case. Invariants when they apply: the execution artefact (the notebook / script / protocol that runs THIS hypothesis, never a shared doc-level one that runs a different workload), the provenance of any artefact used - produced / collected here (how) or obtained externally (exact identity) - so a label never hides where a thing came from, the source / prior work the hypothesis derives from (a paper → digest + original, see the source rule), and the model an agent runs the experiment on. When the author alone knows a field, ask - never invent a plausible identity, path, parameter, or number
- **Result** - measured numbers, including the swept parameter and the guardrail reading; `<br>` may separate logical blocks (decode vs prefill), the text otherwise byte-identical - a recorded Result is immutable, only a line break may be added
- **Verdict** - one of Ships / Kept / Promoted / Dropped / Refuted / Refuted (null) / Killed-at-gate, with the number that justifies it

Name each `E<batch>-H<n>` (docdistance uses `E01-H1`); the name states what is tested, never "try X". `E<batch>` groups 2-5 hypotheses.
- **Global ordinal `<n>`** - one ascending series across all bundles, never reset (E1-H1..H3, E2-H4..H6); unique per hypothesis, trackable across the log
- Keep the `E<batch>` prefix for context; only `H<n>` runs globally; sub-variants fold in as their own ordinal, never a letter suffix

**Experiment block vs shared Setup** - reproducibility lives at whichever level is honest; the block flexes to the document's problem, never a rigid mandated field set.
- **Shared Setup suffices** - a batch where every hypothesis differs by one toggle over one baseline (docdistance: one notebook, one encoder) - the document-level Setup carries reproducibility, the per-hypothesis Experiment block is redundant, omit it
- **Experiment block earns its place** - a hypothesis that owns its regime - produces or obtains an artefact (a model, dataset, sample), fits a component, runs its own procedure, data, or apparatus - the shared Setup cannot describe it; carry the block and let the Lever name the provenance
- **A per-hypothesis Setup line already in a doc** (as some logs use) is the Experiment block under another name - enrich that line with the execution artefact, source paper, and unambiguous provenance rather than adding a second block
- Prose has two homes - the unlabelled lever-detail paragraph before the bullets (the setup story), and, where a `<br>` sub-line cannot carry a fact cleanly, inside the Experiment bullet

## Writing a good hypothesis
- **Predict the result** - state outcome and direction before running; no stated expectation = cannot confirm or refute; a wrong prediction that misses still teaches
- **Pre-register the bar** - the pass/fail gate that decides ship vs drop, before building
- **Diagnostic kill-gate** - measure the precondition before any build; absent precondition → kill cheaply (e.g. errors must concentrate ≥30%, ratio >1.5 → measured 0.93 → killed pre-build)
- **Probe first** - measure firing rate / density on a sample before wiring
- **Two-sided acceptance** - improve the target AND hold the control; no silent regression
- **Mechanism, not data** - gate the feature inert where the mechanism is absent; test the mechanism, not memorised text
- **Falsifiable probe** - measurement-only; never trains, never enters cross-validation
- **Honest splits** - leave-one-X-out; no learner touches the fold it scores; name the headline split and why
- **Size-dependent** - re-run as the data grows; never trust a single snapshot
- **Reproducible plan** - the hypothesis re-runs from its own text: the Experiment block links the notebook / script / protocol that tests it, links the digest and original of any paper it derives from, and states the provenance of any artefact used (produced here + how, or obtained externally + exact identity); the Hypothesis and Lever name that provenance so the claim is never thin (a bare "trained draft head" → "EAGLE-3 head obtained `<id>`" or "trained here on `<corpus>`"); a short line of prose is fine where a bullet cannot carry the plan

## SOTA document - section order
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
- **Appendix: reference build** (default on, drop only if the user declines) - the recipe to build the reference implementation / reference build of the SOTA from scratch: environment, dependencies + versions, build / compile / install commands in order, the exact steps to reproduce the shipped artefact, and a smoke check that it works; where a build recipe already lives as its own doc (e.g. `docs/<name>-build-recipe.md`), link it rather than duplicate

## Examples
Read the closest match before writing; mirror its section order.
- `quantized-inference-experiments.md` - primary canonical log, the per-hypothesis-regime shape (each hypothesis owns its regime); overview → lever-detail paragraph → brief Lever → `<br>`-labelled Experiment → `<br>` Result; GPU-inference domain, model provenance shown (downloaded pre-quantized vs trained here); truncated to nine hypotheses (E12-E13) with the document skeleton preserved
- `wmd-docdistance-experiments.md` - canonical log, compact / shared-Setup variety; one batch (E01), five pre-registered levers, the template, research-at-a-glance + baseline tables, results + benchmarks
- `wmd-docdistance-sota.md` - canonical SOTA doc; Abstract (lineage + digest) → Solution (interpretation, I/O contract, reproducibility) → Mechanism (LaTeX, why-not-cosine) → Performance → FAQ → Conclusions → Bibliography
- `lexical-grounding-experiments.md` - long multi-round arc (12 rounds); research-at-a-glance + per-round progression across data growth and ship decisions
- `lexical-grounding-sota.md` - deterministic-track SOTA; pipeline → performance → limitations → implementation, no maths-heavy mechanism

## Rules
- Terse technical-documentation style every section (see the style note)
- Reasonable, not rigid - fit the structure (per-hypothesis fields, the Experiment block, section order) to the problem the canonical document solves; record what a reader needs to reproduce and understand, skip what does not apply; the templates are a checklist to judge against, never a blank form to fill
- Tables for sweeps - hypothesis × lever × result; never prose where a table scans faster
- Numbers inline on every claim; a verdict label on every hypothesis
- Naive baseline mandatory - defined and described in Methodology, with its numbers on every metric; every result is a delta against it; "beats the naive baseline" is the minimum bar for a Kept / Ships verdict
- Reproducibility - any hypothesis that owns its regime records enough to re-run - the notebook / script / protocol that tests it, the source / prior work it derives from, the provenance of any artefact used (produced here + how, or obtained externally + exact identity); a shared Setup covers only a batch where every hypothesis shares one regime
- Source paper → digest + link both - when a hypothesis derives from a paper (arXiv, DOI), download it, write a short digest into the project reference-docs folder (e.g. `docs/references/<slug>.md` - problem, method, the result borrowed, the exact equation / threshold used), and point the Experiment `source:` line at BOTH the digest and the original; a bare title is not enough - the digest is what a reader consults without re-fetching the paper
- Ask the author, don't guess their regime - when the hypothesis is the user's and you know they hold the knowledge of how they mean to test it, ask them for the Experiment detail you cannot verify from the repo (exact identities, parameters, materials, apparatus / environment, intended notebook or protocol, source / prior work) rather than filling it with a plausible guess - a fabricated regime reads as recorded fact. Where the agent is proposing the hypothesis or the setup is standard / derivable, fill it reasonably and move on
- Model roles - theorise and plan the test on the strongest model (the plan must carry context for the executor); execute on opus by default, ask the user which model runs the experiments when cost or scale warrants; record the execution model in the Experiment block
- Maths - equations liberally, not prose where a formula is exact; unicode glyphs inline for copy-paste (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`, `√(2 − 2cos)`); every full/display equation as a separated `$$…$$` block on its own line (blank line above/below) in the Mechanism section - these are rasterised to images for surfaces that do not run MathJax (Medium, DOCX); never `$…$` inline in a sentence, never a standalone maths section
- Sanitise - no client/customer name ("private dataset"); no em-dashes, unicode arrows (→), escape `\$`
- Append-only - new rounds at the end; never rewrite a recorded verdict
