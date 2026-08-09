---
description: Hostile independent review by spawning fresh reviewer subagents - invokes the devils-advocate:adversarial-review skill, picking the adversary a data science project needs (data-scientist, architect, popular-science, ux-designer); find, fix, re-confirm clean
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, TaskCreate, TaskUpdate]
argument-hint: "what to review, e.g. 'the E12 experiments log before I trust it' or 'the architecture of the pipeline' or 'the article for a generalist reader'"
---

# Adversarial Review

Read `devils-advocate/skills/adversarial-review/SKILL.md` first - it is the single source of truth for the two modes (diff bug-hunt vs whole-repo audit), the rounds protocol, the spawn mechanics, the gotchas, and every adversary persona beside it in `adversaries/<name>.md`. Do NOT duplicate it here. This command is only the data-science entry point into it.

Requires the `devils-advocate` plugin installed - the skill and its adversaries live there. For a non-data-science target, `/devils-advocate:adversarial-review` is the same skill with the full roster up front.

## Toolchain gate (MANDATORY - run before anything else)

Run this first, every session, before any other work. The upgrade always runs; a version mismatch blocks.

```bash
python3 -m pip install --user --upgrade stellars-claude-code-plugins 2>&1 | tail -1
LIB=$(python3 -c "import importlib.metadata as m;print(m.version('stellars-claude-code-plugins'))" 2>/dev/null) || { echo "FATAL: toolkit unavailable"; exit 1; }
PLUG=$(grep -m1 '"version"' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null | cut -d'"' -f4)
[ -n "$PLUG" ] && [ "$LIB" != "$PLUG" ] && { echo "STALE: library $LIB != plugin $PLUG - refusing to run on a mismatched CLI; re-run the upgrade"; exit 1; }
echo "toolkit $LIB"
```

Both branches exit non-zero and neither is advisory: an absent library (`FATAL`) and a version mismatch (`STALE`). A mismatch means the CLI is not the one this file was written against, so its documented flags and rules are unverified. Report the line and stop; do not work around it.

## What to do

1. Read `devils-advocate/skills/adversarial-review/SKILL.md`
2. **No adversary named? ASK before spawning** - state the inferred target, list the fitting candidates with their lens, recommend one, wait. Wrong lens = fluent review of a risk the target lacks. Skip only when the prompt names it
3. **Cap at 3** unless the user explicitly asks for more - your triage, not the spawn, is the bottleneck; 3 lenses catch most of what 5 would, at a review you finish
4. Pick by where the risk lives - the four that earn their keep in a data science project:
   - **data-scientist** → an experiments log, notebook, data-prep pipeline, or metric/eval design, before trusting a conclusion
   - **architect** → the project / pipeline architecture, config, repo structure
   - **popular-science** → the article, story, or README, before publishing for non-specialists
   - **ux-designer** → notebook visuals, figures, dashboards
   - each is also fully generalist - use it on any target that fits its lens. The skill's roster carries more (`bug-hunter`, `qa-engineer`, `methodologist`, `tui`, `devops`, `analyst`) - reach for them when the risk is there: `methodologist` on an experiment's verdict ladder, `qa-engineer` on the test suite, `analyst` on a spec or acceptance-criteria doc
5. Pick the mode: Mode 1 (inline diff, no tools) for a specific change; Mode 2 (whole-repo, tools ON) for systemic rot
6. **`TaskCreate` the review before spawning**, `TaskUpdate` it each round - `completed` only on a clean confirming round. One task per review, not per lens
7. **Spawn the `devils-advocate:adversarial-reviewer` subagent** - one per lens, naming the adversary and scope in its prompt; a panel goes in a single message so the lenses run concurrently and the user can watch each. Pass target, scope and locked decisions only - never your reasoning for the change, which is the thing under review. Drop to `claude -p` (skill's mechanics - `env -u CLAUDECODE`, `< /dev/null`, `--no-session-persistence`) only for what a subagent cannot do - genuinely deny tools in Mode 1, or pin a different model
8. Triage every finding against the code yourself, fix the real ones, then run the re-confirm round - do not call it clean until a confirming round comes back clean
