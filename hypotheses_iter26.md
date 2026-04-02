# Hypotheses - Iteration 26

## H1: Content hash comparison is the simplest structural diff detection
- **Root cause**: _detect_old_format only checks for `gates:` string pattern. A version upgrade could change phase structure, add/remove sections, etc. without triggering the old-format check.
- **Prediction**: comparing MD5/SHA hash of each bundled resource file against its project-local counterpart detects ANY structural difference, not just the legacy gates: pattern. If hashes differ AND local file was modified (mtime != bundled mtime), archive and replace.
- **Evidence**: _ensure_project_resources at L2915-2920 only copies missing files, never checks existing files for staleness
- **Stars**: 5

## H2: NEXT template needs unsolved failures -> PROGRAM/BENCHMARK instruction
- **Root cause**: NEXT template_continue and template_final both mention reviewing failures but don't instruct adding them to PROGRAM.md/BENCHMARK.md
- **Prediction**: adding "If unsolved failures exist, add them as work items to PROGRAM.md and verification items to BENCHMARK.md" to both templates will close the S12 item. One-line change per template.
- **Evidence**: template_final at L924-937 shows `{CMD} failures` review but no PROGRAM.md instruction
- **Stars**: 3

## H3: PLAN template already matches EnterPlanMode - needs explicit 4-step labeling
- **Root cause**: S15 benchmark says "describes a 4-step structured process: explore, design, review, write". Current PLAN template does this implicitly but doesn't label the steps explicitly.
- **Prediction**: adding numbered step headers (Step 1: Explore, Step 2: Design, Step 3: Review, Step 4: Write) to the existing PLAN template content will close S15 items without changing behavior.
- **Evidence**: PLAN template at L383-387 has EnterPlanMode, explore agents, write plan, ExitPlanMode - all 4 steps present but not labeled
- **Stars**: 3
