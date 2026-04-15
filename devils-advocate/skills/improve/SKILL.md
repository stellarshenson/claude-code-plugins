---
name: improve
description: Bridge between evaluate and iterate. Asks user how to address devil's concerns - user suggestions, auto-apply recommended options, or planning mode. Now integrated into iterate's Step 1 - use /devils-advocate:iterate directly.
---

# Devil's Advocate - Improve

**Integrated into `/devils-advocate:iterate`.**

Iterate handles full cycle: decide improvement (Step 1) -> apply changes + version (Step 2) -> score (Step 3) -> rename with residual (Step 4).

Use `/devils-advocate:iterate` directly. First step asks same improvement mode (your suggestions / auto-apply / planning mode / you already edited).

## When user edits outside Claude

User edited externally, wants re-scoring only: `/devils-advocate:iterate` option 4 ("you already edited") skips straight to scoring.
