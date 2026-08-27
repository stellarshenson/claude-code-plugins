# Reports

`report` is the surface the user reads. It prints markdown tables straight into the chat - paste them, do not re-type them and do not summarise them in prose beside the table.

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
- **A dash means nothing in that bucket** - both counts zero, so the eye lands on the cells carrying work
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
| what is still open | `--status open`, the default |
| the AUTH work | `--category AUTH` |
| filed since the release | `--since 2026-08-01` |
| closed in August | `--dates closed --since 2026-08-01 --until 2026-08-31` |
| untouched since June | `--dates updated --until 2026-06-30` |

- **`--category`, `--severity` and the date window narrow the whole report** - the counts, SUMMARY and ITEMS all follow, and a category or severity the filter empties gets no row and no column
- **`--status` narrows ITEMS only** - the summary tables always show the whole scope, so a filtered report still says where the whole thing stands
- **A single category folds** its name and description into the header rather than printing a one-row CATEGORIES table
- **`--severity` is a defect attribute** - a criteria document is skipped with a note on stderr instead of being reported as zeros
- **Dates come off the log**, the only place a date is recorded: `filed` is the first stamp, `closed` the stamp that closed or rejected the item, `updated` the newest. A reopen retires the closed date. `--since` and `--until` take `YYYY-MM-DD`, both ends inclusive
- **A closed window lists what it found** - it can only select closed and rejected items, so it switches ITEMS to `--status all` by itself

## `--plain` and `--summary` are the short forms

- **`--plain`** - the SUMMARY grid and the ITEMS queue, nothing else: no icons, no section blurbs, no CATEGORIES table, no TEST COVERAGE. The counts line and the tables themselves are unchanged, so plain drops the chrome and never the data
- **`--summary`** - stops at the SUMMARY grid and lists no items at all. Plain by itself, so it needs no second flag

Asked for a summary, run `--summary` and print what it returns. The items are a different question. Listing them, or writing a paragraph about the row count and the heaviest clusters under the table, puts back exactly what the flag removed.

## `--detail` is the drill-down

It swaps the ITEMS tables for one block per item: id, title, severity, status, the body, then every sub-line verbatim - repro or test, tags, relations and the whole log.

Tables answer "how many"; only detail answers "what is actually wrong with this one and what has been tried". Scope it with `--category` or `--status`; a whole file in detail is the document itself, so read the document instead.
