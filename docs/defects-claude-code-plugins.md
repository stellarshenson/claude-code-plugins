# Defects - Claude Code Plugins

Defects found and fixed in the stellars-claude-code-plugins library and its marketplace plugins.

## Authors

- `@kj` Konrad Jelen

## journal-tools `JRNL`

journal parser, standardize, sort and archive

- [x] `DEF-JRNL-1` **parser folded non-entry lines into a Result body** - MAJOR; a ## heading, --- rule or <!-- comment --> after an entry counted as body words, so check stayed green while sort and archive rewrote them into the Result line; cause no entry boundary in the parser; fix _ENTRY_BOUNDARY stops the body; journal_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; tests/test_journal_tools.py marker tests
  - repro: entry followed by ## 2026-08; journal-tools check word count vs render
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed: boundary rule, render emits raw lines
- [x] `DEF-JRNL-2` **condense deleted the heading or comment after the entry** - MAJOR; standardize --apply N --decision condense removed the ## heading or trailing standardize-clean comment following the entry; cause the replaced span ran to the next Task line; fix span stops at the boundary; journal_tools.py apply_condense_body
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_apply_condense_body_stops_at_the_entry_boundary
  - repro: entry then ## heading; standardize --apply --decision condense --body-file
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed: walk stops at _ENTRY_BOUNDARY
- [x] `DEF-JRNL-3` **sort added a blank line per run and two on an empty header** - MINOR; each sort run grew the header gap; a journal with no header started with two blank lines; fix header rstrip and conditional gap; journal_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_sort_is_idempotent_on_the_header_gap
  - repro: run sort three times; diff
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed
- [x] `DEF-JRNL-4` **archive with keep-last 0 or above the entry count** - MEDIUM; archive_journal moved every entry or none with a misleading result; fix returns None when keep_last <= 0 or >= entries; journal_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: archive --keep-last 0 on 45 entries
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed
- [x] `DEF-JRNL-5` **sort on a file with no parsed entries rewrote the journal** - MAJOR; a journal the parser could not read was rewritten to header only; fix sort refuses with exit 1 when no entries parse; journal_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: sort a file whose entries carry no Task marker
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed
- [x] `DEF-JRNL-6` **standardize.yaml carried a stale limits block** - MINOR; the prompt file kept a limits: block nothing read; fix deleted, test asserts absence; journal/prompts/standardize.yaml
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: grep limits: standardize.yaml
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed
- [ ] `DEF-JRNL-34` **sort without --start-from renumbers an archived journal from 1** - MEDIUM; a journal starting at entry 110 after archiving is renumbered 1-227 by a bare sort; every plugin doc invokes sort with --dry-run only, so the trap is one missed flag; fix default start from the first entry's number; journal_tools.py
  - repro: archived journal; sort --dry-run; read the first number
  - test-tags: UNIT
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-JRNL-36` **standardize prompt says 70 where the floor is 50** - MINOR; standardize.yaml lines 30, 79, 93 name the old Standard floor; the prompt is cassette-hashed so the edit needs claude on PATH to re-record; journal/prompts/standardize.yaml
  - repro: grep 70 standardize.yaml
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added

## document-processing `DOCP`

ground, validate and the grounding config plumbing

- [x] `DEF-DOCP-7` **validate counted a contradicted claim as confirmed** - MAJOR; only match_type none counted as unconfirmed, so a document contradicting its source passed; fix contradicted counted; validate.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: claim 5 million vs source 6 million; validate
  - test-tags: UNIT
  - log: 2026-08-28T08:22:11Z @kj added
  - log: 2026-08-28T08:22:11Z @kj closed: fixed
- [x] `DEF-DOCP-8` **ground exited 0 on a contradicted claim** - MAJOR; single and batch ground returned 0 with CONTRADICTED printed and the batch summary hid the count; fix exit 1 and contradicted in the summary; cli.py cmd_ground
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_ground_single_contradicted_exits_one
  - repro: ground --claim with a wrong number; echo \$?
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-DOCP-9` **threshold flags shadowed the config defaults** - MEDIUM; six --threshold flags defaulted to literals so the config file values never applied; fix default None filled from config in _grounding_config; cli.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: set fuzzy_threshold in config; ground without flags
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed

## project-management `PMGT`

pm-tools parser, edit, upgrade and reports

