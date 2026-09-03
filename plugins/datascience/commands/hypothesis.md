---
description: Write or update a hypothesis-driven experiments log and its SOTA design doc - record a round, or conclude the design
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill]
argument-hint: "what to document, e.g. 'record round R12: synthetic-retrained weights, single global cut, TNR 0.78' or 'conclude the SOTA doc for the docdistance track'"
---

# Hypothesis

Read the `datascience:hypothesis` skill first - it is the single source of truth for the document structure, the per-hypothesis template, and the canonical-doc-across-runs rules. Do NOT duplicate its content here.

Write up or extend hypothesis-driven research documentation: the canonical append-only **experiments log** (each hypothesis with setup, prediction, result, verdict) and the **SOTA document** (winning components distilled into a final design).

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

**Run the CLI without touching the caller's project.** The gate above puts it on PATH, so the bare command name is the whole invocation. `uv run` instead resolves whatever project the working directory sits in and writes `uv.lock` and `.venv` into it, so if you reach for uv pass `--no-project` (`uv run --no-project <cli> ...`) - it skips project discovery, leaves the tree untouched and still finds the same PATH binary. `--no-sync` and `--frozen` are not substitutes; both still create `.venv`.

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## What to do

1. Read the `datascience:hypothesis` skill, then the closest `examples/` doc for what you are writing
2. **Ask for the author handle once** and reuse it - every write takes `--author @xx`, and the handle must be on the ledger's `## Authors` roster (`hypothesis-tools author LOG --handle @xx --name "Full Name"`) before it can write
3. Decide doc + action: **record a round** → experiments log (default); **conclude / update the design** → SOTA doc
4. **Find the canonical doc first** - `Glob docs/**/*experiments*.md` and `*sota*.md`, confirm by the secondary-title marker (not the filename); if one exists for the track, append - never start a parallel doc
5. **Experiments log (append-only)**:
   - Lock each hypothesis before its first write - `hypothesis-tools lock LOG ID --author @xx`, 24 hours by default - and `unlock` when you stop; `list` names the hypotheses currently worked on before its table, so read that first and ask before writing to one another author holds. The lock never blocks a write: a foreign write warns once and lands, and `verdict` clears the lock it finds
   - Land each signed-off hypothesis with `hypothesis-tools register` (it reads the next free `H<n>` itself - never guess it, never reset the ordinal); record outcomes with `result` / `verdict` / `log-event`, add a field the template does not name with `field`, and never rewrite a recorded verdict (a flip is a new round with a one-line back-reference)
   - Write each hypothesis with the skill's per-hypothesis template; add rows to the research-at-a-glance and per-batch results tables
   - Ensure Methodology defines a naive baseline; report each result as a delta against it (skill: "Naive baseline mandatory")
   - **Show the user the before/after summary tables** (skill: "User-facing summary tables") - pre-registration before the run, verdict + interpretation after
6. **SOTA doc (rewrite on convergence)**: mirror the docdistance SOTA section order; carry surviving components only; cross-link the log as evidence
7. Apply the skill's Rules (sanitise, equations, terse style); re-read and cut any sentence a table or number carries faster

## Creating a new canonical doc

If no doc exists for the track, scaffold it from the matching `examples/` file's section order:
- Experiments log → `docs/experiments/<project>-experiments.md`
- SOTA doc → `docs/<project>-sota.md`

Name for the research track, not the date. Open the log with the H1 title, the secondary-title marker `**Canonical Experiments Document**` (use `**Canonical SOTA Document**` for the design doc), then the one-paragraph overview (what the experiment is, the branch/artefacts, where the data lives), then the problem overview.
