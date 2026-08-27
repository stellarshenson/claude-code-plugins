---
description: File, triage, log, close or reject a defect in the project's defects document - permanent DEF-<CAT>-<N> ids, mandatory CRITICAL/MAJOR/MEDIUM/MINOR severity, repro line and the append-only attempt trail, all through the pm-tools CLI
allowed-tools: [Read, Write, Bash, Skill]
argument-hint: "the defect work, e.g. 'file: auth token empty on the first turn after a fork' or 'log on DEF-LNCH-3: the 200ms delay did not fix it'"
---

# Defect

Read the `project-management` skill first - it is the single source of truth for the id scheme, the line format, the three states, authoring, relations and the `pm-tools` command surface. Do NOT duplicate its content here. Its `references/defects.md` wins on any conflict about defects specifically.

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

1. Read the `project-management` skill, then `references/defects.md`
2. **Ask for the author handle once** and reuse it - every write takes `--author @xx`, and the handle must be on the roster (`pm-tools author FILE --handle @xx --name "Full Name"`) before it can write
3. **Find the store before creating one** - `ls docs/defects*.md`; one consolidated doc per project is the default. An area is a category, never a separate file
4. **Triage it yourself, as you file it** - `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR` off the symptom, on the worst plausible reading. Never ask the user for the level and never leave it unset; `add` refuses one and `check` errors on one. If the symptom itself is unclear, that is a defect question - ask that
5. **Symptom first, in the reporter's terms**; `cause under investigation` is a legitimate value. The `--repro` line is written for whoever will act on it
6. **Log every attempt, including the failures and why they failed** - `pm-tools log --event "attempted: ... - did NOT work"`. The record of what is already ruled out is why the file exists
7. **Close vs reject** - a real defect not being fixed is a `close` with the reason; a report that was never a defect (never reproduced, or the functionality is gone) is a `reject` with the reason
8. **Gate** - `pm-tools check docs` after the session; exit 0 with no errors is the bar
