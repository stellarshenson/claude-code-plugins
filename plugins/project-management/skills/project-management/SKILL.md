---
name: project-management
description: Micro project management for a repository, a personal project or a small team - acceptance criteria and defects tracked in one markdown file per discipline, every item carrying a permanent category-scoped id (ACC-AUTH-102, DEF-LNCH-3) and an author handle (@kj), all reads and writes through the pm-tools CLI. Use when the user asks for acceptance criteria, acc crit, feature criteria, a defects list, a bug tracker, an issue tracker, or asks to log, add, close, reject, reopen, relate, list, report or audit a criterion or defect; for a status, triage or test-coverage report of either, including a filtered or summary one - the critical defects, what is open, the AUTH work, what closed last month; when an old-style document needs upgrading to carry ids and handles; and when a shared acc-crit or defects file hits a git merge conflict.
allowed-tools: Read, Write, Bash
---

# Project Management

Two tracking disciplines over one design: the markdown file is the whole store, `pm-tools` is the only way in, nothing is written down twice. Sized for a repository, a personal project or a small team - not a replacement for Jira.

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

## Disciplines - load only the one in play

| Discipline          | Load                                | Store               | Ids                   |
|---------------------|-------------------------------------|---------------------|-----------------------|
| Acceptance criteria | `references/acceptance-criteria.md` | `docs/acc-crit*.md` | `ACC-<CAT>-<N>`       |
| Defects             | `references/defects.md`             | `docs/defects*.md`  | `DEF-<CAT>-<N>`       |
| Legacy doc upgrade  | `references/upgrade.md`             | either              | assigned by `upgrade` |
| Merge conflicts     | `references/conflicts.md`           | either              | resolved, never renumbered |

Everything below is shared. Read one discipline file, not both. `references/reports.md` carries the report shapes, loaded when a report is asked for.

## No sync problem

Nothing is recorded in two places, so nothing drifts. The item's text, its checkbox, its category and its log are each stored exactly once, on the line itself. Everything else is computed on read:

| Derived fact           | Computed by                |
|------------------------|----------------------------|
| Next free number       | highest id in the file, plus one |
| Backlinks              | `pm-tools refs --id`       |
| Index, contents, counts| `pm-tools list-categories` |
| Test coverage per tag  | `pm-tools report`          |

Consequences, stated once:

- **No `## Contents`** - a hand-kept table of contents is a second index that drifts; `check` rejects one
- **No Open / Fixed sections** - status lives in the checkbox, so an item never moves
- **Links are one-way** - a `related:` on A is the only record; the reverse is computed, never written back
- **`check` reports, it does not repair** - a dangling id is a warning to read, not state to reconcile

## Ids

`ACC-AUTH-102`, `DEF-LNCH-3`. Type prefix, category code, number.

- **Type prefix** - `ACC` criterion, `DEF` defect; fixed by the discipline
- **Category code** - uppercase mnemonic, declared once as inline code at the end of the `##` heading, never re-derived per item. Three to five letters, six the ceiling; it must read as a word, so lengthen the tool's proposal whenever a letter or two spells the actual thing - `FRONT` over `FRON`, `GUARD` over `GUAR` - and never shrink it to bare initials
- **Number** - unique across the whole document, not per category; `add` takes the highest in the file plus one
- **Permanent once assigned** - an item that moves category keeps its id. The category segment records where it was born; the `##` section it sits under is the live truth. `check` deliberately does not compare the two
- **Never reused** - no renumbering, no recycling from a closed item

## Line format

One item is one top-level checklist line plus indented sub-lines. No sub-checkboxes: anything worth its own state gets its own id.

```markdown
## <Category name> `<CODE>`

<one-line category description>

- [ ] `<ID>` **<title>** - <body>
  - <hint>: <the discipline's one-line hint>
  - test-tags: unit, functional
  - evidence: <the proof it is done - written by close, present only while closed>
  - related: <ID>, <ID> - free text around the ids
  - blocked-by: <ID>
  - log: 2026-08-26T08:41:03Z @kj added
```

