# Research - Iteration 26

## S10b: _ensure_project_resources (L2907-2935)
- _detect_old_format (L2897-2904) only checks for `gates:` key
- Need: compare bundled vs project-local for structural differences
- Approach: hash comparison or key structural markers

## S12: NEXT phase template (L909-937)
- template_continue (L909-922) and template_final (L924-937)
- Missing: instruction to add unsolved failures to PROGRAM.md/BENCHMARK.md
- Fix: add to both templates

## S15: PLAN phase template (L367-400)
- Already describes 4-step flow: EnterPlanMode, explore, design+review agents, ExitPlanMode
- Mostly passes - may need minor wording to explicitly call out the 4 steps
