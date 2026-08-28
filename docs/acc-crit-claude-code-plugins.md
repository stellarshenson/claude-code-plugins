# Acceptance Criteria - Claude Code Plugins

One consolidated acceptance-criteria doc for the marketplace. One `##` section per feature or scope; new scopes append a section and a Contents pointer.

## Authors

- `@kj` Konrad Jelen

## SVG validation split `SVG`

Validation of a generated SVG is two things, not one: a deterministic CLI floor (`svg-infographics finalize` and its checkers) that proves construction sanity, and a validator process with a generative model in the loop that judges everything requiring judgment. The CLI must never attempt the second kind - the evals below the line are possible only via a generative model.

| Functionality | CLI validator (deterministic floor) | Validator process (generative model) |
| ------------- | ----------------------------------- | ------------------------------------ |
| Document construction (parses, canvas/viewBox sane) | owns | - |
| Connector construction (stem attaches, head aligned and sized to stem, no zero-length stems) | owns, where cheaply computable | borderline cases |
| Overlap geometry of rendered boxes | owns | adjudicates intentional layering |
| Colour arithmetic (WCAG ratios, both themes, dark declarations present) | owns | - |
| CSS discipline (class-based paint, no forbidden colours) | owns | - |
| Roster honesty (every aspect judged or its SKIP surfaced) | owns | - |
| Legibility in context (reads at ship size, hierarchy scans) | - | owns |
| Semantic fit (the graphic says what the hypothesis claims) | - | owns |
| Aesthetic quality vs the examples/ bar | - | owns |
| Label/number truth against source content | - | owns |