- Id first as inline code, then the `**bold title**`, then ` - ` and the body
- **Log every event** - `- log: <stamp> <@handle> <event>`; append, never rewrite or delete. A failed attempt is logged, not erased
- **Stamps are ISO 8601 UTC** - `2026-08-27T15:59:12Z`, always Zulu, never local and never a bare date: one unambiguous instant across zones, and it sorts as plain text
- Terse and factual; no emojis, no em-dashes, no unicode arrows (`-` and `->` are ASCII and legal), no trailing full stop
- **Details doc is the exception** - most items never need one. Where an item genuinely carries a root-cause study or a design argument, put it in `docs/<discipline>/<ID>-<slug>.md` and link it from the body

A filled-in item, and what belongs in its body, is in the discipline's own reference.

## Three states

| Box     | Status   | Means                                                                          |
|---------|----------|--------------------------------------------------------------------------------|
| `- [ ]` | open     | still to do; in progress stays open and says so in the newest `log:` line       |
| `- [x]` | closed   | met, fixed, or decided and done - and the `evidence:` line says how that is known |
| `- [-]` | rejected | dropped without being done, for a reason the discipline defines |

`reject` demands a reason and writes it to the log. `check` warns on a rejected item with no reason; `report` puts every reason in its own table. `reopen` returns a rejected item to open.

Reopening a **closed defect** does not reverse the closure - it files a regression. `reopen DEF-LNCH-3` leaves the parent closed with its evidence intact and opens `DEF-LNCH-3-1`, carrying the same title and severity; the next time, `-2`. Ordinals are flat, so reopening `DEF-LNCH-3-1` gives `DEF-LNCH-3-2`, never `-1-1`, and the highest ordinal is the number of times that defect has come back. `report` prints the total above the SUMMARY grid, which is how the file answers how regression-prone the system is. A rejected defect reopens normally - nothing was fixed, so nothing regressed - and criteria are unaffected.

## Category

The `##` heading carries the full name and the code (`## Authentication \`AUTH\``); the line under it carries the description. Reports expand the code to the full name, so `AUTH` never has to be decoded by the reader. `describe` sets or replaces the description; `check` warns when a category has none.

## Hint, tags and evidence

Three sub-lines, one line each, one per item.

- **The hint line** - one shortest-possible instruction, named by the discipline (`repro:` or `test:`); which one, and how to write it, is in that discipline's reference. The wrong hint for the discipline is an error, two of either is an error, a missing one is a warning
- **`- test-tags:`** - which kinds of test cover the item, comma separated: `unit`, `integration`, `functional`, `e2e`, `manual`. Free vocabulary, but reuse the words - `report` counts them into the coverage table, which is how "how many items are covered by unit tests" gets answered
- **`- evidence:`** - one line proving the item is actually done: the test that passes, the run that was observed, the commit. `close` demands it and writes the line, so a closure with no proof cannot be recorded. Reopening a criterion retires it and the log keeps what it said; a closed defect keeps it, because the regression is a new item and the old fix really was proven. Never write it by hand and never on an open item - it is the closure's proof, not a plan

## Authoring

Every entry is authored. The handle sits on the log line between the stamp and the event, so each event is attributed and an item's author is the handle on its first log line - nothing recorded twice. The roster is a `## Authors` section, one `- \`@kj\` Konrad Jelen` line per contributor.

- **Ask the user for their handle** at the start of any session that will write, then pass it as `--author` on every write. Ask once and reuse; never invent one and never infer it from the git config
- **A handle is `@` plus two to four lowercase letters**, normally initials
- **The roster is stored data, not a derived index** - handle to name maps to nothing else in the file, which is why `## Authors` is allowed where `## Contents` is not
- **A handle writes only once it is on the roster** - `author` puts it there; the tool refuses an unknown handle rather than inventing an entry
- **Authorship is what makes a shared file mergeable** - who decided what, and when. See `references/conflicts.md`

## Relations

Two indicators, no more: `related` and `blocked-by`.

