---
name: project-management
description: Micro project management for a repository, a personal project or a small team - acceptance criteria and defects tracked in one markdown file per discipline, every item carrying a permanent category-scoped id (ACC-AUTH-102, DEF-LNCH-3) and an author handle (@kj), all reads and writes through the pm-tools CLI. Use when the user asks for acceptance criteria, acc crit, feature criteria, a defects list, a bug tracker, an issue tracker, or asks to log, add, close, reject, reopen, relate, list, report or audit a criterion or defect; for a status, triage or test-coverage report of either, including a filtered or summary one - the critical defects, what is open, the AUTH work, what closed last month; for any table or pivot over them - who owns what, open work by age, regressions per defect; when an old-style document needs upgrading to carry ids and handles; and when a shared acc-crit or defects file hits a git merge conflict.
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
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
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
| Backlinks, outbound links, blocker chain | `pm-tools refs --id` |
| Index, contents, counts| `pm-tools list-categories` |
| Test coverage per tag  | `pm-tools coverage`        |

Consequences, stated once:

- **No `## Contents`** - a hand-kept table of contents is a second index that drifts; `check` rejects one
- **No Open / Fixed sections** - status lives in the checkbox, so an item never moves
- **Links are one-way** - a `related:` on A is the only record; the reverse is computed, never written back
- **`check` reports, it does not repair** - a relation to an id that is not in the scanned files, or a blocked-by cycle, is an error to fix by hand, never state to reconcile; scan the directory so cross-file links resolve

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
  - test-tags: UNIT, FUNCTIONAL
  - evidence: <the proof it is done - written by close, present only while closed>
  - related: <ID>, <ID> - free text around the ids
  - blocked-by: <ID>
  - lock: 2026-08-30T10:11:29Z @kj optional note
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
- **`- test-tags:`** - which kinds of test cover the item, comma separated: `UNIT`, `INTEGRATION`, `FUNCTIONAL`, `E2E`, `MANUAL`. Free vocabulary, always written upper-case - the tool upper-cases whatever `--test-tags` is given and reads any case back off the file - but reuse the words: `coverage` counts them into its grid, which is how "how many items are covered by unit tests" gets answered. An item with no tags line lands in the grid's `NO-TEST` column
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
- **Links, not mentions** - only a `related:`/`blocked-by:` line is a link; an id in a log line is prose. `refs`, `--related-to` and `--blocked` read links; `--grep` and `search` read prose
- **`blocked-by` is checked** - a cycle is an error, a blocker that is closed or rejected is a warning on the open item; `refs --id` prints both directions and the transitive chain
- Every `relate` writes one side only. Run it on the other item too when both sides deserve to read well

## Soft lock

An open item may carry one `- lock: <stamp> @xx [note]` sub-line: @xx is likely working on it until the stamp. The lock is a courtesy signal, never a gate.

- **A read names the items in flight** - `report`, `list`, `search` and `refs` print one stderr line, `N item(s) currently worked on: DEF-X by @xx until <stamp>` (ten ids at most, then `+M more`), whenever an item they show holds an active lock, so the choice of what to pick up is informed before the work starts; `--json` prints no notice
- **Lock an item when you pick it up** - `pm-tools lock FILE --id ID --author @xx`, 24 hours by default; `--hours N` or `--until STAMP` sets another span, locking again as the same author extends it
- **Ask before working on an item locked by someone else** - a lock held by another handle is a person mid-change; ask them before continuing
- **The lock never blocks a write** - a write on an item locked by another author prints one warning on stderr naming the holder and the expiry, then proceeds; exit code and file result are those of the unlocked case. A lock is refused only on a closed or rejected item
- **Expired locks clear themselves on the next write** - any write command but `upgrade` first removes every lock whose stamp is past, silently and unlogged; `close` and `reject` clear the item's lock whatever its expiry. `check` is read-only and reports an expired lock as a warning
- **Unlock at will** - `pm-tools unlock FILE --author @xx --id ID`, or `--all`, or `--expired`; clearing another author's active lock warns once and proceeds
- **Taking or clearing someone else's active lock is a transfer** - `lock` and `unlock` say so on stderr, `TRANSFER: DEF-X was locked by @yy until <stamp> - you are taking it over; ask @yy`, and proceed; a takeover with no `--note` records `taken over from @yy` on the new lock line, so the previous holder stays visible on the item

Locking is never logged. `report` marks a locked item `wip @xx until <stamp>` and counts open locked items in a `Worked on` column; `--locked` and `--locked-by @xx` filter on an active lock, and `lock` is a field.

## Reports and tables

Every collection of items the user is shown is a markdown table, computed by `pm-tools` and pasted verbatim - never a bulleted list, never prose, never re-typed. Three query surfaces, one filter vocabulary:

| Surface | Answers | Shape |
|---------|---------|-------|
| `report` | where does the work stand | SUMMARY, CATEGORIES, ITEMS, REJECTED |
| `coverage` | which tests cover the work | categories down, tags across, `NO-TEST` last, open and closed counted alike |
| `list` | which items | one table, `--columns` and `--sort` chosen to fit the question |
| `pivot` | how many of what by what | any field down, any field across, a count or the ids per cell |

Three rules carry the design:

