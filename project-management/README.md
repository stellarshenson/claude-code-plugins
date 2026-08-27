# project-management

Micro project management for a repository, a personal project or a small team. Acceptance criteria and defects live as markdown checklists in the repo, every item carrying a permanent id, an author handle and a triage level, with every derived fact computed on read by the `pm-tools` CLI.

Everything stays in the repository and the agent does the editing. Ids survive a reorder and a category move. Status is the checkbox, so no second copy can contradict it. The log is append-only and keeps the attempts that failed. It is not a replacement for a hosted tracker.

## Installation

```bash
/plugin marketplace add stellarshenson/claude-code-plugins
/plugin install project-management@stellarshenson-marketplace
```

The `pm-tools` CLI ships as part of the shared Python package:

```bash
pip install stellars-claude-code-plugins
pm-tools --help
```

## Commands

| Command | Use |
|---------|-----|
| `/project-management:acc-crit` | Add, close, reject, relate or audit acceptance criteria in `docs/acc-crit*.md`. Triggers: "acceptance criteria", "acc crit", "feature criteria", "add a criterion" |
| `/project-management:defect` | File, triage, log, close or reject a defect in `docs/defects*.md`. Triggers: "file a bug", "defect list", "log this attempt", "close the defect" |
| `/project-management:report` | Print the status, triage and test-coverage tables for either document, or audit both. Triggers: "where do the defects stand", "report the criteria", "audit the tracker" |
| `/project-management:review` | Hostile independent review of the document - `analyst` on criteria, `qa-engineer` on defects, via `devils-advocate:adversarial-review`. Triggers: "review the acc-crit doc", "is anything untestable" |
| `/project-management:upgrade` | Rebuild a legacy criteria or defects document to this schema - assigns ids, category codes, authored log lines. Triggers: "upgrade the old bug list", "migrate the criteria doc" |

All five carry the toolchain gate and refuse to run against a mismatched CLI.

## Skills

| Skill | Triggers when |
|-------|--------------|
| `project-management` | Any of the phrases above, plus "bug tracker", "issue tracker", "document the dataset of defects", "what is still open" - carries the id scheme, the line format, the three states, authoring, relations and the CLI surface |

## Philosophy

This is project management for an agent to operate. The design follows from that: the operator works inside the repository, and the CLI is the whole interface.

- **No context switch** - the session that changed the code files the defect, in the same turn, from what it already holds. Nothing is restated to a second system and nothing is carried back by hand
- **Two stores drift** - a requirements document and a tracker database holding the same facts diverge the moment either is edited alone, and keeping them in step is the recurring cost of model-driven approaches. One markdown file removes the second store, and the reconciliation with it
- **Markdown parses deterministically** - the schema is a fixed grammar (checkbox, id, bold title, named sub-lines), so `pm-tools` reads it with a parser rather than a model. Same file, same records, every run, at no token cost and with no room for an invented field
- **One format serves both readers** - the file renders in an editor, reviews in a pull request and diffs in git, and it also parses into records. Nothing is exported to read it and nothing is imported to write it
- **The document stays out of the context window** - the file holds everything, and the agent reaches it through the CLI, which returns only the rows asked for. Growth shows up in a report someone asked for, never in the cost of filing or closing the next item
- **Reports are computed from the file** - `report` renders fixed markdown tables, so one document always yields the same tables, and they read correctly pasted straight into a terminal session
- **Terse entries suit a model** - criteria and defects are short declarative statements carrying no narrative. A dry, conservative description gives a model more to infer from and less to misread
- **Authorship needs no server** - every event carries a handle and a UTC timestamp, so a merge conflict on a shared file already contains what resolving it requires. The agent does the resolving

## The design - nothing is written down twice

Every fact is stored exactly once, and everything else is computed when read. That is the whole reason the file cannot drift out of step with itself.

| Fact | Where it lives | How it is known |
|------|----------------|-----------------|
| Item text, title, log | the checklist line and its sub-lines | stored once |
| Open, closed or rejected | the `[ ]` / `[x]` / `[-]` box | stored once |
| Category membership | the `##` section the line sits under | stored once |
| Next free number | not stored | highest id in the file, plus one |
| Backlinks | not stored | `pm-tools refs --id` |
| Index, contents, counts | not stored | `pm-tools list-categories` |
| Test coverage per tag | not stored | `pm-tools report` |

