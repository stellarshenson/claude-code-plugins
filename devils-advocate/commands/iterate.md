---
description: One improvement cycle - decide approach, apply changes, version, re-score, rename with residual - step 3 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion]
argument-hint: "(optional) how to improve, or let it ask"
---

# Devil's Advocate - Iterate

Read `devils-advocate/skills/iterate/SKILL.md` and follow it - it is the single source of truth for the four-step cycle (improve, version, score, rename) and the stop conditions. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 3 of the workflow, run repeatedly until residual is acceptable, stagnation, or the user accepts. Requires `/devils-advocate:evaluate` to have produced a baseline. Re-scores in place when the user edited the document outside Claude. Run `/devils-advocate:run` instead to drive the whole setup → evaluate → iterate loop.

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