- [x] `ACC-SVG-1` **CLI: document construction** - HIGH; parseable XML, canvas/viewBox read, per-tag geometry sane
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj in place (v1.6.45)
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:11:40Z @kj edited test-tags (added)
- [x] `ACC-SVG-2` **CLI: connector construction** - HIGH; stem attaches to card edge, arrowhead aligned to stem and sized from it, zero-length stems flagged
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj in place (v1.6.45)
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:40Z @kj edited test-tags (added)
- [x] `ACC-SVG-3` **CLI: overlap geometry** - HIGH; rendered boxes of visible elements do not overlap; hidden subtrees excluded via one shared `is_display_none` predicate across colour scan, connector walk and overlaps model
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj predicate unified across the three layers (round-8 fix)
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:11:40Z @kj edited test-tags (added)
- [x] `ACC-SVG-4` **CLI: colour arithmetic** - HIGH; WCAG contrast ratios in both themes against the elected background; unreadable paint is reported UNMEASURABLE, never silently passed
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj in place (v1.6.45)
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:11:40Z @kj edited test-tags (added)
- [x] `ACC-SVG-5` **CLI: CSS discipline** - MEDIUM; class-based paint, no forbidden colours, dark-mode declarations where light ones exist
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj in place (v1.6.45)
  - log: 2026-08-28T09:11:39Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [x] `ACC-SVG-6` **CLI: roster honesty** - HIGH; every aspect reports PASS/FAIL/NA/SKIP; an unasked SKIP flips the verdict to NOT VERIFIED plus exit 1 on every branch, HARD path included; `--json` carries the per-file `skipped` map and `totals`
  - test-tags: UNIT
  - log: 2026-08-13T00:00:00Z @kj HARD-path stderr gap closed (round-8 fix)
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [x] `ACC-SVG-7` **CLI: no generative evals** - HIGH; the CLI never attempts readability, semantic or aesthetic judgment; checks stay deterministic (construction, geometry, colour arithmetic)
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj doctrine set by the Star Colonel
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-8` **CLI: verdict names the floor** - MEDIUM; verdict lines assert what was checked, never overall quality
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added - the current "OK - shippable" wording predates the split; reword decision pending the Star Colonel
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [x] `ACC-SVG-9` **Process: hypothesis first** - HIGH; every graphic states its rationale before any wireframing; the CLI cannot check this
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj in place (standing directive)
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-10` **Process: legibility at ship size** - HIGH; generative review of the rendered PNG; no deterministic proxy exists
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-11` **Process: semantic fit** - HIGH; the graphic says what the hypothesis claims; metaphor and flow fit the content
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-12` **Process: examples bar** - HIGH; side-by-side against `plugins/svg-infographics/examples/` production references; "readable infographic" is a generative judgment
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-13` **Process: label truth** - CRITICAL; labels and numbers match the source content the graphic summarizes
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [ ] `ACC-SVG-14` **Process: ambiguity adjudication** - MEDIUM; intentional layering vs overlap defect, decorative density vs clutter: judged by the model, never the CLI
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj criterion added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)
- [x] `ACC-SVG-15` **Ship = floor AND judgment** - CRITICAL; a graphic ships when the CLI floor passes AND the generative review accepts; a CLI PASS alone is never a ship decision
  - test-tags: MANUAL
  - log: 2026-08-13T00:00:00Z @kj doctrine set by the Star Colonel
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:11:41Z @kj edited test-tags (added)

## pm-tools relations and search `PMREL`

related/blocked-by links in every query surface, an exact --grep filter, a ranked search and link integrity in check

- [x] `ACC-PMREL-16` **related field** - HIGH; list --columns related shows the outbound related: ids of each item, - when none
  - evidence: tests/test_pm_tools.py 114 green incl. the 16 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: tracker with one related: line; list --columns id,related
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:36Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-17` **blockers field** - HIGH; list --columns blockers shows the outbound blocked-by: ids of each item
  - evidence: tests/test_pm_tools.py 114 green incl. the 17 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: tracker with one blocked-by: line; list --columns id,blockers
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:36Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-18` **pivot on relation fields** - MEDIUM; pivot --rows blockers buckets one row per target id and names the empty bucket
  - evidence: tests/test_pm_tools.py 114 green incl. the 18 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: two items, one blocked; pivot --rows blockers
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-19` **report detail shows links** - MEDIUM; report --detail prints the related: and blocked-by: lines under the item
  - evidence: tests/test_pm_tools.py 114 green incl. the 19 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: item with both kinds of link; report --detail
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:37Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-20` **--blocked filter** - HIGH; blocked keeps only items with at least one blocked-by target that is still open
  - evidence: tests/test_pm_tools.py 114 green incl. the 20 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: blocker open then closed; list --blocked before and after
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-21` **--related-to filter** - HIGH; related-to ID keeps items linked to ID in either direction and either kind, never ID itself
  - evidence: tests/test_pm_tools.py 114 green incl. the 21 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: A related: B; list --related-to A and --related-to B
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-22` **refs outbound** - HIGH; refs --id lists what ID points at as well as what points at it
  - evidence: tests/test_pm_tools.py 114 green incl. the 22 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: item with a related: line; refs --id on it
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-23` **refs blocker chain** - HIGH; refs --id prints the transitive blocked-by chain with each hop's status
  - evidence: tests/test_pm_tools.py 114 green incl. the 23 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: A blocked-by B blocked-by C; refs --id A
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-24` **--grep filter** - HIGH; grep PATTERN keeps items whose title, body, evidence or a log line matches the case-insensitive regex, on report, list and pivot
  - evidence: tests/test_pm_tools.py 114 green incl. the 24 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: two items; list --grep on a word only one carries
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:39Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-25` **Edge: invalid --grep** - MEDIUM; an unparseable --grep pattern is refused with the regex error, exit non-zero
  - evidence: tests/test_pm_tools.py 114 green incl. the 25 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: list --grep '('
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-26` **search ranks by BM25** - HIGH; search QUERY orders items by BM25 over id, title, body, evidence and logs with id and title weighted higher
  - evidence: tests/test_pm_tools.py 114 green incl. the 26 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: two items sharing a body word, one carrying it in the title; search that word
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-27` **search tolerates a typo** - MEDIUM; a query token with one typo or a stem still matches through fuzzy token matching
  - evidence: tests/test_pm_tools.py 114 green incl. the 27 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: title 'token race'; search tokne
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:40Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-28` **search --top** - LOW; top N truncates the rows and the footer states how many matched
  - evidence: tests/test_pm_tools.py 114 green incl. the 28 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: 12 hits; search --top 3
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:39Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-29` **search --json** - MEDIUM; search --json returns rank, id, score, title, matched_in, file and line per row
  - evidence: tests/test_pm_tools.py 114 green incl. the 29 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: search --json; parse
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:39Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-30` **search takes FILTERS** - HIGH; search accepts the shared FILTERS and ranks only what they leave
  - evidence: tests/test_pm_tools.py 114 green incl. the 30 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: search --status open on a mixed tracker
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:39Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-31` **Edge: empty query** - LOW; a query with no searchable token is refused with a message
  - evidence: tests/test_pm_tools.py 114 green incl. the 31 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: search ' '
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-32` **Edge: unquoted multi-word query** - MEDIUM; search docs token race is refused with the quoting hint instead of ranking race
  - evidence: tests/test_pm_tools.py 114 green incl. the 32 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: search docs token race
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-33` **check: dangling link is an error** - HIGH; a related: or blocked-by: target absent from the scanned files fails check
  - evidence: tests/test_pm_tools.py 114 green incl. the 33 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: link to DEF-NONE-9; check
  - test-tags: UNIT
  - log: 2026-08-28T08:20:49Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-34` **check: cycle is an error** - HIGH; a blocked-by cycle fails check, reported once on its smallest id
  - evidence: tests/test_pm_tools.py 114 green incl. the 34 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: A blocked-by B, B blocked-by A; check
  - test-tags: UNIT
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-35` **check: closed blocker warns** - MEDIUM; an open item blocked by a closed or rejected target gets a warning naming the target
  - evidence: tests/test_pm_tools.py 114 green incl. the 35 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: close the blocker; check
  - test-tags: UNIT
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:21Z @kj closed: shipped with the relations/search and reporting passes
- [x] `ACC-PMREL-36` **stdlib only** - HIGH; the search and relation code adds no dependency and no import cost at startup
  - evidence: tests/test_pm_tools.py 114 green incl. the 36 contract tests; confirming reviews SHIP on wf_62aa2929 fixes and wf_da9438b2
  - test: grep imports in pm_tools.py; time pm-tools --help
  - test-tags: MANUAL
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T09:11:38Z @kj edited importance
  - log: 2026-08-28T09:44:20Z @kj closed: shipped with the relations/search and reporting passes

