# Benchmark: README Rewrite

## Score

**Direction**: MINIMIZE (target: 0)

```
score = unchecked_items + accuracy_residual + completeness_residual + clarity_residual + flow_residual
```

## Evaluation

**Programmatic checks**:
1. `make lint` clean
2. README.md exists and is non-empty

**Generative checks**:
3. For each [ ] item, verify against actual README.md content. Mark [x] with evidence
4. Grade all 4 fuzzy scales using rubrics below
5. EDIT this file, UPDATE Iteration Log, report score

---

## Section 1: Accuracy

- [x] Test count is 212 (not 115)
  Evidence: L153 "make test             # run 212 tests"
- [ ] Version referenced matches pyproject.toml (0.8.59)
  Note: version not explicitly mentioned in README, acceptable
- [x] Both plugins listed: auto-build-claw, devils-advocate
  Evidence: L30-33 plugins table with both entries
- [x] auto-build-claw has 3 skills: auto-build-claw, program-writer, benchmark-writer
  Evidence: L39 "Skills: auto-build-claw (orchestrator), program-writer, benchmark-writer"
- [x] devils-advocate has 4 skills: setup, evaluate, iterate, run
  Evidence: L74 "Skills: setup, evaluate, iterate, run"
- [x] Workflow types match workflow.yaml (full, gc, hotfix, fast, planning)
  Evidence: L43-49 workflow types table with all 5 types
- [x] Architecture shows both plugin directories
  Evidence: L113 auto-build-claw/ and L124 devils-advocate/ in architecture tree
- [x] Makefile targets listed are accurate
  Evidence: L151-158 matches actual Makefile targets (install, test, lint, format, build, publish)
- [ ] Every file path shown in README exists on disk
  FAIL: orchestrate.py (L116) and resources/*.yaml (L117-119) don't exist at auto-build-claw/skills/auto-build-claw/
- [ ] Every CLI command shown is a valid orchestrate subcommand or plugin slash command
  Partially verified, /plugin marketplace add command syntax assumed valid

## Section 2: Completeness

- [x] Header with badges (GitHub Actions, PyPI, downloads, Python, KOLOMOLO)
  Evidence: L3-7, all 5 badges present
- [x] Opening description explains YAML-driven orchestration engine concept
  Evidence: L11 "shared YAML-driven orchestration engine that pulls agents through structured phases"
- [x] First 3 paragraphs explain: what the project does, what problem it solves, how to start
  Evidence: L9 (problem), L11 (solution), L13-17 (TIP + NOTE for getting started)
- [x] Each plugin section leads with value proposition before technical details
  Evidence: L37 auto-build-claw leads with concept, L72 devils-advocate leads with concept
- [x] Problem statement section explaining what it solves
  Evidence: L19-26 "What it solves" with 6 concrete problems
- [x] Plugin overview table
  Evidence: L28-33 plugins table
- [x] auto-build-claw section with workflow types, features, usage examples
  Evidence: L35-68 with workflow table, usage code blocks
- [x] devils-advocate section with skills, risk scoring concept, artefacts, usage examples
  Evidence: L70-90 with skills, Fibonacci scoring, usage examples
- [x] Architecture section with directory structure showing both plugins
  Evidence: L104-130 architecture tree (paths need fixing in iter 2)
- [x] Installation section (pip + plugin marketplace)
  Evidence: L92-102 with both pip and marketplace commands
- [x] Usage examples for both plugins
  Evidence: L51-66 auto-build-claw, L80-88 devils-advocate
- [x] Development section with accurate Makefile targets
  Evidence: L149-158 with 212 test count
- [x] Building a new plugin section
  Evidence: L132-147
- [x] Links to plugin-specific READMEs for detailed documentation
  Evidence: L68 and L90 "See [auto/devils-advocate/README.md]..."

## Section 3: Quality

- [x] Modus primaris: flowing narrative, not bullet-only reference
  Evidence: opening paragraphs are narrative, plugin sections flow with prose before tables
- [x] GitHub alert callouts used appropriately (TIP, NOTE, IMPORTANT)
  Evidence: L13 TIP, L16 NOTE
- [x] No emojis
  Evidence: grep confirms no emoji characters
- [x] No em-dashes (use hyphens with spaces)
  Evidence: all dashes use " - " pattern
- [x] No arrow symbols in prose (use -> in code blocks only)
  Evidence: arrows only in workflow type table (code context)
- [x] Professional technical tone throughout
  Evidence: no marketing language, specific facts
- [x] README.md is under 250 lines
  Evidence: 162 lines (wc -l)

---

## Fuzzy Scales

### Scale 1: Accuracy (0-10)

Current grade: [7] /10. Residual: [3]

Rubric: 10 = every fact, number, path, and command verified correct. 8 = minor discrepancies that don't mislead. 5 = some wrong numbers or paths. 2 = significant factual errors.
Note: 4 file paths in architecture section don't exist on disk. Version not mentioned.

### Scale 2: Completeness (0-10)

Current grade: [9] /10. Residual: [1]

Rubric: 10 = all sections present, both plugins documented, usage examples work. 8 = one minor section thin. 5 = a plugin or major section missing. 2 = mostly incomplete.
Note: all 14 completeness items pass.

### Scale 3: Clarity (0-10)

Current grade: [9] /10. Residual: [1]

Rubric: 10 = a developer can understand the project's purpose, install it, and start using it from the README alone. 8 = clear with minor ambiguity. 5 = requires consulting other files to understand. 2 = confusing or misleading.
Note: clear value proposition, both plugins well-explained, install instructions work.

### Scale 4: Flow (0-10)

Current grade: [9] /10. Residual: [1]

Rubric: 10 = information ordered by reader priority (problem -> solution -> usage -> architecture -> development), natural reading progression. 8 = good flow with one awkward transition. 5 = sections feel disconnected. 2 = random ordering.
Note: natural progression from problem to solution to plugins to install to architecture to development.

---

## Iteration Log

| Iter | Score | Notes |
|------|-------|-------|
| base | ~71   | outdated README, wrong test count, missing devils-advocate, no value-first framing |
| 1    | 9     | 3 unchecked (paths, version, commands) + 6 residual. 162 lines. Both plugins documented. |
