---
name: run
description: Run the full devil's advocate workflow end-to-end. Setup persona, evaluate baseline, then iterate corrections until residual risk is acceptable. Use when the user wants the complete analysis in one go.
---

# Devil's Advocate - Run

End-to-end wrapper: build the devil, score the baseline, iterate until the residual is acceptable. Each step is its own skill and owns its rules; this file only sequences them.

## Task Tracking

**MANDATORY**: `TaskCreate` / `TaskUpdate` for setup, evaluation and each iteration. Mark in_progress / completed.

## Artefacts

Three, in the target document's directory: `devils_advocate.md` (persona, concerns, every scorecard), `fact_repository.md` (verified claims from sources and the user), and the versioned document with its embedded scorecard. Shapes and file naming live in the `setup`, `evaluate` and `iterate` skills. Optional visuals: the `svg-infographics:svg-infographics` skill, which owns its own toolchain gate - this workflow needs no install step.

## Sequence

1. **Setup** - invoke `devils-advocate:setup`: identify the target, build the persona (user seed, user description, or derived from the document), harvest facts into `fact_repository.md`. Persona BEFORE concerns, always
2. **Evaluate** - invoke `devils-advocate:evaluate`: concern catalogue in the devil's voice, Fibonacci risk, 0-100% scorecard, options per gap; embed the scorecard and rename to `<name>_v01_<score>.md`
3. **Iterate** - invoke `devils-advocate:iterate` until its stopping criteria fire: decide the mode with the user, apply corrections as `<name>_v<NN>_<score>.md`, re-score, append the new scorecard to `devils_advocate.md`. It stops on target reached, all gaps small, stagnation, a scope change beyond the document, or the user saying so
4. **Report** - the score trajectory (`v01_89 -> v02_28 -> v03_12`), the top remaining gaps, and what would close them

The scoring principles and anti-patterns are in `evaluate`; the version chain, cross-concern tensions and the in-place rule for `devils_advocate.md` / `fact_repository.md` are in `iterate`.
