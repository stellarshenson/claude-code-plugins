# Changelog

One synced version for the library and the seven plugins. Entries summarise; the per-session record is `.claude/JOURNAL.md`.

## [Unreleased]

### Changed

- **devils-advocate** - the adversarial-review skill, its spec, agent prompts and command are restructured per Anthropic's context-engineering guidance for Claude 5-generation models: the nine loop invariants are stated once (`references/loop-spec.md`) with pointers from SKILL.md, the README and the command; the adjudicator's and reviewer's method lives in their agent files and the workflow script passes data only; SKILL.md is a lightweight guide with the manual rounds protocol and remedy discipline moved to `references/`; incident narratives kept in the spec alone. Reference: [The new rules of context engineering for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) - one placement per rule, outcomes over guardrails, progressive disclosure, code over prose
- **project-management** - work-in-progress soft locks on acceptance criteria and defects: `pm-tools lock` / `unlock`, a `- lock: <until> @xx` line, warnings (never refusals) when writing to an item someone else holds, automatic expiry on the next write, `--locked` / `--locked-by` filters, a `lock` field and a `Worked on` count in reports

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
