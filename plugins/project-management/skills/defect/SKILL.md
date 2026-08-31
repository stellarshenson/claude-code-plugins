---
name: defect
description: File, triage, log, close or reject a defect in the project's defects document - permanent category-scoped ids (DEF-LNCH-3), mandatory CRITICAL/MAJOR/MEDIUM/MINOR severity, repro line and the append-only attempt trail, all through the pm-tools CLI
allowed-tools: [Read, Write, Bash, Skill]
---

# Defect

Read the `project-management` skill first - it is the single source of truth for the id scheme, the line format, the three states, authoring, relations and the `pm-tools` command surface. Do NOT duplicate its content here. Its `skills/project-management/references/defects.md` wins on any conflict about defects specifically.

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

1. Read the `project-management` skill, then `skills/project-management/references/defects.md`
2. **Ask for the author handle once** and reuse it - every write takes `--author @xx`, and the handle must be on the roster (`pm-tools author FILE --handle @xx --name "Full Name"`) before it can write
3. **Find the store before creating one** - `ls docs/defects*.md`; one consolidated doc per project is the default. An area is a category, never a separate file
4. **Lock what you work on, release when you stop** - default, unasked: `pm-tools lock FILE --id ID --author @xx` writes its `lock:` line before your first write to a defect, `unlock` when you are done with it; ask before working on a defect locked by someone else. The lock never blocks a write, expired locks clear themselves on the next write, and `pm-tools unlock FILE --author @xx --id ID` clears one at will; taking or clearing an active lock held by another handle is a transfer - `lock` and `unlock` print `TRANSFER: DEF-LNCH-3 was locked by @yy until <stamp> - you are taking it over; ask @yy` and proceed, and a takeover with no `--note` records `taken over from @yy`. `report`, `list`, `search` and `refs` print `N item(s) currently worked on: DEF-LNCH-3 by @xx until <stamp>` on stderr before the table - read it before choosing what to pick up
5. **Triage it yourself, as you file it** - `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR` off the symptom, on the worst plausible reading. Never ask the user for the level and never leave it unset; `add` refuses one and `check` errors on one. If the symptom itself is unclear, that is a defect question - ask that
6. **Symptom first, in the reporter's terms**; `cause under investigation` is a legitimate value. The `--repro` line is written for whoever will act on it
7. **Record the cause the moment you have one** - `pm-tools root-cause FILE --id ID --text "<why it happens>" --author @xx`. A later theory OVERRIDES: it is written above the previous record and the previous record stays, so the dead end you already ruled out is still readable days later. `--update` only rewords the newest record; it is not how a new theory is recorded
8. **Log every attempt, including the failures and why they failed** - `pm-tools log --event "attempted: ... - did NOT work"`. The record of what is already ruled out is why the file exists
9. **Close vs reject** - a real defect not being fixed is a `close` with the reason; a report that was never a defect (never reproduced, or the functionality is gone) is a `reject` with the reason
10. **Closing needs proof** - `close` refuses without `--evidence`: one line saying what shows the defect is gone, the regression test that passes or the build the repro no longer fires on. Do not close on the strength of having written a fix; run something first and record what it said
11. **A fixed defect that breaks again is a regression, not a reopen** - `reopen DEF-LNCH-3` files `DEF-LNCH-3-1` and leaves the original closed with its proof intact. Record how the regression reproduces with `edit --repro`; it need not be the old one. Never hand-edit a closed defect back to open - the ordinals are what make regressions countable
12. **Gate** - `pm-tools check docs` after the session; exit 0 with no errors is the bar
