# Spec - Managed Adversarial Review Loop

This spec is the plugin's authoritative contract for the loop - it ships with the plugin. With the dynamic Workflow capability, constructing a workflow from this spec IS the execution path; everything else is fallback.

The contract is deliberately small: nine invariants, stated as outcomes. How a constructed workflow reaches those outcomes - its stage graph, its verification patterns, its budgets, its names - is the constructing model's design, and the harness's own workflow practices are expected to be used, not worked around. A spec that fixed the mechanism would make every improvement in agentic-loop engineering unusable here; a spec that fixes only the outcomes stays valid as the harness improves.

Two motivating cases, both 2026-08-28 on `jupyterlab_paste_content_as_markdown_extension`. A manual 8-round loop rewrote its target mid-review, never adjudicated, trusted prose verdicts the severity mix contradicted, applied reviewer remedies wholesale, and grew the target 302 → 537 lines before measurement deleted the growth; the user killed round 8. Then the first scripted loop (wf_a1812379, plugin 1.7.7) rated a `<select>` pasted into a notebook cell MAJOR under an output-only bar, planned a normalisation pass for it, applied the pass inside the workflow, and spent two more rounds (fanout 7/7, then 12/12) and most of a 1.4M-token run refining a pass that answered no real use - the user deleted it in one glance. Every invariant below exists because one of those sessions lacked it.

## Principle

The protocol is code, the judgement is the model's. With the dynamic Workflow capability present, the model CONSTRUCTS the workflow for the task from this spec - the invariants below are the binding contract every constructed script must encode; the loop shape around them is free. What the model never does is hold the protocol in working memory: an invariant lives in script control flow or it does not exist. A constructed script is checked against the invariant list before it runs; the worked example is the drift baseline, not the template.

## Invariants (every path MUST hold; each maps to a criterion in `docs/acc-crit-claude-code-plugins.md` ACC-REVIEW-44..60)

Each invariant names the outcome the script must guarantee. The clause in brackets is how the worked example satisfies it - one way, not the way.

1. No run without a bar, and the bar names the product's purpose, its input universe and its primary path - refuse to start rather than review against "all inputs in the world". An output-only bar ("never fuse two values") is not a bar: it promotes every input in the world into scope. [`args.bar` object with `purpose`, `inputs`, `primaryPath`; the script throws without them]
2. The adjudicator rules what blocks - severities are reviewer evidence, never a gate; an empty adjudicated change plan rules the round clean; reviewer prose verdicts are never consumed. [severity tally is reporting only; `changes.length === 0` is the clean signal]
3. Every round with findings passes through adjudication before any change, and a non-empty plan EXITS the workflow for the main session to apply - exactly the plan, nothing else. Adjudication starts fresh each time, so the loop threads its prior record (rulings, refutations, deferrals) into every adjudication. [`status: 'PLAN'` return carrying `state`; `priorRecord()` in the adjudicator prompt]
4. Confirming rounds are pinned: the closure list plus the applied delta is the whole attack surface, never a fresh sweep - and the script enforces it: a confirming finding that is taste, or sits outside the applied delta without naming a closure it fails or whose change caused it, is discarded before adjudication, logged by title, never silently. [`pinFilter` on `closure` / delta-file membership]
5. The loop exits only on the required number of consecutive clean confirming rounds, an adjudicator `STOP`, a fanout stop, or a round cap. Fanout counts a round only when its adjudication still ordered changes or reverts; a clean round - no findings, or adjudicated clean - is clean whatever its findings' lineage and resets the streak; the stop fires on two consecutive counted rounds with over half the findings in the loop's own fixes. [`cleanRequired`, `FANOUT_STOP`, `ROUND_CAP`, `maxRounds`, `highFanoutStreak`]
6. The workflow never edits the tree - no reviewer, adjudicator or other agent inside it writes a file; changes land only between invocations, applied by the main session from the plan, and the next invocation's pinned confirm attacks exactly that delta. [re-invocation with `state` + `appliedFixes`]
7. Full history is returned whatever the terminal status - a killed loop still reports what it knew. [`history`, `closures`, `deferred`, `refuted` on every return]
8. Materiality before severity - every finding states who is harmed, doing what the product is for, on an input inside the input universe, and marks itself material or not; an immaterial finding is capped by the script at MINOR/out-of-bar whatever its technical truth, and the adjudicator's first step is materiality triage, refuting immaterial findings before verifying anything. Technical truth is not materiality. [`material` + `materiality` in the findings schema; `capImmaterial`; STEP 0 in the adjudicator prompt]
9. Revert before refine - a finding living in code a previous plan introduced is first tested as "remove that mechanism, defer the original finding"; the adjudicator refines only when the original was material. Every planned change says whether it adds a new mechanism (a pass, plugin, branch, helper, guard or data shape); every change flagged `newMechanism` is returned for the main session to veto unless it answers a material CRITICAL or MAJOR; the plan is ranked by materiality within an advisory budget; and every plan and stop payload carries `reverts` so the main session removes machinery deterministically instead of being told to re-model. [`reverts` and `newMechanism` in the adjudication schema; `mechanisms` on `PLAN`; `reverts` on `PLAN`, `STOP`, `FANOUT_STOP`; `maxChanges`]

