---
description: Write or update a hypothesis-driven experiments log and its SOTA design doc - record a round, or conclude the design
allowed-tools: [Read, Write, Edit, Glob, Grep, Skill]
argument-hint: "what to document, e.g. 'record round R12: synthetic-retrained weights, single global cut, TNR 0.78' or 'conclude the SOTA doc for the docdistance track'"
---

# Hypothesis

Read the `datascience:hypothesis` skill first - it is the single source of truth for the document structure, the per-hypothesis template, and the canonical-doc-across-runs rules. Do NOT duplicate its content here. The two `examples/wmd-docdistance-*.md` docs win on any conflict.

Write up or extend hypothesis-driven research documentation: the canonical append-only **experiments log** (each hypothesis with setup, prediction, result, verdict) and the **SOTA document** (winning components distilled into a final design).

## What to do

1. Read the `datascience:hypothesis` skill, then read the closest `examples/` doc for the document you are writing
2. Decide the document and the action from the user's request:
   - **Record a round** → the experiments log (the default)
   - **Conclude / update the design** → the SOTA doc
3. **Find the canonical doc first** - `Glob docs/**/*experiments*.md` and `*sota*.md`; if one exists for this track, append to it - never start a parallel doc
4. **For the experiments log (append-only)**:
   - Read the existing doc, find the last round (`E<batch>` / `R<round>`), note its number
   - Append the new round at the end with a monotonic number; never renumber or rewrite a recorded verdict
   - Write each hypothesis with the canonical bullet template: Hypothesis (one causal claim) / Lever / Mechanism / Prediction / Acceptance bar / Result / Verdict
   - Add a row to the research-at-a-glance table and to any per-batch results table
   - If a later round supersedes an earlier verdict, add a one-line back-reference - do not edit the old round
5. **For the SOTA doc (rewrite on convergence)**:
   - Mirror the docdistance SOTA section order: Abstract → Problem → Solution → Pipeline → Mechanism → Performance → Setup → Methods of measurement → Throughput/footprint → Limitations → FAQ → Implementation → Conclusions → Bibliography
   - Carry surviving components only; cross-link the experiments log as its evidence
   - Maths as inline unicode in prose plus separated `$$…$$` display blocks in the Mechanism section
6. **Sanitise** - no client/customer name (use "private dataset"); no em-dashes, unicode arrows (→), escape `\$`
7. Re-read the written section against the skill's checklists; cut any sentence a table or number carries faster

## Creating a new canonical doc

If no doc exists for the track, scaffold it from the matching `examples/` file's section order:
- Experiments log → `docs/experiments/<project>-experiments.md`
- SOTA doc → `docs/<project>-sota.md`

Name for the research track, not the date. Open the log with the title + one-paragraph overview (what the experiment is, the branch/artefacts, where the data lives), then the problem overview.
