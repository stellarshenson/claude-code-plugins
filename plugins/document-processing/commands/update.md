---
description: Update an existing document processing output - re-verify, apply corrections, add new source material
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "what to update and why, e.g. 'add new hearing transcript to timeline'"
---

# Document Processing - Update

Invoke `document-processing:update` skill. Updates existing `3-output/` document with new info, corrections, re-applied rules, or re-verification against updated sources - and **always re-runs grounding CLI on changed content before declaring done** (step 5 of skill is gate, not optional).

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

## When to use

- New source document added to `1-input/` - re-run affected sections
- User found errors in `3-output/` document - correct and re-verify
- Grounding audit failed - fix unconfirmed claims
- Uniformization rules changed - re-apply to existing output
- Additional context available - enrich existing document

## Flow

1. Skill identifies what exists (`3-output/`, `2-wip/`, `INSTRUCTIONS.md`, `BENCHMARK.md`), asks what changed and which document, then does targeted update (default) or full re-run via `process` skill
2. Mandatory grounding pass via `grounding` skill: `document-processing extract-claims` on changed doc -> review `claims.json` -> `document-processing ground --manifest ... --source <each 1-input/ source> --output validation/grounding-report.md` -> `document-processing check-consistency --document <doc> --output validation/consistency-report.md`; fix every UNCONFIRMED / CONTRADICTED claim and consistency finding
3. Re-verify against `BENCHMARK.md`, report score delta
4. WIP manifest updated with what changed, when, and post-update grounding score

## When NOT to use this

- Building new deliverable from scratch -> use `/document-processing:process`
- Validating document you did not produce here -> use `/document-processing:validate`
- Bare claim grounding -> use `/document-processing:grounding`
