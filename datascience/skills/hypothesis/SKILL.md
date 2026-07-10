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
- Updating an existing hypothesis (a re-run, a fix, a changed threshold) - append a `log:` line to its Log; the original Result and Verdict stay as recorded, a verdict flip becomes a new round
- Before concluding a SOTA - suggest an ablative study of the strongest hypothesis or all survivors, to measure each component's marginal worth and settle the final design; see `references/execution-and-ablation.md`
- Draft, then re-read; cut any sentence a table or number carries faster

## Model roles - theorise strong, execute deliberately
The plan is only as good as the model that wrote it, the result only as trustworthy as the model that ran it.
- **Theorise + plan on the strongest model** - the hypothesis, mechanism, and Experiment test-plan carry enough context for the executor; a thin plan wastes the run
- **Execute on opus by default** - offer the choice (opus / sonnet / haiku) before a costly sweep; record the execution model in the Experiment block; execution is agent-based (a spawned agent primed with the full Experiment block + a return schema), never inline - full protocol in `references/execution-and-ablation.md`

## Canonical documents across runs
The log is one durable file many runs append to - the system of record, not a fresh writeup each session.
- **Repeatable layout** - one home per kind so experiment work is never scattered:
  - `docs/experiments/<project>-experiments.md`, `docs/<project>-sota.md` - canonical log + SOTA, one per track, named for the track not the date
  - `src/experiments/` - durable experiment code + the notebook that runs a hypothesis; the Experiment block's execution-artefact points here; a plain `scripts/` folder only for simple one-offs that do not belong in `src/`
  - `reports/experiments/` - the true written-up experiment reports
  - `tmp/<kind>/` - transient only (temp models, temp data, scratch "just-find-out" notebooks, temp scripts); nothing durable lands here
- **Experiment code naming** - name each code file for the id it serves so it maps back to the log: `E<batch>-H<n>` when specific to one hypothesis, `E<batch>` when it covers the whole experiment / batch (e.g. `E30-H106_throughput.ipynb`, `E30_setup.py`)
- **Secondary-title marker** - under the H1, every canonical doc carries `**Canonical Experiments Document**` (log) or `**Canonical SOTA Document**` (design); marks the system of record so the skill recognises it beyond the filename
- **Find it first** - `Glob docs/**/*experiments*.md` and `*sota*.md`, confirm by the marker (a marked doc is canonical even if the filename misses the glob); append to it, never start a parallel doc for the track
- **Append-only** - each run adds its round at the end (`E<batch>` / `R<round>`), monotonic numbering; a recorded verdict is immutable - later evidence is a new round that supersedes it with a one-line back-reference; never renumber or rewrite an old round; within a hypothesis, a dated **Log** records its own re-runs and changes append-only (`log:` lines, newest at the bottom), and a verdict flip still spawns a new round
- **SOTA on convergence** - rewrite the SOTA doc only when the winning design changes; it carries surviving components only
- **Cross-link the pair** - SOTA doc states the design, log proves it; each names the other by path
- **Sanitise every run** - no client/customer name (use "private dataset"); private data paths stay git-ignored

## User-facing summary tables (before and after execution)
Present two tables in the conversation - the pre-registration (planned hypotheses, signed off before any run) and the finding (same rows plus a Verdict column with the number that justifies it). This pair drives hypothesis testing, distinct from the in-doc research-at-a-glance table. Full column spec, the jargon-with-a-gloss rule, and the column→template mapping in `references/summary-tables.md`; concrete tables to mirror in `examples/summary-table.md`.
- **Always show both** - before table = what the user signs off, after table = what was learned; surface in the reply, not only in the doc
- **Render 2+ hypotheses as a markdown pipe table** - whenever two or more hypotheses are surfaced (a summary / recap / status, or you restate or propose them), default to a pipe table, one row per hypothesis, not `label: value` stanzas or `────` blocks; adapt only when the render genuinely needs otherwise (a single hypothesis, a one-number answer)

