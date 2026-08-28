# Reports

`report` is the surface the user reads. It prints markdown tables straight into the chat - paste them, do not re-type them and do not summarise them in prose beside the table. When the question does not match a report section, `list` and `pivot` shape a table that does; see [Ad-hoc tables](#ad-hoc-tables---list-and-pivot).

## Sections, in order

| Section           | Carries |
|-------------------|---------|
| **SUMMARY**       | the one aggregate - categories down, severity or test tag across |
| **CATEGORIES**    | code, full name, description |
| **TEST COVERAGE** | items per tag and share, plus untagged |
| **ITEMS**         | one table per category - id, title, description, severity on defects, status, tags, evidence |
| **REJECTED**      | id, title, reason; printed under `--status all` or `--status rejected`, never on a default report |

## SUMMARY

It answers one question - what is still to do, and how bad - and every choice follows from that.

- **`open/closed` fills every cell** - `10/43` is 10 open, 43 closed. One unit across the whole grid, row total included, so any two cells compare directly
- **A zero reads as `-`** - `-/5` is nothing open and five closed, `3/-` three open and nothing closed yet; a lone `-` is an empty bucket. The eye lands on the cells carrying work
- **The legend is always printed** - one line under the SUMMARY heading says what the `x/y` form means, on `--plain` and `--summary` as well, so a pasted grid never travels unexplained
- **A column appears only when something is in it** - a severity or tag with no items gets no column, and the grid shrinks as the file resolves
- **Rejected is not work** - excluded from SUMMARY entirely. The header line carries its count on every report; the reasons are one flag away, in REJECTED under `--status rejected`
- **On criteria the columns can double-count** - one criterion with two tags sits in two columns, so row cells may exceed the row total

## ITEMS is a fix queue, not an inventory

The reader wants what is left and what to fix first, so ITEMS lists OPEN items only, worst severity first, oldest id first inside a level.

- **Closed and rejected work is counted, not enumerated** - SUMMARY counts it, a footer line names it; `--status all`, `closed` or `rejected` when it is genuinely wanted
- **The Status column disappears** whenever every row shares one status - a constant column carries nothing
- **The Evidence column appears** only when something listed carries one, which in practice means a listing that includes closed work. `--status closed` is how a reader checks what the closures were actually proven on

## Filters

A filtered ask is answered with flags. Reading the document and filtering inside the reply is the one thing this design exists to prevent: the counts stop being computed, and nothing in the output tells the reader that.

| The ask | The flags |
|---------|-----------|
| the critical defects | `--severity CRITICAL` |
| the open defects, and only those | `--status open`, the default; the counts line still says how many are closed and rejected |
| the AUTH work | `--category AUTH` |
| what @kj filed | `--author @kj` |
| what the e2e tests cover | `--tag e2e` |
| the regressions | `--regressions` - only the `-N` items |
| filed since the release | `--since 2026-08-01` |
| closed in August | `--dates closed --since 2026-08-01 --until 2026-08-31` |
| untouched since June | `--dates updated --until 2026-06-30` |

Filters combine: "what @kj still has open in AUTH" is `--author @kj --category AUTH --status open`. The same flags work unchanged on `list` and `pivot`.

- **`--category`, `--severity`, `--author`, `--tag`, `--regressions` and the date window narrow the whole report** - the counts, SUMMARY and ITEMS all follow, and a category or severity the filter empties gets no row and no column
- **`--status` narrows ITEMS only** - the summary tables always show the whole scope, so a filtered report still says where the whole thing stands
- **A single category folds** its name and description into the header rather than printing a one-row CATEGORIES table
- **`--severity` is a defect attribute** - a criteria document is skipped with a note on stderr instead of being reported as zeros
- **Dates come off the log**, the only place a date is recorded: `filed` is the first stamp, `closed` the stamp that closed or rejected the item, `updated` the newest. Reopening a criterion retires its closed date; a regressed defect keeps the one it earned, since that closure really happened. `--since` and `--until` take `YYYY-MM-DD`, both ends inclusive
- **Regression count** - a defect report prints `N regressions across M defects` under the headline whenever any item carries a `-N` id, in the summary form as well; it is the answer to how regression-prone the work is
- **A closed window lists what it found** - it can only select closed and rejected items, so it switches ITEMS to `--status all` by itself

## `--plain` and `--summary` are the short forms

- **`--plain`** - the SUMMARY grid and the ITEMS queue, nothing else: no icons, no section blurbs, no CATEGORIES table, no TEST COVERAGE. The counts line, the one-line `open/closed` legend and the tables themselves are unchanged, so plain drops the chrome and never the data
- **`--summary`** - stops at the SUMMARY grid and lists no items at all. Plain by itself, so it needs no second flag

Asked for a summary, run `--summary` and print what it returns. The items are a different question. Listing them, or writing a paragraph about the row count and the heaviest clusters under the table, puts back exactly what the flag removed.

## Ad-hoc tables - `list` and `pivot`

A question the report sections do not answer is still answered with a computed table, never with a reading of the file. Two commands cover the space; both take the filters above and print one markdown table per file.

- **`list [--columns F,F,..] [--sort=F,-F,..]`** - one row per item. Default columns are id, title, severity (defects), status, category, author, filed and tags; `--columns` replaces them in the order given. Default order is the fix order (open first, worst first, oldest first); `--sort` takes fields in priority order, and a `-` prefix descends - write it `--sort=-age`, since a bare `-age` reads as a flag. Severity ascending is worst first
- **`pivot --rows F [--cols F] [--values count|ids]`** - one field down, another across, a count in every cell (`-` for zero), a Total column and row. Without `--cols` it is a one-column tally. `--values ids` puts the ids in the cells instead, for the reader who wants to click through
- **FIELDS**, the one vocabulary for `--columns`, `--sort`, `--rows` and `--cols`: `id title body category severity status author filed closed updated age tags evidence hint regr root logs`. `root` is the parent id a regression descends from (an original is its own root), `regr` its ordinal, `logs` the number of log lines, `hint` the repro or test line
- **Multi-valued and bucketed fields** - `tags` puts an item in every tag it carries, so a tag pivot's total can exceed the item count and the footer says how many items there were; `filed`, `closed` and `updated` pivot by month; `age` pivots by band (`<7d`, `7-30d`, `31-90d`, `>90d`), counting days from filing to closure or to today while open

| The ask | The command |
|---------|-------------|
| who owns what, by severity | `pivot --rows author --cols severity` |
| how regression-prone each defect is | `pivot --rows root --regressions --values ids` |
| the open work, oldest first, with owners | `list --status open --columns id,title,author,age --sort=-age` |
| what closed per month, by category | `pivot --rows closed --cols category --status closed` |
| coverage by category | `pivot --rows category --cols tags` |
| the untriaged and the untagged | `pivot --rows severity --cols tags` - the `untriaged` row and `untagged` column |

- **`--json`** on `report`, `list`, `pivot`, `list-categories` and `refs` returns the same facts as data - a list of documents, one per file. Use it only for the rare table that has to be assembled from two queries; a single query's markdown is the deliverable, and re-rendering its JSON by hand invites the format drift the tools exist to remove

## `--detail` is the drill-down

It swaps the ITEMS tables for one block per item: id, title, severity, status, the body, then every sub-line verbatim - repro or test, tags, relations and the whole log.

Tables answer "how many"; only detail answers "what is actually wrong with this one and what has been tried". Scope it with `--category` or `--status`; a whole file in detail is the document itself, so read the document instead.
