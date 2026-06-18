---
name: hypothesis
description: Structure and maintain hypothesis-driven experiment documentation for software or data-science research - a canonical running experiments log (each hypothesis with its setup, prediction, result, and verdict) plus a SOTA document that distils the winning hypotheses into a final design. Manages both docs across runs - read the existing canonical doc, append the new round, never rewrite a recorded verdict. Use whenever the user is writing up an experiment, recording a hypothesis and its result, comparing approaches to decide which wins, drafting a research report needing a problem overview and executive summary, or concluding a state-of-the-art / final-design document - even without the word "hypothesis". Enforces the terse technical-documentation style (overview then factual bullets). Triggers - "document this experiment", "write up the hypothesis", "experiments doc", "sota doc", "research writeup", "which approach won", "record this round", "update the experiments log", "structure my results".
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Hypothesis

Structure and maintain two complementary research documents: a canonical running **experiments log** (every hypothesis with its setup, prediction, result, and verdict) and a **SOTA document** (the surviving hypotheses distilled into a final design). Built for falsifiable hypotheses, an honest problem overview, and a skim-readable executive summary. The experiments log is canonical and append-only - it persists and grows across runs; the SOTA doc is rewritten when the arc converges.

> **Required style (mandatory)** - write every section in the terse technical-documentation style: one or two overview sentences, then factual bullets; one fact per bullet; numbers inline; no full stop ending a bullet; no em-dashes (use ` - `), unicode arrows (→), escape `\$`. Flowing prose only where an argument genuinely needs it. The `technical-documentation` skill is the full reference if available.

> **docdistance wins** - the two `examples/wmd-docdistance-*.md` docs are the latest canonical shape. When this skill's guidance and a docdistance example disagree on section order, per-hypothesis layout, or phrasing, follow the docdistance example.

## Workflow
- **Pick the document** - the experiments log (recording ongoing work) or the SOTA doc (concluding it once the arc converges)
- **Read the closest example** in `examples/` first, then mirror its section order - do not invent a new structure
- **For an existing canonical doc, read it before writing** - find the last round, append the next; never renumber or rewrite a recorded verdict
- **Draft, then re-read with fresh eyes** against the section checklists below; cut any sentence a table or a number would carry faster

## Canonical documents across runs
The experiments log is one durable file that many runs append to; treat it as the system of record, not a fresh writeup each session.
- **Stable location** - `docs/experiments/<project>-experiments.md` for the log, `docs/<project>-sota.md` (or `<project>-solution-sota.md`) for the design; one of each per research track, named for the track not the date
- **Find it first** - `Glob docs/**/*experiments*.md` and `*sota*.md` before creating anything; if a canonical doc exists, append to it - never start a parallel doc for the same track
- **Append-only log** - each run adds its round at the end (`E<batch>` or `R<round>`); numbering is monotonic; a recorded verdict is immutable, later evidence is a new round that supersedes it, with a one-line back-reference
- **Update, don't duplicate** - new round → append a section + a row to the research-at-a-glance table + a row to any results table; do not rewrite earlier rounds
- **SOTA on convergence** - rewrite the SOTA doc only when the winning design changes; it carries surviving components only, and links the log as its evidence
- **Cross-link the pair** - the SOTA doc states the design, the log proves it; each names the other by path
- **Sanitise every run** - no client or customer name (use "private dataset"); private data paths stay git-ignored and uncommitted

## Two documents
- **Experiments log** - the evidence; one section per hypothesis round/batch; appended as work proceeds; a verdict on every hypothesis
- **SOTA document** - the conclusion; written once the arc converges; winning components only, plus performance, limitations, implementation
- **Linked pair** - the SOTA doc states the design, the experiments log proves it; each links the other

## Experiments log - section order
Mirror `examples/wmd-docdistance-experiments.md` (the canonical compact shape) or `examples/lexical-grounding-experiments.md` (a long multi-round arc).
- **Title + overview** - one paragraph: what the experiment is, the branch/artefacts, where the data lives
- **Problem overview** - dataset (size, labels, class balance, domain/language spread), caveats, the core difficulty; exact counts, no framing fluff
- **Executive summary** - headline result first; then a "research at a glance" table (one row per hypothesis: lever, mechanism, predicted, result, verdict); then a baseline/performance table
- **Methodology and metrics** - signals/features or the metrics each lever moves, the verdict head, the cross-validation splits, the guardrails
- **Setup** - data/fixtures, dependencies, operating point, the execution vehicle (notebook/CLI), reproducibility - exact enough to re-run
- **Hypothesis rounds/batches** - one section per `E<batch>` or `R<round>`; each opens with one line, then a subsection per hypothesis, then a per-batch results table and benchmarks
- **Lessons learned** - generalisable insights, not a result restatement
- **Conclusions** - what ships and why
- **Next steps** - open threads; a "refuted, do not revisit" list

