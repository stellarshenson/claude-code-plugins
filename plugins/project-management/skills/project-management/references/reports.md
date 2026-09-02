# Reports

`report` is the surface the user reads. It prints markdown tables straight into the chat - paste them, do not re-type them and do not summarise them in prose beside the table. When the question does not match a report section, `coverage`, `list`, `pivot` and `search` shape a table that does; see [Ad-hoc tables](#ad-hoc-tables---list-and-pivot).

## Sections, in order

| Section           | Carries |
|-------------------|---------|
| **SUMMARY**       | the one aggregate - two grids of plain counts: status per category, then the open items per level |
| **CATEGORIES**    | code, full name, description |
| **ITEMS**         | one table per category - id, title, description, severity on defects, importance on criteria, status, tags, evidence |
| **REJECTED**      | id, title, reason; printed under `--status all` or `--status rejected`, never on a default report |

Test coverage is not a report section; it is its own command, `coverage`, below.

## SUMMARY

It answers two questions - how much is left, and how bad - with one grid for each, so a status count never sits beside a level count as if they partitioned the same thing.

- **Plain integer counts, 0 allowed** - no compound cells and no legend line; the grids explain themselves
- **The status grid comes first** - `| Category | Open | Fixed | Rejected | Total |` on a defects document, `Done` in place of `Fixed` on a criteria document; Total is the category size, open plus closed plus rejected
- **The level grid follows, under the line `Open by severity` or `Open by importance`** - `| Category | CRITICAL | MAJOR | MEDIUM | MINOR | Open |` on defects, `| Category | CRITICAL | HIGH | MEDIUM | LOW | Open |` on criteria. It breaks the Open column down alone - the last column is that Open count, the sum of the level cells - and it is printed only when something is open
- **An `UNTRIAGED` / `UNRATED` column appears only when an open item lacks a level** - on a clean file it is absent, and `check` fails until it is
- **A `Worked on` column counts the open items with an active lock** - after Open in the status grid, Total row included, and only when an item in scope is locked; an active lock is a `lock:` line whose stamp is still in the future
- **A Total row closes every grid**
- **Regression count** - a defect report prints `N regressions across M defects` above the grid whenever any item carries a `-N` id, in the summary form as well

## ITEMS is a fix queue, not an inventory

The reader wants what is left and what to fix first, so ITEMS lists OPEN items only, worst level first (severity on defects, importance on criteria), oldest id first inside a level.

- **Closed and rejected work is counted, not enumerated** - SUMMARY counts it, a footer line names it; `--status all`, `closed` or `rejected` when it is genuinely wanted
- **Defect rows carry a Severity column, criterion rows an Importance column** - the discipline's level, always shown
- **The Status column disappears** whenever every row shares one status - a constant column carries nothing
- **The Evidence column appears** only when something listed carries one, which in practice means a listing that includes closed work. `--status closed` is how a reader checks what the closures were actually proven on
- **Tags print upper-case** - `UNIT, E2E` - however the file spells them
- **A locked item's row carries `wip @xx until <stamp>`** - @xx is likely working on it; ask before picking it up, and lock an item when you pick it up yourself (`pm-tools lock FILE --id ID --author @xx`). The lock never blocks a write, expired locks clear themselves on the next write, and `pm-tools unlock` clears one at will. The read announces them first: `report`, `list`, `search` and `refs` print `N item(s) currently worked on: DEF-X by @xx until <stamp>` on stderr whenever a shown item is locked, so the notice arrives while the item is still being chosen; taking or clearing an active lock held by another handle is a transfer - `lock` and `unlock` print `TRANSFER: DEF-X was locked by @yy until <stamp> - you are taking it over; ask @yy` and proceed, and a takeover with no `--note` records `taken over from @yy`

## `coverage` - the test-coverage grid

`pm-tools coverage [paths]` prints one grid per file: categories down, test tags across, counting **open and closed items alike** - coverage is a property of the whole tracked surface, not of the queue. Rejected items are excluded.

- **Columns are the tags that occur** - `UNIT`, `INTEGRATION`, `FUNCTIONAL`, `E2E`, `MANUAL` first in that order, any other tag after them, and `NO-TEST` always last: the bucket for items carrying no `test-tags:` line
- **An item with several tags counts in several columns**; the footer says how many items there were
- **A Total row closes the grid**
- **The shared filters apply** - `coverage --category AUTH` is the coverage of one area, `coverage --status open` narrows to the queue when that is genuinely the question

## Filters

A filtered ask is answered with flags. Reading the document and filtering inside the reply is the one thing this design exists to prevent: the counts stop being computed, and nothing in the output tells the reader that.

| The ask | The flags |
|---------|-----------|
| the critical defects | `--severity CRITICAL` |
| the critical criteria | `--importance CRITICAL` |
| the open defects, and only those | `--status open`, the default; the counts line still says how many are closed and rejected |
| the AUTH work | `--category AUTH` |
| what @kj filed | `--author @kj` |
| what the e2e tests cover | `--tag e2e` - the tag reads in any case |
| the regressions | `--regressions` - only the `-N` items |
| anything mentioning the token | `--grep token` - case-insensitive regex over title, body, evidence and log lines |
| what is waiting on open work | `--blocked` - at least one blocked-by target still open |
| everything around DEF-LNCH-3 | `--related-to DEF-LNCH-3` - linked either way, related or blocked-by |
| what is being worked on | `--locked` - an active lock, whoever holds it |
| what @kj is working on | `--locked-by @kj` |
| filed since the release | `--since 2026-08-01` |
| closed in August | `--dates closed --since 2026-08-01 --until 2026-08-31` |
| untouched since June | `--dates updated --until 2026-06-30` |

Filters combine: "what @kj still has open in AUTH" is `--author @kj --category AUTH --status open`. The same flags work unchanged on `coverage`, `list`, `pivot` and `search`.

- **`--category`, `--severity`, `--importance`, `--author`, `--tag`, `--regressions`, `--grep`, `--blocked`, `--related-to`, `--locked`, `--locked-by` and the date window narrow the whole report** - the counts, SUMMARY and ITEMS all follow, and a category the filter empties gets no row; the level columns stay and read 0 while anything in scope is open, and a filter that leaves nothing open drops the level grid
- **`--status` narrows ITEMS only** - the summary tables always show the whole scope, so a filtered report still says where the whole thing stands
- **A single category folds** its name and description into the header rather than printing a one-row CATEGORIES table
- **`--severity` is a defect attribute and `--importance` a criterion attribute** - the other discipline's document is skipped with a note on stderr instead of being reported as zeros
- **Links, not mentions** - `--related-to` and `--blocked` read `related:`/`blocked-by:` lines; an id in a log line is prose, found by `--grep` and `search`
- **Dates come off the log**, the only place a date is recorded: `filed` is the first stamp, `closed` the stamp that closed or rejected the item, `updated` the newest. Reopening a criterion retires its closed date; a regressed defect keeps the one it earned, since that closure really happened. `--since` and `--until` take `YYYY-MM-DD`, both ends inclusive
- **A closed window lists what it found** - it can only select closed and rejected items, so it switches ITEMS to `--status all` by itself

## `--plain` and `--summary` are the short forms

- **`--plain`** - the SUMMARY grid and the ITEMS queue, nothing else: no icons, no section blurbs, no CATEGORIES table. The counts line and the tables themselves are unchanged, so plain drops the chrome and never the data
- **`--summary`** - stops at the SUMMARY grid and lists no items at all. Plain by itself, so it needs no second flag

Asked for a summary, run `--summary` and print what it returns. The items are a different question. Listing them, or writing a paragraph about the row count and the heaviest clusters under the table, puts back exactly what the flag removed.

## Ad-hoc tables - `list` and `pivot`

A question the report sections do not answer is still answered with a computed table, never with a reading of the file. Two commands cover the space; both take the filters above and print one markdown table per file.

- **`list [--columns F,F,..] [--sort=F,-F,..]`** - one row per item. Default columns are id, title, severity (defects) or importance (criteria), status, category, author, filed and tags; `--columns` replaces them in the order given. Default order is the fix order (open first, worst first, oldest first); `--sort` takes fields in priority order, and a `-` prefix descends - write it `--sort=-age`, since a bare `-age` reads as a flag. Severity or importance ascending is worst first
- **`pivot --rows F [--cols F] [--values count|ids]`** - one field down, another across, a count in every cell (`-` for zero), a Total column and row. Without `--cols` it is a one-column tally. `--values ids` puts the ids in the cells instead, for the reader who wants to click through
- **FIELDS**, the one vocabulary for `--columns`, `--sort`, `--rows` and `--cols`: `id title body category severity importance status author filed closed updated age tags evidence hint regr root logs related blockers lock`. `root` is the parent id a regression descends from (an original is its own root), `regr` its ordinal, `logs` the number of log lines, `hint` the repro or test line, `related` and `blockers` the linked ids, `lock` renders `@xx until <stamp>` for an active lock and `-` otherwise
- **Multi-valued and bucketed fields** - `tags` puts an item in every tag it carries (the empty bucket is `NO-TEST`), and `related` / `blockers` under every id they name; `filed`, `closed` and `updated` pivot by month; `age` pivots by band (`<7d`, `7-30d`, `31-90d`, `>90d`), counting days from filing to closure or to today while open

| The ask | The command |
|---------|-------------|
| who owns what, by severity | `pivot --rows author --cols severity` |
| how regression-prone each defect is | `pivot --rows root --regressions --values ids` |
| the open work, oldest first, with owners | `list --status open --columns id,title,author,age --sort=-age` |
| what closed per month, by category | `pivot --rows closed --cols category --status closed` |
| coverage by category | `coverage` - the shipped grid; `pivot --rows category --cols tags` when a different cut is needed |
| criteria by importance and status | `pivot --rows importance --cols status` |
| what is waiting on open work | `list --blocked --columns id,title,blockers` |
| who is working on what | `list --locked --columns id,title,lock` |

## `search` ranks, `--grep` filters

`search "QUERY" [--top N]` prints the N items most relevant to the query, best first, one table over every scanned file - BM25 over id, title, body, evidence and log lines, id and title weighted, tolerant of a typo or a stem. Quote a multi-word query. The shared filters narrow the candidates first; `--grep` is the exact filter, `search` the ranking. "Is there already an item about X" is a `search`, pasted like any other table.

## `refs` walks the link graph

`refs --id ID` prints what points at `ID`, what `ID` points at, and the transitive blocked-by chain - each path hop carrying the blocker's status, a repeated blocker ending its chain with `...`, a cycle named where it closes. Inbound references are listed even for an id no item carries any more, which is what `remove --force` leaves behind.

- **`--json`** on `report`, `coverage`, `list`, `pivot`, `search`, `list-categories` and `refs` returns the same facts as data - a list of documents, one per file; the `report` and `list` item records carry `lock` as `{by, until, note}` or `null`. Use it only for the rare table that has to be assembled from two queries; a single query's markdown is the deliverable, and re-rendering its JSON by hand invites the format drift the tools exist to remove

## `--detail` is the drill-down

It swaps the ITEMS tables for one block per item: id, title, the discipline's level, status, the body, then every sub-line verbatim - repro or test, tags, relations and the whole log.

Tables answer "how many"; only detail answers "what is actually wrong with this one and what has been tried". Scope it with `--category` or `--status`; a whole file in detail is the document itself, so read the document instead.
