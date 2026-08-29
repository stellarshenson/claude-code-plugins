---
name: report
description: Print the status, triage and test-coverage report for the project's acceptance criteria or defects - SUMMARY, categories, the open fix queue, the rejected reasons and the coverage grid - or an ad-hoc table or pivot over them, computed from the file by pm-tools
allowed-tools: [Read, Bash, Skill]
---

# Report

Read the `project-management` skill first - it is the single source of truth for what the sections mean and how the tables are read. Do NOT duplicate its content here. `skills/project-management/references/reports.md` carries the section shapes, the filter semantics and `--detail`.

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

1. Read the `project-management` skill, then `skills/project-management/references/reports.md`
2. **Run `pm-tools report`** on the store - `docs` scans for both disciplines, a path narrows to one
3. **Map a filtered ask onto flags; never filter by hand.** "The open defects only" is `--status open`, "the critical defects" is `--severity CRITICAL`, "what @kj has left in AUTH" is `--author @kj --category AUTH`, "what closed in August" is `--dates closed --since 2026-08-01 --until 2026-08-31`, "the critical criteria" is `--importance CRITICAL`, "the regressions" is `--regressions`, "what is blocked" is `--blocked`, "everything around DEF-LNCH-3" is `--related-to DEF-LNCH-3`, "anything whose title, body, evidence or log mentions the token" is `--grep token`, "what is being worked on" is `--locked` and "what @kj is working on" is `--locked-by @kj`. Flags combine. Every filter narrows the whole report except `--status`, which narrows ITEMS alone; `--detail` swaps the ITEMS tables for one block per item. Reading the document and filtering inside the answer is the failure this tool exists to prevent
4. **Asked about test coverage, run `pm-tools coverage`** - the grid of categories by tags (`UNIT`, `INTEGRATION`, `FUNCTIONAL`, `E2E`, `MANUAL`, any other tag, `NO-TEST` last), counting open and closed items alike; it takes the same filters
5. **A question no report section answers is a `list` or a `pivot`, still a table.** Who owns what by severity is `pivot --rows author --cols severity`; the open work oldest first with owners is `list --status open --columns id,title,author,age --sort=-age`; regressions per defect is `pivot --rows root --regressions --values ids`. "Is there already an item about X" is `search "X"` - a ranked table, pasted like any other, never a reading of the file. The ask-to-command table and the FIELDS vocabulary are in `references/reports.md`. Never tabulate by hand from the document - shape the table with the tools and paste it
6. **Asked for a summary, run `--summary`** - it stops at the SUMMARY grid and lists no items, and it is plain by itself. Asked for something plain or short of a full report, `--plain` gives the grid and the queue with no icons, no blurbs and no CATEGORIES. The grid is plain counts - open per level, then Fixed / Done and Rejected - and needs no legend
7. **A `wip @xx until <stamp>` on an ITEMS row is a soft lock** - the item's `lock:` line; @xx is likely working on that item, and the SUMMARY `Worked on` column counts them. Ask before picking a locked item up; lock one you pick up yourself with `pm-tools lock FILE --id ID --author @xx`. The lock never blocks a write, expired locks clear themselves on the next write, and `pm-tools unlock` clears one at will. `report`, `list`, `search` and `refs` also print `N item(s) currently worked on: DEF-X by @xx until <stamp>` on stderr before the table whenever a shown item is locked - read that line before choosing what to work on; taking or clearing an active lock held by another handle is a transfer - `lock` and `unlock` print `TRANSFER: DEF-X was locked by @yy until <stamp> - you are taking it over; ask @yy` and proceed, and a takeover with no `--note` records `taken over from @yy`
8. **Paste the tables verbatim** - they are the deliverable. Do not re-type them, do not restate them in prose beside the table, do not summarise a table the user can read. A collection of items is always a table, never a bulleted list
9. Add at most one line of your own: what the reader should do next, if anything is obvious from the queue. After a `--summary`, add nothing - naming the items, the clusters or the row count underneath puts back what the flag removed
10. **Audit mode** - asked to audit rather than report, run `pm-tools check docs --strict` first and lead with its errors and warnings; the report follows underneath. `check` reports, it does not repair: a dangling relation and a blocked-by cycle are errors to fix by hand, an open item blocked by finished work is a warning
