---
description: Print the status, triage and test-coverage report for the project's acceptance criteria or defects - SUMMARY, categories, coverage, the open fix queue and the rejected reasons, computed from the file by pm-tools
allowed-tools: [Read, Bash, Skill]
argument-hint: "what to report, e.g. 'where do the defects stand' or 'the AUTH criteria in detail' or 'audit both documents'"
---

# Report

Read the `project-management` skill first - it is the single source of truth for what the sections mean and how the tables are read. Do NOT duplicate its content here. `references/reports.md` carries the section shapes, the filter semantics and `--detail`.

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

1. Read the `project-management` skill, then `references/reports.md`
2. **Run `pm-tools report`** on the store - `docs` scans for both disciplines, a path narrows to one
3. **Map a filtered ask onto flags; never filter by hand.** "The critical defects" is `--severity CRITICAL`, "what closed in August" is `--dates closed --since 2026-08-01 --until 2026-08-31`, "the AUTH work" is `--category AUTH`, "what is open" is `--status open`. `--category`, `--severity` and the date window narrow the whole report; `--status` narrows ITEMS alone; `--detail` swaps the ITEMS tables for one block per item. Reading the document and filtering inside the answer is the failure this tool exists to prevent
4. **Asked for a summary, run `--summary`** - it stops at the SUMMARY grid and lists no items, and it is plain by itself. Asked for something plain or short of a full report, `--plain` gives the two grids with no icons, no blurbs, no CATEGORIES and no TEST COVERAGE
5. **Paste the tables verbatim** - they are the deliverable. Do not re-type them, do not restate them in prose beside the table, do not summarise a table the user can read
6. Add at most one line of your own: what the reader should do next, if anything is obvious from the queue. After a `--summary`, add nothing - naming the items, the clusters or the row count underneath puts back what the flag removed
7. **Audit mode** - asked to audit rather than report, run `pm-tools check docs --strict` first and lead with its errors and warnings; the report follows underneath. `check` reports, it does not repair, so a dangling id is something to fix deliberately, not to reconcile silently
