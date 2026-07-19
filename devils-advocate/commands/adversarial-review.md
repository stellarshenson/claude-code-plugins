---
description: Hostile independent review by spawning fresh claude -p subprocesses that try to BREAK a change - invokes the devils-advocate:adversarial-review skill, seeding one of ten expert adversaries; find, fix, re-confirm clean
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
argument-hint: "what to review, e.g. 'the auth middleware change before I merge' or 'audit the repo architecture' or 'my spec against the code'"
---

# Adversarial Review

Read `devils-advocate/skills/adversarial-review/SKILL.md` first - it is the single source of truth for the two modes, the rounds protocol, the spawn mechanics and gotchas, and the roster. The adversary personas live beside it in `adversaries/<name>.md`, one self-contained prompt each. Do NOT duplicate any of it here; this command only routes into it.

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
5. Pick the mode: Mode 1 (inline diff, no tools, `--max-turns 1`) for a specific change; Mode 2 (whole-repo, tools ON, `--max-turns 50`, background) for systemic rot between files
6. Spawn per the skill's mechanics (`env -u CLAUDECODE`, `< /dev/null`, `--no-session-persistence`), seeding the chosen adversary body in place of the generic reviewer role
7. Triage every finding against the code yourself, fix the real ones, then run the re-confirm round - never call it clean on the round that still had findings, only on a clean confirming round
