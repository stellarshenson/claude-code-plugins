---
name: hypothesis
description: Structure and maintain hypothesis-driven research documentation - a canonical append-only experiments log (each hypothesis with a self-contained, independently reproducible experiment setup, prediction, result, verdict) and a SOTA design doc distilling the winners. Use when the user is writing up an experiment, recording a hypothesis and its result, comparing approaches to decide which wins, defining a naive baseline, running an experiment's hypotheses as agents, fanning out the next round of hypotheses, ablating survivors into a final design, drafting a research report with a problem overview and executive summary, or concluding a state-of-the-art / final-design doc - even without the word "hypothesis". Triggers - "document this experiment", "write up the hypothesis", "experiments doc", "sota doc", "research writeup", "which approach won", "record this round", "run this experiment", "fan out hypotheses", "propose the next round", "ablation study", "update the experiments log", "structure my results".
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
- Generating hypotheses (single or a fanout batch) - ask scale + persona, pre-register before anything lands or runs; see the Fanout section
- Before concluding a SOTA - suggest an ablative study of the strongest hypothesis or all survivors, to measure each component's marginal worth and settle the final design; see `references/execution-and-ablation.md`
- Draft, then re-read; cut any sentence a table or number carries faster

## Model roles - theorise strong, execute deliberately
Two phases, two model choices - the plan is only as good as the model that wrote it, the result only as trustworthy as the model that ran it.
- **Theorise + plan on the strongest model** - formulating the hypothesis, mechanism, and the Experiment test-plan runs on the strongest available model, so the plan carries enough context for the agents that execute it; a thin plan from a weak model wastes the run
- **Execute on opus, ideally** - the agents or notebooks that run the experiment default to opus; when an agent runs it, the execution model is part of the regime - record it in the Experiment block
- **Ask when it matters** - offer the execution-model choice (opus / sonnet / haiku) before spawning experiment agents or a costly sweep; default opus when the user does not pick
- **Execution is agent-based** - a hypothesis test, or a whole `E<batch>` run as a fleet, is carried out by a spawned execution agent on the selected model (best executor by default, user may change), never inline in the writing session; prime it with the full Experiment block and a return schema, record the model it ran on - full protocol in `references/execution-and-ablation.md`

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
- **Before execution (pre-registration)** - state the planned hypotheses back to the user for sign-off; title it `Pre-registration - E<batch> (before execution)`, one row per hypothesis, columns in plain language a non-specialist reads at a glance: **ID** (`E<batch>-H<n>`, with the memory slug where the cell has room, e.g. `E30-H106 turbomind-throughput`), **<what is under test> (claim)** - name this column for what THIS project actually tests (a model, a method, a reagent, a personal skill); with no project-specific name, default to **Hypothesis under test (claim)** - do not hardcode a label. The cell is one relatable sentence: what is exercised and the outcome it should deliver, understandable to a non-specialist (`<thing> actually <delivers the outcome>`; domain terms are fine when glossed - see Jargon allowed below); the comparison-against goes in the Lever, the hard numbers in Prediction and Falsifier, **Lever (one knob)** - the single thing changed and what is held fixed, **Prediction** - expected direction + number, **Falsifier (acceptance bar)** - the pre-registered `Refuted unless <numeric gate>` that would sink it. The user confirms this before any run
- **After execution** - the same rows plus a **Verdict** column - Ships / Kept / Promoted / Dropped / Refuted / Killed-at-gate, each with the number that justifies it - and interpretation (what the number means; for a refuted or killed hypothesis, the specific failure and the gate it missed)
- **Always show both** - before table = what the user signs off, after table = what was learned; surface in the reply, not only in the doc
- **Rendering hypotheses back → the markdown pipe table** - any time two or more hypotheses are surfaced in the conversation - the user asks for a summary / recap / status, OR you restate, demonstrate, or propose them yourself - default to a markdown pipe table (pre-registration form before any run; finding form with the Verdict column once results exist; shape in `examples/summary-table.md`), one markdown row per hypothesis, not `label: value` stanzas or `────`-separated blocks. This is the house default, not a law in stone - adapt when the render genuinely needs something else (a single hypothesis, a one-number answer); the failure is a multi-hypothesis text dump where the table would have carried it. Never make them dig it out of the doc
- **Jargon allowed, but glossed** - the claim and lever may use domain terms (engine names, quant formats, metric names) as long as each rides with a plain companion a non-specialist gets (`TurboMind (LMDeploy's optimized server) out-serves vLLM once requests pile up`); the prediction and falsifier still carry exact thresholds - the plain gloss rides alongside the jargon, it never softens the pre-registered bar
- Columns map to the per-hypothesis template (hypothesis-under-test→Hypothesis, lever→Lever, prediction→Prediction, falsifier→Acceptance bar, verdict→Verdict, interpretation→Result reading)

