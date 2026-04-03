# Benchmark: Fix Real Gaps

## Score

**Direction**: MINIMIZE (target: 0)

```
score = (broken_items * 3) + missing_enforcement_items + test_depth_residual
```

Broken items weighted 3x because they cause runtime failures.

## Evaluation

**Programmatic checks**:
1. `make test` >= 236
2. `make lint` clean
3. `grep -c "AUTO-ACTION (agent)" stellars_claude_code_plugins/engine/orchestrator.py` = 0 (no stdout printing)
4. `grep -c "execution" stellars_claude_code_plugins/engine/model.py` = 0 for ActionDef execution field

**Generative checks**:
4. For each [ ] item, verify against actual code AND runtime behavior. Mark [x] with evidence
5. Grade fuzzy scale
6. EDIT this file, UPDATE Iteration Log

---

## Section 1: Broken Code (weight: 3x)

- [ ] _claude_evaluate retries on rate limit responses (up to 3 attempts with backoff)
  Evidence: code detects "hit your limit" pattern and retries instead of returning FAIL
- [ ] RECORD readback prompt acknowledges CLAUDE.md overrides phase instructions
  Evidence: readback prompt contains instruction that agent adapting to CLAUDE.md is PASS not FAIL
- [ ] RECORD template says git operations conditional on project policy (not mandatory)
  Evidence: template text mentions CLAUDE.md / project policy as override
- [ ] RECORD readback only requires "iteration summary" - git is conditional
  Evidence: readback prompt "Must mention: iteration summary" without requiring git
- [ ] Output file path does not double when {phase_dir} resolves to absolute path
  Test: create file at absolute phase_dir path, pass as --output-file, verify it reads correctly
- [ ] HYPOTHESIS end template instructs agent to write hypotheses.yaml before calling end
  Evidence: phases.yaml HYPOTHESIS end template contains write instructions with {artifacts_dir}
- [ ] HYPOTHESIS compliance check: hypotheses.yaml exists, loads, has entries, all pass richness
  Evidence: _check_lifecycle_compliance loads hypotheses.yaml and runs richness validation
- [ ] `execution` field removed from ActionDef (no more agent/standalone distinction)
  Evidence: model.py ActionDef has no `execution` field
- [ ] stdout print "--- AUTO-ACTION (agent)" removed from _run_auto_actions
  Evidence: grep returns 0 matches

## Section 2: Missing Enforcement

- [ ] cmd_end checks acknowledged entries gained new notes during phase
  Evidence: code in cmd_end or _check_lifecycle_compliance counts notes before/after
- [ ] Phase end fails if acknowledged context has no new notes from this phase
  Test: acknowledged entry with 0 notes added during phase -> SystemExit
- [ ] Phase end passes if acknowledged context has new notes added
  Test: acknowledged entry with note added -> no error
- [ ] RESEARCH output validated: 4 required section headers present (case-insensitive)
  Evidence: code scans for "current state", "gap analysis", "file inventory", "risk assessment"
- [ ] RESEARCH output validated: >= 500 chars total length
  Evidence: code checks len(output) >= 500
- [ ] RESEARCH output validated: >= 3 file path references (contains / or .py or .yaml)
  Evidence: code counts path-like patterns
- [ ] RESEARCH output validated: each section has >= 50 chars of content
  Evidence: code measures content between headers
- [ ] RESEARCH phase end fails programmatically if ANY validation fails
  Test: output without "Gap Analysis" -> SystemExit
- [ ] RESEARCH validation error names the specific failing check
  Evidence: error message says "missing section: Gap Analysis" or "output too short: 120 chars < 500"
- [ ] Hypothesis richness: `hypothesis` field >= 20 chars per entry
  Evidence: code checks len(entry["hypothesis"]) >= 20
- [ ] Hypothesis richness: `prediction` field >= 10 chars AND contains number or comparison word
  Evidence: code checks length + regex for digits or from/to/increase/decrease/reduce
- [ ] Hypothesis richness: `evidence` field >= 10 chars (not empty, not "TBD")
  Evidence: code checks len + content
- [ ] Hypothesis richness: `stars` field is int 1-5
  Evidence: code validates type and range
- [ ] HYPOTHESIS phase end fails programmatically if ANY entry fails richness
  Test: hypothesis with prediction="" -> SystemExit with "prediction too short: 0 chars < 10"
- [ ] Richness error names the entry and failing field with actual vs minimum
  Evidence: error message format includes identifier, field name, actual length

## Section 3: Tests

- [ ] Test: readback subprocess not influenced by CLAUDE.md
- [ ] Test: output-file absolute path works without doubling
- [ ] Test: HYPOTHESIS gatekeeper/compliance check validates hypotheses.yaml
- [ ] Test: note-count enforcement blocks empty notes
- [ ] Test: note-count enforcement passes with notes
- [ ] Test: RESEARCH validation catches missing section header
- [ ] Test: RESEARCH validation catches output < 500 chars
- [ ] Test: RESEARCH validation catches < 3 file references
- [ ] Test: HYPOTHESIS richness catches short hypothesis (< 20 chars)
- [ ] Test: HYPOTHESIS richness catches empty prediction
- [ ] Test: HYPOTHESIS richness catches empty evidence
- [ ] Test: HYPOTHESIS richness passes with valid rich entries

---

## Fuzzy Scales

### Scale 1: Test Depth (0-10)

Current grade: [0] /10. Residual: [10]

Rubric: 10 = every enforcement rule has test covering happy path + rejection + edge case. 8 = main paths tested. 5 = gaps. 2 = minimal.
Why not programmatic: test coverage percentage doesn't capture whether the RIGHT things are tested.

---

## Iteration Log

| Iter | Score | Tests | Notes |
|------|-------|-------|-------|
| base | ~45   | 230   | path doubling, agent no-op, no note enforcement, no richness validation |