- **A narrowed ask is a flag, never a reading** - "the open defects" is `report --status open`, "what @kj still has in AUTH" is `--author @kj --category AUTH`, "the critical ones filed since the release" is `--severity CRITICAL --since <date>`. Every filter narrows the whole report except `--status`, which narrows ITEMS alone, so a filtered report still says where the whole scope stands. Filtering in the answer, or adding prose under a summary, puts back what the flag removed
- **A question no report answers is still a table** - who owns what by severity, how old the open work is, regressions per defect: shape it with `list --columns` or `pivot`, and paste what comes back. Tabulating by hand from the document is the failure the tools exist to prevent - the counts stop being computed and nothing tells the reader. `--json` on any query gives the same facts as data, for the rare table that has to be assembled from two queries
- **SUMMARY answers one question** - what is still to do, and how bad. Plain counts: `| Category | Open | CRITICAL | MAJOR | MEDIUM | MINOR | Fixed | Rejected |` on defects, `| Category | Open | CRITICAL | HIGH | MEDIUM | LOW | Done | Rejected |` on criteria, each with a Total row. The level columns count OPEN items only - Open is their sum, Fixed / Done the closed count - and an `UNTRIAGED` / `UNRATED` column appears only when an open item lacks a level. ITEMS is a fix queue, not an inventory - OPEN items only, worst level first; closed and rejected work is counted, not enumerated

Section shapes, the ask-to-flag table, FIELDS, the short forms and `--detail`: `references/reports.md`.

## Tooling

`pm-tools <command>` - the console script shipped by the `stellars-claude-code-plugins` package, gated above. Query paths are files or directories (a directory is scanned for `acc-crit*.md` and `defects*.md`); no path means `./docs`. Run `pm-tools <command> --help` for the exact flags rather than trusting a spelling written here.

Read:

| Command | Does |
|---------|------|
| `report` | the standing analysis; filters and short forms in `references/reports.md` |
| `coverage` | the test-coverage grid: categories down, occurring tags across, `NO-TEST` last, Total row |
| `list` | one table of items; `--columns` and `--sort=` pick the shape, the shared filters pick the rows |
| `pivot --rows F [--cols F]` | an ad-hoc count grid over any two fields; `--values ids` names the items instead |
| `list-categories` | the derived index: code, name, open / closed / rejected |
| `search QUERY [--top N]` | the items most relevant to `QUERY`, best first - BM25 with fuzzy tokens; the shared filters narrow first |
| `refs --id ID` | what points at `ID`, what `ID` points at, and its blocker chain |
| `check` | conformity gate; non-zero exit on errors, `--strict` also fails on warnings |

`--json` on any of the first seven returns the same facts as data. The filters `--category`, `--severity`, `--importance`, `--status`, `--author`, `--tag` (any case), `--regressions`, `--grep`, `--blocked`, `--related-to`, `--locked`, `--locked-by` and the `--dates` / `--since` / `--until` window are the same on `report`, `coverage`, `list`, `pivot` and `search`.

Write - one file per call, and `--author` on every one of them:

| Command | Does |
|---------|------|
| `add` | next id, appended under the category; creates the category when named; `--severity` mandatory on a defect, `--importance` mandatory on a criterion, each refused on the other |
| `edit` | amend title, body, severity, importance, hint, tags or evidence; logged |
| `author` | add or update a roster entry; required before that handle can write |
| `describe` | set or replace the category description |
| `relate` | add one `related:` or `blocked-by:` line |
| `log` | append an event to the item's log |
| `close` / `reopen` | `close` demands `--evidence`; `reopen` retires it on a criterion, and on a closed defect files `<id>-<n>` instead |
| `reject` | mark `[-]`; the reason is required |
| `remove` | delete an item created in error; refuses while anything still cites it |
| `lock` / `unlock` | write or remove the `lock:` line; `lock` refuses only on a closed or rejected item, neither is logged |
| `upgrade` | rebuild a legacy doc to this schema, dry run first; `--apply` always applies the safe rewrites, exits 0, and prints one `HINT` with the exact command per content problem; `references/upgrade.md` |

Run `check` after every edit session. It is the only gate.

## Rules

- **Ask before the first file** - one consolidated doc per project is the default; a scoped `acc-crit-<scope>.md` or `defects-<scope>.md` only when the user asks. Never a file per item
- **Edit through `pm-tools`** - hand-editing is legal markdown but loses the id assignment and the log line; use the tool, then `check`
- **`remove` is for mistakes and duplicates only** - never as a way to resolve something. An item that turned out to be invalid is rejected with a reason, so the trail survives
- **Triage every defect yourself** - assign the severity as you file it, never ask the user for it and never leave it out. There is no unset: `add` refuses one and `check` errors on one. The four levels and their rubric are in `references/defects.md`
- **Rate every criterion yourself** - assign the `--importance` (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`) as you file it, the same way: never ask the user, never leave it out, `add` refuses one and `check` errors on one. The rubric is in `references/acceptance-criteria.md`
- **In doubt, ask** - a criterion, an expected behaviour, an edge case, which category something belongs in, how a merge should resolve. A wrong entry reads exactly like a right one, so nothing downstream catches it. Three exceptions, all decided by you: a defect's severity, a criterion's importance, and a merge case `references/conflicts.md` already settles

<!-- improved 2026-08-27 | body 2500→2075w / 189→177L (marketplace import: toolchain gate added, pm.py → pm-tools console script, Reports mechanics to references/reports.md, caveman-lite trim across every section) | quality n/a (eval skipped, token cost) | trigger n/a (eval skipped, token cost) | 47 CLI tests green | via improve-skill -->