Concrete before/after tables to mirror - technical register (jargon carried with a plain companion) and plain named-subject register, each with pre-registration and finding forms - in `examples/summary-table.md`. Rename the claim column for what the project tests, else keep `Hypothesis under test`; Verdict is blank at pre-registration, filled by the finding.

## Experiments log - section order
Mirror `examples/quantized-inference-experiments.md` (per-hypothesis regime - lever-detail paragraph + `<br>` Experiment - the primary reference), `examples/wmd-docdistance-experiments.md` (compact, shared Setup), or `examples/lexical-grounding-experiments.md` (long multi-round arc).
- **Title + marker + overview** - H1, then `**Canonical Experiments Document**`, then one paragraph: what the experiment is, the branch/artefacts, where the data lives
- **Problem overview** - dataset (size, labels, class balance, domain/language spread, exact counts), caveats (cohort effects, what the split does and does not test), the core difficulty; facts only - a reader grasps the problem from this section alone
- **Executive summary** - headline result first; the research-at-a-glance table (one row per hypothesis: id + slug, lever, mechanism, predicted, result, verdict); key findings (beats X, lever is Y, replicated across Z, residual W); the baseline/performance table anchored on the naive baseline; a gain-trajectory diagram only if it earns its place; define the key comparison metrics (the axes every hypothesis is scored on) and refresh this section and its table every round so it always states the current best - see `references/execution-and-ablation.md`
- **Methodology and metrics** - the metrics each lever moves, each carrying the naive baseline's reading (e.g. `baseline +0.79`); define and describe the naive baseline here - the simplest reasonable method (raw embeddings + cosine, majority class, lexical overlap), named, what it does, its per-metric score - the floor every hypothesis must beat; then the verdict head, the cross-validation splits, the guardrails
- **Setup** - data/fixtures, dependencies, operating point, execution vehicle (notebook/CLI), reproducibility - exact enough to re-run
- **Hypothesis rounds/batches** - one section per `E<batch>` / `R<round>`; opens with one line, then a subsection per hypothesis, then a per-batch results table and benchmarks
- **Lessons learned** - generalisable insights, not a result restatement
- **Conclusions** - what ships and why
- **Next steps** - open threads; a "refuted, do not revisit" list

## Per-hypothesis template (canonical, from quantized-inference)
Each hypothesis opens with a one-paragraph **overview** (why this hypothesis, what it tests or converts), then - only when the regime has a story worth telling - an **unlabelled lever-detail paragraph** (what is exercised and why that isolates the effect; the setup narrative in prose, no byte counts - its position identifies it, no `Lever detail:` prefix), then the fixed bullet set. A one-toggle hypothesis on a shared Setup needs no lever-detail paragraph. The prediction makes the hypothesis falsifiable - the gap between predicted and measured is the finding. The overview, lever-detail, and Experiment block together MUST let a reader reproduce and independently test the hypothesis from the doc alone - the exact artefacts, parameters, data location, harness / commands, and operating point are written down, never left to the conversation transcript or to reverse-engineering the code. A hypothesis a reader cannot re-run without the transcript is under-specified.
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
- **Slug per hypothesis** - each hypothesis carries a 2-3 part kebab-case slug naming what it tests (`turbomind-throughput`, `amx-cpu-kernels`), written after the numeric id: `E30-H106 turbomind-throughput`; the slug aids memory, it is not the identity
- **Numeric id is primary** - refer to a hypothesis by its numeric id (`E30-H106`); add the slug where space allows (prose mentions, an id cell with room, section headings), drop it where it does not fit (dense table cells, repeated references)
- **Batch slug (optional)** - an `E<batch>` may carry a 3-part slug for what the round focuses on (`E30 graph-theory-levers`), shown in the round's section heading (`## E30 - graph-theory-levers`); optional, never required

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