- [x] `DEF-PMGT-10` **edit --text re-triaged a defect whose text opened with a level word** - MAJOR; SEV matched Major refactor ... case-insensitively at a word boundary and replaced the severity; fix delimiter lookahead (;:,) as the guard; pm_tools.py SEV
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_severity_case_is_free_but_the_delimiter_is_not
  - repro: edit --text 'Major refactor needed' on a CRITICAL item
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-11` **age of a closed item with no closing stamp** - MEDIUM; age_of counted from the filed date for a closed item with no closed: stamp, printing 230 days; fix returns None; pm_tools.py age_of
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: close by hand without a log line; list --columns age
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-12` **malformed log stamp crashed list, report and pivot** - MAJOR; 2026-02-30T10:00:00Z raised ValueError day out of range; fix _valid_stamp guard, check reports the stamp; pm_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: log line with 2026-02-30; list
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-13` **upgrade left non-canonical severity forms** - MEDIUM; High: became MAJOR: and major; stayed lower case; fix alias, case and delimiter land on LEVEL; ; pm_tools.py cmd_upgrade
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_upgrade_writes_the_canonical_severity_form
  - repro: tracker with High: and major;; upgrade --apply
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-14` **upgrade dropped the regression ordinal** - MAJOR; DEF-LNCH-3-1 was rewritten to DEF-LNCH-3, a duplicate id; fix ordinal appended to plan line and rewrite; pm_tools.py cmd_upgrade
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_upgrade_keeps_regression_ordinals_and_leaves_criteria_alone
  - repro: closed root plus open -1 regression; upgrade --apply; check
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-15` **upgrade rewrote criteria opening with a level word** - MAJOR; an ACC item 'Normal, degraded and offline ...' became 'MEDIUM; degraded ...' and check steered the operator into it; fix severity rewrite and the foreign-severity error are DEF-only; pm_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: ACC item opening Normal,; upgrade --apply
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-16` **upgrade MANUAL lines named the root of a regression** - MINOR; the printed edit command targeted DEF-LNCH-3 for an untriaged DEF-LNCH-3-1; fix id built once with the ordinal; pm_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: untriaged regression; upgrade
  - test-tags: UNIT
  - log: 2026-08-28T08:22:12Z @kj added
  - log: 2026-08-28T08:22:12Z @kj closed: fixed
