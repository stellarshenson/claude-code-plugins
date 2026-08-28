# Acceptance Criteria

A criterion is one assertion about behaviour that a reviewer can call met or not met. The store is `docs/acc-crit-<project>.md`, ids are `ACC-<CAT>-<N>`. Shared format, ids, relations and tooling live in `SKILL.md`; this file carries only what is specific to criteria.

## Writing a criterion

- **One assertion per item** - if a bullet needs "and", it is two criteria
- **Terse wording, complete coverage** - every behaviour, display rule, persistence rule and failure path gets its own item. Terseness is a property of the sentence, never of the fanout
- **Edge cases are explicit items** - `**Edge: <case>** - expected behaviour`; enumerate the whole fanout: removed, stale, concurrent, empty, already-done, invalid input
- **Overview stays at one or two sentences** under the H1: what the feature is, what mechanism carries it

## Importance

Every criterion carries an importance - how much the release depends on it. There is no unset: `add` refuses a criterion without one and `check` errors on any that lacks it.

**You assign it, at the moment you file the criterion.** Read it off the assertion itself. Never ask the user for the level and never leave it for later - a wrong level costs one `edit --importance`, an absent one blocks the gate.

- **CRITICAL** - the release is wrong without it
- **HIGH** - core behaviour
- **MEDIUM** - supporting behaviour
- **LOW** - polish

The level is the first word of the body - `HIGH; <assertion>...` - and it is read only on criteria, exactly as severity is read only on defects: a criterion body opening with `Normal, ...` is prose, never a level. `report` reads it back into the SUMMARY columns and the ITEMS Importance column, so it must be one of those four words and nothing else.

## Categories

One `##` per feature or area, code declared on the heading. A criterion sits under the category it belongs to today; its id keeps the code it was born with.

```markdown
## Branch Switching `BRSW`

Switching a project row between its conversation branches

- [x] `ACC-BRSW-1` **Submenu** - HIGH; row with >1 conversation JSONL shows "Switch Conversation Branch"
  - test: seed a project with 2 JSONLs, right-click the row
  - test-tags: UNIT, E2E
  - evidence: jest 43 green, submenu observed on a 2-branch project in v1.3.0
  - log: 2026-06-12T08:41:03Z @kj implemented (v1.2.2)
- [ ] `ACC-BRSW-2` **Names** - MEDIUM; submenu entries show conversation names, never the shared project path
  - test: seed two named branches, assert the labels differ from the path
  - test-tags: UNIT
  - related: DEF-BRSW-14 - the mislabelled-row defect this closes
  - log: 2026-06-12T09:14:27Z @kj added, in progress
- [-] `ACC-BRSW-3` **Edge: branch removed before click** - MEDIUM; switch returns 404, panel shows the error and refreshes
  - test: delete the JSONL between render and click
  - test-tags: MANUAL
  - log: 2026-06-14T11:02:55Z @kj rejected: the panel no longer caches rows, so the window cannot open
```

The rejected item stays in place with its reason. It is the record that the case was considered. A criterion is rejected when the feature it asserts no longer exists or was cut; a criterion that was met is closed. Defect-side rejection is a different case, in `defects.md`.

## Test hint, tags and evidence

Every criterion carries three more sub-lines. Each is one line, and the first two feed the report.

- **`- test:`** - the shortest instruction that tests the criterion, written so a reviewer can run it without asking. Name the fixture, the action and the assertion: `freeze clock, idle 31 min, assert 401`
- **`- test-tags:`** - which kinds of test cover it: `UNIT`, `INTEGRATION`, `FUNCTIONAL`, `E2E`, `MANUAL`. Free vocabulary, always written upper-case (the tool upper-cases whatever it is given and reads any case back); reuse the words across the file - `pm-tools coverage` counts them, and that count is the answer to "how many criteria are covered by unit tests"
- An untested criterion is tagged `MANUAL` or carries no tags line and lands in the coverage grid's `NO-TEST` column, never tagged for a test that does not exist. The coverage grid is only worth reading while it is true
- **`- evidence:`** - what proves the criterion is met, written by `close --evidence`: the run of the `test:` line and what it showed. `frozen clock, idle 31 min, 401 observed in v1.3.0` is evidence; `done` is not. `close` refuses to run without it, so met is never a claim

The `test:` line says how it would be checked; the `evidence:` line says it was, and what happened. A criterion rejected because the feature was cut needs a reason, not evidence.

## API section

A feature with endpoints gets one `### API` section at the end of its category, outside the checklist: method, path, payload shape, error codes. Level three, not two - `pm-tools` reads every `##` as a category and fails `check` on one with no code.

```markdown
- `GET sessions/branches?encoded_path=...` -> `{current, total, branches: [{session_id, file_mtime, label}]}`
- `POST sessions/switch` body `{encoded_path, session_id}` -> `{requested, current}`; 404 `branch_not_found`, 400 invalid input
```

## Regime matrix

When one functionality behaves differently per role, mode or state, a table shows the fanout that prose hides. Rows are functionality, columns are the regimes, `-` means unavailable.

- **One axis per table** - roles, or scenarios, or modes; whichever explains the behaviour in fewer cells
- **Only when the regimes genuinely differ** - two regimes with identical behaviour need no table
- **Place it under the category overview**, before the checklist
- **The matrix explains, the checklist asserts** - every cell carrying real behaviour still needs its own criterion, and that criterion names its regime in the title

```markdown
| Functionality | Owner                    | Shared viewer        | Read-only link |
| ------------- | ------------------------ | -------------------- | -------------- |
| Submenu entry | shown when >1 branch     | shown when >1 branch | hidden         |
| Switch        | switches, persists mtime | switches, no persist | -              |
| Rename branch | allowed                  | -                    | -              |

- [ ] `ACC-BRSW-8` **Read-only: no submenu** - HIGH; a read-only link never renders "Switch Conversation Branch"
  - log: 2026-06-12T13:38:19Z @kj added
- [ ] `ACC-BRSW-9` **Viewer: switch without persist** - MEDIUM; a viewer switch updates the panel and leaves the JSONL mtime untouched
  - log: 2026-06-12T15:07:44Z @kj added
```

## Working the file

```bash
pm-tools author docs/acc-crit-app.md --handle @kj --name "Konrad Jelen"
pm-tools add docs/acc-crit-app.md --category AUTH --name Authentication --author @kj \
    --importance HIGH --description "Login, session lifetime and password handling" \
    --title "Password generation" --text "16 chars, 3 character classes" \
    --test "generate 100 passwords, assert length and class count" --test-tags "UNIT"
pm-tools relate docs/acc-crit-app.md --id ACC-AUTH-1 --blocked-by "DEF-LNCH-3"
pm-tools close  docs/acc-crit-app.md --id ACC-AUTH-1 --author @kj --event "verified in v1.3.0" \
    --evidence "100 generated passwords, all 16 chars and 3 classes"
pm-tools reject docs/acc-crit-app.md --id ACC-AUTH-9 --author @kj \
    --event "the password screen was cut from 2.0"
pm-tools report docs/acc-crit-app.md
pm-tools check docs --strict
```

`check docs` resolves the `blocked-by: DEF-LNCH-3` line against the defects file beside; `check docs/acc-crit-app.md` alone reports it as not found, and a closed or rejected blocker on an open criterion is a warning.
