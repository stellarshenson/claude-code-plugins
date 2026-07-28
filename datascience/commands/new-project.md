---
description: Create a new data science project from copier template
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion]
argument-hint: "project name and brief description"
---

# Create New Data Science Project

Scaffold a new data science project using the copier-data-science template.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## Prerequisites

- `copier` must be installed: `pip install copier` or `uv tool install copier`
- Template: `https://github.com/stellarshenson/copier-data-science`

## Steps

1. ASK the user:
   - **Project name** (e.g. `my-analysis`)
   - **Description** (one line)
   - **Author** (name and email)
   - **Python version** (default: 3.12)
   - **Location** (default: current directory)

2. Run copier:
   ```bash
   copier copy https://github.com/stellarshenson/copier-data-science <project-name>
   ```

3. After scaffolding, seed the project `.claude/CLAUDE.md` (create the `.claude/` dir if absent; if the template already wrote a CLAUDE.md, append the sections below under a `## Project working rules` heading rather than overwriting):

   ```markdown
   # Project: <project-name>

   Data science project scaffolded from copier-data-science. Extends the workspace / global configuration with the conventions this project runs by.

   ## Core engineering rules (precedence over everything below)

   1. **Think before coding** - state assumptions; surface tradeoffs; ask when unclear; present interpretations rather than silently picking one
   2. **Simplicity first** - minimum code that solves the problem, nothing speculative; if 200 lines could be 50, rewrite
   3. **Surgical changes** - touch only what the task needs; match existing style; remove only the orphans your change creates
   4. **Goal-driven execution** - turn each task into a verifiable goal (write the test / define the metric, then satisfy it); loop until verified

   ## Datascience plugin skills to use

   - `datascience:notebook-standards` - notebook structure, GPU-by-UUID, grouped imports, config render, rich output, figures, progress bars, checkpointing long runs
   - `datascience:hypothesis` - the experiments log + SOTA doc; run the project as falsifiable hypotheses (below)
   - `datascience:papers` - download + digest every cited paper into `references/papers/`
   - `datascience:progressbars` - a rich / tqdm progress bar for every medium or long loop
   - `devils-advocate:adversarial-review` - hostile review: data-scientist (experiment rigor), architect (project architecture), popular-science (the writeup), ux-designer (notebook visuals)
   - `datascience:prompt-engineering`, `datascience:footnotes` - prompt techniques; notebook / markdown footnotes
   - `datascience` - naming, file-format, and project-structure conventions (auto-applies)

   ## Run the project as hypotheses

   - Maintain a canonical append-only experiments log (`docs/experiments/<project>-experiments.md`) and a SOTA design doc (`docs/<project>-sota.md`) via `datascience:hypothesis`
   - Each hypothesis is `E<batch>-H<n>` with a 2-3 part memory slug (`E12-H37 graph-degree-lever`); refer by numeric id, add the slug where space allows; a batch may carry a focus slug (`E12 graph-theory-levers`)
   - Record a self-contained, independently reproducible experiment setup per hypothesis - a reader re-runs it from the doc alone, not from the transcript or by reading the code
   - Pre-register every hypothesis (prediction + falsifier / acceptance bar + diagnostic kill-gate) against a defined naive baseline; show the before / after summary as a markdown pipe table
   - Execute a hypothesis or a whole batch as a spawned agent on the selected model (best executor by default; ask when cost or scale warrants); record the execution model
   - Cite papers through `datascience:papers` (PDF + digest in `references/papers/`)
   - Before concluding SOTA, run an ablative study of the strongest hypothesis or all survivors to settle each component's marginal worth
   - Keep the executive summary and the research-at-a-glance table current every round
   ```

   Then finish setup:
   - Initialize git: `git init && git add -A && git commit -m "initial scaffold from copier-data-science"`
   - Create venv: `make create_environment` (if Makefile exists)
   - Install deps: `make requirements`

4. Report what was created:
   - List the directory structure
   - Show the Makefile targets
   - Confirm the project is ready

## Do NOT

- Skip asking the user for project name
- Run copier without user confirmation
- Overwrite the template's own files (it follows all datascience standards already) - seeding `.claude/CLAUDE.md` is additive and expected