## Experiments log - section order
Mirror the closest example (`quantized-inference` per-hypothesis regime, `wmd-docdistance` compact shared-Setup, `lexical-grounding` long multi-round arc). Sections in order: Title + `**Canonical Experiments Document**` marker + overview → Problem overview → Executive summary (research-at-a-glance table + naive-baseline performance table) → Methodology and metrics (define the naive baseline here) → Setup → Hypothesis rounds/batches → Lessons learned → Conclusions → Next steps (with a "refuted, do not revisit" list). Each section's must-have in `references/experiments-log-structure.md`.

## Per-hypothesis template (from quantized-inference)
Each hypothesis: a one-paragraph overview, an optional unlabelled lever-detail paragraph (the setup story, only when the regime has one), then the fixed bullet set. The overview, lever-detail, and Experiment block together must let a reader reproduce and independently test it from the doc alone - artefacts, parameters, data location, harness, operating point written down, never left to the transcript. Full field spec, the naming/ordinal scheme, the Log rendered example, and Experiment-block-vs-shared-Setup in `references/per-hypothesis-template.md`.
- **Fields** - Hypothesis (`because <mechanism>, <intervention> will <outcome ≥ threshold> while <guardrail>`); Lever (one knob + what is held fixed, with a provenance hint); Mechanism; Prediction (direction + number); Acceptance bar (pre-registered pass/fail, distinct from Prediction); Pre-experiment probe (optional cheap screen + generous go/no-go gate); Experiment (the re-runnable regime as `<br>`-labelled sub-lines); Result (measured, immutable); Verdict (Ships / Kept / Promoted / Dropped / Refuted / Killed-at-gate + the number); Log (optional dated `log:` lines, append-only)
- **Id** - `E<batch>-H<n>`, one global ascending `<n>` never reset; a 2-3 part slug aids memory but the numeric id is the identity; `E<batch>` groups 2-5 hypotheses
- **Experiment block vs shared Setup** - carry the block when a hypothesis owns its regime (its own artefact / procedure / data); omit it when a shared Setup already covers a one-toggle batch

## Writing a good hypothesis
- **Predict the result** - state outcome and direction before running; no stated expectation = cannot confirm or refute; a wrong prediction that misses still teaches
- **Pre-register the bar** - the pass/fail gate that decides ship vs drop, before building
- **Diagnostic kill-gate** - measure the precondition before any build; absent precondition → kill cheaply (e.g. errors must concentrate ≥30%, ratio >1.5 → measured 0.93 → killed pre-build)
- **Probe first** - measure firing rate / density on a sample before wiring
- **Two-sided acceptance** - improve the target AND hold the control; no silent regression
- **Mechanism, not data** - gate the feature inert where the mechanism is absent; test the mechanism, not memorised text
- **Falsifiable probe** - measurement-only; never trains, never enters cross-validation
- **Honest splits** - leave-one-X-out; no learner touches the fold it scores; name the headline split and why
- **Size-dependent** - re-run as the data grows; never trust a single snapshot - record each re-run as a `log:` line in the hypothesis's Log so the trajectory stays visible, not overwritten
- **Reproducible plan** - the hypothesis re-runs from its own text; the Hypothesis and Lever name the provenance of any artefact used so the claim is never thin (a bare "trained draft head" → "EAGLE-3 head obtained `<id>`" or "trained here on `<corpus>`"); full re-run requirements in the Reproducibility rule below

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
- Maths - equations liberally, not prose where a formula is exact; unicode glyphs inline for copy-paste (`τ(i) = Σⱼ Tᵢⱼ·posⱼ / Σⱼ Tᵢⱼ`, `√(2 − 2cos)`); every full/display equation as a separated `$$…$$` block on its own line (blank line above/below) in the Mechanism section - these are rasterised to images for surfaces that do not run MathJax (Medium, DOCX); never `$…$` inline in a sentence, never a standalone maths section