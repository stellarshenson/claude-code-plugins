# Changelog

One synced version for the library and the seven plugins. Entries summarise; the per-session record is `.claude/JOURNAL.md`.

## [Unreleased]

### Added

- **datascience** - `hypothesis-tools` grows from four read-only queries into the working surface of a hypothesis campaign, shaped by five real ledgers across four projects (docdistance, knowledge-graph-foundry, sci-demographic-collapse, gpu-benchmark - up to 6,432 lines and 554 hypotheses). Parsing: a third declaration shape (a row of an at-a-glance table whose header names claim/verdict columns - one store declares 478 hypotheses of which the previous parser saw 46), and open-vocabulary verdict reading (case, emphasis, dated qualifiers and hyphen variants fold to canonical; a ledger-grown label like `SUPPORTED` is read as written, warned once aggregated; only an unreadable verdict errors) - the five ledgers went from 867 check errors to 18, all on genuinely mixed verdicts. Writes, append-only like the ledger itself: `register` lands a pre-registered hypothesis at the next free ordinal and verifies it parses back - a field name given twice, or one opening with a hypothesis id, is refused before the file is touched, as is any `result` or `field` line no reader would match (a `*` in the label; ACC-HYPTL-119..121), `result` / `verdict` / `log-event` record outcomes (Result immutable - a re-run needs a qualifier; one verdict ever - a flip is a new round). Reporting: `report` renders batches by verdict labels, `values <quantity>` returns every reading of one measured number (`theta(0.08) = 0.7644` off line 4317 of 6,432) so the file is never read end to end (ACC-HYPTL-93..103). Authorship is the `project-management` toolkit's, unchanged, so one handle is one person across a project's ledgers, criteria and defects: a `## Authors` roster written by `hypothesis-tools author`, `--author @xx` required on every write and refused when the handle is not on the roster, and each write appending its own dated `log:` line naming it - registered, result recorded, verdict recorded, field added - so who recorded what survives the session. `field` adds a name the template does not list, or replaces one already recorded with `--update`, keeping the label and its qualifier: the five real ledgers carry hundreds of field names of their own (`Grounding`, `Persona`, `Status`), so `check` never flags an unknown name - it errors only on a log handle nobody is rostered for, and warns once, aggregated, on unauthored lines the ledgers already had; `list --author` names the registrant and never the first writer (ACC-HYPTL-104..109). `check` reads a canonical label followed by scoping prose (`Refuted on the replacement bar;`, `**Refuted** as an order measure (...)`) as that label - the last three errors standing on the two docdistance ledgers - counts unrun hypotheses (neither Result nor Verdict) in its summary line instead of warning once per block, and reports missing fields as one line per field naming the ids. The template declares a batch's shared guardrails once in the batch's opening line rather than in every block
- **project-management** - one registered explanation per item, and it keeps its history: `- mechanism: <stamp> @xx <text>` on a criterion says how it is meant to work, `- root-cause: <stamp> @xx <text>` on a defect says why it happens. A second write puts the new record ABOVE the previous one and keeps it, so on a hunt that runs for days the theory disproved on Tuesday is still readable on Friday and nobody explores that dead end twice; `--update` rewrites the newest record instead, for a rewording of an unchanged theory. The top record is what every query reports, `--grep` and `search` read the superseded ones too, and `--json` carries the whole history under `causes`. Written by `pm-tools mechanism` / `pm-tools root-cause`, or by `add --mechanism` / `add --root-cause` at filing time; refused on the other discipline; never logged, because the record carries its own stamp and author (ACC-PMWHY-82..90)

### Changed

