# Program: Research & Hypothesis Output Quality + File Organization

## Objective

Fix 4 issues identified from production usage of auto-build-claw orchestrator in cp-simulations project. Research output is too thin for context restart, hypothesis entries lack substance, output files land in artifacts root instead of phase dirs, and planning iteration doesn't auto-chain for single-iteration runs.

## Forensic Evidence

From cp-simulations session (d4d6c789, 3.2MB):
- RESEARCH output passed gatekeeper but user found it insufficient for context restart - "Current State" + "Gap Analysis" with no per-agent findings, no structured evidence blocks
- Hypothesis autowrite DID fire correctly (agent mode). Gatekeeper caught incomplete status classification (good), but final hypothesis entries still lacked depth for reusable context
- 5 of 6 `--output-file` arguments were PLACEHOLDER PATHS (`"path"`, `"path/to/plan.md"`) because the template shows literal placeholders. When a real path was tried (`.auto-build-claw/research.md`), it failed because the directory wasn't created yet
- Iteration 0 (planning) didn't auto-chain because `total_iterations > 1` excludes `--iterations 0` (unlimited) and `--iterations 1`
- Gatekeeper system IS working: caught 2 failures (readback + hypothesis status), forced correction

## Pending Work Items

- **RESEARCH output depth requirements** (high)
  - Scope: phases.yaml FULL::RESEARCH template, RESEARCH gatekeeper
  - Root cause: template says "gather evidence" but has no explicit depth requirements. Gatekeeper checks for "specific file references" but interpretation is subjective. No minimum content structure enforced
  - Fix: strengthen RESEARCH template with explicit output requirements:
    - Each Explore agent must produce a structured finding block: FINDING (what), EVIDENCE (code refs, line numbers, metrics), IMPACT (why it matters for the objective), FILES (specific paths)
    - Minimum: 5 findings per agent, each with code references
    - The merged research output must contain: current state summary, gap analysis with specifics, file inventory (what exists, what's missing), dependency map, risk assessment
    - Gatekeeper must check for these structural elements, not just "specific enough"
  - The output must be rich enough that a new session starting from PLAN with only the research output could proceed without re-reading the codebase
  - Acceptance: RESEARCH gatekeeper rejects outputs without structured findings + evidence

- **HYPOTHESIS entry richness** (high)
  - Scope: phases.yaml FULL::HYPOTHESIS template, HYPOTHESIS gatekeeper, ACTION::HYPOTHESIS_AUTOWRITE prompt
  - Root cause: despite the template specifying the rich format (ID, HYPOTHESIS, WHAT TO DO, PREDICT, EVIDENCE, RISK, STARS), agents produce shallow entries. The gatekeeper checks for "measurable prediction" but doesn't enforce the full format structure
  - Fix: strengthen the HYPOTHESIS gatekeeper to explicitly check for ALL format fields in each hypothesis. The gatekeeper prompt must list the required fields and FAIL if any hypothesis is missing fields
  - Also strengthen the HYPOTHESIS_AUTOWRITE action prompt to extract ALL format fields from the debate output, not just hypothesis + stars
  - Acceptance: HYPOTHESIS gatekeeper rejects outputs where hypotheses lack the full format structure

- **Output file placement in phase directories** (high)
  - Scope: orchestrator.py cmd_end --output-file handling, phases.yaml template instructions
  - Root cause: `Path(output_file_str).resolve()` resolves relative paths against CWD (project root), not against the phase directory. Agents write `research.md` to project root or artifacts root, not to `phase_01_research/`
  - Fix two things:
    1. In cmd_end: if output_file is a relative path, resolve it against `_phase_dir(state)` instead of CWD. If it's absolute, use as-is
    2. Update ALL phase template instructions that mention `--output-file "path/to/..."` to use a placeholder that resolves to the phase dir, e.g. `--output-file "{phase_dir}/research.md"` where {phase_dir} is resolved to the actual phase directory path
  - The phase_dir is already created by `_phase_dir(state)` - use it
  - Acceptance: output files land in phase_NN_name/ directories, not in artifacts root or project root

- **Hypothesis notes format and status validation** (high)
  - Scope: orchestrator.py _load_hypotheses, phases.yaml HYPOTHESIS_AUTOWRITE prompt, HYPOTHESIS template
  - Root cause: forensic evidence from cp-simulations shows hypotheses with plain string notes (`["Selected as primary approach"]`) instead of dict format (`[{processed: "message"}]`). Also uses `status: selected` which is not a valid status
  - Fix: (1) _load_hypotheses validates notes are list of dicts with status key, crashes on invalid format (2) HYPOTHESIS_AUTOWRITE prompt explicitly specifies notes dict format (3) HYPOTHESIS template instructs: selected hypotheses get `status: "processed"`, not "selected" (4) _load_hypotheses validates status against valid set (new, dismissed, processed, deferred)
  - Acceptance: invalid notes format or status crashes with clear error, HYPOTHESIS_AUTOWRITE produces correct format

## Exit Conditions

- All pending items implemented
- make test >= 228
- make lint clean
- RESEARCH gatekeeper checks for structured findings
- HYPOTHESIS gatekeeper checks for full format fields
- Output files resolve to phase directories

## Constraints

- No backward compatibility for old state files (crash with clear error)
- Template changes must not break existing test assertions - update tests as needed
- Phase dir resolution must handle both relative and absolute paths
- Occam's razor: minimal changes to achieve each fix
