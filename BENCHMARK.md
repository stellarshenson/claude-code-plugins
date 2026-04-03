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

- [ ] Test count is 212 (not 115)
- [ ] Version referenced matches pyproject.toml (0.8.59)
- [ ] Both plugins listed: auto-build-claw, devils-advocate
- [ ] auto-build-claw has 3 skills: auto-build-claw, program-writer, benchmark-writer
- [ ] devils-advocate has 4 skills: setup, evaluate, iterate, run
- [ ] Workflow types match workflow.yaml (full, gc, hotfix, fast, planning)
- [ ] Architecture shows both plugin directories
- [ ] Makefile targets listed are accurate
- [ ] Every file path shown in README exists on disk
- [ ] Every CLI command shown is a valid orchestrate subcommand or plugin slash command

## Section 2: Completeness

- [ ] Header with badges (GitHub Actions, PyPI, downloads, Python, KOLOMOLO)
- [ ] Opening description explains YAML-driven orchestration engine concept
- [ ] First 3 paragraphs explain: what the project does, what problem it solves, how to start
- [ ] Each plugin section leads with value proposition before technical details
- [ ] Problem statement section explaining what it solves
- [ ] Plugin overview table
- [ ] auto-build-claw section with workflow types, features, usage examples
- [ ] devils-advocate section with skills, risk scoring concept, artefacts, usage examples
- [ ] Architecture section with directory structure showing both plugins
- [ ] Installation section (pip + plugin marketplace)
- [ ] Usage examples for both plugins
- [ ] Development section with accurate Makefile targets
- [ ] Building a new plugin section
- [ ] Links to plugin-specific READMEs for detailed documentation

## Section 3: Quality

- [ ] Modus primaris: flowing narrative, not bullet-only reference
- [ ] GitHub alert callouts used appropriately (TIP, NOTE, IMPORTANT)
- [ ] No emojis
- [ ] No em-dashes (use hyphens with spaces)
- [ ] No arrow symbols in prose (use -> in code blocks only)
- [ ] Professional technical tone throughout
- [ ] README.md is under 250 lines

---

## Fuzzy Scales

### Scale 1: Accuracy (0-10)

Current grade: [0] /10. Residual: [10]

Rubric: 10 = every fact, number, path, and command verified correct. 8 = minor discrepancies that don't mislead. 5 = some wrong numbers or paths. 2 = significant factual errors.

### Scale 2: Completeness (0-10)

Current grade: [0] /10. Residual: [10]

Rubric: 10 = all sections present, both plugins documented, usage examples work. 8 = one minor section thin. 5 = a plugin or major section missing. 2 = mostly incomplete.

### Scale 3: Clarity (0-10)

Current grade: [0] /10. Residual: [10]

Rubric: 10 = a developer can understand the project's purpose, install it, and start using it from the README alone. 8 = clear with minor ambiguity. 5 = requires consulting other files to understand. 2 = confusing or misleading.

### Scale 4: Flow (0-10)

Current grade: [0] /10. Residual: [10]

Rubric: 10 = information ordered by reader priority (problem -> solution -> usage -> architecture -> development), natural reading progression. 8 = good flow with one awkward transition. 5 = sections feel disconnected. 2 = random ordering.

---

## Iteration Log

| Iter | Score | Notes |
|------|-------|-------|
| base | ~71   | outdated README, wrong test count, missing devils-advocate, no value-first framing |
