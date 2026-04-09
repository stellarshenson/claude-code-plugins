---
name: improve
description: Bridge between evaluate and iterate. Asks user how to address devil's concerns - user suggestions, auto-apply recommended options, or planning mode. Now integrated into iterate's Step 1 - use /devils-advocate:iterate directly.
---

# Devil's Advocate - Improve

**This skill is now integrated into `/devils-advocate:iterate`.**

The iterate skill handles the full cycle: decide how to improve (Step 1) -> apply changes + version (Step 2) -> score (Step 3) -> rename with residual (Step 4).

Use `/devils-advocate:iterate` directly. It will ask the same improvement mode question (your suggestions / auto-apply / planning mode / you already edited) as its first step.

## When user edits outside Claude

If the user made changes themselves and just wants re-scoring, `/devils-advocate:iterate` handles this too - choose option 4 ("you already edited") and it skips straight to scoring.
