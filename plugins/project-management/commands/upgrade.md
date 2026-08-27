---
description: Rebuild a legacy acceptance-criteria or defects document to the tracked schema - assigns permanent ids, puts a code on every category, converts dated notes to authored log lines, drops the hand-kept contents table; dry run first
allowed-tools: [Read, Write, Bash, Skill]
argument-hint: "the document to upgrade, e.g. 'docs/acceptance-criteria.md' or 'the old bug list under docs/'"
---

# Upgrade

Read the `project-management` skill first for the target schema, then `references/upgrade.md` - it is the single source of truth for the upgrade order and what the dry run refuses to guess. Do NOT duplicate either here.

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

## What to do

1. Read the `project-management` skill, then `references/upgrade.md`, and follow that file's numbered order literally
2. **Roster first** - `pm-tools author FILE --handle @xx --name "Full Name"`; nothing else runs until a handle exists
3. **Dry run before anything is written** - `pm-tools upgrade FILE` prints every change and every item it cannot handle, and writes nothing. Read the refusals; they are the work
4. **Apply with `--author`** - a legacy file carries no handles, and `--author` signs every unauthored log line with the importer's handle. Without it the dry run refuses to guess
5. **Triage every defect the dry run flags** - it prints a ready `pm-tools edit ... --severity ...` line per untriaged one. Assign the level yourself against the rubric in `references/defects.md`; the gate stays red until the file is fully triaged
6. **Describe every category** - the tool never invents a description
7. **Gate** - `pm-tools check FILE` must exit 0, and `--strict` once the per-item hints and tags are filled. That fill can take several passes on a large file; they are warnings, not errors