## Freedom - what the constructing model designs

Everything not named above. In particular, and explicitly encouraged:

- **Stage graph** - the worked example is panel → adjudicate → exit; a constructed loop may `pipeline()` findings through verification as they land, run per-finding adversarial refutation votes (N skeptics, majority kills), use perspective-diverse verifiers (correctness, reproduction, materiality as separate lenses), put a judge panel behind the adjudication, or discover with a loop-until-dry pattern - whatever the harness's workflow guidance offers. The invariants bound the outcomes; they do not name the stages
- **Verification depth** - a finding may be refuted by a cheap skeptic before an expensive reproduction; a materiality vote may precede adjudication as its own stage; the adjudicator may be a synthesis over several independent adjudications
- **Budget and scale** - lens count, verifier count, `effort` and `model` per stage, `budget`-driven scaling, sub-workflows via `workflow()` for the discovery sweep - all free, and the cheapest stage that satisfies an invariant is the right one. Turns are the bill: spend them on the primary path, never on immaterial findings
- **Names and shapes** - argument names, status names, schema field names and return shapes are the worked example's conventions, not the contract; a constructed loop keeps the concepts (bar, closure list, applied delta, plan, reverts, prior record, history) and may name them as it likes, as long as the main session can read the payload it receives
- **Isolation and tooling** - `isolation: 'worktree'` for any stage that needs a scratch tree, custom `agentType`s beyond the plugin's two, MCP tools where the review needs them, a code graph when one exists

What stays fixed is only the list above: a bar with purpose, inputs and primary path; adjudication before change; materiality before severity; revert before refine; pinned confirms filtered by the script; the exit set; no edits from inside the workflow; a plan-exit round-trip through the main session; full history on every return.

## Worked example

`../workflows/adversarial-loop.js` (in the library repo: `plugins/devils-advocate/skills/adversarial-review/workflows/adversarial-loop.js`, guarded by `tests/test_adversarial_workflow_script.py`) implements the nine invariants in the plainest shape. Consult it while constructing - for the invariant mechanics, not for the loop shape; for harnesses without dynamic workflow capability it is the supplied protocol - the procedural checklist the fallback follows.

Its args contract (target, bar, lenses mandatory; the script throws without them and on a bar missing purpose, inputs or primaryPath):

