---
description: Add, close, reject, relate or audit acceptance criteria in the project's acc-crit document - permanent ACC-<CAT>-<N> ids, author handles, test hints and tags, all through the pm-tools CLI
allowed-tools: [Read, Write, Bash, Skill]
argument-hint: "the criterion work, e.g. 'add a criterion that the session times out after 30 idle minutes' or 'close ACC-AUTH-4, verified in v1.3.0'"
---

# Acceptance Criteria

Read the `project-management` skill first - it is the single source of truth for the id scheme, the line format, the three states, authoring, relations and the `pm-tools` command surface. Do NOT duplicate its content here. Its `references/acceptance-criteria.md` wins on any conflict about criteria specifically.

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

1. Read the `project-management` skill, then `references/acceptance-criteria.md`
2. **Ask for the author handle once** and reuse it - every write takes `--author @xx`, and the handle must be on the roster (`pm-tools author FILE --handle @xx --name "Full Name"`) before it can write
3. **Find the store before creating one** - `ls docs/acc-crit*.md`; one consolidated doc per project is the default, a scoped file only when the user asks. Never a file per criterion
4. **One assertion per item** - a criterion needing "and" is two criteria; edge cases are their own items, enumerated across the whole fanout
5. **Write through `pm-tools`, never by hand** - `add` assigns the next id and the log line; hand-editing loses both
6. Fill the `--test` hint and `--test-tags` as you add, and never tag a test that does not exist
7. **Gate** - `pm-tools check docs` after the session; exit 0 with no errors is the bar
