---
name: adversarial-review
description: Hostile, independent review - spawn fresh context-free reviewer subagents that try to BREAK a change. Two modes - diff bug-hunt (no tools, inline diff) and whole-repo audit (tools on - slop, brittle design, hardcodings, config drift, broken SoC). Expert adversaries seed the lens - architect, bug-hunter, qa-engineer, analyst, ux-designer, tui, data-scientist, methodologist, popular-science, devops, slop-hunter. Multi-round - find, fix, re-confirm. Use before a risky commit/merge, a UI or terminal-UI ship, a shell installer, trusting an experiment's verdicts or a green test suite, signing off a spec, or publishing docs. Triggers - "adversarial review", "red-team this", "find bugs in my change", "review before ship", "audit the architecture", "UX review", "TUI review", "shell review", "methodology review", "can this test fail", "review my tests", "readability review", "review my README/docs", "deployment review", "review my spec", "acceptance criteria review", "find gaps in the spec", "does the code match the spec", "hunt dead weight", "what can I delete", "is this over-engineered / bloated", "cut the bloat / slop", "find unnecessary code / tests / comments", "de-slop this", "check for fabricated citations".
---

# Adversarial Review

Spawn a hostile reviewer with no attachment to the code - a second model catches what the author rationalises away. Two modes; run the one that fits the risk, or both:

- **Mode 1 - diff bug-hunt** - no tools, inline diff, one turn. Bugs, logic errors, security holes, broken edge cases IN a specific change
- **Mode 2 - architecture & quality audit** - tools ON, whole-repo, many turns. Systemic rot a diff cannot show; the finding is usually a RELATIONSHIP across files

Mode = HOW (inline diff vs whole-repo, tools off/on). Adversary = WHO (the expert lens). They compose freely. Multi-round always: one pass is a smoke test, not a verdict.

**The reviewer must not inherit your context** - one that read the author's reasoning reviews the case for the change, not the change. A subagent starts context-free like a `claude -p` process; the leak channel is the prompt you write:

- Write every prompt as a `claude -p` command line - target, scope, locked decisions. Never your reasoning, what you ruled out, or what an earlier round concluded
- Default spawn is the plugin subagent, one per lens - visible under the user's prompt, interruptible
- `claude -p` only for what a subagent cannot do - genuinely deny tools (Mode 1), pin a model. Mechanics and gotchas: `references/spawn-mechanics.md`

## Toolchain gate (MANDATORY - before any `review-tools` call)

The three `review-tools` commands ship in the library; run this first, every session, before the first of them. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
OLDER=$(printf '%s\n%s\n' "$LIB" "$PLUG" | sort -V | head -1)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && [ "$OLDER" = "$LIB" ] && { echo "STALE: library $LIB older than plugin $PLUG - refusing to run on an outdated CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags are unverified. Report the line and stop; do not work around it.

## When to use

- Non-trivial feature or fix, before commit/merge; a goal that requires "survived adversarial review"
- Risky logic (auth, money, migrations, concurrency, deletion, permissions) → Mode 1, + Mode 2 if it touches structure
- New config, env, labels, routes, components, cross-service boundaries → Mode 2
- Not for trivial mechanical edits - spawn cost exceeds the value

## Register the review as a task (before the first spawn)

`TaskCreate` before round 1, `TaskUpdate` through the loop - untracked, the re-confirm round silently never runs. One task per review, not per lens; description carries adversary, mode, scope, round, findings location so a cold session resumes it. `completed` only on a clean confirming round. One task per confirmed finding when fixes exceed a single edit.

## Workflow execution - the default multi-round path

Session has the dynamic Workflow tool → do not drive the loop by hand. **Construct the workflow for the task from the spec (`references/loop-spec.md`)** - the spec's nine invariants (a bar naming purpose, input universe and primary path; blocking ruled by the adjudicator, never a severity gate - an empty adjudicated plan rules the round clean; adjudication before any change with the loop's prior record threaded into each fresh adjudicator spawn; pinned confirming rounds attacking each applied delta, with out-of-delta and taste findings discarded by the script; the clean-streak/STOP/FANOUT_STOP/ROUND_CAP exits; the workflow never edits the tree - a non-empty plan EXITS as status PLAN for the main session to apply; full history on every exit; materiality before severity - an immaterial finding is capped at MINOR and the adjudicator triages materiality first; revert before refine - loop-introduced machinery is removed, not polished, and every plan carries `reverts` and `newMechanism` flags) are the contract your script MUST encode; the loop shape around them (lens count, extra stages, budget scaling) is yours to fit to the task. A hand-driven loop loses the protocol to compaction and eagerness - an 8-round manual loop on record rewrote its target mid-review, never spawned the adjudicator and obeyed inflated prose verdicts - so the invariants live in the script's control flow, never in your working memory.