## Per-hypothesis template (canonical, from docdistance)
Each hypothesis is a record, written as this fixed bullet set. The prediction is what makes it falsifiable - the gap between predicted and measured is the finding.
- **Hypothesis** - one terse causal claim: `because <mechanism + observed precondition>, <intervention> will <measurable outcome ≥ threshold> while <guardrail holds>`; the `because` carries the rationale, the `will` is the falsifiable numeric prediction, the `while` is the guardrail
- **Lever** - the single thing changed (and the baseline it replaces), e.g. "embedding geometry (baseline raw mmBERT)"
- **Mechanism** - how the lever acts, one or two clauses, concrete
- **Prediction** - the expected outcome and direction before running, e.g. "DR ≥ 1.5x, margin widens"
- **Acceptance bar** - the pre-registered pass/fail numbers, distinct from the prediction, e.g. "DR ≥ 1.5x baseline and V = 0"
- **Result** - the measured numbers, including the swept parameter and the guardrail reading
- **Verdict** - one of Ships / Kept / Promoted / Dropped / Refuted / Refuted (null) / Killed-at-gate, with the number that justifies it

Name each `R<round>-H<n>` or `E<batch>-H<n>` (docdistance uses `E01-H1`); the name states what is tested, never "try X". `E<batch>` is an experiments batch, typically grouping 2-5 hypotheses.
- **Global ordinal `<n>`** - one continuous ascending series across all bundles, never reset per bundle (E1-H1..H3, E2-H4..H6, E3-H7..); a unique number per hypothesis, trackable across the whole log
- **Keep the bundle prefix** - `E<batch>` stays for context; only `H<n>` runs globally
- **Sub-variants fold in** - a fallback or `Hxb` becomes its own ordinal, never a letter suffix

## Writing a good hypothesis
- **Predict the result** - state the expected outcome and direction before running; a hypothesis with no stated expectation cannot be confirmed or refuted, and a result that matches a wrong prediction still teaches something
- **Pre-register the bar** - the pass/fail numbers before building; the gate that decides ship vs drop
- **Diagnostic kill-gate** - measure the precondition before any build; absent precondition → kill cheaply (e.g. errors must concentrate ≥30%, ratio >1.5 → measured 0.93 → killed pre-build)
- **Probe first** - measure firing rate / density on a sample before wiring
- **Two-sided acceptance** - improve the target AND hold the control; no silent regression
- **Mechanism, not data** - gate the feature so it stays inert where the mechanism is absent; test the mechanism, not memorised text
- **Falsifiable probe** - measurement-only, never trains, never enters cross-validation
- **Honest splits** - leave-one-X-out; no learner touches the fold it scores; name the headline split and why
- **Size-dependent** - re-run as the data grows; never trust a single snapshot

## SOTA document - section order
The full conclusion-doc shape; mirror `examples/wmd-docdistance-sota.md` (the canonical full shape). Drop a section only when the design genuinely has nothing for it.
- **Abstract** - one dense paragraph: what it is, the foundational result it adapts (inline footnote + digest link), what it swaps vs keeps from that prior work, the headline number, and a closing "this is the conclusion doc, the experiments log is its evidence" cross-link
- **Problem** - why the task is hard: the coarse or blind baseline, the missing signal, the property the solution must satisfy (e.g. a metric); bullets, exact terms
- **Solution** - the lift in one sentence, then the load-bearing readout bullets: a one-line result interpretation (what the number means, its range, the normalized form), a "why and how to use" I/O contract (what goes in → what comes out), a determinism / reproducibility-as-strength bullet where it beats a baseline (e.g. vs a sampling LLM judge), and the headline result
- **Pipeline / components** - the stages, input → verdict; one bullet per stage, each naming its model / cost / output
- **Mechanism / theory** (mandatory) - why the winning design works: the principle or foundational result it rests on, cited to the paper with a digest link; prose + separated LaTeX (arxiv style), with "why not <the obvious alternative>" worked inline; terse, enough to ground the design, not a literature review
- **Performance** - a shipped-vs-baseline table, one row per measure, at the operating point; interpretive bullets that separate the win from the accepted tradeoff
- **Setup** (when measured performance is reported) - benchmark prep: hardware named, models, workload, thread pinning for the single-core unit
- **Methods of measurement** - how each figure is taken: warmup, reps, single-stream, what each number means, caveats
- **Throughput / footprint** - the single-core benchmark (ms/unit, tokens/s, end-to-end on a named workload), the per-core unit and deployment extrapolation (e.g. AWS Lambda ≈ 1 vCPU per 1769 MB), latency, footprint, dependencies
- **Limitations** - honest residuals; what it does not do; separate intrinsic-to-the-fixture from a defect of the method
- **FAQ** - a "why not <X>?" entry for every obvious alternative a reviewer would raise, each killed with one concrete disqualifier (no metric, needs logits, non-deterministic, too coarse)
- **Implementation** - notebooks, experiments-doc link, the shipped functions / library, the validation artefact
- **Conclusions** - the bounded interpretable readout restated: range, verdict rule, use scenario, operating point, headline performance
- **Bibliography** - footnote-anchor pattern (`<span id="refN">…</span>` paired with `[<sup>refN</sup>](#refN)` at first use), each ref with its digest path