- **Free text is welcome around the ids** - the parser anchors on the id shape `(ACC|DEF)-[A-Z]{2,6}-<N>`, so `- related: DEF-LNCH-3 - the race this covers` reads as both a link and a sentence
- **Cross-type** - a criterion may cite a defect and the other way round
- **One line per `relate` call** - lines are never merged, because a merge would bury a new id inside the previous line's prose; `check` and `refs` union them
- Every `relate` writes one side only. Run it on the other item too when both sides deserve to read well

## Reports

`report` is the surface the user reads. It prints markdown tables straight into the chat: paste them verbatim, never re-typed and never summarised in prose beside the table.

Five sections per file: SUMMARY (the one aggregate), CATEGORIES, TEST COVERAGE, ITEMS, and REJECTED under `--status rejected` or `all`. Two rules carry the design:

- **SUMMARY answers one question** - what is still to do, and how bad. Every cell is `open/closed`, one unit across the whole grid; a dash means nothing in that bucket; an empty column does not print
- **ITEMS is a fix queue, not an inventory** - OPEN items only, worst severity first; closed and rejected work is counted, not enumerated
- **A narrowed ask is a flag, never a reading** - severity, category, status and dates are filters `report` applies; a summary is `--summary`. Filtering in the answer, or adding prose under a summary, puts back what the flag removed

Section shapes, the ask-to-flag table, the short forms and `--detail`: `references/reports.md`.

## Tooling

`pm-tools <command>` - the console script shipped by the `stellars-claude-code-plugins` package, gated above. Query paths are files or directories (a directory is scanned for `acc-crit*.md` and `defects*.md`); no path means `./docs`. Run `pm-tools <command> --help` for the exact flags rather than trusting a spelling written here.

Read:

| Command | Does |
|---------|------|
| `report` | the markdown tables above; filters and short forms in `references/reports.md` |
| `list-categories` | the derived index: code, name, open / closed / rejected |
| `list` | items, one line each; filtered by state or category |
| `refs --id ID` | every item pointing at `ID` - the computed backlinks |
| `check` | conformity gate; non-zero exit on errors, `--strict` also fails on warnings |

Write - one file per call, and `--author` on every one of them:

| Command | Does |
|---------|------|
| `add` | next id, appended under the category; creates the category when named; `--severity` mandatory on a defect and refused on a criterion |
| `edit` | amend title, body, severity, hint, tags or evidence; logged |
| `author` | add or update a roster entry; required before that handle can write |
| `describe` | set or replace the category description |
| `relate` | add one `related:` or `blocked-by:` line |
| `log` | append an event to the item's log |
| `close` / `reopen` | `close` demands `--evidence`; `reopen` retires it on a criterion, and on a closed defect files `<id>-<n>` instead |
| `reject` | mark `[-]`; the reason is required |
| `remove` | delete an item created in error; refuses while anything still cites it |
| `upgrade` | rebuild a legacy doc to this schema, dry run first; `references/upgrade.md` |

Run `check` after every edit session. It is the only gate.

## Rules

- **Ask before the first file** - one consolidated doc per project is the default; a scoped `acc-crit-<scope>.md` or `defects-<scope>.md` only when the user asks. Never a file per item
- **Edit through `pm-tools`** - hand-editing is legal markdown but loses the id assignment and the log line; use the tool, then `check`
- **`remove` is for mistakes and duplicates only** - never as a way to resolve something. An item that turned out to be invalid is rejected with a reason, so the trail survives
- **Triage every defect yourself** - assign the severity as you file it, never ask the user for it and never leave it out. There is no unset: `add` refuses one and `check` errors on one. The four levels and their rubric are in `references/defects.md`
- **In doubt, ask** - a criterion, an expected behaviour, an edge case, which category something belongs in, how a merge should resolve. A wrong entry reads exactly like a right one, so nothing downstream catches it. Two exceptions, both decided by you: a defect's severity, and a merge case `references/conflicts.md` already settles

<!-- improved 2026-08-27 | body 2500→2075w / 189→177L (marketplace import: toolchain gate added, pm.py → pm-tools console script, Reports mechanics to references/reports.md, caveman-lite trim across every section) | quality n/a (eval skipped, token cost) | trigger n/a (eval skipped, token cost) | 47 CLI tests green | via improve-skill -->