- **Spec (we own it, it ships here)** - `references/loop-spec.md`: invariants, args contract, statuses. Constructing a workflow from this spec IS the dynamic execution path
- **Design the loop with the harness's own workflow practices** - the spec fixes nine outcomes, nothing else: stage graph, per-finding refutation votes, perspective-diverse verifiers, judge panels, `pipeline()` over findings, budget scaling, effort and model per stage, names and payload shapes are yours. A constructed loop that copies the worked example's shape is allowed; one that improves on it is the point
- **Worked example** - `${CLAUDE_PLUGIN_ROOT}/skills/adversarial-review/workflows/adversarial-loop.js` implements the spec in its plainest shape; consult it for the invariant mechanics, not the loop shape. Before running a constructed script, check it against the invariant list one by one - a dropped invariant is the drift this design exists to close
- **This instruction is the Workflow opt-in** - invoking this skill or its command licenses the call
- **`bar` is mandatory, an object, and yours to write** - `purpose` (what the product is for, for whom), `inputs` (the input universe - what a user actually feeds it), `primaryPath` (the use every CRITICAL/MAJOR must sit on); optional `guarantees`, `outOfScope`, `degrade`. Confirm it with the user in one line before the first spawn. The script refuses a bar missing any of the three: an output-only bar ("never fuse two values") promotes every input in the world into scope - on record it turned a `<select>` nobody pastes into a MAJOR, a normalisation pass and 1.4M tokens. Out-of-bar findings cap at MINOR
- **Materiality before severity** - every finding answers who is harmed, doing what the product is for, on an in-universe input; `material=false` is capped by the script at MINOR/outOfBar whatever the reproduction showed, and the adjudicator's step 0 refutes immaterial findings before verifying anything. Ask it yourself when you read a plan: is this really an issue for this product, or a true fact about an input it is not for?
- **Revert before refine** - a finding on code the loop itself introduced is first tested as "remove the mechanism, defer the original"; refinement only when the original was material. Contested semantics (two rounds of conflicting findings on one loop-introduced site) are always a revert. `PLAN`, `STOP` and `FANOUT_STOP` carry `reverts`; apply them before `plan`
- **Statuses** - `PLAN` (apply in the main session first `reverts`, then the plan - exact changes, smallest radius, nothing else; read `mechanisms` first and veto any that does not answer a material CRITICAL/MAJOR; run the tests, then re-invoke with `args.state` from the return plus `args.appliedFixes` with `files` per fix; the next round is a pinned confirm attacking exactly that delta), `SHIP`, `STOP` (adjudicator: loop is generating its own work - re-model), `FANOUT_STOP`, `ROUND_CAP`. Every status returns round history, findings, closures, deferrals, refutations - relay them. `STOP`/`FANOUT_STOP`/`ROUND_CAP` are user decision points, never a licence to loop again by hand
- **The workflow never edits your tree** - it reviews and adjudicates; changes land only between invocations, applied by the main session from the `PLAN` return, visible and interruptible. That is the regression protection the old in-workflow fixer lacked: every applied batch is hostile-reviewed and adjudicated before the loop can close
- **Graph first - ask if absent** - a refreshed graphify graph (`graphify update`, AST-only, seconds) passed as `args.graph` cuts reviewer turns (one `graphify affected` call replaces a dozen greps - turns are the token bill) and lets the adjudicator group findings by shared cause and bound each change's radius, which is what keeps plans small and fixes clean. No graph in the repo → ASK the user whether to build one (`/graphify` - LLM-billed, their call) before the discovery round; never build it unasked

**No dynamic Workflow capability (different harness)** → the supplied workflow is the protocol: execute `workflows/adversarial-loop.js` stage by stage as the procedural checklist (its control flow is the round order, gates and exit conditions), holding every invariant yourself via the manual rounds protocol below. The `review-tools loop` runner specified in the execution spec will own this path once built.

## Never gate a Stop hook on "survived adversarial review"

