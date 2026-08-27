---
description: Generate the baseline concern catalogue and scorecard from the devil persona - step 2 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
argument-hint: "(optional) the target document, if not already set up"
---

# Devil's Advocate - Evaluate

Read `devils-advocate/skills/evaluate/SKILL.md` and follow it - it is the single source of truth for producing the concern catalogue with Fibonacci risk scores and the baseline scorecard. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 2 of the workflow. Requires `/devils-advocate:setup` to have run first (`devils_advocate.md` and `fact_repository.md` must exist). Its baseline residual is what `/devils-advocate:iterate` drives down. Run `/devils-advocate:run` instead for the full loop in one go.

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