## adversarial review tooling `REVIEW`

review-tools CLI, graphify wiring in the devils-advocate reviewer and the measured cost rules for review rounds

- [x] `ACC-REVIEW-37` **review-tools dossier** - HIGH; dossier builds an AST inventory of the given files: symbols, argparse surface versus documented subcommands, risky primitives, cross-module literals and top callers from graph.json
  - evidence: tests/test_review_tools.py dossier tests (11 tests green); 86 KB dossier of src/ built in 1.8 s
  - test: review-tools dossier on a fixture tree; assert each section
  - test-tags: UNIT
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-38` **review-tools cost** - HIGH; cost profiles a subagent transcript deduplicated by API message id: turns, cache read, output, context median, tool mix, re-reads
  - evidence: tests/test_review_tools.py cost test; round-2 transcripts profiled to 14 and 15 turns
  - test: jsonl with two lines sharing a message id; assert one turn
  - test-tags: UNIT
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-39` **review-tools findings** - HIGH; findings merges VERDICT lines and severity bullets from N reports by file:line within 25 lines or normalised title
  - evidence: tests/test_review_tools.py findings merge test; round-1 panel reports merged for the adjudicator
  - test: two reports citing the same line; assert one merged finding
  - test-tags: UNIT
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-40` **graphify in the reviewer** - MEDIUM; the adversarial-reviewer agent reads graphify affected, explain and path before grep when tmp/graphify-out/graph.json exists
  - evidence: plugins/devils-advocate/agents/adversarial-reviewer.md code-graph paragraph; used by rounds 1-5
  - test: read the agent file; spawn a Mode 2 review with a graph present
  - test-tags: MANUAL
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-41` **graph refreshed before a panel** - MEDIUM; the orchestrator runs the AST-only graphify update before spawning reviewers
  - evidence: SKILL.md Mode 2 bullet; graphify update run before rounds 1-5
  - test: SKILL.md Mode 2 bullet; observe a panel spawn
  - test-tags: MANUAL
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-42` **confirming round is pinned** - HIGH; a confirming round carries the closure list, frozen md5 hashes and the batching rule, and finishes in about 15 turns rather than 67-115
  - evidence: rounds 2-5 measured 13-15 turns by review-tools cost against 67-115 in round 1
  - test: review-tools cost on the round transcript
  - test-tags: MANUAL
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance
- [x] `ACC-REVIEW-43` **dossier is optional** - LOW; the pasted dossier block is not required by the skill; a round measures its own cost with review-tools cost
  - evidence: round-2 A/B: with dossier 14 turns 1.56M cache read 4 findings, without 15 turns 1.02M 9 findings
  - test: SKILL.md wording; round-2 A/B numbers
  - test-tags: MANUAL
  - log: 2026-08-28T08:20:50Z @kj added
  - log: 2026-08-28T08:22:33Z @kj closed: verified on the sweep rounds
  - log: 2026-08-28T09:11:39Z @kj edited importance