## SOTA doc - the load-bearing bits
What separates a SOTA doc from a feature README; get these or it reads as notes.
- **Abstract names its lineage** - the foundational paper it adapts, cited inline with a digest link, and exactly what it swaps vs keeps
- **One-line interpretation** - a single bullet that says what the number means and its range, with the normalized readout (e.g. closeness `= 1 − d/max`); a reader grasps the output from this line alone
- **I/O contract** - "two texts in → one metric distance, a verdict, and the alignment"; state what goes in and what comes out before any maths
- **Reproducibility as a strength** - where the method is deterministic and a baseline is not, say so as a selling point
- **"Why not X" pre-empts the reviewer** - every obvious alternative gets a one-line disqualifier in the FAQ or Mechanism; the rejected options are the argument
- **Win vs tradeoff split** - the Performance bullets name the metric that improved AND the metric that regressed, with the reason the tradeoff is accepted
- **Deployment unit** - carry the single-core number to a cloud sizing (vCPU / MB), so the figure is actionable not academic
- **Cross-linked pair** - the Abstract and Limitations link the experiments log and any sibling design doc

## Problem overview - the opening
- **Dataset first** - size, label schema, class balance, language/domain spread; exact counts
- **Caveats** - cohort effects, evaluation choices, what the split does and does not test
- **Core difficulty** - the gap that makes the task hard, one or two bullets
- **Facts only** - the reader grasps the problem from this section alone

## Executive summary
- **Headline first** - best model/lever + key metric in the first sentence
- **Research-at-a-glance table** - one row per hypothesis: lever, mechanism, predicted, result, verdict; the whole sweep at once
- **Key findings** - beats X, the lever is Y, replicated across Z, the residual is W
- **Performance/baseline table** - the reference numbers every lever is measured against
- **Diagram only if it earns its place** - e.g. a gain-trajectory figure across rounds

## Examples
Read the closest match before writing; mirror its section order. docdistance is the canonical shape and wins on any conflict.
- `examples/wmd-docdistance-experiments.md` - **canonical** experiments log; one batch (E01), five pre-registered levers, the per-hypothesis template, research-at-a-glance + baseline tables, results table + benchmarks
- `examples/wmd-docdistance-sota.md` - **canonical** SOTA doc; the full shape Abstract (lineage + digest link) → Solution (one-line interpretation, I/O contract, reproducibility-as-strength) → Mechanism (prose + separated LaTeX, why-not-cosine, exact-EMD-vs-Sinkhorn) → Performance → FAQ → Conclusions → Bibliography
- `examples/lexical-grounding-experiments.md` - experiments log, a long multi-round arc (12 rounds); the research-at-a-glance table and per-round progression across data growth and ship decisions
- `examples/lexical-grounding-sota.md` - SOTA design on a deterministic track; pipeline → performance → limitations → implementation, no maths-heavy mechanism

## Rules
- terse technical-documentation style for every section (see the note at the top)
- Tables for sweeps - hypothesis × lever × result; never prose where a table scans faster
- Numbers inline on every claim; a verdict label on every hypothesis
- No client/customer name - sanitise to "private dataset"; no em-dashes, unicode arrows (→), escape `\$`
- Maths - inline unicode in prose for copy-paste (`√(2 − 2cos)`), plus the same maths as separated `$$…$$` LaTeX display blocks placed as separate paragraphs in the relevant Mechanism section (arxiv style, render-ready); never `$…$` inline in a sentence, never a standalone maths section
- Append-only on the canonical experiments log - new rounds at the end; never rewrite a recorded verdict
