---
name: upgrade
description: Rebuild a legacy acceptance-criteria or defects document to the tracked schema - assigns permanent ids, puts a code on every category, converts dated notes to authored log lines, drops the hand-kept contents table; dry run first
allowed-tools: [Read, Write, Bash, Skill]
---

# Upgrade

Read the `project-management` skill first for the target schema, then `skills/project-management/references/upgrade.md` - it is the single source of truth for the upgrade order and what the dry run refuses to guess. Do NOT duplicate either here.

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

1. Read the `project-management` skill, then `skills/project-management/references/upgrade.md`, and follow that file's numbered order literally
2. **Roster first** - `pm-tools author FILE --handle @xx --name "Full Name"`; nothing else runs until a handle exists
3. **Dry run before anything is written** - `pm-tools upgrade FILE` prints the plan and the `HINT` lines, and writes nothing
4. **Apply with `--author`** - `pm-tools upgrade FILE --author @xx --apply`. It always applies every safe rewrite (ids, codes, stamps, severity and test-tag canonicalisation, the Contents drop) and exits 0; every content problem prints as a `HINT` carrying the exact command to run. A missing roster or `--author` is a hint too - everything needing no signature still lands
5. **Run every hinted command** - the hints are the work. Rate every unrated criterion yourself with the hinted `pm-tools edit ... --importance ...` against the rubric in `skills/project-management/references/acceptance-criteria.md`, and triage every untriaged defect with `edit ... --severity ...` against `skills/project-management/references/defects.md`; never ask the user and never skip one - both are `check` errors, so the gate stays red until done
6. **Describe every category** - the tool never invents a description
7. **Gate** - `pm-tools check FILE` must exit 0, and `--strict` once the per-item hints and tags are filled. That fill can take several passes on a large file; they are warnings, not errors
