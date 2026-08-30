---
name: adversarial-review
description: Hostile, independent review - spawn fresh context-free reviewer subagents that try to BREAK a change. Two modes - diff bug-hunt (no tools, inline diff) and whole-repo audit (tools on - slop, brittle design, hardcodings, config drift, broken SoC). Multi-round - find, fix, re-confirm. Use before a risky commit/merge, a UI or terminal-UI ship, a shell installer, trusting an experiment's verdicts or a green test suite, signing off a spec, or publishing docs. Triggers - "adversarial review", "red-team this", "find bugs in my change", "review before ship", "audit the architecture", "UX review", "TUI review", "shell review", "methodology review", "can this test fail", "review my tests", "readability review", "review my README/docs", "deployment review", "review my spec", "acceptance criteria review", "does the code match the spec", "hunt dead weight", "what can I delete", "de-slop this", "check for fabricated citations", "review my agent instructions", "audit my skills", "is my harness portable".
---

# Adversarial Review

Spawn a hostile reviewer with no attachment to the code - a second model catches what the author rationalises away. Two modes; run the one that fits the risk, or both:

- **Mode 1 - diff bug-hunt** - no tools, inline diff, one turn. Bugs, logic errors, security holes, broken edge cases in one change
- **Mode 2 - architecture & quality audit** - tools on, whole-repo, many turns. Systemic rot a diff cannot show; the finding is usually a relationship across files

Mode is how (tools off/on); adversary is who (the lens). They compose freely. Always multi-round: one pass is a smoke test, not a verdict.

The reviewer must not inherit your context - one that read the author's reasoning reviews the case for the change, not the change. A subagent starts context-free; the leak channel is the prompt you write:

- Write every prompt as a `claude -p` command line - target, scope, locked decisions. Never your reasoning, what you ruled out, or what an earlier round concluded
- Default spawn is the plugin subagent, one per lens - visible under the user's prompt, interruptible
- `claude -p` only for what a subagent cannot do - genuinely deny tools (Mode 1), pin a model: `references/spawn-mechanics.md`

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

**Run the CLI without touching the caller's project.** The gate above puts it on PATH, so the bare command name is the whole invocation. `uv run` instead resolves whatever project the working directory sits in and writes `uv.lock` and `.venv` into it, so if you reach for uv pass `--no-project` (`uv run --no-project <cli> ...`) - it skips project discovery, leaves the tree untouched and still finds the same PATH binary. `--no-sync` and `--frozen` are not substitutes; both still create `.venv`.

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags are unverified. Report the line and stop; do not work around it.

## When to use

- Non-trivial feature or fix, before commit/merge; a goal that requires "survived adversarial review"
- Risky logic (auth, money, migrations, concurrency, deletion, permissions) → Mode 1, + Mode 2 if it touches structure
- New config, env, labels, routes, components, cross-service boundaries → Mode 2
- Not for trivial mechanical edits - spawn cost exceeds value

## Register the review as a task

`TaskCreate` before round 1, `TaskUpdate` through the loop - untracked, the re-confirm round silently never runs. One task per review, not per lens; the description carries adversary, mode, scope, round and findings location for a cold session. `completed` only on a clean confirming round.

## Workflow execution - the default multi-round path

Routing: with the dynamic Workflow capability, construct the workflow from the spec and pass it inline; without it, run the shipped `adversarial-loop.js` as the supplied protocol. The loop's nine invariants live in the script's control flow, never in your working memory - a hand-driven loop loses them to compaction; `references/loop-spec.md` is the one full statement of the contract (invariants, args, statuses, execution paths and the incidents behind each rule). This skill and its command are the Workflow opt-in.