- [x] `DEF-PMGT-17` **upgrade reported N changes on an unchanged file** - MINOR; every item produced a plan line even when the id was unchanged; fix plan line only on change; pm_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: upgrade twice
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [ ] `DEF-PMGT-29` **parser assigns a severity to criteria opening with a level word** - MEDIUM; an ACC item 'Normal, degraded ...' shows MEDIUM in list --columns severity, report --detail prints NORMAL as its head, and edit --text writes NORMAL; as a prefix; cause parse() reads SEV for every prefix; fix gate on prefix DEF in parse(); pm_tools.py
  - repro: ACC item opening Normal,; list --columns id,severity
  - test-tags: UNIT
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-PMGT-30` **LEGACY regex drops a legacy regression ordinal** - MINOR; a pre-category DEF-7-1 upgrades to a fresh id and the root link is lost; legacy files never carried regressions so the input is theoretical; pm_tools.py LEGACY
  - repro: legacy file with DEF-7-1; upgrade
  - test-tags: UNIT
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-PMGT-31` **upgrade counts plan lines, not edited lines** - MINOR; applied N change(s) aggregates severity renames into one line and omits [X] lower-casing; pm_tools.py cmd_upgrade
  - repro: file with 3 renames; read the count
  - test-tags: UNIT
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-PMGT-32` **shipped tracker examples fail check** - MINOR; check exits 1 on plugins/project-management README.md, references/defects.md, references/acceptance-criteria.md (dangling example ids, no evidence); cause examples cite ids that do not exist in the file; fix either self-consistent examples or a skip marker
  - repro: pm-tools check plugins/project-management
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-PMGT-38` **upgrade rewrites indented lines inside fenced code blocks** - MEDIUM; a fenced example containing an indented dated note or tag line is converted and signed by upgrade --apply like real history; cause the output loop never tracks fence state; fix toggle on ``` lines and pass fenced lines through; pm_tools.py cmd_upgrade
  - repro: tracker with a fenced '  - 2026-06-12 note' line; upgrade --apply; read the fence
  - test-tags: UNIT
  - log: 2026-08-28T09:44:20Z @kj added
- [ ] `DEF-PMGT-39` **add writes a doubled level word when the text repeats it** - MINOR; add --importance HIGH --text 'HIGH; ...' writes HIGH; HIGH; ...; same for --severity on defects; cause add prefixes the level without stripping one already opening the text; fix strip a leading level word before prefixing; pm_tools.py cmd_add
  - repro: add --severity MAJOR --text 'MAJOR; x'; read the body
  - test-tags: UNIT
  - log: 2026-08-28T09:44:20Z @kj added
- [x] `DEF-PMGT-51` **report SUMMARY grid mixes status with level - the level columns split Open only, yet sit as peers of Open, Done and Rejected** - MAJOR; The SUMMARY header reads | Category | Open | CRITICAL | HIGH | MEDIUM | LOW | Done | Rejected | (Fixed on defects, plus Worked on when a lock is active). Two axes share one row: status (Open, Worked on, Done, Rejected) and level, where the four level cells are a breakdown of the Open column alone and sum to it. Nothing in the table says so - eight count columns render as peers, so a reader takes CRITICAL..LOW as the whole category split by level, sees Done as a fifth level or a second count, and Rejected trailing Done as a lifecycle stage. Observed 2026-09-02 on docs/acc-crit-docdistance.md: the owner read Done as 2+2 against a Total of 13, then asked why severity sits between Open and Done; the explanation needed a five-row legend. The --json shape already keeps the nesting (open, levels, worked_on, closed, rejected per category) - only the markdown flattens it. The layout is documented as intended (pm_tools.py docstring, SKILL.md:189, references/reports.md:21) and pinned by seven header assertions in tests/test_pm_tools*.py, so this is a design defect, not drift
  - evidence: uv run pm-tools report docs/defects-claude-code-plugins.md --summary prints | Category | Open | Fixed | Rejected | Total | and then Open by severity with | Category | CRITICAL | MAJOR | MEDIUM | MINOR | Open |; tests/test_pm_tools.py::test_the_defects_grid_is_plain_open_counts_per_severity asserts '| Open | CRITICAL' absent in every report form; pm-tools suites 190 passed, full suite 1267 passed 2 skipped, ruff clean; ACC-PMREP-122, ACC-PMREP-123
  - test-tags: UNIT
  - repro: pm-tools report docs/acc-crit-claude-code-plugins.md --summary; the four level cells of any row sum to its Open cell while Done and Rejected stand beside them unbroken; pivot --rows category --cols status prints the status-only grid the SUMMARY does not
  - root-cause: 2026-09-02T05:39:34Z @kj one grid was made to answer two questions at once - how much is left (status) and how bad it is (level) - by appending the status columns to the open-by-level split at pm_tools.py:1327 (head = [Category, Open] + cols + wip + [done, Rejected]); markdown has no column groups, so the nesting the JSON carries is lost on the page
  - log: 2026-09-02T05:39:34Z @kj added
  - log: 2026-09-02T05:39:34Z @kj candidate layouts, none decided: (a) two grids - a status grid | Category | Open | Worked on | Done | Rejected | Total | and an open-by-level grid | Category | CRITICAL | HIGH | MEDIUM | LOW | Open |; (b) one grid with the level split moved to the end under a heading that names it, | Category | Done | Rejected | Open | of which CRITICAL | HIGH | MEDIUM | LOW |; either way the seven header tests, the docstring, SKILL.md and references/reports.md change with it and the --json shape stays
  - log: 2026-09-02T06:17:20Z @kj edited test-tags (added)
  - log: 2026-09-02T06:17:20Z @kj closed
  - log: 2026-09-02T06:52:39Z @kj survived the same loop (wf_812326e5-afd, wf_5c7c86a1-d53, SHIP); round 1 found two doc sentences still describing the one-row grid (skills/report/SKILL.md step 6, references/reports.md filter clause) - corrected; the reviewers reproduced the two-grid output on scratch stores in default, --plain, --summary and filtered forms

## hypothesis-tools `HYPO`

ledger parser, verdict reading and orphan checks

- [x] `DEF-HYPO-18` **verdict prefix match read a partial verdict as clean** - MAJOR; Confirmed-partially and Refuted for k=1, Confirmed for k=3 parsed as single verdicts; fix label must end the value or be followed by ;; hypothesis_tools.py match_verdict
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; test_bold_label_still_reads
  - repro: verdict 'Confirmed-partially; x'; list --verdict
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed; the first fix rejected **Confirmed**; bold labels, corrected in the same loop
- [x] `DEF-HYPO-19` **orphan check missed ids in table rows** - MEDIUM; find_orphan_ids skipped | E1-H9 | table cells; fix TABLE_ID_RE arm; hypothesis_tools.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: summary table citing a missing id; check
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [x] `DEF-HYPO-20` **list silently dropped compact hypotheses** - MEDIUM; --verdict filters excluded unjudged compact hypotheses with no notice; fix count printed to stderr; hypothesis_tools.py cmd_list
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: list --verdict Ships on the lexical ledger
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [ ] `DEF-HYPO-33` **summary-table example fails check with orphan errors** - MINOR; examples/summary-table.md cites ids from other ledgers so the new table arm reports 5 orphans; SKILL.md says such tables live in the conversation, so check on it is out of contract; fix document or exclude
  - repro: hypothesis-tools check plugins/datascience/skills/hypothesis/examples/summary-table.md
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
- [ ] `DEF-HYPO-49` **A summary table written to the skill's own ID-cell spec cannot declare** - MAJOR; the skill prescribes an ID cell carrying the id AND the memory slug (summary-table.md:6, 'E30-H106 turbomind-throughput'), but _table_declarations only accepts a first cell that is exactly one id with nothing else, so such a row declares nothing while TABLE_ID_RE reports it as a failed declaration; a ledger whose hypotheses live only in such a table gets an error per row from check and a refusal from next-id and register
  - repro: hypothesis-tools check plugins/datascience/skills/hypothesis/examples/summary-table.md - 7 errors, 0 hypotheses; the same file is the skill's own worked example of the format
  - test-tags: FUNCTIONAL
  - root-cause: 2026-09-01T10:33:41Z @kj the at-a-glance table shape was added against sci-demographic-collapse, whose ID cells are bare ids; the shipped example's documented id-plus-slug form was never in that evidence base
  - log: 2026-09-01T10:33:41Z @kj added

## autobuild orchestrator `BUILD`

orchestrate CLI, resources and the TEST phase

- [x] `DEF-BUILD-21` **resource byte-compare archived user customisations** - MAJOR; any edit to .autobuild/resources/*.yaml was archived and overwritten on the next run; fix only the legacy gates: format triggers the archive; orchestrator.py _detect_stale_resources
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; tests/test_orchestrator.py
  - repro: append a comment to app.yaml; orchestrate status
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed; bundled updates no longer propagate, refresh by deleting the directory
- [x] `DEF-BUILD-22` **help and status printed a python orchestrate.py path** - MINOR; app.yaml cmd pointed at a script path; fix cmd orchestrate; resources/app.yaml
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: orchestrate --help
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [x] `DEF-BUILD-23` **missing make target failed the TEST phase forever** - MAJOR; make lint with no lint target exited 2 and every iteration rejected to IMPLEMENT; the FileNotFoundError arm was unreachable under shell=True; fix exit-2 target-missing and exit-127 make-absent skip, LC_ALL=C for the stderr match; orchestrator.py _verify_test_phase
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: Makefile with test only; orchestrate end
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [x] `DEF-BUILD-24` **unrequested version check hit the network** - MINOR; _check_version and its cache file ran on every command; fix deleted with --no-version-check; orchestrator.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: orchestrate status offline
  - test-tags: UNIT
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [x] `DEF-BUILD-25` **archive warning named the removed byte-compare** - MINOR; message said resources differ from bundled version after that rule was gone; fix names the legacy gates: format; orchestrator.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: legacy phases.yaml; orchestrate status
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:13Z @kj added
  - log: 2026-08-28T08:22:13Z @kj closed: fixed
- [ ] `DEF-BUILD-37` **orchestrate end with iterations 0 records no benchmark score** - MEDIUM; the TEST phase in --iterations 0 mode has no way to pass a score, so benchmark_scores stays empty; alternatives --score flag or deleting the mode, decision pending; orchestrator.py cmd_end
  - repro: orchestrate new --iterations 0; end the TEST phase; read benchmark_scores
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added

## svg-infographics `SVG`

svg-infographics umbrella skill docs and svg_tools

- [x] `DEF-SVG-26` **svg-designer docs cited flags the CLI rejects** - MAJOR; tools.md, fix.md, validation.md, background.md, connector.md and export-png.md named flags such as --x on circle, --container-id, background <texture>, --tangent-magnitude; an agent following them gets unrecognized arguments; fix flag columns regenerated from --help
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; round-5 diff of all 21 primitives rows against --help
  - repro: svg-infographics primitives circle --x 1 --y 1 --r 5
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
  - log: 2026-08-28T08:22:14Z @kj closed: fixed over rounds 2-5
- [x] `DEF-SVG-27` **manifest listed a shapes render form the CLI rejects** - MINOR; string said shapes render <name> with a --library flag order the parser refused; fix string corrected; svg_tools/manifest.py
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED
  - repro: svg-infographics shapes render
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
  - log: 2026-08-28T08:22:14Z @kj closed: fixed
- [ ] `DEF-SVG-35` **validators exit 0 on findings** - MEDIUM; check_overlaps, check_alignment, check_connectors and check_contrast return 0 with findings printed, so a pipeline cannot gate on them; contrast would fail 27 of 30 shipped examples if made hard, so it needs calibration first; svg_tools
  - repro: run check_contrast on an example; echo \$?
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
- [x] `DEF-SVG-55` **Skill(svg-infographics:svg-infographics) fails with Unknown skill** - MEDIUM; the plugin:plugin form that resolves for datascience, journal, project-management and autobuild had no target in svg-infographics, whose umbrella skill was named svg-designer; a caller following the convention of the other four plugins got Unknown skill and had to discover the real name
  - evidence: skills/svg-infographics/SKILL.md carries name: svg-infographics; test_svg_tools structure check and test_toolchain_gate read the new path; suite 1268 passed, 2 skipped; grep svg-designer over the tree finds only journal history and DEF-SVG-26
  - repro: Skill(skill="svg-infographics:svg-infographics") on plugin 1.7.16 - Error: Unknown skill: svg-infographics:svg-infographics
  - root-cause: 2026-09-02T07:59:22Z @kj the umbrella skill directory and frontmatter were named svg-designer while every other umbrella plugin names its skill after the plugin
  - log: 2026-09-02T07:59:22Z @kj added
  - log: 2026-09-02T07:59:22Z @kj renamed skills/svg-designer to skills/svg-infographics (git mv), frontmatter name and every live reference in the plugin, devils-advocate, datascience, svg_tools/manifest.py, tests and docs updated
  - log: 2026-09-02T07:59:22Z @kj closed

## build tooling `MAKE`

Makefile targets and CI parity

- [x] `DEF-MAKE-28` **make lint ran a floating ruff** - MEDIUM; uvx ruff resolved 0.16.5 with a different rule set and reported 237 findings the project ruff 0.15.8 does not; fix uv run --extra dev ruff, matching ci.yml; Makefile
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; round-5 fresh-clone make lint exit 0
  - repro: make lint with uvx resolving a newer ruff
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
  - log: 2026-08-28T08:22:14Z @kj closed: fixed
- [x] `DEF-MAKE-54` **README links showcase/ after the directory moved to docs/showcase/** - MINOR; the v1.7.15 repository cleanup moved showcase/ under docs/ but README.md line 34 still linked showcase/, so the check-links CI job (lychee) failed with File not found on release runs 33579299161 (v1.7.15) and 33601564782 (v1.7.16); every other checked link resolved (90 successful, 13 excluded)
  - evidence: README.md line 34 now links docs/showcase/, which exists; grep -c '](showcase/)' README.md returns 0
  - repro: ls showcase -> No such file; grep -n '](showcase/)' README.md matches line 34; the lychee job reports file:///.../showcase File not found
  - log: 2026-09-02T07:10:02Z @kj added
  - log: 2026-09-02T07:10:02Z @kj closed

## devils-advocate adversarial-review `ADVR`

Adversarial-review loop: reviewer, adjudicator, workflow script, spec

- [x] `DEF-ADVR-40` **Immaterial finding admitted as MAJOR - no materiality test** - MAJOR; Reviewers rate a technically true defect on an input the product is not for as MAJOR with outOfBar=false; the bar states output guarantees only (no purpose, input universe or primary path), so the reviewer has nothing to test materiality against and the finding contract never asks who is harmed. Session 1833dce5 wf_a1812379 (plugin 1.7.7): <select>, <summary>/<legend>, <sup>/<sub>, <datalist> pasted into a notebook cell all MAJOR under the bar clause 'never fuse two distinct values'; 10 MAJORs on a 300-line extension; the <select> finding became a normalisation pass that then hosted 100% of rounds 2-3 findings
  - evidence: tests/test_adversarial_workflow_script.py 17 passed; full suite 1035 passed, ruff clean (test_bar_must_name_purpose_inputs_and_primary_path, test_materiality_before_severity); ACC-REVIEW-56
  - repro: Run the loop with a bar of output guarantees only against any HTML-to-markdown target; paste a form control fixture; the reviewer returns MAJOR outOfBar=false and the adjudicator plans a pass for it
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-29T09:22:06Z @kj closed: fixed: bar object with purpose/inputs/primaryPath enforced by the script; material+materiality in the findings schema with a script cap; adjudicator step 0 materiality triage; materiality line in reviewer agent, authoring reference and all 11 personas
- [x] `DEF-ADVR-41` **Remedy proposes machinery and the adjudicator enlarges it - no newMechanism flag, no change budget** - MAJOR; The reviewer remedy field invites code; the adjudicator's 'smallest terminal change grouped by root cause' yields completeness, not minimality, and nothing marks a change as a new mechanism or bounds the number of changes per round. wf_a1812379 round 1: reviewer proposed a one-line select replacement; the adjudicator planned selected-options joined by ', ', first-option fallback, datalist dropped, plus a regression test; the round-1 plan touched 6 sites and introduced 4 new mechanisms (three GFM plugins, the select pass, caption lift, reshaped clipboard result). Every one of them hosted round-2 findings
  - evidence: tests/test_adversarial_workflow_script.py 17 passed; full suite 1035 passed, ruff clean (test_new_mechanism_flag_and_change_budget); ACC-REVIEW-57
  - related: DEF-ADVR-40
  - repro: Feed the adjudicator a MAJOR whose remedy is a new pass; the plan returns the pass enlarged with fallbacks and a test, with no flag distinguishing it from an edit to existing code
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-29T09:22:06Z @kj closed: fixed: newMechanism required on every planned change, CHANGE BUDGET (maxChanges, default 3) in the adjudicator prompt, mechanisms surfaced in the PLAN payload for veto; reviewer remedy is EDIT or DEFER with NEW MECHANISM named
- [x] `DEF-ADVR-42` **Fanout read as refine, never revert - adjudicator has no REVERT verb and FANOUT_STOP exits without a revert list** - MAJOR; When findings sit in code the loop's own previous plan introduced, the adjudicator can only refine or STOP; it has no ruling that removes the mechanism and defers the original finding, so contested semantics are refined forever. wf_a1812379: round 2 fanout 7/7 -> PROCEED_WITH_DEFERRALS with 4 refinements; round 3 fanout 12/12 -> 5 refinements; FANOUT_STOP fired after two rounds of applied damage with 're-model the component' and no list of what to revert; the follow-up fix workflow (wf_c911e444) refined the same pass again and was refuted by a headless-Chrome measurement. Every list-box semantics violated one bar clause, so no clean round was reachable - only deletion, which the user ordered in one glance
  - evidence: tests/test_adversarial_workflow_script.py 17 passed; full suite 1035 passed, ruff clean (test_revert_before_refine); ACC-REVIEW-58
  - related: DEF-ADVR-41
  - repro: Apply a plan that adds a pass, run a pinned confirm that reports findings only on that pass; the adjudicator returns refinements of the pass, never its removal, and the FANOUT_STOP payload names no mechanism to revert
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-29T09:22:06Z @kj closed: fixed: reverts required in the adjudication schema; REVERT BEFORE REFINE rule with every applied change a revert candidate; PLAN/STOP/FANOUT_STOP carry reverts (all applied changes when none ruled); fanout above 0.5 without a revert logged; adjudicator agent step 4 rewritten
- [x] `DEF-ADVR-43` **Confirming rounds sweep instead of confirm - pinning is prompt-only, no script filter** - MEDIUM; The confirm prompt pins reviewers to closures plus the newest delta, but the script discards nothing, so reviewers re-audit everything adjacent. wf_a1812379 rounds 2 and 3: 19 raw findings each, including README wording, a log-prefix literal, a doc comment, 'the added test does not exercise the retag', an export with no caller - taste and out-of-delta items that were merged and sent to the adjudicator at full verification cost (reviewer transcripts 260-390KB, adjudicator ~320KB per confirm round)
  - evidence: tests/test_adversarial_workflow_script.py 17 passed; full suite 1035 passed, ruff clean (test_confirm_round_filter_is_script_enforced); ACC-REVIEW-59
  - repro: Run a pinned confirm on a delta of one function; count findings whose file:line is outside the delta and cite no closure - they reach the adjudicator
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-29T09:22:06Z @kj closed: fixed: pinFilter after both confirm panels keeps only closure-citing or in-delta non-taste findings, logs the rest into history; closure field in the findings schema; appliedFixes.files; TURN BUDGET in the confirm prompt
- [x] `DEF-ADVR-44` **Fixer inside the workflow edits the tree with no human gate** - CRITICAL; In plugin 1.7.7 the workflow's Fix stage applied the adjudicated plan itself, so the tree changed with nobody looking and a user instruction could not reach it. wf_a1812379: the order 'when finished - do not implement anything; just stop there' arrived 15:12 local, mid-fix, and was unenforceable; the run exited FANOUT_STOP with two rounds of fixes applied and 12 standing findings in them (+175/-48 across 8 files, uncommitted)
  - evidence: commit 54b9d62 (v1.7.8); tests/test_adversarial_workflow_script.py::test_workflow_never_edits_the_tree passes - no FIX_SCHEMA, 'Apply ONLY this plan in the main session' present
  - repro: Run the 1.7.7 adversarial-loop.js with findings that produce a non-empty plan; observe src/ modified before the workflow returns
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-28T17:36:29Z @kj closed: fixed in 1.7.8: Fix stage deleted; a non-empty plan exits as status PLAN for the main session to apply, re-invocation pinned-confirms the applied delta
- [ ] `DEF-ADVR-45` **Loop cost - 1.41M tokens over 14 agents for a 300-line target** - MAJOR; wf_a1812379: 77.7 minutes, 14 agents, 1,406,526 tokens; confirm-round reviewers 260-390KB transcripts, adjudicator ~320KB per round, reviewers writing Jest scratch specs and running headless Chrome to verify findings that were immaterial. Every finding was verified at full depth regardless of materiality; the 1.7.7 script had no args.graph so reviewers rediscovered the repo by grep. Rounds 2-3 (about two thirds of the bill) attacked machinery that should never have existed
  - related: DEF-ADVR-40, DEF-ADVR-42, DEF-ADVR-43
  - repro: Run the loop on a small target with a bar of output guarantees only; read totalTokens from the workflow run json and the per-agent transcript sizes under subagents/workflows/<runId>/
  - log: 2026-08-28T17:36:18Z @kj added
  - log: 2026-08-28T17:36:29Z @kj partially mitigated in 1.7.8: args.graph threads graphify into reviewer and adjudicator prompts (fewer discovery turns); the round-2/3 share of the bill stands until DEF-ADVR-40, 42 and 43 are fixed - did NOT close
  - log: 2026-08-29T10:11:29Z @kj measured on the loop's own review (this repo, 23-file delta): shipped-script rounds 318k/197k/199k/230k tokens at 4 agents each; constructed run with refutation votes 512k at 9 agents - the vote stage buys precision at cost; the 1.41M/14-agent bill of wf_a1812379 is not reproduced, but a re-run on the paste-ext target is still the closing measurement
  - log: 2026-08-29T15:57:45Z @kj Held open by decision, not by oversight. Measuring the hardened loop's cost needs a re-run against the original external target (the paste extension), which is a separate campaign outside this repository; the Star Colonel has elected to keep this open rather than name a target now. The fixes that should lower it are shipped and guarded: pinFilter discards taste and out-of-delta confirm findings, capImmaterial forces immaterial findings to MINOR, the fanout streak counts only refining rounds, and the confirm round is pinned to the applied delta
  - log: 2026-08-29T16:27:34Z @kj MEASURED on copier-tui (wf_2ce1c6b3-868, 2026-08-29): 19 agents, 0 errors, 1,214,188 tokens, 205 tool calls, 17.6 min wall clock, one invocation, exit PLAN with 2 changes. Verdict: the 1.7.9 hardening fixed WHAT the loop spends on, not HOW MUCH. Pre-fix the run burned most of 1.4M refining a non-issue; this run raised 11 findings, refuted or deferred 9 as immaterial, planned 2 changes with empirical verification and zero reverts. But one round now costs 86 percent of what the entire pre-fix campaign cost, so cost is NOT closed. Attribution by role: materiality skeptics 15 agents / 764,792 tokens / 63 percent; lens reviewers 3 agents / 360,823 / 30 percent; adjudicator 1 / 88,573 / 7 percent. Token burn is therefore dominated by the skeptic-per-finding fan-out, and latency by the slowest single lens (12.5 min of a 17.6 min wall clock). Caveat on comparability: different repository and a single invocation, so this is per-round cost of the hardened loop, not a like-for-like rerun of the paste-extension campaign
- [x] `DEF-ADVR-46` **FANOUT_STOP pre-empts an adjudicated-clean round** - MAJOR; The script evaluates the fanout streak before the clean check, so a confirming round the adjudicator rules clean (empty plan, every finding refuted) still exits FANOUT_STOP when its findings sat on the previous delta. Found by running the loop on its own change set (wf_f61c8fde-144, round 3: PROCEED, 0 changes, 3 refuted, fanout 3/3 -> FANOUT_STOP instead of SHIP with cleanRequired 1). Fanout is evidence only while the adjudicator keeps ordering changes; a clean ruling means the loop stopped generating work
  - evidence: tests/test_adversarial_workflow_script.py::test_gates_present asserts 'fanout > 0.5 && refining'; 17 passed
  - repro: Run a pinned confirm whose findings all sit in the applied delta and have the adjudicator refute them all; the script returns FANOUT_STOP, not a clean round
  - log: 2026-08-29T09:55:42Z @kj added
  - log: 2026-08-29T09:55:42Z @kj closed: fixed: highFanoutStreak advances only when the adjudication ordered changes or reverts (const refining); spec invariant 5 reworded
- [ ] `DEF-ADVR-47` **a dead reviewer panel is read as a clean round** - CRITICAL; mergeFindings maps a null agent return (agent died, terminal API error, skipped) to an empty findings list, so a round in which every reviewer died produces findings=[], skips adjudication entirely and exits SHIP - the loop reports a clean review it never performed
  - repro: Construct or run the loop with an agentType that does not resolve in the session (e.g. 'devils-advocate:adversarial-reviewer' when the plugin agents are not registered). All lens agents error; parallel/pipeline yield null; the run returns status SHIP with findings 0. Observed live as wf_00afc000-19a: 3 agents, 3 errored, 0 tokens, 82ms, returned {"status":"SHIP","note":"no findings survived the materiality skeptics"}
  - log: 2026-08-29T16:06:00Z @kj added
  - log: 2026-08-29T18:30:38Z @kj guarantee recorded as ACC-REVIEW-80 - the criterion the loop spec requires for every invariant; this defect is its discovery record
- [x] `DEF-ADVR-48` **the constructed-loop invariant check produces no artifact, so the supplied script wins on perceived safety** - MAJOR; The spec routes a harness WITH the dynamic Workflow capability to construct the loop from loop-spec.md, and names running the shipped adversarial-loop.js by path 'the fallback route taken by mistake'. Its mitigation for the risk of construction - 'check the script against the spec's invariant list one by one before running it' (SKILL.md:52), 'verifies it against the invariant list' (loop-spec.md:64) - produces NO observable artifact, so it can be skipped silently and cannot be shown to have happened. The shipped script meanwhile carries 22 passing tests, so the fallback route is the one that feels provably safe and the instructed route feels like a memory test. A capable session weighing 127 lines of same-evening protocol churn takes the script. Two alternative causes were tested and are NOT supported: prominence ('construct' 37 times across the plugin markdown against 6 mentions of the script path, 4 of those 6 inside the same sentence as the construct rule) and skill length (SKILL.md 146 lines / 2259 words, routing at line 49 under its own heading, 654 words in, progressive disclosure already across 8 reference files)
  - evidence: tests/test_adversarial_workflow_script.py::test_the_invariant_check_produces_an_artifact - 23 passed in that file, suite 1190 passed + 1 skipped, ruff clean. Guard proven non-vacuous: restoring the old wording 'check the script against the spec's invariant list one by one' fails it on the skill surface, restoring the map passes
  - test-tags: UNIT
  - repro: Give a session with the dynamic Workflow capability the adversarial-review skill and a multi-round review to run. Observed live 2026-08-29 in an external repository: the session ran the shipped worked example by path (wf_0af13805-a28), stated 'the spec permits construction and encourages it' while choosing otherwise, and on being challenged quoted the contract correctly, said 'the spec's own mitigation covers it - which I skipped rather than performed', stopped the run and constructed the loop properly (wf_b28d738c-5d2)
  - log: 2026-08-29T21:00:55Z @kj added
  - log: 2026-08-29T21:03:33Z @kj edited test-tags (added)
  - log: 2026-08-29T21:03:33Z @kj fixed: loop-spec.md gains '## The invariant map - required before a constructed loop runs' (nine INV-1..INV-9 lines naming the site in the constructed script, marked at the site); execution path 1 now 'emits the invariant map above' instead of 'verifies it against the invariant list'; SKILL.md:52 and commands/adversarial-review.md:45 require the map before the first spawn. adversarial-loop.js untouched
  - log: 2026-08-29T21:03:37Z @kj closed
- [x] `DEF-ADVR-50` **FANOUT_STOP fires on a converging confirm - fanout is structural on a pinned round and any ordered change counts as refining** - MAJOR; On a pinned confirm round pinFilter admits only findings inside the applied delta or citing a closure, so every surviving finding traces to the loop's own fixes and fanout is n/n by construction whenever any finding exists. The only remaining discriminator (adversarial-loop.js:370-372, highFanoutStreak advances on fanout > 0.5 && refining, refining = any change or revert ordered) treats a one-line MINOR wording edit the same as re-modelling a pass, so two confirm rounds that each find one MINOR exit FANOUT_STOP with instructions to revert every applied mechanism. Session 3301e203 (plugin 1.7.14, constructed loop, runs wf_72207f8f wf_77e10307 wf_6c4ec364): findings 21 -> 3 -> 3 -> 3, fanout 0/21, 2/3, 3/3, 3/3; round 2 ordered 0 changes (streak 0), round 3 one MAJOR plus two MINOR with 2 changes (streak 1), round 4 three MINOR with 1 change - a refusal-message wording edit (streak 2) -> FANOUT_STOP naming both applied plans as reverts, each of which re-opens a MAJOR the adjudicator had confirmed. The run converged - max severity fell from MAJOR to MINOR, no new mechanism was added, the delta shrank - and the stop read it as the wf_a1812379 spiral. 1.85M tokens over 20 agents in 61 min and no SHIP reachable: with cleanRequired 2 a confirm round that finds one MINOR both resets the clean streak and advances the fanout streak. The bound must stay - the stop exists to end a spiral and maxRounds remains the unconditional cap; what is missing is a convergence test that tells a descending round from a spiralling one
  - evidence: adversarial-loop.js gates FANOUT_STOP on spiralStreak (adj.trajectory === 'spiralling' && refining) with trajectory and trajectoryReason required in ADJUDICATION_SCHEMA, the prompt naming the judgment and adjudicator.md step 8 defining it; loop-spec invariant 5 rewritten; tests/test_adversarial_workflow_script.py 23 passed; full suite 1267 passed 2 skipped; ACC-REVIEW-49 re-closed on the new gate
  - test-tags: UNIT
  - related: DEF-ADVR-46, DEF-ADVR-42, DEF-ADVR-45
  - repro: Run the loop with cleanRequired 2 on any change set; apply the round-1 PLAN; run the pinned confirm twice so that each returns one MINOR the adjudicator orders a one-line change for; the second confirm exits FANOUT_STOP with reverts naming every applied change
  - root-cause: 2026-09-02T01:30:33Z @kj fanout measures where findings sit, which on a pinned confirm is always the delta; refining measures whether anything was ordered, not whether the ordered work is shrinking; neither reads severity or count trend, so DEF-ADVR-46 (clean-round case) left every non-clean confirm indistinguishable from a spiral
  - log: 2026-09-02T01:30:33Z @kj added
  - log: 2026-09-02T01:30:42Z @kj candidate mechanisms, none decided, each keeping maxRounds as the unconditional bound: (a) count a round toward highFanoutStreak only when an ordered change answers a material MAJOR or CRITICAL - a MINOR-only refining round is convergence, not spiral; (b) descent test - a refining round counts only when its finding set is not strictly lower than the previous round by max severity then count; (c) a MINOR-only plan on a confirm round exits as a terminal PLAN that needs no re-confirm, so a wording edit never buys another round
  - log: 2026-09-02T05:36:39Z @kj the three hard candidates above are REJECTED by the Star Colonel - the criterion must be generative, not a script threshold on severity or count. Direction under discussion: the adjudicator, which already sees the full ruling history, judges the trajectory itself in one schema field (converging or spiralling, with its reason) and the script fires FANOUT_STOP only on two consecutive spiralling judgments; fanoutTraced/fanoutTotal stays as evidence the adjudicator cites, not as the gate. maxRounds remains the unconditional bound. Not decided
  - log: 2026-09-02T06:17:20Z @kj edited test-tags (added)
  - log: 2026-09-02T06:17:20Z @kj closed
  - log: 2026-09-02T06:52:39Z @kj survived the architect + bug-hunter loop constructed from the updated spec (wf_812326e5-afd round 1: 8 findings, 1 MAJOR, PLAN with 2 changes, converging; wf_5c7c86a1-d53 rounds 2-3: adjudicated clean twice, converging, SHIP). The round-1 MAJOR was this fix's own leftover - the advisory 'fanout above 0.5 ... veto at PLAN or revert by hand' log line and the ratio const still steered the operator by the removed ratio; deleted with its two test pins. The new gate ran live: three adjudications each carried trajectory + reason, spiralStreak stayed 0
- [ ] `DEF-ADVR-52` **loop-spec status list omits PANEL_DIED** - MINOR; references/loop-spec.md line 60 lists the loop statuses as PLAN, SHIP, STOP, FANOUT_STOP, ROUND_CAP and ADJUDICATOR_DIED; adversarial-loop.js also returns PANEL_DIED (every reviewer in a panel died - the round reviewed nothing) and tests/test_adversarial_workflow_script.py pins it, so a loop constructed from the spec's status list omits the dead-panel status. Pre-existing since the DEF-ADVR-47 fix; surfaced by the round-1 review of DEF-ADVR-50 (wf_812326e5-afd) and deferred there as outside that fix
  - repro: grep -n PANEL_DIED plugins/devils-advocate/skills/adversarial-review/references/loop-spec.md returns nothing; grep -n PANEL_DIED plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js returns two return sites
  - log: 2026-09-02T06:33:55Z @kj added
- [x] `DEF-ADVR-53` **review-tools dossier finds no subcommands on Python 3.12 - the help probe reads only quoted choices** - MAJOR; help_subcommands runs the console script with a probe subcommand and parses argparse's invalid-choice error for the choice list with the regex '([\w-]+)', which needs quotes around each name. Python 3.12.13 prints the list bare - (choose from run, fly) - while 3.11.14 and 3.13.15 print 'run', 'fly', so on 3.12 the probe returns an empty set, the --help fallback never runs, and the dossier reports every console script as defining no subcommands and every advertised command as undefined. CI: test (3.12) red on tests/test_review_tools.py::test_cli_surface_reads_flags_and_help_finds_the_loop_built_subcommand (assert [] == ['fly', 'run']) and ::test_advertised_surface_counts_code_spans_not_prose (assert [] == ['soar']) on release runs 33579299161 (v1.7.15) and 33601564782 (v1.7.16); 3.11 and 3.13 green
  - evidence: help_subcommands splits the choice list on commas and strips quotes, accepting both renderings; tests/test_review_tools.py::test_help_probe_reads_bare_and_quoted_choice_lists feeds a module printing each shape and expects {'run','fly'}; the review-tools file passes 14/14 on a scratch 3.12.13 venv built like CI and on 3.13.15
  - test-tags: UNIT
  - repro: python3.12 -c "import argparse,sys; p=argparse.ArgumentParser(); s=p.add_subparsers(dest='c',required=True); s.add_parser('run'); s.add_parser('fly'); p.parse_args(['x'])" prints (choose from run, fly); on 3.13 the same prints (choose from 'run', 'fly'); review-tools dossier on any package with a console script then lists no subcommands on 3.12
  - root-cause: 2026-09-02T07:10:01Z @kj the choice-list parser assumed argparse's quoted rendering; the interpreter's argparse changed the rendering between patch releases and nothing pinned the bare shape
  - log: 2026-09-02T07:10:01Z @kj added
  - log: 2026-09-02T07:10:01Z @kj edited test-tags (added)
  - log: 2026-09-02T07:10:02Z @kj closed

