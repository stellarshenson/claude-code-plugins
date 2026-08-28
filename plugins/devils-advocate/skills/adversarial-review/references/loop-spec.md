# Spec - Adversarial Review Loop Execution

This spec is the plugin's authoritative contract for the loop - it ships with the plugin. With the dynamic Workflow capability, constructing a workflow from this spec IS the execution path; everything else is fallback.

The multi-round adversarial review runs as deterministic code, not as orchestrator judgement. Motivating case (2026-08-28, `jupyterlab_paste_content_as_markdown_extension`): a manual 8-round loop rewrote its target mid-review, never adjudicated, trusted prose verdicts the severity mix contradicted, applied reviewer remedies wholesale, and grew the target 302 → 537 lines before measurement deleted the growth; the user killed round 8. Every invariant below exists because that session lacked it.

## Principle

The protocol is code, the judgement is the model's. With the dynamic Workflow capability present, the model CONSTRUCTS the workflow for the task from this spec - the invariants below are the binding contract every constructed script must encode; the loop shape around them is free. What the model never does is hold the protocol in working memory: an invariant lives in script control flow or it does not exist. A constructed script is checked against the invariant list before it runs; the worked example is the drift baseline.

## Worked example

`../workflows/adversarial-loop.js` (in the library repo: `plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js`, guarded by `tests/test_adversarial_workflow_script.py`) implements this spec in full. Consult it while constructing; for harnesses without dynamic workflow capability it is the supplied protocol - the procedural checklist the fallback follows.

Args contract (target, bar, lenses mandatory - the script throws without them):

| Arg | Meaning |
| --- | --- |
| `target` | what is under review |
| `scope` | in-scope files/dirs and exclusions, prose |
| `bar` | the product bar; findings outside it cap at MINOR |
| `lenses` | adversary names, e.g. `["architect", "bug-hunter"]` |
| `graph` | optional path to a refreshed graphify graph.json - fewer reviewer turns, cause-grouping and radius-bounding for the adjudicator |
| `state` | re-invocation only: the `state` object from the previous `PLAN` return, verbatim |
| `appliedFixes` | re-invocation only: `[{site, summary}]` the main session actually applied |
| `maxRounds` | total reviewer rounds before `ROUND_CAP` (default 6) |
| `cleanRequired` | consecutive clean rounds to exit - no findings, or adjudicated clean (default 2) |

Statuses: `PLAN` (the adjudicated change plan for the main session to apply; carries `state` for the re-invocation), `SHIP`, `STOP` (adjudicator ruling), `FANOUT_STOP`, `ROUND_CAP`, `ADJUDICATOR_DIED`. Every status returns the full round history, findings, closures, deferrals and refutations.

## Execution paths

1. **Dynamic (default)** - the session has the dynamic Workflow capability: the model constructs the workflow from this spec (the worked example is consultable starting material), verifies it against the invariant list, and runs it. A slash-command instruction to do so is legitimate Workflow opt-in
2. **Supplied (no dynamic capability - different harness)** - the worked example is the protocol: a library runner `review-tools loop` executes it by driving `claude -p` subprocesses (spec below, not implemented)
3. **Manual (interim, until the runner ships)** - a harness without dynamic capability follows the worked example stage by stage as a procedural checklist through the skill's rounds protocol; known-weaker, which is what this spec exists to retire

## Fallback runner `review-tools loop` (pending)

- Python, in `stellars_claude_code_plugins.review`; one subcommand: `review-tools loop --target ... --bar ... --lens architect --lens bug-hunter [--test-cmd ...] [--max-rounds 6] [--clean-required 2]`
- Reviewers and adjudicator spawn as `claude -p` with the persona/adjudicator body inlined, `env -u CLAUDECODE`, stdin `/dev/null`, `--no-session-persistence`, structured findings demanded as a fenced JSON block and parsed; `parse_report` is the salvage parser when the block is absent
- The runner never edits the tree either: a non-empty adjudicated plan ends the run with the `PLAN` payload printed for the operator to apply; `--resume` re-enters at the pinned confirm with `--applied` describing the delta
- State checkpoints to `tmp/adv-review/ledger.json` after every stage; `--resume` continues from the last completed stage, so a dead container re-enters mid-loop
- Testing follows the cassette contract in `docs/testing_claude_cassettes.md` - recorded `claude -p` responses replayed in CI, replay mode raising on a missing cassette

## Invariants (every path MUST hold; each maps to a criterion in `docs/acc-crit-claude-code-plugins.md` ACC-REVIEW-44..53)

1. No run without a bar - refuse to start rather than review against "all inputs in the world"
2. The adjudicator rules what blocks - severities are reviewer evidence, never a gate; an empty adjudicated change plan rules the round clean; reviewer prose verdicts are never consumed
3. Every round with findings passes through the adjudicator before any change; a non-empty plan EXITS the workflow as `PLAN` - the main session applies exactly the plan, nothing else. The adjudicator starts fresh each round, so the loop threads its prior record (rulings, refutations, deferrals) into every adjudication
4. Confirming rounds are pinned: closure list plus fix delta is the whole attack surface, never a fresh sweep
5. Exit only on `cleanRequired` consecutive clean confirming rounds, `STOP`, `FANOUT_STOP` (fanout above 0.5 in two consecutive rounds), or `ROUND_CAP`
6. The workflow never edits the tree - no reviewer, adjudicator or other agent inside it writes a file; changes land only between invocations, applied by the main session from the `PLAN` return, and the next invocation's pinned confirm attacks exactly that delta
7. Full history is returned whatever the terminal status - a killed loop still reports what it knew

## Status

| Piece | State |
| --- | --- |
| Worked example + guardrail tests | implemented |
| Verdict-coupling validator in `review-tools findings` (standalone reports) | implemented |
| Contract text (MAJOR blocks, coupling in 11 personas + reference) | implemented |
| Skill/command routing (construct-from-spec default, supplied fallback) | implemented |
| `review-tools loop` fallback runner | spec only |
