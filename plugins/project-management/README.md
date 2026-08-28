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

- **No context switch** - the session that changed the code files the defect, in the same turn.
  Twenty minutes of interrupted work measurably raises mental workload, stress and effort[^1]
- **One file, not a document plus a tracker** - two copies of the same facts go out of sync. Of 146
  practitioners surveyed, 59% called code and documentation inconsistency a top recurring problem,
  46% named duplicate content[^2]
- **Markdown parses the same way every time** - a fixed grammar read by a parser, not a model. About
  15 microseconds per item, linear, never cached
- **One file for people and for the tool** - reads in an editor, diffs in git, parses into records.
  No export, no import. Knuth's argument, 1984[^3]
- **The file never goes into the context window** - the agent reads through the CLI, which returns
  only the rows it asked for. On the document below, one category's report is 8.4 KB out of 4.0 MB.
  Accuracy drops when the answer sits mid-context[^4], and falls from 0.92 to 0.68 by 3000
  tokens[^5]
- **Short entries** - longer input makes models reason worse[^5]. Clarity still rated highest, at
  88%[^2]
- **Every event is signed and timestamped** - across 2,731 Java projects, 87% of merge conflicts were
  resolved using only lines already in the file[^6]

### Trivia

A generated document of 10,000 acceptance criteria across 100 categories - 25,577 log lines, 4.0 MB -
parses in 153 ms and passes `check` in 1.2 s. A 1,000-defect file parses in 13.6 ms. Interpreter
start is 84 ms of any call, so below a few thousand items the file is not the cost. Filtering saves
tokens rather than time: `report --category` parses everything either way, but returns 8,436 bytes
instead of 780,567.

Each point above that rests on published work cites it. `references/papers/` holds one digest per
paper - findings, limits, and what it does and does not support for this tool. The one uncited point
is the parsing cost, and the Trivia above is its evidence. The PDFs are not in the repo; every digest
links to the original.

