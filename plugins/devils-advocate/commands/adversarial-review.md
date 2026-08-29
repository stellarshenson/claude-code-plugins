---
description: Hostile independent review by spawning fresh reviewer subagents that try to BREAK a change - invokes the devils-advocate:adversarial-review skill, seeding one of twelve expert adversaries; find, fix, re-confirm clean
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, TaskCreate, TaskUpdate]
argument-hint: "what to review, e.g. 'the auth middleware change before I merge' or 'audit the repo architecture' or 'my spec against the code'"
---

# Adversarial Review

Read `devils-advocate/skills/adversarial-review/SKILL.md` first - it is the single source of truth for the two modes, the rounds protocol, the spawn mechanics and gotchas, and the roster. The adversary personas live beside it in `adversaries/<name>.md`, one self-contained prompt each. Do NOT duplicate any of it here; this command only routes into it.

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

## What to do

1. Read the skill
2. **No adversary named? ASK before spawning** - state the inferred target, list the fitting candidates with their lens, recommend one, wait. The wrong lens returns a fluent review of a risk the target does not have - worse than none, because it reads like assurance. Skip only when the prompt names the adversary, or one lens obviously fits
3. **Cap the panel at 3** unless the user explicitly asks for more - triage, not the spawn, is the bottleneck; five lenses buy a backlog you abandon half-done rather than five times the signal
4. Pick by where the risk lives - the full roster and each lens is in the skill's table:
   - **architect** → architecture, consistency, hardcodings, config drift, SoC, over-engineering
   - **bug-hunter** → shell, installers, startup - quoting, `set -e`, lifecycle races
   - **qa-engineer** → test strategy - risk-based coverage, can-each-test-fail, tests to delete
   - **analyst** → specs and acceptance criteria - coverage gaps, unverifiable criteria, silos, spec-vs-code drift
   - **ux-designer** → friction, hierarchy, focus, accessibility
   - **tui** → Textual/Rich internals - chrome duplication, key propagation, headless verification
   - **data-scientist** → hypothesis rigor, leakage, metric validity, reproducibility
   - **methodologist** → scientific-method integrity - can the test fail, does the verdict ladder span outcomes
   - **popular-science** → readability for a generalist - jargon, unsourced claims, buried lede, visuals
   - **devops** → containers and deploy - Dockerfile hygiene, secrets in layers, PID-1 signals, probes
   - **slop-hunter** → what can go - dead code, YAGNI abstractions, vanity tests, doc over-prose, unused deps; AI-slop tells and fabrication
   - **ai-engineer** → the instruction layer that steers assistants - portability, pinned command surfaces, duplicated rules, context budget, stage graphs and loop bounds
5. Pick the mode: Mode 1 (inline diff, no tools) for a specific change; Mode 2 (whole-repo, tools ON) for systemic rot between files
6. **Multi-round**: with the dynamic Workflow capability, construct the workflow from the spec and pass it inline; without it, run the shipped `adversarial-loop.js` as the supplied protocol. `${CLAUDE_PLUGIN_ROOT}/skills/adversarial-review/references/loop-spec.md` is the one full statement of the contract - the nine invariants every constructed script must encode, the args contract, the statuses, the execution paths and the incidents behind each rule; check the constructed script against its invariant list before running it. This command is the Workflow opt-in. The `bar` object, the `graph` argument and the handling of `PLAN`, `STOP`, `FANOUT_STOP` and `ROUND_CAP` are stated once in the skill's Workflow execution section - follow it. Steps 7-11 below are the supplied fallback for harnesses without the dynamic Workflow capability - follow the worked example (`${CLAUDE_PLUGIN_ROOT}/skills/adversarial-review/workflows/adversarial-loop.js`) stage by stage as the checklist
7. **`TaskCreate` the review before spawning**, `TaskUpdate` it each round - `completed` only on a clean confirming round. One task per review, not per lens
8. **Mode 2: build the dossier first** - refresh the code-graph index if one exists (the AST-only refresh its own tooling documents, seconds, no tokens), then `review-tools dossier <in-scope dirs> --plugins <plugin docs dir> --graph tmp/graphify-out/graph.json --out /tmp/dossier.md` and paste the file into every reviewer prompt under `DOSSIER:`. It replaces the 40-60 discovery turns each reviewer would otherwise spend and it is the same inventory for every lens
9. **Spawn the `devils-advocate:adversarial-reviewer` subagent** - one per lens, naming the adversary and scope in its prompt; a panel goes in a single message so the lenses run concurrently and the user can watch each. Write the prompt as if it were a `claude -p` command line - a process that knows nothing but what you typed. Pass target, scope and locked decisions; never your reasoning for the change, which is the thing under review. Drop to `claude -p` (skill's mechanics - `env -u CLAUDECODE`, `< /dev/null`, `--no-session-persistence`) only for what a subagent cannot do - genuinely deny tools in Mode 1, or pin a different model
10. **Adjudicate before fixing** - save each report as `<lens>.md`, merge them with `review-tools findings <lens>.md ... --full > /tmp/findings.md`, then for a panel, or any round past 3, spawn `devils-advocate:adjudicator` with the merged table and the reports plus anything you know (a blast radius you already have, a locked decision, domain insight, the previous round's findings and the fixes since). It returns one change plan grouped by root cause, with each change's radius and what it could break. Skip only for a single lens with one or two findings you can verify yourself
11. Triage what the adjudicator left UNPROVEN and spot-check its confirmed and refuted calls - you still own the final call - then fix the real ones and run the re-confirm round - never call it clean on the round that still had findings, only on a clean confirming round