A hostile reviewer on freshly written remedy code near-never returns clean, so a Stop hook (or goal) that opens only on a clean verdict, driving an obedient fixer, is an unbounded loop by construction. Legitimate terminal states are exactly two: the configured consecutive clean confirming rounds, or an adjudicator `STOP`/`FANOUT_STOP` put to the user. A gate must accept both.

## The rounds protocol (manual fallback - only without the Workflow tool)

Lesson on record: a de-hardcode audit passed a no-tools review clean, yet a whole-repo pass found a hardcoded label-key fallback duplicating a Dockerfile ENV - and the fix needed a SECOND pass to prove it gone.

1. **Round 1 - find.** Run the reviewer, capture findings
2. **Triage.** Confirm each finding against the code yourself - context-free reviewers raise false positives. Keep the real ones
3. **Fix** the confirmed findings
4. **Round 2 - re-confirm.** SAME review, PINNED to the fixes and touched files - never a fresh sweep (unpinned Mode 2 samples different ground each round, so "new findings" means it looked elsewhere). Two jobs, demand both in the prompt: reproduce each closed finding (a reviewer accepting the author's account cannot catch a fix wrong in a new way), and attack what the fix broke. Seed with fix-round shapes - partial conversion, borrowed defaults, sibling left behind, Nth weaker copy - and the question under them all: what did the old code fail at, and who silently relied on that failure? Full recipe: `references/regression-patterns.md`
5. **Loop until a full pass is clean.** Routine = 2-3 rounds. Past 3, adjudicate before spawning another reviewer - round inflation is the symptom of oversized remedies. High stakes: two consecutive clean passes. Never flip a "survived review" criterion on the round that still had findings

**Perspective-diverse panel (high stakes)** - one distinct lens each, concurrent; diversity catches what redundancy cannot. A finding is real when you confirm it, not by vote. **Cap the panel at 3** unless the user asks for more - triage, not the spawn, is the bottleneck; five lenses buy a half-abandoned backlog, which is how a real finding ships with the noise.

**Caller named no adversary → ASK.** State the inferred target, list fitting candidates, recommend one, wait. The wrong lens returns a fluent review of a risk the target does not have - worse than none, because it reads like assurance.

## Remedy discipline

Oversized remedies turn a review into 1 fix → 2 defects → 3 fixes → 6 defects: every remedy is new review surface, so fixing wide pushes the branching factor above one. The growth comes from the remedies, not the findings.

- **Conservative, surgical, strategic** - smallest impact radius that removes the defect at its origin, stated at diff scale. Small and shallow is not the goal; small and terminal is
- **Surface the opportunity, never mandate the shape** - the implementor chooses
- **No unmeasured machinery** - a remedy adding a cap, guard, knob or normalisation pass must name the input that makes it necessary and the measurement showing the unguarded cost; absent both, measure-first or delete-the-need, never the guard. On record: three size ceilings added as remedies fed three rounds of findings about their own bounds before a benchmark showed removing all of them cost 1.4 s on a deliberately pathological input - 235 lines deleted
- **Say when the small fix would paper over** - advising wider needs evidence: the property the narrow fix cannot reach, the narrow fix tried, why it failed. Untried alternative is not evidence
- **Materiality first** - a remedy answers a finding that harms a user on the product's primary path with an in-universe input; a true defect on an input the product is not for gets a `NONE` materiality line and no remedy. A remedy that adds a new pass, plugin, branch, helper or data shape is named NEW MECHANISM and enters a plan only for a material CRITICAL/MAJOR
- **Only load-bearing findings block** - false claim, nonexistent command/flag, unexecutable instruction, surviving mutant, broken behaviour. Word count, structure, duplication, phrasing = `MINOR (taste)`: advisory, declined with one line, never re-litigated

## Adjudicate before you fix

Findings are input to a decision, not a work order. Spawn `devils-advocate:adjudicator` with every lens's findings → ONE change plan: verified, grouped by root cause, smallest change per group, radius, what each could break, what is deferred. It plans, never edits.

- **Materiality triage is its step 0** - immaterial findings are refuted before any verification is spent; pass the bar so it can test them
- **Revert before refine** - findings on loop-introduced code are ruled as reverts (mechanism, dissolved findings, deferred originals) unless the original was material; its plan flags `newMechanism` and stays inside the per-round budget (default 3)
- **Always for a panel** - three lenses reporting one defect is one item
- **Merge reports first** - `review-tools findings <lens>.md ... [--full]` joins VERDICT lines and severity bullets into one table keyed by `file:line` (same file within 25 lines = one row); `--full` keeps original bullets for the remedies
- **Always past round 3** - by then the findings are usually the previous round's fixes; its `STOP` ruling is the honest outcome
- **Pass what you know** - graph, blast radius, locked decisions, previous round's findings and fixes. Supplied context outranks its inference
- **Skip** for a single lens with one or two findings you can verify yourself

## Mode 1 - diff bug-hunt (no tools, inline diff)

Spawn `devils-advocate:adversarial-reviewer` with the diff pasted INTO the prompt, instructed to review only that. Tools-off is an INSTRUCTION on this path - the agent still holds `Read`/`Grep`; when a reviewer that provably cannot wander is the point, use the `claude -p` fallback (`references/spawn-mechanics.md`). Template: `examples/mode1-diff-prompt.txt`.

## Mode 2 - architecture & quality audit (tools ON, whole-repo)

Spawn `devils-advocate:adversarial-reviewer` naming the lens, in-scope dirs and exclusions - it carries `Read`/`Grep`/`Glob`/`Bash`, no turn cap. Panel = one spawn per lens in a single message. Template: `examples/mode2-audit-prompt.txt`. `claude -p` fallback: `references/spawn-mechanics.md`.

- **Tools ON is the whole difference** - the reviewer greps the repo, reads call sites, judges the relationship; without tools it sees only what you paste, exactly where these bugs hide
- **Scope by instruction, not diff** - name in-scope and excluded dirs (tests, vendored, generated)
- **Refresh the code graph, hand it over** - `tmp/graphify-out/graph.json` present → run AST-only `graphify update` (seconds, no tokens) so reviewers read a graph matching HEAD; say so in the prompt. One `graphify affected "<symbol>()"` call replaces a dozen greps and prices severity by blast radius. Building a graph where none exists is your call (LLM-billed), never the reviewer's
- **Dossier for DISCOVERY reviewers only - never a confirming round.** A pinned confirming round needs no inventory (its attack surface is the closure list and fix delta); the one A/B on record measured a pasted dossier there at +52% tokens for fewer findings. `review-tools dossier <src dirs> --plugins <plugin docs> --graph tmp/graphify-out/graph.json --out /tmp/dossier.md` (seconds, AST only) writes the inventory a discovery reviewer otherwise spends its first 40-60 turns rediscovering - symbol index, argparse surface vs documented subcommands, risky primitives as `file:line`, repeated literals, most-called symbols. Paste under `DOSSIER:`, tell the reviewer it is the inventory
- **Turns are the cost, not files** - a reviewer re-reads its whole transcript every turn, so cost grows with turns squared; a 100-turn review bills ~10M cached tokens. Tight scope + the graph converges in a third of the turns
- **Name the smell classes** - vague "review the architecture" gets a vague answer; the template enumerates them and demands file:line evidence. Only executable use counts as a violation, never a comment/docstring literal

## Adversaries - pluggable expert lenses

One self-contained persona prompt per expert in `adversaries/*.md` - role + methodology + output contract. The `lens:` frontmatter is the authoritative summary; the table is the index.

### Signal standard (every adversary)

- **VERDICT** first line, always - `VERDICT: SHIP (<n> findings)` or `VERDICT: DO-NOT-SHIP (<n> findings)` + half-sentence why
- **SEVERITY** per finding - exactly `[CRITICAL|MAJOR|MINOR]`; taste = MINOR tagged `(taste)`
- **REMEDY** per finding - smallest impact radius at diff scale; a wider remedy is an opportunity stated with evidence, never a mandate. Per **Remedy discipline**
- **Coupling** - `DO-NOT-SHIP` iff any finding is CRITICAL or MAJOR; otherwise `SHIP`. The verdict is a pure function of the severity mix - `review-tools findings` recomputes and flags a disagreeing verdict line

Canonical contract: `references/authoring-an-adversary.md`.

| Adversary | Catches | Mode |
| --- | --- | --- |
| `architect` | architecture, consistency, hardcodings & config drift, SoC, leaky abstractions, advertised-surface-vs-reality; over-engineering & dead weight as primary axis, under a proportionality rule binding its own fixes | 2 |
| `bug-hunter` | runtime bugs in shell/installers/startup - quoting, `set -e`, fresh-vs-restart asymmetry, cross-platform parity, secrets hygiene, lifecycle races | 2 |
| `qa-engineer` | test STRATEGY - risk-based coverage, confidence ladder, can-each-test-fail, regression pinning, test slop to DELETE, harness fitness | 2 |
| `ux-designer` | friction & intent, visual hierarchy, focus, motion comfort, accessibility, desktop/mobile parity, edge states | 2 |
| `tui` | Textual/Rich internals - chrome duplication, mis-wired widgets, key propagation, focus & highlight, truecolor, headless-render verification | 2 |
| `data-scientist` | hypothesis formulation, refutation protocol, reproducibility from the doc alone, test power, leakage, metric validity, sensitivity | 2 |
| `methodologist` | scientific-METHOD integrity - can the test fail, verdict ladder spans outcomes, pre-registration honoured, can the control move | 2 |
| `popular-science` | readability for a curious generalist - jargon, unsourced claims, buried lede, pace, visuals vs best-in-class figures, the ending, simplification that broke the truth. Reviews against the `datascience` plugin craft canon | 1 |
| `devops` | containers & deploy - Dockerfile hygiene, layer cache, secrets in layers, root runtime, PID-1 signals, probes, pipeline gates, env drift | 2 |
| `analyst` | specs & acceptance criteria - coverage gaps, missing edge-case fanout, unverifiable criteria, sibling silos, spec-vs-code widows & orphans, gold plating | 2 |
| `slop-hunter` | dead weight across the whole tree - dead code, YAGNI abstractions, vanity tests, comment/doc over-prose, unused deps; AI-slop tells & fabrication. Remedy = delete, gated by a load-bearing check | 2 |

**Boundaries** (so a panel does not return one finding three times):

- `tui` judges what the framework does; `ux-designer` what the user perceives
- `bug-hunter` finds the bug; `qa-engineer` judges why the suite missed it; `methodologist` judges an experiment's verdict ladder, never a software suite
- `devops` owns image and pipeline; `bug-hunter` owns the script inside them
- Spec says nothing about it → `analyst`; spec says it, tests miss it → `qa-engineer`; code contradicts its own conventions → `architect`. Two *specs* diverging → `analyst`; two *implementations* → `architect`; how the divergence feels → `ux-designer`
- Slop: `architect` judges whether a *design* is proportionate ("is this structure justified?"); `slop-hunter` runs the exhaustive whole-tree delete pass ("what can go?"), load-bearing check first; `qa-engineer` cuts only tests paying no rent. Fabrication (fake citation, hallucinated API) is `slop-hunter`'s alone

### Spawn path

One agent serves every adversary: spawn `devils-advocate:adversarial-reviewer`, name the lens in the prompt - it loads the persona itself.

- **Never review with `general-purpose`** - no lens returns a fluent summary that reads like assurance
- **Name the adversary explicitly** - unnamed or misspelled, the agent lists the roster and stops rather than reviewing lens-less
- **Tools are least-privilege, not a sandbox** - `Read, Grep, Glob, Bash`, no `Write`/`Edit`, no MCP; `Bash` still writes, so "critique only" stays the persona's own rule
- **Two lenses degrade on this path** - `popular-science` wants no tools + a downloaded reference figure; `ux-designer` wants a rendered pixel. Route through `claude -p` when the visual bar decides the verdict
- Pick the mode by where the defect lives, not by the adversary

### Add your own expert

The file IS the plugin - drop `adversaries/<name>.md` with `name`/`lens`/`default-mode` frontmatter, add a table row above and triggers to the `description`. The agent resolves any name from disk; no agent-file edit. Authoring contract: `references/authoring-an-adversary.md`.

## After the review

- Triage, fix, re-confirm; flip a "review clean" criterion only on a clean confirming round. For each dismissed finding, know why it is wrong (caller guards it, type forbids it, test covers it, env provides it)
- `DO-NOT-SHIP` on a confirmed CRITICAL or MAJOR blocks the ship; one driven by false positives or style nits does not - say which
- **Shrink the remedy before applying it** - a confirmed finding does not license the reviewer's proposed fix; blocking findings tracing to the previous round's fixes mean the loop is generating its own work
- Record what the review caught and how you fixed it (acc-crit log, journal)
- **Measure the review** - `review-tools cost <transcript.jsonl>...` over `~/.claude/projects/<slug>/subagents/agent-*.jsonl`: turns, cached tokens, tool mix, re-reads, deduplicated by API message id. Cache read is the bill and grows with turns squared; a prompt change that did not cut turns saved nothing

<!-- improved 2026-08-28 | body 5105→2872w / 260→177L | trigger n/a (skipped) | via improve-skill -->
