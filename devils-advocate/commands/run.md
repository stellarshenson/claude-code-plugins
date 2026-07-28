---
description: Run the full devil's advocate critical analysis workflow
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash, Agent, AskUserQuestion, Skill]
argument-hint: "describe the document to critique and who the toughest reader is"
---

# Devil's Advocate - Run

Read `devils-advocate/skills/run/SKILL.md` and follow it - it is the single source of truth for the end-to-end workflow, the persona build, the Fibonacci scoring model, the versioned-file naming (`<name>_v<NN>_<residual>.md`), and the stop conditions. Do NOT duplicate it here; this command is only the explicit entry point into that workflow.

Full setup → evaluate → iterate loop in one go. The same three steps are also available as their own thin commands when you want to drive them by hand:

```
/devils-advocate:setup       # 1. build persona, harvest facts
/devils-advocate:evaluate    # 2. concern catalogue + baseline scorecard
/devils-advocate:iterate     # 3. improve, version, re-score (repeat until done)
```

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