- **repository** - `assets/` is `.resources/` (the README's seven image paths follow), `showcase/` lives under `docs/`, and `logs/`, `experiments/` and `graphify-out/` are untracked and ignored - none of them is part of the package or the plugins
- **project-management** - the record's shared rules (a second write overrides, `--update` replaces, the top record is current, never logged) are stated once in the skill; both discipline references keep only what is specific to them and point at it. The `acc-crit` and `defect` skill and command descriptions now carry a concrete id (`ACC-AUTH-102`, `DEF-LNCH-3`) - the `ACC-<CAT>-<N>` form they used fails the skill frontmatter gate, which refuses angle brackets in a description (ACC-PMWHY-91, -92). The record column's rendered header carries the discipline's own name - `Mechanism` on a criteria file, `Root cause` on a defects file - whatever spelling asked for it
- **all plugins** - no skill or command frontmatter description carries `<` or `>` any more (`dataset-<name>.zip` and `analyze -> draft` were the last two, in `datascience:dataset` and `document-processing:process`); `tests/test_command_skill_parity.py` now pins the rule across every skill and command, because skill-creator's frontmatter gate refuses such descriptions

## [1.7.13] - 2026-08-30

### Fixed

- **all plugins** - the toolchain gate now says how to invoke the CLI it just installed. The gate puts the command on PATH, but in a uv-managed repository the reflex invocation is `uv run <cli>`, which resolves the caller's project first and writes `uv.lock` and `.venv` into it - an edit to the user's tree that no plugin asked for. All 31 gate sites now carry the rule: bare command name, and `uv run --no-project` if uv is used at all, which writes neither file and resolves the same binary (`--no-sync` and `--frozen` still create `.venv`). Two guards in `tests/test_toolchain_gate.py` pin the rule at every gate and fail on any project-scoped `uv run` of a toolkit CLI in the shipped docs

## [1.7.12] - 2026-08-29

### Fixed

- **devils-advocate** - the invariant check a constructed loop must pass now produces an artifact. It used to read "check the script against the invariant list one by one", which leaves nothing behind, so it could be skipped in silence while the shipped worked example carried 22 passing tests - the fallback route was the one that felt provably safe, and a capable session with the dynamic Workflow capability took it. A constructed loop now emits its invariant map before the first spawn: nine lines, `INV-1` .. `INV-9`, each naming the site in its own script that carries that invariant. `adversarial-loop.js` is unchanged - this is a contract change, not a protocol change (DEF-ADVR-48)

### Changed

- **project-management** - soft locking is stated as a default, not offered as a feature. The lock surface shipped complete in 1.7.10 and nobody reached for it, because the docs described what a lock is instead of saying when to take one. Every procedure that writes to an item now says lock before the first write and release when you stop, `review` included - it touches items in bulk and previously said nothing about locking at all (ACC-PMLOCK-81)

## [1.7.11] - 2026-08-29

### Fixed

- **devils-advocate** - a round whose whole reviewer panel died is no longer read as a clean review. `mergeFindings` mapped a null agent return to an empty findings list, so a round in which every reviewer errored produced no findings, skipped adjudication entirely and exited `SHIP` - the loop reporting a clean review it never performed. Observed live as a 3-agent, 3-errored, 82ms run returning `SHIP`. Every panel call now routes through a checked wrapper and a whole-panel death exits `PANEL_DIED` carrying full history (DEF-ADVR-47, ACC-REVIEW-80)

## [1.7.10] - 2026-08-29

### Added

- **all plugins** - every command procedure is now also a callable skill. 27 of 42 commands had no same-named skill, so an agent could not invoke through the Skill tool what a user can type as `/plugin:name`. Each command body moved verbatim into `skills/<name>/SKILL.md` and the command became a router that points at it, giving one procedure and two surfaces; plugin skills went 27 to 54. `tests/test_command_skill_parity.py` pins parity, addressability and routing across all 42
- **devils-advocate** - `adversaries/ai-engineer.md`, a vendor-neutral lens on the instruction layer that steers AI assistants (skills, agent prompts, instruction files, tool and MCP descriptions, workflow scripts, context layout), judged against open standards and published paradigms rather than one vendor's practice
- **devils-advocate** - `references/agentic-engineering-canon.md`, the adversary's evidence base: 93 source URLs, every entry quote-verified against fetched bytes
- **devils-advocate** - `references/code-graph-instrument.md`, describing what a code-graph index offers a reviewer without pinning a command surface
- **project-management** - work-in-progress soft locks on acceptance criteria and defects: `pm-tools lock` / `unlock`, a `- lock: <until> @xx` line, warnings (never refusals) when writing to an item someone else holds, automatic expiry on the next write, `--locked` / `--locked-by` filters, a `lock` field and a `Worked on` count in reports
- `CHANGELOG.md` itself

### Changed

- **devils-advocate** - the adversarial-review skill, its spec, agent prompts and command are restructured per Anthropic's context-engineering guidance for Claude 5-generation models: the nine loop invariants are stated once (`references/loop-spec.md`) with pointers from SKILL.md, the README and the command; the adjudicator's and reviewer's method lives in their agent files and the workflow script passes data only; SKILL.md is a lightweight guide with the manual rounds protocol and remedy discipline moved to `references/`; incident narratives kept in the spec alone. Reference: [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) - one placement per rule, outcomes over guardrails, progressive disclosure, code over prose
- **devils-advocate** - no tool command surface is pinned anywhere in the plugin. An instrument reaches an agent as data - what exists, where - never as a written invocation, because a spelled-out command pins an API that moves; `test_instrument_threaded_as_data_never_prescribed` fails if one returns

### Fixed

- **tests** - the toolchain-gate guard no longer reads its reference gate block from one named file, and its CLI-name scan ignores YAML frontmatter, so a router that merely names a CLI in its menu description is not required to carry a network upgrade
- **devils-advocate** - invariant 7 (full history on every return) is now true and guarded. `closures` was absent from four of the five returns and `ADJUDICATOR_DIED`, the killed-loop case the invariant names, carried neither `deferred` nor `refuted`; every exit now returns all four
- **devils-advocate** - `ai-engineer` gained a MEDIUM severity, an activation-and-trigger-surface axis, and a deletion axis that scores always-loaded bytes separately from activation-time prose - all three from its first real outing
- **devils-advocate** - two method rules stated in both the workflow script and the agent files were removed from the script, which loads those agent files by `agentType`

## [1.7.9] - 2026-08-29

### Changed

- **devils-advocate** - managed adversarial review: materiality before severity (bar object with purpose, input universe and primary path; `material` on every finding; immaterial findings capped by the script; adjudicator triages materiality first), revert before refine (`reverts` and `newMechanism` in every plan; reverts carried by `PLAN`, `STOP` and `FANOUT_STOP`), script-enforced confirm-round scope, fanout counted only on refining rounds, `loop-spec.md` restated as outcome invariants with a Freedom section, construct-from-spec routing pinned by test

### Fixed

- DEF-ADVR-40..43 and 46 - the failure modes of the first scripted review loop (immaterial findings admitted as MAJOR, remedies enlarged into machinery, fanout refined instead of reverted, confirming rounds sweeping, a clean round exiting `FANOUT_STOP`)

## [1.7.8] - 2026-08-28

### Changed

- **devils-advocate** - the plugin owns and ships the loop spec; the workflow never edits the tree (`PLAN` exit, the main session applies, the next invocation confirms the delta); the adjudicator rules what blocks with its prior record threaded into every round; graphify graph threaded into reviewer and adjudicator prompts

## [1.7.7] - 2026-08-28

### Changed

- **devils-advocate** - first scripted adversarial-review loop; verdict coupling (DO-NOT-SHIP iff any CRITICAL or MAJOR) validated by `review-tools findings`
