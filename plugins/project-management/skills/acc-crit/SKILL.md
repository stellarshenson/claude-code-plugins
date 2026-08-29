---
name: acc-crit
description: Add, close, reject, relate or audit acceptance criteria in the project's acc-crit document - permanent ACC-<CAT>-<N> ids, author handles, test hints and tags, all through the pm-tools CLI
allowed-tools: [Read, Write, Bash, Skill]
---

# Acceptance Criteria

Read the `project-management` skill first - it is the single source of truth for the id scheme, the line format, the three states, authoring, relations and the `pm-tools` command surface. Do NOT duplicate its content here. Its `skills/project-management/references/acceptance-criteria.md` wins on any conflict about criteria specifically.

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

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## What to do

1. Read the `project-management` skill, then `skills/project-management/references/acceptance-criteria.md`
2. **Ask for the author handle once** and reuse it - every write takes `--author @xx`, and the handle must be on the roster (`pm-tools author FILE --handle @xx --name "Full Name"`) before it can write
3. **Find the store before creating one** - `ls docs/acc-crit*.md`; one consolidated doc per project is the default, a scoped file only when the user asks. Never a file per criterion
4. **Lock what you work on, release when you stop** - default, unasked: `pm-tools lock FILE --id ID --author @xx` writes its `lock:` line before your first write to an item, `unlock` when you are done with it; ask before working on an item locked by someone else. The lock never blocks a write, expired locks clear themselves on the next write, and `pm-tools unlock FILE --author @xx --id ID` clears one at will; taking or clearing an active lock held by another handle is a transfer - `lock` and `unlock` print `TRANSFER: ACC-AUTH-1 was locked by @yy until <stamp> - you are taking it over; ask @yy` and proceed, and a takeover with no `--note` records `taken over from @yy`. `report`, `list`, `search` and `refs` print `N item(s) currently worked on: ACC-AUTH-1 by @xx until <stamp>` on stderr before the table - read it before choosing what to pick up
5. **One assertion per item** - a criterion needing "and" is two criteria; edge cases are their own items, enumerated across the whole fanout
6. **Rate it yourself, as you file it** - `--importance CRITICAL|HIGH|MEDIUM|LOW`, read off the assertion against the rubric in `skills/project-management/references/acceptance-criteria.md`. Never ask the user for the level and never leave it unset; `add` refuses one and `check` errors on one
7. **Write through `pm-tools`, never by hand** - `add` assigns the next id and the log line; hand-editing loses both
8. Fill the `--test` hint and `--test-tags` as you add (tags are written upper-case - `UNIT`, `E2E`), and never tag a test that does not exist
9. **Closing needs proof** - `close` refuses without `--evidence`: one line saying the `test:` line was run and what it showed. Run it first; do not close a criterion on the strength of the code looking right
10. **Gate** - `pm-tools check docs` after the session; exit 0 with no errors is the bar
