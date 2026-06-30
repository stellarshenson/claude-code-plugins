---
description: Write or update a hypothesis-driven experiments log and its SOTA design doc - record a round, or conclude the design
allowed-tools: [Read, Write, Edit, Glob, Grep, Skill]
argument-hint: "what to document, e.g. 'record round R12: synthetic-retrained weights, single global cut, TNR 0.78' or 'conclude the SOTA doc for the docdistance track'"
---

# Hypothesis

Read the `datascience:hypothesis` skill first - it is the single source of truth for the document structure, the per-hypothesis template, and the canonical-doc-across-runs rules. Do NOT duplicate its content here. The two `examples/wmd-docdistance-*.md` docs win on any conflict.

Write up or extend hypothesis-driven research documentation: the canonical append-only **experiments log** (each hypothesis with setup, prediction, result, verdict) and the **SOTA document** (winning components distilled into a final design).

## What to do

1. Read the `datascience:hypothesis` skill, then the closest `examples/` doc for what you are writing
2. Decide doc + action: **record a round** → experiments log (default); **conclude / update the design** → SOTA doc
3. **Find the canonical doc first** - `Glob docs/**/*experiments*.md` and `*sota*.md`, confirm by the secondary-title marker (not the filename); if one exists for the track, append - never start a parallel doc
4. **Experiments log (append-only)**:
   - Find the last round (`E<batch>` / `R<round>`), append the next with a monotonic number; never rewrite a recorded verdict (supersede with a one-line back-reference)
   - Write each hypothesis with the skill's per-hypothesis template; add rows to the research-at-a-glance and per-batch results tables
   - Ensure Methodology defines a naive baseline; report each result as a delta against it (skill: "Naive baseline mandatory")
   - **Show the user the before/after summary tables** (skill: "User-facing summary tables") - pre-registration before the run, verdict + interpretation after
5. **SOTA doc (rewrite on convergence)**: mirror the docdistance SOTA section order; carry surviving components only; cross-link the log as evidence
6. Apply the skill's Rules (sanitise, equations, terse style); re-read and cut any sentence a table or number carries faster

## Creating a new canonical doc

If no doc exists for the track, scaffold it from the matching `examples/` file's section order:
- Experiments log → `docs/experiments/<project>-experiments.md`
- SOTA doc → `docs/<project>-sota.md`

Name for the research track, not the date. Open the log with the H1 title, the secondary-title marker `**Canonical Experiments Document**` (use `**Canonical SOTA Document**` for the design doc), then the one-paragraph overview (what the experiment is, the branch/artefacts, where the data lives), then the problem overview.