| Arg | Meaning |
| --- | --- |
| `target` | what is under review |
| `scope` | in-scope files/dirs and exclusions, prose |
| `bar` | object: `purpose` (what the product is for, for whom), `inputs` (the input universe), `primaryPath` (the use every CRITICAL/MAJOR sits on); optional `guarantees`, `outOfScope`, `degrade`. Findings outside it cap at MINOR |
| `lenses` | adversary names, e.g. `["architect", "bug-hunter"]` |
| `graph` | optional path to a refreshed graphify graph.json - fewer reviewer turns, cause-grouping and radius-bounding for the adjudicator |
| `state` | re-invocation only: the `state` object from the previous `PLAN` return, verbatim |
| `appliedFixes` | re-invocation only: `[{site, summary, files?}]` the main session actually applied, reverts included, each revert recorded with summary starting `reverted: <mechanism>`; `files` sharpens the confirm filter |
| `maxRounds` | total reviewer rounds before `ROUND_CAP` (default 6) |
| `cleanRequired` | consecutive clean rounds to exit - no findings, or adjudicated clean (default 2) |
| `maxChanges` | advisory plan budget per round (default 3); a longer plan is logged and the main session applies the top entries |

Its statuses: `PLAN` (the adjudicated change plan for the main session to apply - `reverts` first, then `plan`; `mechanisms` lists the changes that add review surface, for veto; carries `state` for the re-invocation), `SHIP`, `STOP` (adjudicator ruling), `FANOUT_STOP`, `ROUND_CAP`, `ADJUDICATOR_DIED`. `STOP` and `FANOUT_STOP` carry `reverts` - the adjudicator's list (`{mechanism, site, dissolves, defers}`), else every applied change in closure shape (`{site, summary, files}`), entries whose summary starts `reverted:` being reverts already applied and skipped - so the main session reverts deterministically. Every status returns the full round history, findings, closures, deferrals and refutations.

## Execution paths

1. **Dynamic (default)** - the session has the dynamic Workflow capability: the model constructs the workflow from this spec using the harness's workflow guidance (the worked example is consultable for invariant mechanics), verifies it against the invariant list, passes it inline, and runs it. A slash-command instruction to do so is legitimate Workflow opt-in. Running the shipped script by path on a harness that has the capability is the fallback route taken by mistake
2. **Supplied (no dynamic capability - different harness)** - the worked example is the protocol: a library runner `review-tools loop` executes it by driving `claude -p` subprocesses (spec below, not implemented)
3. **Manual (interim, until the runner ships)** - a harness without dynamic capability follows the worked example stage by stage as a procedural checklist through the skill's rounds protocol; known-weaker, which is what this spec exists to retire

## Fallback runner `review-tools loop` (pending)

- Python, in `stellars_claude_code_plugins.review`; one subcommand: `review-tools loop --target ... --bar bar.json --lens architect --lens bug-hunter [--test-cmd ...] [--max-rounds 6] [--clean-required 2]`
- Reviewers and adjudicator spawn as `claude -p` with the persona/adjudicator body inlined, `env -u CLAUDECODE`, stdin `/dev/null`, `--no-session-persistence`, structured findings demanded as a fenced JSON block and parsed; `parse_report` is the salvage parser when the block is absent
- The runner never edits the tree either: a non-empty adjudicated plan ends the run with the `PLAN` payload printed for the operator to apply; `--resume` re-enters at the pinned confirm with `--applied` describing the delta
- State checkpoints to `tmp/adv-review/ledger.json` after every stage; `--resume` continues from the last completed stage, so a dead container re-enters mid-loop
- Testing follows the cassette contract in `docs/testing_claude_cassettes.md` - recorded `claude -p` responses replayed in CI, replay mode raising on a missing cassette

## Status

| Piece | State |
| --- | --- |
| Worked example + guardrail tests | implemented |
| Verdict-coupling validator in `review-tools findings` (standalone reports) | implemented |
| Contract text (MAJOR blocks, coupling and materiality in 11 personas + reference) | implemented |
| Skill/command routing (construct-from-spec default, supplied fallback, pinned by test) | implemented |
| `review-tools loop` fallback runner | spec only |
