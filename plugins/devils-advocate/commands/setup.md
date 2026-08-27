---
description: Build the devil's-advocate persona and harvest the fact repository for a target document - step 1 of the workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent]
argument-hint: "the document to critique and who its toughest reader is"
---

# Devil's Advocate - Setup

Read `devils-advocate/skills/setup/SKILL.md` and follow it - it is the single source of truth for building the devil persona (role, biases, triggers) and harvesting verified facts from source material. Do NOT duplicate it here; this command is only the explicit entry point into that step.

Step 1 of the workflow. It writes `devils_advocate.md` (the persona) and `fact_repository.md` (verified claims with sources), which `/devils-advocate:evaluate` then reads. Run `/devils-advocate:run` instead for the full setup → evaluate → iterate loop in one go.

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