## Fanout - generating the next round
Generate hypotheses from the campaign's kernel instead of waiting for them; pre-registration gates everything. Full mechanics, kernel definition, perturbation operators, portfolio rule in `references/fanout.md`.
- **Two scales** - a single specific hypothesis on request, or a persona-driven `E<batch>` fanout; ask the user for scale (probe 3-5 / round 8-12 / batch 15-25) and persona, recommending both from the log state
- **User's framework is the generative seed (key)** - a user-dictated framework (hypothesis, mechanism, lever, area, hunch) is what the fanout generates FROM - perturbed by the operators, extrapolated, explored creatively around; never filed as just one more candidate
- **Personas** - pluggable hypothesisers in `generators/` (follower, contrarian, heretical, hybridizer, mechanist, deflationist, scout); each an exploration policy with an expected verdict signature that self-tests the round - read the chosen file before generating
- **Kernel first** - fanout requires the log's typed interface: channel vocabulary, lever record (forcing + decay + cost), metric panel + naive baseline, verdict protocol; elicit it into Methodology on the first fanout - ask the author, never invent channels
- **Pre-registration is the prerequisite** - every generated hypothesis, single or batch, is proposed via the pre-registration table and signed off BEFORE it is appended to the log or executed; dedupe against the global H-ordinal registry and a cheap kill-gate pass run before the proposal

## SOTA document - section order
The conclusion doc; mirror `examples/wmd-docdistance-sota.md`, carry surviving components only, cross-link the log as evidence. Full section order and each section's must-have in `references/sota-document.md`: Title+marker → Abstract → Problem → Solution → Pipeline → Mechanism (mandatory, LaTeX + why-not) → Performance → Setup → Methods of measurement → Throughput/footprint → Limitations → FAQ → Implementation → Conclusions → Bibliography → Appendix: reference build. Drop a section only when the design has nothing for it.

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
- Reproducibility - any hypothesis that owns its regime records enough to re-run FROM THE DOC ALONE - a reader reconstructs and independently tests it without the conversation transcript or reading the code: the notebook / script / protocol that tests it (with the exact command / entry point and parameters), the data location, the operating point, the source / prior work it derives from, and the provenance of any artefact used (produced here + how, or obtained externally + exact identity); a shared Setup covers only a batch where every hypothesis shares one regime
- Source paper → follow the `datascience:papers` skill - when a hypothesis derives from a paper (arXiv, DOI), invoke the `datascience:papers` skill to download the PDF and write its structured digest into `references/papers/` (`[paper] <name>, <year>.pdf` + `[paper digest] <name>.md`); point the Experiment `source:` line at BOTH the local digest and the original URL; a bare title is not enough, and a cited-but-undigested paper is a defect - the digest is what a reader consults without re-fetching
- Ask the author, don't guess their regime - when the hypothesis is the user's and you know they hold the knowledge of how they mean to test it, ask them for the Experiment detail you cannot verify from the repo (exact identities, parameters, materials, apparatus / environment, intended notebook or protocol, source / prior work) rather than filling it with a plausible guess - a fabricated regime reads as recorded fact. Where the agent is proposing the hypothesis or the setup is standard / derivable, fill it reasonably and move on
- Model roles - theorise and plan the test on the strongest model (the plan must carry context for the executor); execute on opus by default, ask the user which model runs the experiments when cost or scale warrants; record the execution model in the Experiment block
- Maths - equations liberally, not prose where a formula is exact; unicode glyphs inline for copy-paste (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`, `√(2 − 2cos)`); every full/display equation as a separated `$$…$$` block on its own line (blank line above/below) in the Mechanism section - these are rasterised to images for surfaces that do not run MathJax (Medium, DOCX); never `$…$` inline in a sentence, never a standalone maths section
- Sanitise - no client/customer name ("private dataset"); no em-dashes, unicode arrows (→), escape `\$`
- Fanout is pre-registration-gated - no generated hypothesis (single or batch) is appended or executed before the user signs off its prediction + acceptance bar; personas in `generators/`, mechanics in `references/fanout.md`
- Append-only - new rounds at the end; never rewrite a recorded verdict
