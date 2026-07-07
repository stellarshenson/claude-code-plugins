---
description: Hostile independent review by spawning fresh claude -p subprocesses - DS-tuned adversaries (data-scientist, architect, popular-science, ux-designer), each also generalist; find, fix, re-confirm clean
allowed-tools: [Read, Write, Edit, Glob, Grep, Bash]
argument-hint: "what to review, e.g. 'the E12 experiments log before I trust it' or 'the architecture of the pipeline' or 'the article for a generalist reader'"
---

# Adversarial Review

Read the `datascience:adversarial-review` skill first - it is the single source of truth for the two modes (diff bug-hunt vs whole-repo audit), the rounds protocol, the spawn mechanics, the gotchas, and the four adversary personas in `adversaries/`. Do NOT duplicate it here.

## What to do

1. Read the `datascience:adversarial-review` skill
2. Pick the adversary by where the risk lives - in a data science project:
   - **data-scientist** → an experiments log, notebook, data-prep pipeline, or metric/eval design, before trusting a conclusion
   - **architect** → the project / pipeline architecture, config, repo structure
   - **popular-science** → the article, story, or README, before publishing for non-specialists
   - **ux-designer** → notebook visuals, figures, dashboards
   - each is also fully generalist - use it on any target that fits its lens
3. Pick the mode: Mode 1 (inline diff, no tools, `--max-turns 1`) for a specific change; Mode 2 (whole-repo, tools ON, `--max-turns 50`, background) for systemic rot
4. Spawn the reviewer per the skill's mechanics (`env -u CLAUDECODE`, `< /dev/null`, `--no-session-persistence`); seed the chosen adversary body in place of the generic reviewer role
5. Triage every finding against the code yourself, fix the real ones, then run the re-confirm round - do not call it clean until a confirming round comes back clean