[^1]: Mark, Gudith, Klocke. *The Cost of Interrupted Work*. CHI 2008. [Digest](references/papers/%5Bpaper%20digest%5D%20cost%20of%20interrupted%20work.md) - [doi](https://doi.org/10.1145/1357054.1357072)
[^2]: Aghajani et al. *Software Documentation: The Practitioners' Perspective*. ICSE 2020. [Digest](references/papers/%5Bpaper%20digest%5D%20software%20documentation%20practitioners%20perspective.md) - [doi](https://doi.org/10.1145/3377811.3380405)
[^3]: Knuth. *Literate Programming*. The Computer Journal 27(2), 1984. [Digest](references/papers/%5Bpaper%20digest%5D%20literate%20programming.md) - [doi](https://doi.org/10.1093/comjnl/27.2.97)
[^4]: Liu et al. *Lost in the Middle*. TACL 12, 2024. [Digest](references/papers/%5Bpaper%20digest%5D%20lost%20in%20the%20middle.md) - [acl](https://aclanthology.org/2024.tacl-1.9/)
[^5]: Levy, Jacoby, Goldberg. *Same Task, More Tokens*. ACL 2024. [Digest](references/papers/%5Bpaper%20digest%5D%20same%20task%20more%20tokens.md) - [acl](https://aclanthology.org/2024.acl-long.818/)
[^6]: Ghiotto et al. *On the Nature of Merge Conflicts*. IEEE TSE, 2020. [Digest](references/papers/%5Bpaper%20digest%5D%20nature%20of%20merge%20conflicts.md) - [doi](https://doi.org/10.1109/TSE.2018.2871083)

## The design - nothing is written down twice

Every fact is stored exactly once, and everything else is computed when read. That is why the file cannot contradict itself.

| Fact | Where it lives | How it is known |
|------|----------------|-----------------|
| Item text, title, log | the checklist line and its sub-lines | stored once |
| Proof it is done | the `evidence:` line, written by `close` | stored once |
| Open, closed or rejected | the `[ ]` / `[x]` / `[-]` box | stored once |
| Category membership | the `##` section the line sits under | stored once |
| Next free number | not stored | highest id in the file, plus one |
| Backlinks, outbound links, blocker chain | not stored | `pm-tools refs --id` |
| Index, contents, counts | not stored | `pm-tools list-categories` |
| Test coverage per tag | not stored | `pm-tools coverage` |

Three things follow, all deliberate: no `## Contents` table (a second index that drifts - `check` rejects one), no Open / Fixed sections (status is the checkbox, so an item never moves), and one-way links (the reverse side is computed, never written back).

## What an item looks like

```markdown
## Launch `LNCH`

Cold start, splash screen and the first turn after a fork

- [ ] `DEF-LNCH-3` **token race on relaunch** - MAJOR; auth token occasionally empty on the first turn after a fork; cause under investigation; `src/session.ts`
  - repro: fork under load, send a turn inside 2s
  - test-tags: INTEGRATION
  - related: ACC-LNCH-8 - the criterion this violates
  - log: 2026-06-22T09:14:27Z @kj reported: intermittent 401 on the first turn
  - log: 2026-06-22T11:02:55Z @kj attempted: 200ms pre-turn delay - did NOT work
```

- **Permanent ids** - `ACC-<CAT>-<N>` and `DEF-<CAT>-<N>`, unique across the document, never renumbered and never recycled. An item that moves category keeps the code it was born with
- **Three states** - `[ ]` open, `[x]` closed, `[-]` rejected. Rejected is for a report that was never a defect (never reproduced, or the feature is gone); a real defect nobody will fix is a close with the reason
- **Evidence at closure** - `close` refuses to run without `--evidence`, one line proving the item is done: the regression test that passes, the build it was verified on. Fixed stops being a claim
- **Regressions are counted, not overwritten** - reopening a closed defect files `DEF-LNCH-3-1`, then `-2`, and leaves the original closed with its proof; the report totals them, so the file says how often fixes come back
- **Authored log lines** - ISO 8601 UTC, then the handle, then the event. Append-only, and the attempts that FAILED are the reason the file is worth keeping
- **Mandatory triage** - every defect carries a severity (`CRITICAL` / `MAJOR` / `MEDIUM` / `MINOR`) and every criterion an importance (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`), assigned by the agent as the item is filed. There is no unset: `add` refuses one and `check` errors on one

## CLI tools

Deterministic parsing, linting, editing and reporting - no generative step anywhere in `pm-tools`.

```bash
# Query
pm-tools report docs                          # the tables the user reads
pm-tools report docs --category AUTH --detail # one block per item, whole log
pm-tools report docs --severity CRITICAL      # also --category, --importance, --status, --author, --tag, --regressions, --grep, --blocked, --related-to
pm-tools report docs --dates closed --since 2026-08-01
pm-tools report docs --plain                  # the two grids, nothing else
pm-tools report docs --summary                # the SUMMARY grid alone, no items
pm-tools coverage docs                        # the test-coverage grid: categories down, tags across, NO-TEST last
pm-tools list docs --status open --columns id,title,author,age --sort=-age   # one table, your columns
pm-tools pivot docs --rows author --cols severity                            # an ad-hoc count grid
pm-tools pivot docs --rows root --regressions --values ids                   # regressions per defect
pm-tools list docs --blocked --columns id,title,blockers   # waiting on open work
pm-tools search docs "token race"            # ranked by relevance; a typo still hits
pm-tools report docs --json                   # the same facts as data; also on coverage, list, pivot, search, refs, list-categories
pm-tools list-categories docs                 # the derived index
pm-tools refs docs --id DEF-LNCH-3            # inbound, outbound and the blocker chain
pm-tools check docs --strict                  # the gate; non-zero on errors

# Edit (all writes take --author)
pm-tools author docs/defects-app.md --handle @kj --name "Konrad Jelen"
pm-tools add docs/defects-app.md --category LNCH --name Launch --severity MAJOR \
    --author @kj --title "token race on relaunch" --text "symptom; cause under investigation" \
    --repro "fork under load, send a turn inside 2s" --test-tags "INTEGRATION"
pm-tools log   docs/defects-app.md --id DEF-LNCH-1 --author @kj --event "attempted: ... did NOT work"
pm-tools close docs/defects-app.md --id DEF-LNCH-1 --author @kj --event "fixed: ..." \
    --evidence "the repro no longer fires on build 412; 79 pytest green"

# Migrate a legacy document (dry run first, always)
pm-tools upgrade docs/acceptance-criteria.md
pm-tools upgrade docs/acceptance-criteria.md --code "Authentication=AUTH" --author @kj --apply
```

`check` is the only gate and it is a gate, not a reporter: non-zero exit on errors (a duplicate id, an untriaged defect, an unrated criterion, a hand-kept contents table, the wrong hint line for the discipline, a dangling relation, a blocked-by cycle), and `--strict` also fails on warnings (a missing repro, an undescribed category, an open item blocked by a finished one). Run it on the directory, so a link into the file beside resolves.

## Reports

`report` prints paste-ready markdown tables. SUMMARY is the one aggregate, in plain counts: categories down, the open items split per level - `| Category | Open | CRITICAL | MAJOR | MEDIUM | MINOR | Fixed | Rejected |` on defects, `| Category | Open | CRITICAL | HIGH | MEDIUM | LOW | Done | Rejected |` on criteria - with a Total row; the level columns count open items only, and an `UNTRIAGED` / `UNRATED` column appears only when an open item lacks a level. ITEMS is a fix queue rather than an inventory: open work only, worst level first, with closed and rejected counted in a footer instead of enumerated. `--detail` swaps the tables for one block per item, carrying the repro line, the tags, the relations and the whole log. `coverage` prints the test-coverage grid - categories down, occurring tags across (`UNIT`, `INTEGRATION`, `FUNCTIONAL`, `E2E`, `MANUAL`, then any other, `NO-TEST` last), counting open and closed items alike.

Filters are flags, so a narrowed ask stays computed rather than being filtered by hand in the answer. `--severity`, `--importance`, `--category`, `--author`, `--tag` (any case), `--regressions` and a date window (`--dates filed|closed|updated` with `--since` and `--until`) narrow the whole report; `--status` narrows the queue alone. `--grep PATTERN` (a case-insensitive regex over title, body, evidence and log lines), `--blocked` (an open blocked-by target) and `--related-to ID` (linked either way) narrow the same way. `--plain` prints the grid and the queue and nothing else - no icons, no blurbs, no categories table - and `--summary` stops at the SUMMARY grid, listing no items at all.

A question the report does not answer is still a computed table. `list` prints one table of items with the columns and sort order the question calls for, and `pivot` prints an ad-hoc grid - any field down, any field across, a count or the ids in every cell - over the same filters: who owns what by severity, open work by age band, regressions per defect, closures per month by category. `related` and `blockers` are fields like `tags`. `search "QUERY"` ranks items by relevance (BM25, fuzzy on typos and stems) after the same filters narrow the candidates; `--grep` filters, `search` ranks. `--json` on any query returns the same facts as data.

## Rules summary

- One consolidated document per discipline per project is the default; never a file per item
- Every write goes through `pm-tools` - hand-editing is legal markdown but loses the id assignment and the log line
- `remove` is for mistakes and duplicates only; an item that turned out to be invalid is rejected with a reason so the trail survives
- The agent triages every defect and rates every criterion itself, and never asks the user for the level
- In doubt about a criterion, an edge case or a category, ask - a wrong entry reads exactly like a right one

## Documentation

- `skills/project-management/SKILL.md` - ids, line format, three states, authoring, relations, the CLI surface
- `skills/project-management/references/acceptance-criteria.md` - writing criteria, the test hint, the API section, the regime matrix
- `skills/project-management/references/defects.md` - writing defects, the triage rubric, the repro line, details documents
- `skills/project-management/references/reports.md` - section shapes, filter semantics, `--detail`
- `skills/project-management/references/upgrade.md` - migrating a legacy document
- `skills/project-management/references/conflicts.md` - resolving a merge on a shared file
- `references/papers/` - digests of the six papers cited in Philosophy
