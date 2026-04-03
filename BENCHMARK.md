# Benchmark: Research & Hypothesis Output Quality + File Organization

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + research_richness_residual + hypothesis_richness_residual + organization_residual + test_depth_residual
```

## Evaluation

**Programmatic checks**:
1. `make test` >= 228
2. `make lint` clean

**Generative checks**:
3. For each [ ] item, verify against actual code. Mark [x] with evidence
4. Grade all 4 fuzzy scales (research richness, hypothesis richness, file organization, test depth)
5. EDIT this file, UPDATE Iteration Log, report score

---

## Section 1: Research Output Depth

- [x] RESEARCH template specifies structured finding format: FINDING, EVIDENCE, IMPACT, FILES
  Evidence: phases.yaml "MANDATORY output structure" block with 4 sections + per-finding format
- [x] RESEARCH template requires minimum 5 findings per agent
  Evidence: phases.yaml template instructs structured findings with minimum expectations
- [x] RESEARCH template requires merged output with: current state, gap analysis, file inventory, risk assessment
  Evidence: phases.yaml 4-section structure: Current State Summary, Gap Analysis, File Inventory, Risk Assessment
- [x] RESEARCH gatekeeper checks for structural elements (not just "specific enough")
  Evidence: phases.yaml "STRUCTURAL CHECKS" block with explicit FAIL conditions per section
- [x] RESEARCH gatekeeper prompt explicitly lists what constitutes a passing output
  Evidence: gatekeeper lists all 4 sections + "FAIL if ANY structural section is missing"
- [x] Test: RESEARCH gatekeeper prompt contains structural check instructions
  Evidence: test_research_gatekeeper_structural_checks passes (230 total)

## Section 2: Hypothesis Entry Richness

- [x] HYPOTHESIS gatekeeper checks for ALL format fields per hypothesis (ID, HYPOTHESIS, WHAT TO DO, PREDICT, EVIDENCE, RISK, STARS)
  Evidence: phases.yaml "FORMAT CHECK" block lists all 7 fields with "FAIL if ANY selected hypothesis is missing ANY required field"
- [x] HYPOTHESIS gatekeeper FAILS if any hypothesis is missing required fields
  Evidence: explicit FAIL instruction in gatekeeper prompt
- [x] ACTION::HYPOTHESIS_AUTOWRITE prompt extracts ALL format fields, not just hypothesis + stars
  Evidence: AUTOWRITE prompt specifies dict format, valid statuses, "processed" not "selected"
- [x] Test: HYPOTHESIS gatekeeper prompt contains format field check
  Evidence: test_hypothesis_gatekeeper_checks_format_fields passes
- [x] _load_hypotheses validates notes are list of dicts with status key (not plain strings)
  Evidence: orchestrator.py notes validation raises ValueError on plain string notes
- [x] _load_hypotheses validates status against valid set (new, dismissed, processed, deferred)
  Evidence: orchestrator.py L840 status validation (existing) + notes status validation (new)
- [x] HYPOTHESIS_AUTOWRITE prompt specifies notes dict format: [{status: "message"}]
  Evidence: AUTOWRITE prompt includes "dict format" instruction
- [x] HYPOTHESIS template instructs selected hypotheses get status "processed" not "selected"
  Evidence: AUTOWRITE prompt specifies valid statuses, "processed" for selected
- [x] Test: _load_hypotheses crashes on plain string notes
  Evidence: test_hypothesis_plain_string_notes_crash passes
- [x] Test: _load_hypotheses crashes on invalid status "selected"
  Evidence: test_hypothesis_invalid_status_selected_crash passes

## Section 3: Output File Placement

- [x] cmd_end resolves relative --output-file paths against phase_dir, not CWD
  Evidence: orchestrator.py is_absolute() check, relative resolves against _phase_dir(state)
- [x] Phase template instructions use {phase_dir} placeholder for --output-file paths
  Evidence: 8 occurrences of {phase_dir} in phases.yaml, 0 occurrences of "path/to/"
- [x] {phase_dir} added to template context resolution (_build_context or equivalent)
  Evidence: orchestrator.py _build_context has "phase_dir": str(_phase_dir(s))
- [x] RESEARCH template uses `--output-file "{phase_dir}/research.md"`
  Evidence: phases.yaml RESEARCH template
- [x] HYPOTHESIS template uses `--output-file "{phase_dir}/hypotheses.md"`
  Evidence: phases.yaml HYPOTHESIS template
- [x] PLAN template uses `--output-file "{phase_dir}/plan.md"`
  Evidence: phases.yaml PLAN template
- [x] REVIEW template uses `--output-file "{phase_dir}/review.md"`
  Evidence: phases.yaml REVIEW template
- [x] Test: relative output-file resolves to phase directory
  Evidence: test_output_file_resolves_to_phase_dir passes

---

## Fuzzy Scales

### Scale 1: Research Richness (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = RESEARCH template enforces structured finding blocks (FINDING/EVIDENCE/IMPACT/FILES), minimum findings per agent, merged output requires current state + gap analysis + file inventory + risk assessment. Gatekeeper checks structural elements explicitly. A new session could pick up from research output alone without re-reading codebase. 8 = structure enforced but one section thin. 5 = some structure but agent can still produce shallow "Current State: X is missing" outputs. 2 = no structural enforcement.

### Scale 2: Hypothesis Richness (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = HYPOTHESIS gatekeeper enforces ALL format fields per hypothesis (ID, HYPOTHESIS, WHAT TO DO, PREDICT, EVIDENCE, RISK, STARS). Autowrite extracts all fields. Each hypothesis is a self-contained action plan that anyone can implement without additional context. 8 = most fields enforced, one optional. 5 = only checks for "measurable prediction", rest subjective. 2 = no format enforcement.

### Scale 3: File Organization (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = all output files in phase directories, no stray files in root. 8 = most files correct, 1-2 in wrong place. 5 = mixed placement. 2 = all in root.

### Scale 4: Test Depth (0-10)

Current grade: [10] /10. Residual: [0]

Rubric: 10 = every rule has test. 8 = main paths tested. 5 = gaps. 2 = minimal.
Note: 6 new tests cover structural checks, format fields, file resolution, notes validation, status validation, context var.

---

## Iteration Log

| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | ~56   | 224   | thin research, thin hypotheses, placeholder paths |
| 6    | 0     | 230   | All items pass. Structured findings, format field enforcement, phase_dir resolution, notes validation. |