The consequences are deliberate: no `## Contents` table (a second index that drifts - `check` rejects one), no Open / Fixed sections (status is the checkbox, so an item never moves), and one-way links (the reverse side is computed, never written back).

## What an item looks like

```markdown
## Launch `LNCH`

Cold start, splash screen and the first turn after a fork

- [ ] `DEF-LNCH-3` **token race on relaunch** - MAJOR; auth token occasionally empty on the first turn after a fork; cause under investigation; `src/session.ts`
  - repro: fork under load, send a turn inside 2s
  - test-tags: integration
  - related: ACC-LNCH-8 - the criterion this violates
  - log: 2026-06-22T09:14:27Z @kj reported: intermittent 401 on the first turn
  - log: 2026-06-22T11:02:55Z @kj attempted: 200ms pre-turn delay - did NOT work
```

- **Permanent ids** - `ACC-<CAT>-<N>` and `DEF-<CAT>-<N>`, unique across the document, never renumbered and never recycled. An item that moves category keeps the code it was born with
- **Three states** - `[ ]` open, `[x]` closed, `[-]` rejected. Rejected is for a report that was never a defect (never reproduced, or the feature is gone); a real defect nobody will fix is a close with the reason
- **Authored log lines** - ISO 8601 UTC, then the handle, then the event. Append-only, and the attempts that FAILED are the reason the file is worth keeping
- **Mandatory triage** - `CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR`, assigned by the agent as the defect is filed. There is no unset: `add` refuses one and `check` errors on one

## CLI tools

Deterministic parsing, linting, editing and reporting - no generative step anywhere in `pm-tools`.

```bash
# Query
pm-tools report docs                          # the tables the user reads
pm-tools report docs --category AUTH --detail # one block per item, whole log
pm-tools list-categories docs                 # the derived index
pm-tools refs docs --id DEF-LNCH-3            # computed backlinks
pm-tools check docs --strict                  # the gate; non-zero on errors

# Edit (all writes take --author)
pm-tools author docs/defects-app.md --handle @kj --name "Konrad Jelen"
pm-tools add docs/defects-app.md --category LNCH --name Launch --severity MAJOR \
    --author @kj --title "token race on relaunch" --text "symptom; cause under investigation" \
    --repro "fork under load, send a turn inside 2s" --test-tags "integration"
pm-tools log   docs/defects-app.md --id DEF-LNCH-1 --author @kj --event "attempted: ... did NOT work"
pm-tools close docs/defects-app.md --id DEF-LNCH-1 --author @kj --event "fixed: ... 79 pytest green"

# Migrate a legacy document (dry run first, always)
pm-tools upgrade docs/acceptance-criteria.md
pm-tools upgrade docs/acceptance-criteria.md --code "Authentication=AUTH" --author @kj --apply
```

`check` is the only gate and it is a gate, not a reporter: non-zero exit on errors (a duplicate id, an untriaged defect, a hand-kept contents table, the wrong hint line for the discipline), and `--strict` also fails on warnings (a missing repro, an undescribed category, a dangling relation).

## Reports

`report` prints paste-ready markdown tables. SUMMARY is the one aggregate - categories down, severity or test tag across, `open/closed` in every cell so any two compare directly. ITEMS is a fix queue rather than an inventory: open work only, worst severity first, with closed and rejected counted in a footer instead of enumerated. `--detail` swaps the tables for one block per item, carrying the repro line, the tags, the relations and the whole log.

## Rules summary

- One consolidated document per discipline per project is the default; never a file per item
- Every write goes through `pm-tools` - hand-editing is legal markdown but loses the id assignment and the log line
- `remove` is for mistakes and duplicates only; an item that turned out to be invalid is rejected with a reason so the trail survives
- The agent triages every defect itself and never asks the user for the level
- In doubt about a criterion, an edge case or a category, ask - a wrong entry reads exactly like a right one

## Documentation

- `skills/project-management/SKILL.md` - ids, line format, three states, authoring, relations, the CLI surface
- `skills/project-management/references/acceptance-criteria.md` - writing criteria, the test hint, the API section, the regime matrix
- `skills/project-management/references/defects.md` - writing defects, the triage rubric, the repro line, details documents
- `skills/project-management/references/reports.md` - section shapes, filter semantics, `--detail`
- `skills/project-management/references/upgrade.md` - migrating a legacy document
- `skills/project-management/references/conflicts.md` - resolving a merge on a shared file
