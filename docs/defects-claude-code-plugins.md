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

svg-designer skill docs and svg_tools

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

## build tooling `MAKE`

Makefile targets and CI parity

- [x] `DEF-MAKE-28` **make lint ran a floating ruff** - MEDIUM; uvx ruff resolved 0.16.5 with a different rule set and reported 237 findings the project ruff 0.15.8 does not; fix uv run --extra dev ruff, matching ci.yml; Makefile
  - evidence: fixed in commit 1416159; suite 962 green; confirming round CLOSED; round-5 fresh-clone make lint exit 0
  - repro: make lint with uvx resolving a newer ruff
  - test-tags: MANUAL
  - log: 2026-08-28T08:22:14Z @kj added
  - log: 2026-08-28T08:22:14Z @kj closed: fixed