- **Name it for its target** - `review-turndown-diff`, not `adversarial-review-loop`: kebab-case lowercase `meta.name`, a one-line lowercase `meta.description`, both pure literals since the harness parses `meta` before the script runs
- **Construct, check, run** - design the loop with the harness's own workflow practices (stage graph, verifiers, budgets, names are yours), then emit its invariant map before the first spawn: nine lines, `INV-1` .. `INV-9`, each naming the site in your own script that carries that invariant, marked `INV-n` at the site. The map IS the check - a loop that cannot show one has not been checked, and an unobservable check is what sends a careful session to the shipped script instead. Worked example: `${CLAUDE_PLUGIN_ROOT}/skills/adversarial-review/workflows/adversarial-loop.js` - consult it for the invariant mechanics, not the loop shape
- **`bar` is mandatory, an object, and yours to write** - `purpose` (what the product is for, for whom), `inputs` (the input universe - what a user actually feeds it), `primaryPath` (the use every CRITICAL/MAJOR must sit on); optional `guarantees`, `outOfScope`, `degrade`. Confirm it with the user in one line before the first spawn. The script refuses a bar missing any of the three; out-of-bar findings cap at MINOR
- **On `PLAN`** - apply in the main session first `reverts`, then the plan - exact changes, smallest radius, nothing else; read `mechanisms` first and veto any that does not answer a material CRITICAL/MAJOR; run the tests; re-invoke with `args.state` from the return plus `args.appliedFixes` with `files` per fix. Changes land only between invocations, visible and interruptible
- **`STOP`, `FANOUT_STOP`, `ROUND_CAP`** are user decision points, never a licence to loop again by hand. Every status returns round history, findings, closures, deferrals, refutations - relay them
- **Instrument first - ask if absent** - a refreshed code-graph index passed as `args.graph` cuts reviewer turns (one index lookup replaces a dozen greps - turns are the token bill) and lets the adjudicator group findings by shared cause and bound each change's radius, which is what keeps plans small and fixes clean. Which query answers which review question, what each costs and the traps that make it lie: `references/code-graph-instrument.md`. No index in the repo → ASK the user whether to build one before the discovery round - building it is billed, so it is their call; never build it unasked

**Without the capability**, execute `workflows/adversarial-loop.js` stage by stage as the procedural checklist (its control flow is the round order, gates and exit conditions), holding every invariant yourself through `references/manual-rounds.md`. The `review-tools loop` runner specified in the spec will own this path once built.

## Never gate a Stop hook on "survived adversarial review"

A hostile reviewer on freshly written remedy code near-never returns clean, so a Stop hook or goal that opens only on a clean verdict is an unbounded loop. The two terminal states: the configured consecutive clean confirming rounds, or an adjudicator `STOP`/`FANOUT_STOP` put to the user; a gate accepts both.

## The rounds protocol (manual fallback - only without the Workflow tool)

The hand-driven find → triage → fix → pinned re-confirm loop and the panel cap: `references/manual-rounds.md`.

## Remedy discipline

The rules a remedy must satisfy and why oversized remedies multiply defects: `references/remedy-discipline.md`.

## Adjudicate before you fix

Findings are input to a decision, not a work order. Spawn `devils-advocate:adjudicator` with every lens's findings → one change plan: verified, grouped by root cause, smallest change per group, radius, what each could break, what is deferred. It plans, never edits.

