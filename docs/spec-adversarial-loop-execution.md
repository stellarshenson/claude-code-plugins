# Spec - Adversarial Review Loop Execution

The multi-round adversarial review runs as deterministic code, not as orchestrator judgement. Motivating case (2026-08-28, `jupyterlab_paste_content_as_markdown_extension`): a manual 8-round loop rewrote its target mid-review, never adjudicated, trusted prose verdicts the severity mix contradicted, applied reviewer remedies wholesale, and grew the target 302 → 537 lines before measurement deleted the growth; the user killed round 8. Every invariant below exists because that session lacked it.

## Principle

The protocol is code, the judgement is arguments. The orchestrating model decides WHAT to review (target, scope, bar, lenses, test command); it never authors or improvises the loop's control flow. A generated-per-task script would reintroduce the drift channel this design closes.

## Canonical script

`plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js` - shipped, versioned, guarded by `tests/test_adversarial_workflow_script.py`.

Args contract (target, bar, lenses mandatory - the script throws without them):

| Arg | Meaning |
| --- | --- |
| `target` | what is under review |
| `scope` | in-scope files/dirs and exclusions, prose |
| `bar` | the product bar; findings outside it cap at MINOR |
| `lenses` | adversary names, e.g. `["architect", "bug-hunter"]` |
| `testCmd` | command the fixer keeps green (optional) |
| `maxRounds` | total reviewer rounds before `ROUND_CAP` (default 6) |
| `cleanRequired` | consecutive clean confirming rounds to exit (default 2) |

Terminal statuses: `SHIP`, `STOP` (adjudicator ruling), `FANOUT_STOP`, `ROUND_CAP`, `FIX_FAILED`, `ADJUDICATOR_DIED`. Every status returns the full round history, open findings, fixes, deferrals and refutations.

## Execution paths

1. **Stock (present)** - the session has the dynamic Workflow tool: invoke the shipped script via `Workflow({scriptPath: <plugin path>/workflows/adversarial-loop.js, args: {...}})`. A slash-command instruction to do so is legitimate Workflow opt-in
2. **Fallback (spec only, not implemented)** - the session lacks the Workflow tool: a library runner `review-tools loop` executes the SAME protocol by driving `claude -p` subprocesses
3. **Manual (interim fallback)** - until the runner ships, sessions without the Workflow tool follow the skill's rounds protocol by hand; known-weaker, which is what this spec exists to retire

## Fallback runner `review-tools loop` (pending)

- Python, in `stellars_claude_code_plugins.review`; one subcommand: `review-tools loop --target ... --bar ... --lens architect --lens bug-hunter [--test-cmd ...] [--max-rounds 6] [--clean-required 2]`
- Reviewers and adjudicator spawn as `claude -p` with the persona/adjudicator body inlined, `env -u CLAUDECODE`, stdin `/dev/null`, `--no-session-persistence`, structured findings demanded as a fenced JSON block and parsed; `parse_report` is the salvage parser when the block is absent
- The fixer spawns as `claude -p --dangerously-skip-permissions` restricted by prompt to the adjudicated plan; the runner re-runs `--test-cmd` itself after the fixer returns and does not trust the fixer's own report
- State checkpoints to `tmp/adv-review/ledger.json` after every stage; `--resume` continues from the last completed stage, so a dead container re-enters mid-loop
- Testing follows the cassette contract in `docs/testing_claude_cassettes.md` - recorded `claude -p` responses replayed in CI, replay mode raising on a missing cassette

## Invariants (both paths MUST hold; each maps to a criterion in `docs/acc-crit-claude-code-plugins.md` ACC-REVIEW-44..53)

1. No run without a bar - refuse to start rather than review against "all inputs in the world"
2. Verdict computed from severities - blocking iff any CRITICAL or MAJOR; reviewer prose verdicts are never consumed
3. Every round with blocking findings passes through the adjudicator before any fix; the fixer receives only the adjudicated plan
4. Confirming rounds are pinned: closure list plus fix delta is the whole attack surface, never a fresh sweep
5. Exit only on `cleanRequired` consecutive clean confirming rounds, `STOP`, `FANOUT_STOP` (fanout above 0.5 in two consecutive rounds), or `ROUND_CAP`
6. The target is not edited while a review round is in flight; fixes land only in the Fix stage
7. Full history is returned whatever the terminal status - a killed loop still reports what it knew

## Status

| Piece | State |
| --- | --- |
| Canonical script + guardrail tests | implemented |
| Verdict-coupling validator in `review-tools findings` | implemented |
| Contract text (MAJOR blocks, coupling in 11 personas + reference) | implemented |
| Skill/command routing to the stock path | implemented |
| `review-tools loop` fallback runner | spec only |
