# Reports

`report` is the surface the user reads. It prints markdown tables straight into the chat - paste them, do not re-type them and do not summarise them in prose beside the table.

## Sections, in order

| Section           | Carries |
|-------------------|---------|
| **SUMMARY**       | the one aggregate - categories down, severity or test tag across |
| **CATEGORIES**    | code, full name, description |
| **TEST COVERAGE** | items per tag and share, plus untagged |
| **ITEMS**         | one table per category - id, title, description, severity on defects, status, tags |
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

## Filters

- **`--category`** narrows every section, and a single category folds its name and description into the header rather than printing a one-row CATEGORIES table
- **`--status`** narrows ITEMS only - the summary tables always show the whole scope, so a filtered report still says where the whole thing stands

## `--detail` is the drill-down

It swaps the ITEMS tables for one block per item: id, title, severity, status, the body, then every sub-line verbatim - repro or test, tags, relations and the whole log.

Tables answer "how many"; only detail answers "what is actually wrong with this one and what has been tried". Scope it with `--category` or `--status`; a whole file in detail is the document itself, so read the document instead.