- **It triages materiality first and rules reverts before refinements** - pass the bar so it can test materiality; the plan flags `newMechanism` and stays inside the per-round budget (default 3)
- **Always for a panel** (three lenses reporting one defect is one item) **and past round 3** (the findings are usually the previous round's fixes; its `STOP` ruling is the honest outcome). Skip for a single lens with findings you can verify yourself
- **Merge reports first** - `review-tools findings <lens>.md ... [--full]` merges VERDICT lines and severity bullets into one table keyed by `file:line`; `--full` keeps the original bullets
- **Pass what you know** - graph, blast radius, locked decisions, previous round's findings and fixes. Supplied context outranks its inference

## Mode 1 - diff bug-hunt (no tools, inline diff)

Spawn `devils-advocate:adversarial-reviewer` with the diff pasted into the prompt, instructed to review only that. Tools-off is an instruction here - the agent still holds `Read`/`Grep`; to provably deny tools use `claude -p`. Template: `examples/mode1-diff-prompt.txt`.

## Mode 2 - architecture & quality audit (tools on, whole-repo)

Spawn `devils-advocate:adversarial-reviewer` naming the lens - it carries `Read`/`Grep`/`Glob`/`Bash`, no turn cap. Panel = one spawn per lens in a single message. Template: `examples/mode2-audit-prompt.txt`.

- **Tools on is the difference** - the reviewer greps the repo, reads call sites, judges the relationship; without tools it sees only what you paste
- **Scope by instruction, not diff** - name in-scope and excluded dirs (tests, vendored, generated)
- **Hand over the refreshed index** (see Instrument first) and say so in the prompt, naming what it is and where - never a command line: a spelled-out invocation pins an API that moves, and the reviewer reads the tool's own help for its current surface
- **Dossier for discovery reviewers only** - `review-tools dossier <src dirs> --plugins <plugin docs> --graph tmp/graphify-out/graph.json --out /tmp/dossier.md` writes the inventory a discovery reviewer otherwise spends 40-60 turns rediscovering; paste under `DOSSIER:`. Never in a confirming round - its attack surface is the closure list and fix delta (measured: +52% tokens for fewer findings)
- **Turns are the cost** - a reviewer re-reads its whole transcript every turn, so cost grows with turns squared; tight scope plus the graph converges in a third of the turns
- **Name the smell classes** - the template enumerates them and demands file:line evidence; only executable use is a violation, never a comment/docstring literal

## Adversaries - pluggable expert lenses

One self-contained persona prompt per expert in `adversaries/*.md`. The `lens:` frontmatter is authoritative; the table is the index.

### Signal standard (every adversary)

- **VERDICT** first line, always - `VERDICT: SHIP (<n> findings)` or `VERDICT: DO-NOT-SHIP (<n> findings)` + half-sentence why
- **SEVERITY** per finding - exactly `[CRITICAL|MAJOR|MINOR]`; taste = MINOR tagged `(taste)`
- **REMEDY** per finding - smallest impact radius at diff scale; a wider remedy is an opportunity stated with evidence, never a mandate. Per `references/remedy-discipline.md`
- **Coupling** - `DO-NOT-SHIP` iff any finding is CRITICAL or MAJOR; otherwise `SHIP`. The verdict is a pure function of the severity mix - `review-tools findings` recomputes and flags a disagreeing verdict line

| Adversary | Catches | Mode |
| --- | --- | --- |
| `architect` | architecture, consistency, config drift, SoC, over-engineering | 2 |
| `bug-hunter` | shell/installer/startup runtime bugs - quoting, `set -e`, restart asymmetry | 2 |
| `qa-engineer` | test strategy - risk-based coverage, can-each-test-fail, test slop | 2 |
| `ux-designer` | friction & intent, hierarchy, motion comfort, accessibility, edge states | 2 |
| `tui` | Textual/Rich internals - chrome duplication, mis-wired widgets, key propagation | 2 |
| `data-scientist` | hypothesis formulation, refutation protocol, reproducibility, leakage | 2 |
| `methodologist` | scientific-method integrity - can the test fail, verdict ladder | 2 |
| `popular-science` | readability for a curious generalist - jargon, unsourced claims, buried lede, visuals | 1 |
| `devops` | containers & deploy - Dockerfile hygiene, secrets in layers, root runtime, env drift | 2 |
| `analyst` | specs & acceptance criteria - coverage gaps, unverifiable criteria, silos, spec-vs-code drift | 2 |
| `slop-hunter` | whole-tree dead weight - dead code, YAGNI, vanity tests, over-prose; AI-slop tells & fabrication | 2 |
| `ai-engineer` | the instruction layer for any assistant - lock-in, pinned commands, drifted rules, unbounded loops, costly fan-out | 2 |

Which lens owns an overlap: Boundaries between lenses in `references/authoring-an-adversary.md`.

### Spawn path

One agent serves every adversary: `devils-advocate:adversarial-reviewer` loads the persona for the lens named in the prompt.

- **Never review with `general-purpose`** - no lens returns a fluent summary that reads like assurance
- **Name the adversary explicitly** - unnamed or misspelled, the agent lists the roster and stops. Caller named none → state the inferred target, recommend a lens, wait
- **Tools are least-privilege, not a sandbox** - `Read, Grep, Glob, Bash`, no `Write`/`Edit`, no MCP; `Bash` still writes, so critique-only stays the persona's rule
- **Two lenses degrade here** - `popular-science` wants no tools + a reference figure; `ux-designer` a rendered pixel. Route through `claude -p` when the visual bar decides the verdict
- Pick the mode by where the defect lives, not by the adversary

### Add your own expert

Drop `adversaries/<name>.md` with `name`/`lens`/`default-mode` frontmatter, add a table row above and triggers to the `description`; no wiring. Authoring contract: `references/authoring-an-adversary.md`.

## After the review

- For each dismissed finding, know why it is wrong (caller guards it, type forbids it, test covers it, env provides it)
- `DO-NOT-SHIP` on a confirmed CRITICAL or MAJOR blocks the ship; one driven by false positives or style nits does not - say which
- A confirmed finding does not license the reviewer's proposed fix
- Record what the review caught and the fix (acc-crit log, journal)
- **Measure the review** - `review-tools cost <transcript.jsonl>...` over `~/.claude/projects/<slug>/subagents/agent-*.jsonl`; cache read is the bill, and a prompt change that did not cut turns saved nothing

<!-- improved 2026-08-29 | body 2872→2196 w | via improve-skill -->
