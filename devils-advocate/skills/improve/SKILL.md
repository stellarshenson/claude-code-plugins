---
name: improve
description: Bridge between evaluate and iterate. Asks user how to address devil's concerns - user suggestions, auto-apply recommended options, or planning mode. Now integrated into iterate's Step 1 - use /devils-advocate:iterate directly.
---

# Devil's Advocate - Improve

**Integrated into `/devils-advocate:iterate`.**

Iterate handles full cycle: decide improvement (Step 1) -> apply changes + version (Step 2) -> score (Step 3) -> rename with residual (Step 4).

Use `/devils-advocate:iterate` directly. First step asks same improvement mode (your suggestions / auto-apply / planning mode / you already edited).

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

## When user edits outside Claude

User edited externally, wants re-scoring only: `/devils-advocate:iterate` option 4 ("you already edited") skips straight to scoring.
