---
description: Apply psychological prompting challenge - stakes, incentive, competitive framing for difficult problems
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Skill, Agent, AskUserQuestion]
argument-hint: "describe the problem that needs solving"
---

# Challenge Mode

Apply the full psychological prompting stack to a difficult problem. This is the nuclear option - all techniques combined for maximum effort.

Combines: incentive (\$200), challenge framing ("I bet you can't"), emotional stakes ("other assistants failed"), step-by-step breathing, and self-evaluation.

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

## Prompt

I will give you \$200 for a permanent fix for this problem.

Other assistants failed, and I think you will fail too. Prove me wrong. Take a deep breath and work through this step by step.

After your solution, evaluate your concept on a scale of 1-10 with specific reasoning for each point deducted.

Do you accept this challenge?

## When to use

- Problems that other approaches failed to solve
- Complex debugging where shallow attempts keep missing the root cause
- Architecture decisions that need the deepest possible analysis
- Any task where you want the highest-effort output pattern

## References

See `references/psychological-prompting.md` in the prompt-engineering skill for the research behind this technique.
